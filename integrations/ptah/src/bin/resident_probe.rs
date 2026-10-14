use native_process::{
    ControlScope, DisconnectPolicy, NativeProcessProvider, NativeProcessProviderConfig,
    ProcessMode, ProcessSpec, TerminalSize,
};
use ptah_identifiers::EntityRef;
use ptah_provider_api::{
    ProviderGeneration, ProviderHealth, ProviderInstance, ProviderKind, ProviderReachability,
    ProviderReadiness, ProviderRevision,
};
use serde_json::json;
use std::{
    collections::BTreeMap,
    error::Error,
    fs,
    path::PathBuf,
    sync::Arc,
    thread,
    time::{Duration, Instant},
};
const NOW: &str = "2026-10-14T10:00:00Z";
type Res<T> = Result<T, Box<dyn Error>>;
fn reference(kind: &str) -> EntityRef {
    EntityRef::new(kind).expect("valid ref")
}
fn clock() -> Arc<dyn Fn() -> String + Send + Sync> {
    Arc::new(|| NOW.to_string())
}
fn provider() -> Res<NativeProcessProvider> {
    let revision_ref = reference("runtime.provider_revision");
    Ok(NativeProcessProvider::new(NativeProcessProviderConfig {
        revision: ProviderRevision {
            revision_ref: revision_ref.clone(),
            provider_ref: reference("runtime.provider"),
            provider_kind: ProviderKind::Process,
            implementation_name: "native-process".into(),
            implementation_version: "0.0.0-phase0c".into(),
            build_or_package_digest: "sha256:development-resident-process-proof-not-production"
                .into(),
            configuration_digest: "sha256:creative-resident-development".into(),
            supported_facility_refs: vec![reference("runtime.facility")],
            capability_claim_refs: vec![reference("runtime.capability_claim")],
            dependency_refs: vec![],
            node_requirements: vec![],
            security_requirements: vec![],
            known_limitations: vec!["not enrolled production Node".into()],
        },
        instance: ProviderInstance {
            instance_ref: reference("runtime.provider_instance"),
            provider_revision_ref: revision_ref,
            node_ref: reference("core.node"),
            node_generation: 1,
            provider_generation: ProviderGeneration::new(1)?,
            connection_epoch: 1,
            reachability: ProviderReachability::Reachable,
            readiness: ProviderReadiness::Ready,
            health: ProviderHealth::Healthy,
            endpoint_aliases: vec![],
            process_or_service_refs: vec![],
            observation_refs: vec![reference("proof.evidence")],
            started_at: NOW.into(),
            limitations: vec![],
        },
        clock: clock(),
    })?)
}
fn await_marker(
    provider: &NativeProcessProvider,
    id: ptah_identifiers::EntityId,
    marker: &str,
    timeout: Duration,
) -> Res<()> {
    let until = Instant::now() + timeout;
    loop {
        let snapshot = provider.snapshot(id)?;
        let tail = snapshot.terminal.as_ref().ok_or("no PTY stream")?;
        let observed = String::from_utf8_lossy(&tail.bytes);
        if observed.contains(marker) {
            return Ok(());
        }
        if snapshot.record.exit.is_some() {
            return Err(format!("resident exited before {marker}: {}", observed).into());
        }
        if Instant::now() >= until {
            return Err(format!("resident timed out waiting for {marker}: {}", observed).into());
        }
        thread::sleep(Duration::from_millis(40));
    }
}
fn main() -> Res<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 3 {
        return Err(
            "usage: resident_probe <workspace run-root> <requestA.json> <requestB.json>".into(),
        );
    }
    let workspace = PathBuf::from(&args[0]).canonicalize()?;
    let reqs = [
        PathBuf::from(&args[1]).canonicalize()?,
        PathBuf::from(&args[2]).canonicalize()?,
    ];
    let studio = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|x| x.parent())
        .ok_or("no studio")?
        .to_path_buf();
    let allowed = studio.join(".workspace").canonicalize()?;
    if !workspace.starts_with(&allowed) || reqs.iter().any(|p| !p.starts_with(&allowed)) {
        return Err("paths outside workspace".into());
    }
    let run_root = workspace.join("resident-jobs");
    if run_root.exists() {
        return Err("resident run root must be fresh".into());
    }
    fs::create_dir(&run_root)?;
    let provider = provider()?;
    let script = studio.join("integrations/ptah/resident_worker.py");
    let id = provider.spawn(ProcessSpec {
        program: std::env::var("TTG_CREATIVE_PYTHON").unwrap_or_else(|_| "/usr/bin/python3".into()),
        args: vec![
            "-B".into(),
            script.display().to_string(),
            "--run-root".into(),
            run_root.display().to_string(),
        ],
        env: BTreeMap::new(),
        clear_env: false,
        cwd: Some(studio.display().to_string()),
        mode: ProcessMode::Pty {
            size: TerminalSize::default(),
        },
        max_stream_bytes: 131072,
        disconnect_policy: DisconnectPolicy::Retain,
    })?;
    let owner = reference("identity.principal");
    let lease = provider.acquire_control(
        id,
        owner,
        vec![ControlScope::Input, ControlScope::Terminate],
    )?;
    let test_result = (|| -> Res<()> {
        await_marker(&provider, id, "TTG_RESIDENT_EVENT", Duration::from_secs(10))?;
        let mut receipts = Vec::new();
        for (index, req) in reqs.iter().enumerate() {
            let raw: serde_json::Value = serde_json::from_slice(&fs::read(req)?)?;
            let request_id = raw["request_id"].as_str().ok_or("request id missing")?;
            let command =
                json!({"command":"run","request":req.display().to_string()}).to_string() + "\n";
            provider.write_input(id, &lease, command.as_bytes())?;
            let expected = run_root
                .join(request_id)
                .join("independent_verification.json");
            let deadline = Instant::now() + Duration::from_secs(42);
            loop {
                if expected.is_file() {
                    break;
                }
                if provider.poll_exit(id)?.is_some() {
                    return Err("resident died before job completion".into());
                }
                if Instant::now() > deadline {
                    return Err(format!("resident timeout on job {index}").into());
                }
                thread::sleep(Duration::from_millis(45));
            }
            let result: serde_json::Value = serde_json::from_slice(&fs::read(&expected)?)?;
            if result["passed"] != true {
                return Err("independent verifier reported failure".into());
            }
            let evidence = run_root.join(request_id).join("editable.ttgstudio.json");
            if !evidence.is_file() {
                return Err("editable project missing".into());
            }
            let snapshot = provider.snapshot(id)?;
            if snapshot.record.exit.is_some() {
                return Err("service not resident after job".into());
            }
            receipts.push(json!({"request_id":request_id,"verified":true,"project_bytes":fs::metadata(evidence)?.len(),"service_alive":true}));
            println!("PTAH_RESIDENT_JOB_PASS {index} {}", request_id);
        }
        // Duplicating a completed request must be rejected by the same live worker.
        let duplicate =
            json!({"command":"run","request":reqs[0].display().to_string()}).to_string() + "\n";
        provider.write_input(id, &lease, duplicate.as_bytes())?;
        await_marker(
            &provider,
            id,
            "duplicate resident job refused",
            Duration::from_secs(8),
        )?;
        println!("PTAH_RESIDENT_DUPLICATE_REJECTED");
        provider.write_input(id, &lease, b"{\"command\":\"shutdown\"}\n")?;
        let exit = provider.wait_for_exit(id, Duration::from_secs(10))?;
        if !exit.success {
            return Err("resident shutdown exit was not successful".into());
        }
        let observed = provider
            .snapshot(id)?
            .terminal
            .ok_or("terminal evidence missing")?;
        let output = String::from_utf8_lossy(&observed.bytes);
        if !output.contains("\"event\": \"stopped\"") {
            return Err("shutdown receipt not observed".into());
        }
        provider.advance_provider_generation()?;
        if provider
            .write_input(id, &lease, b"{\"command\":\"shutdown\"}\n")
            .is_ok()
        {
            return Err("stale terminal lease accepted after generation advance".into());
        }
        let result = json!({"schema":"ttg.creative.ptah.resident_probe.v1","status":"PASS","node_enrollment":"not_proven","control_lease":"development_a05_pty_control_only","jobs":receipts,"shutdown_observed":true,"stale_provider_generation_rejected":true,"duplicate_resident_request_rejected":true});
        fs::write(
            workspace.join("resident_proof.json"),
            serde_json::to_vec_pretty(&result)?,
        )?;
        println!(
            "PTAH_RESIDENT_PROOF_PASS {}",
            serde_json::to_string(&result)?
        );
        Ok(())
    })();
    if test_result.is_err() {
        // Scope-bound cleanup, never leave a potentially unqualified resident worker.
        let _ = provider.terminate(id, &lease);
    }
    test_result
}

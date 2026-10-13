use std::{collections::BTreeMap, error::Error, fs, path::PathBuf, sync::Arc, time::Duration};
use ptah_activity_runtime::{
    ActivityRuntime, ActivitySpec, AttemptContext, IdempotencyClass, LedgerJournal,
    OperationSpec, RetryClass, SideEffectClass,
};
use ptah_identifiers::{EntityId, EntityRef};
use ptah_object_store::{
    ArtifactPromotionSpec, ObjectStore, ObjectStoreConfig, OriginClass,
    ProductionEvidence, RegisterObjectSpec, RevisionRole, VerificationSpec,
};
use ptah_receipts::{
    AuthorityClass, ProofLevel, ReceiptContext, ReceiptKind, ReceiptOutcome, ReceiptSpec,
};
use ptah_provider_api::{
    ProviderGeneration, ProviderHealth, ProviderInstance, ProviderKind, ProviderReachability,
    ProviderReadiness, ProviderRevision,
};
use ptah_workspace::{CreateWorkspace, WorkspaceStore};
use native_process::{DisconnectPolicy, NativeProcessProvider, NativeProcessProviderConfig, ProcessMode, ProcessSpec};
use serde_json::json;

const NOW: &str = "2026-10-13T13:40:00Z";
type Res<T> = Result<T, Box<dyn Error>>;
fn reference(kind: &str) -> EntityRef { EntityRef::new(kind).expect("valid Ptah namespaced reference") }
fn clock() -> Arc<dyn Fn() -> String + Send + Sync> { Arc::new(|| NOW.to_string()) }

fn provider() -> Res<NativeProcessProvider> {
    let revision_ref = reference("runtime.provider_revision");
    Ok(NativeProcessProvider::new(NativeProcessProviderConfig {
        revision: ProviderRevision {
            revision_ref: revision_ref.clone(),
            provider_ref: reference("runtime.provider"),
            provider_kind: ProviderKind::Process,
            implementation_name: "native-process".to_owned(),
            implementation_version: "0.0.0-phase0c".to_owned(),
            build_or_package_digest: "sha256:ptah-direct-embedded-demo-not-production-admission".to_owned(),
            configuration_digest: "sha256:ttg-creative-direct-workload".to_owned(),
            supported_facility_refs: vec![reference("runtime.facility")],
            capability_claim_refs: vec![reference("runtime.capability_claim")],
            dependency_refs: Vec::new(), node_requirements: Vec::new(),
            security_requirements: Vec::new(),
            known_limitations: vec!["Embedded local proof: not an enrolled production Node".to_owned()],
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
            endpoint_aliases: Vec::new(), process_or_service_refs: Vec::new(),
            observation_refs: vec![reference("proof.evidence")],
            started_at: NOW.to_owned(), limitations: Vec::new(),
        },
        clock: clock(),
    })?)
}

fn begin(
    runtime: &ActivityRuntime,
    workspace: &EntityRef,
    authority: &EntityRef,
    provider: &NativeProcessProvider,
    name: &str,
    target: EntityRef,
) -> Res<(EntityId, EntityId, EntityId, AttemptContext)> {
    let activity = runtime.create_activity(ActivitySpec {
        request_ref: reference("core.request"), workspace_ref: workspace.clone(),
        caller_ref: authority.clone(), authority_ref: authority.clone(),
        activity_kind: "creative.direct_proof".to_owned(), intent_ref: reference("knowledge.intent"),
        priority: 0, max_attempts: 1,
    })?;
    assert_eq!(runtime.admit_next()?, Some(activity));
    let operation = runtime.create_operation(activity, OperationSpec {
        operation_kind: name.to_owned(), logical_target_refs: vec![target],
        command_or_action_ref: reference("core.command"),
        side_effect_class: SideEffectClass::IdempotentMutation,
        retry_class: RetryClass::RetrySafe,
        idempotency_class: IdempotencyClass::NoneRequired, idempotency_key: None,
        required_authority_refs: vec![authority.clone()], precondition_refs: Vec::new(),
        desired_proof_refs: vec![reference("proof.claim")], compensating_operation_ref: None,
    })?;
    runtime.make_operation_ready(operation)?;
    let context = provider.attempt_context(1, reference("runtime.facility"))?;
    let attempt = runtime.create_attempt(operation, context.clone())?;
    runtime.dispatch_attempt(attempt)?;
    runtime.accept_attempt(attempt)?;
    runtime.begin_attempt_execution(attempt)?;
    Ok((activity, operation, attempt, context))
}
fn emit_receipt(
    runtime: &ActivityRuntime,
    ids: (EntityId, EntityId, EntityId),
    context: &AttemptContext,
    kind: ReceiptKind,
    levels: Vec<ProofLevel>,
    summary: &str,
) -> Res<EntityId> {
    let (activity, operation, attempt) = ids;
    let nonce = runtime.attempt(attempt)?.ok_or("missing Attempt")?
        .correlation_nonce().to_owned();
    let result = runtime.append_receipt(ReceiptSpec {
        kind, outcome: ReceiptOutcome::Positive,
        authority_class: AuthorityClass::FacilityRuntime,
        context: ReceiptContext {
            activity_ref: EntityRef::from_id(activity, "core.activity")?,
            operation_ref: EntityRef::from_id(operation, "core.operation")?,
            attempt_ref: EntityRef::from_id(attempt, "core.attempt")?,
            idempotency_key: None, correlation_nonce: nonce,
            node_ref: context.node_ref.clone(), node_generation: context.node_generation,
            provider_ref: context.provider_ref.clone(),
            provider_generation: context.provider_generation,
            workload_generation: context.workload_generation,
            connection_epoch: context.connection_epoch,
            facility_ref: context.facility_ref.clone(),
            producer_instance_ref: context.producer_instance_ref.clone(),
            producer_version: context.producer_version.clone(),
        },
        producer_identity_evidence_refs: vec![reference("proof.evidence")],
        proof_claim_refs: vec![reference("proof.claim")],
        proof_levels: levels,
        previous_or_superseded_receipt_refs: Vec::new(),
        summary: summary.to_string(), limitations: Vec::new(),
        occurred_at: NOW.to_owned(),
    })?;
    Ok(result)
}
fn production(ids: (EntityId, EntityId, EntityId), receipts: &[EntityId]) -> Res<ProductionEvidence> {
    Ok(ProductionEvidence {
        activity_ref: EntityRef::from_id(ids.0, "core.activity")?,
        operation_ref: EntityRef::from_id(ids.1, "core.operation")?,
        attempt_ref: EntityRef::from_id(ids.2, "core.attempt")?,
        receipt_refs: receipts.iter().map(|id| EntityRef::from_id(*id,"proof.receipt"))
            .collect::<Result<Vec<_>,_>>()?,
    })
}
fn finish(runtime: &ActivityRuntime, ids: (EntityId,EntityId,EntityId), completion: EntityId, result: EntityRef) -> Res<()> {
    runtime.complete_attempt(ids.2,completion)?;
    runtime.prove_operation_succeeded(ids.1, completion, vec![result.clone()])?;
    runtime.complete_activity(ids.0,vec![result])?;
    Ok(())
}
fn execute_python(provider: &NativeProcessProvider, script: PathBuf, studio: &PathBuf, req: &PathBuf, output: &PathBuf, label: &str) -> Res<String> {
    let spec=ProcessSpec {
        program: "/usr/bin/python3".into(),
        args: vec!["-B".into(),script.to_string_lossy().into_owned(),
            "--request".into(),req.to_string_lossy().into_owned(),
            "--output".into(),output.to_string_lossy().into_owned()],
        env: BTreeMap::new(),clear_env:false,
        cwd: Some(studio.to_string_lossy().into_owned()),
        mode: ProcessMode::Pipes,max_stream_bytes:65536,
        disconnect_policy:DisconnectPolicy::Retain,
    };
    let id=provider.spawn(spec)?;
    let exit=provider.wait_for_exit(id,Duration::from_secs(25))?;
    let snapshot=provider.snapshot(id)?;
    let stdout=snapshot.stdout.as_ref().map(|x|String::from_utf8_lossy(&x.bytes).into_owned()).unwrap_or_default();
    let stderr=snapshot.stderr.as_ref().map(|x|String::from_utf8_lossy(&x.bytes).into_owned()).unwrap_or_default();
    if !exit.success { return Err(format!("{label} failed: {exit:?}; stderr={stderr} stdout={stdout}").into()); }
    println!("PTAH_A05_{label}_SUCCESS {}",stdout.trim());
    Ok(stdout)
}
fn resume_verified(
    proof:&PathBuf, ledger:&PathBuf, cas:&PathBuf, output:&PathBuf,
    request_hash:&str, request_id:&str, job:&serde_json::Value
) -> Res<()> {
    let prior:serde_json::Value=serde_json::from_slice(&fs::read(proof)?)?;
    if prior["request_sha256"]!=request_hash || prior["request_id"]!=request_id ||
       prior["result"]!="PASS_DIRECT_EMBEDDED_PTAH_A04_A05_A06_A07" {
        return Err("previous result does not match requested operation".into());
    }
    // Reconciliation must also fence changes to the original ad input assets.
    if let Some(sources)=prior.get("source_hashes").and_then(|v|v.as_object()) {
        for (path, digest) in sources {
            let bytes=fs::read(path)?;
            if ObjectStore::sha256(&bytes)!=digest.as_str().ok_or("input hash malformed")? {
                return Err(format!("input asset has changed since proof: {path}").into());
            }
        }
    }
    if job["operation"]=="ad_from_assets" {
        let path=std::path::Path::new(job["asset_dir"].as_str().ok_or("missing input directory")?);
        let prior_names=prior["source_hashes"].as_object().ok_or("missing prior source inventory")?;
        let mut current=Vec::new();
        for entry in fs::read_dir(path)? {
            let entry=entry?;
            let file=entry.path();
            let ext=file.extension().and_then(|x|x.to_str()).unwrap_or("").to_ascii_lowercase();
            if ["png","jpg","jpeg","webp"].contains(&ext.as_str()) {
                if entry.file_type()?.is_symlink() || !file.is_file() {
                    return Err("source folder contains unsupported image entry".into());
                }
                current.push(file.display().to_string());
            }
        }
        current.sort();
        let mut expected:Vec<String>=prior_names.keys().cloned().collect();
        expected.sort();
        if current!=expected {return Err("source image inventory changed".into());}
    }
    let files=prior["artifacts"].as_array().ok_or("missing artifact list")?;
    if files.len()!=3 {return Err("wrong artifact count".into());}
    for file in files {
        let name=file["name"].as_str().ok_or("missing artifact name")?;
        if !["editable.ttgstudio.json","preview.jpg","preview.png","project_bundle.zip"].contains(&name) {
            return Err("unexpected artifact filename".into());
        }
        let digest=file["sha256"].as_str().ok_or("missing digest")?;
        if digest.len()!=64 || !digest.bytes().all(|b|b.is_ascii_hexdigit()) {
            return Err("invalid artifact digest".into());
        }
        let original=fs::read(output.join(name))?;
        let stored=fs::read(cas.join("sha256").join(&digest[..2]).join(digest))?;
        if original!=stored || ObjectStore::sha256(&stored)!=digest {
            return Err(format!("resume content verification failed for {name}").into());
        }
    }
    let ws:EntityId=prior["workspace_id"].as_str().ok_or("workspace missing")?.parse()?;
    WorkspaceStore::open(ledger,clock())?.workspace(ws)?;
    println!("PTAH_RESUME_REUSED_VERIFIED {}",serde_json::to_string(&prior)?);
    Ok(())
}

fn main() -> Res<()> {
    let studio=PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent()
        .and_then(|v|v.parent()).ok_or("Studio root missing")?.to_path_buf();
    let argv:Vec<String>=std::env::args().skip(1).collect();
    if argv==["--describe"] {
        print!("{}",fs::read_to_string(studio.join("integrations/ptah/studio_tool.json"))?);
        return Ok(());
    }
    if argv.len()<4 || argv[0]!="--request" || argv[2]!="--run-dir" {
        return Err("expected --request <json> --run-dir <path> [--resume]".into());
    }
    let resume=argv.len()==5 && argv[4]=="--resume";
    if argv.len()!=4 && !resume {return Err("unsupported arguments".into());}
    let req=PathBuf::from(&argv[1]).canonicalize()?;
    let workspace_dir=studio.join(".workspace").canonicalize()?;
    if !req.starts_with(&workspace_dir) {return Err("request outside Studio workspace".into());}
    let request_bytes=fs::read(&req)?;
    let request_hash=ObjectStore::sha256(&request_bytes);
    let job:serde_json::Value=serde_json::from_slice(&request_bytes)?;
    if job["schema"]!="ttg.creative.ptah.request.v1" {return Err("wrong request schema".into());}
    if !["scene_edit","ad_from_assets"].contains(&job["operation"].as_str().unwrap_or("")) {
        return Err("unsupported operation".into());
    }
    let request_id=job["request_id"].as_str().ok_or("request_id missing")?;
    if request_id.len()<3 || request_id.len()>80 ||
       !request_id.bytes().all(|b| b.is_ascii_alphanumeric()||b==b'-'||b==b'_') {
        return Err("unsafe request_id".into());
    }
    let scratch=PathBuf::from(&argv[3]);
    let ancestor=if scratch.exists() {scratch.canonicalize()?}
        else {scratch.parent().ok_or("run-dir parent missing")?.canonicalize()?};
    if !ancestor.starts_with(&workspace_dir) {return Err("run-dir outside Studio workspace".into());}
    let output=scratch.join("output");
    let ledger=scratch.join("ptah-ledger.sqlite3");
    let cas=scratch.join("ptah-cas");
    let proof=scratch.join("ptah_proof_manifest.json");
    if resume {
        return resume_verified(&proof,&ledger,&cas,&output,&request_hash,request_id,&job);
    }
    if ledger.exists() || proof.exists() || (output.exists() && output.read_dir()?.next().is_some()) {
        return Err("existing/incomplete run: reconciliation required, no implicit retry".into());
    }
    fs::create_dir_all(&output)?;
    let principal=reference("identity.principal");
    let mut workspaces=WorkspaceStore::open(&ledger,clock())?;
    let workspace=workspaces.create_workspace(CreateWorkspace {
        workspace_key:format!("creative-{}",request_id),
        title:"Creative Studio Ptah direct embedded proof".to_owned(),
        description:Some("isolated read-only-donor proof".to_owned()),
        owner_ref:principal.clone(),authority_ref:principal.clone(),created_by_ref:principal.clone(),
        policy_refs:Vec::new(),
    })?;
    let process_provider=provider()?;
    let runtime=ActivityRuntime::new(8,Arc::new(LedgerJournal::open(&ledger)?),clock())?;
    let ids0=begin(&runtime,&workspace.workspace_ref,&principal,&process_provider,
        "creative.edit_and_render",reference("object.object"))?;
    // A05 performs actual headless Creative Studio editing as an OS process.
    // Worker argv must be [studio,output]; helper passes [output,studio], so explicit process spec here.
    let process=process_provider.spawn(ProcessSpec{
        program:"/usr/bin/python3".into(),
        args:vec!["-B".into(),studio.join("integrations/ptah/creative_worker.py").display().to_string(),
                  "--request".to_string(),req.display().to_string(),
                  "--output".to_string(), output.display().to_string()],
        env:BTreeMap::new(),clear_env:false,cwd:Some(studio.display().to_string()),
        mode:ProcessMode::Pipes,max_stream_bytes:65536,disconnect_policy:DisconnectPolicy::Retain,
    })?;
    let exit=process_provider.wait_for_exit(process,Duration::from_secs(30))?;
    let snap=process_provider.snapshot(process)?;
    let worker_out=snap.stdout.as_ref().map(|x|String::from_utf8_lossy(&x.bytes).into_owned()).unwrap_or_default();
    let worker_err=snap.stderr.as_ref().map(|x|String::from_utf8_lossy(&x.bytes).into_owned()).unwrap_or_default();
    if !exit.success { return Err(format!("Creative Studio A05 exit failure: {worker_err} {worker_out}").into()); }
    println!("PTAH_A05_CREATIVE_SUCCEEDED {}",worker_out.trim());
    // Real second A05 process verifies actual saved bytes and saved-project replay.
    let _verification=execute_python(&process_provider,studio.join("integrations/ptah/verify_output.py"),&studio,&req,&output,"INDEPENDENT_VERIFIER")?;
    let verified:serde_json::Value=serde_json::from_slice(&fs::read(output.join("independent_verification.json"))?)?;
    if verified["passed"]!=true {return Err("independent visual/project verification was not true".into());}
    let output_receipt=emit_receipt(&runtime,(ids0.0,ids0.1,ids0.2),&ids0.3,
        ReceiptKind::OutputObservation,vec![ProofLevel::OutputCreated,ProofLevel::OperationCompleted],
        "Creative Studio editable project and PNG observed after successful A05 process exit")?;
    let hash_receipt=emit_receipt(&runtime,(ids0.0,ids0.1,ids0.2),&ids0.3,
        ReceiptKind::HashVerification,vec![ProofLevel::OutputHashVerified],
        "separate A05 verification process proved on-disk project and rendered image and portable bundle hashes")?;
    let registration_prod=production((ids0.0,ids0.1,ids0.2),&[output_receipt,hash_receipt])?;
    let mut store=ObjectStore::open(&ledger,&cas,ObjectStoreConfig {
        backend_ref:reference("storage.backend"),
        connection_ref:reference("storage.connection"),
        producer_ref:reference("runtime.provider_instance"),
        producer_version:"0.0.0-phase0c".to_owned()
    },clock())?;
    let mut registered=Vec::new();
    let files=verified["registered_files"].as_array().ok_or("no registered file set")?;
    if files.len()!=3 {return Err("exactly three outputs required".into());}
    for entry in files {
        let name=entry.as_str().ok_or("invalid output name")?;
        if !["editable.ttgstudio.json","preview.png","preview.jpg","project_bundle.zip"].contains(&name) {
            return Err("unrecognized Creative Studio output".into());
        }
        let typ=if name.ends_with(".json") {"creative_project"}
            else if name.ends_with(".zip") {"creative_bundle"} else {"creative_preview"};
        let bytes=fs::read(output.join(name))?;
        let hash=ObjectStore::sha256(&bytes);
        if verified["sha256"][name].as_str()!=Some(hash.as_str()) {
            return Err(format!("verified digest changed before Ptah CAS registration: {name}").into());
        }
        let reg=store.register_bytes(&bytes,RegisterObjectSpec {
            workspace_ref:workspace.workspace_ref.clone(),authority_ref:principal.clone(),
            object_class:typ.into(),declared_name:Some(name.into()),
            source_refs:vec![reference("proof.evidence")],revision_role:RevisionRole::Generated,
            origin_class:OriginClass::Generated,created_reason:"Ptah A05 direct creative workflow".into(),
            production:registration_prod.clone(),expected_sha256:Some(hash),
        })?;
        println!("PTAH_A07_REGISTERED {name} digest={} revision={}",reg.sha256,reg.revision_ref.entity_id);
        registered.push((name.to_string(),reg));
    }
    finish(&runtime,(ids0.0,ids0.1,ids0.2),output_receipt,registered[0].1.object_ref.clone())?;
    let mut artifacts=Vec::new();
    for (name, reg) in &registered {
        let v=begin(&runtime,&workspace.workspace_ref,&principal,&process_provider,
            "creative.verify_cas",reg.location_ref.clone())?;
        let readback=emit_receipt(&runtime,(v.0,v.1,v.2),&v.3,ReceiptKind::Readback,
            vec![ProofLevel::OutputReadBack,ProofLevel::OperationCompleted],
            "Ptah A07 independently re-read CAS content and verified exact digest")?;
        let proof=production((v.0,v.1,v.2),&[readback])?;
        let result=store.verify_location(reg.location_ref.entity_id,VerificationSpec {
            workspace_ref:workspace.workspace_ref.clone(),authority_ref:principal.clone(),
            production:proof,
        })?;
        if result.outcome!="verified" {return Err(format!("A07 verification not passed: {}",result.outcome).into());}
        finish(&runtime,(v.0,v.1,v.2),readback,result.verification_ref.clone())?;
        let x=begin(&runtime,&workspace.workspace_ref,&principal,&process_provider,
            "creative.promote_artifact",reg.revision_ref.clone())?;
        let promotion_receipt=emit_receipt(&runtime,(x.0,x.1,x.2),&x.3,
            ReceiptKind::OutputObservation,vec![ProofLevel::OutputCreated,ProofLevel::OperationCompleted],
            "A07 explicit artifact promotion requires separately evidenced operation")?;
        let artifact=store.promote_artifact(reg.revision_ref.entity_id,ArtifactPromotionSpec{
            workspace_ref:workspace.workspace_ref.clone(),authority_ref:principal.clone(),
            artifact_type:"creative_proof".into(),artifact_version:"1.0.0".into(),
            purpose:format!("direct Studio Ptah proof {name}"),subject_refs:Vec::new(),
            production:production((x.0,x.1,x.2),&[promotion_receipt])?,
        })?;
        finish(&runtime,(x.0,x.1,x.2),promotion_receipt,artifact.clone())?;
        artifacts.push(json!({"name":name,"artifact_id":artifact.entity_id.to_string(),
            "object_id":reg.object_ref.entity_id.to_string(),
            "revision_id":reg.revision_ref.entity_id.to_string(),
            "location_id":reg.location_ref.entity_id.to_string(),
            "sha256":reg.sha256,"readback":result.outcome}));
        println!("PTAH_A07_ARTIFACT_VERIFIED {name} ref={}",artifact.entity_id);
    }
    // Verify the durable ledger's workspace still exists on independent reopen.
    drop(store);drop(workspaces);
    let reopened=WorkspaceStore::open(&ledger,clock())?.workspace(workspace.workspace_ref.entity_id)?;
    if reopened.workspace_key!=format!("creative-{}",request_id) {return Err("Workspace failed durable readback".into());}
    let manifest=json!({
        "result":"PASS_DIRECT_EMBEDDED_PTAH_A04_A05_A06_A07",
        "ptah_mode":"embedded API, not resident control/node service",
        "project":"TTG Creative Studio","hunter_used":false,
        "limitations":["No production-enrolled Node identity","No general public Ptah dispatch API exposed by this integration","Not a visual-quality model check"],
        "workspace_id":workspace.workspace_ref.entity_id.to_string(),
        "activity_id":ids0.0.to_string(),"operation_id":ids0.1.to_string(),
        "attempt_id":ids0.2.to_string(),
        "process_id":process.to_string(),
        "artifact_count":artifacts.len(),"artifacts":artifacts,
        "request_sha256":request_hash,"request_id":request_id,"operation":job["operation"],
        "source_hashes":serde_json::from_slice::<serde_json::Value>(&fs::read(output.join("worker_result.json"))?)?["source_hashes"],
        "verified":verified,
        "ledger":ledger.display().to_string(),
        "cas_root":cas.display().to_string(),
    });
    fs::write(scratch.join("ptah_proof_manifest.json"),serde_json::to_vec_pretty(&manifest)?)?;
    println!("PTAH_DIRECT_E2E_PASS {}",serde_json::to_string(&manifest)?);
    Ok(())
}

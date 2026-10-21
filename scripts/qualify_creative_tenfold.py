#!/usr/bin/env python3
"""Real Tenfold Gen1 read-only engineering acceptance for TTG Creative Studio.

The ordinary image/render operation remains Creative Studio-owned. This runs
actual Tenfold Foreman, ResourceScheduler, LocalWorkforce and isolated workers
for the approved complex engineering-qualification campaign only. There is no
shadow implementation, repository mutation or claim of Sergeant approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True,
                          timeout=15, check=True).stdout.strip()


def qualify(studio: Path, tenfold: Path, qt_deps: Path | None = None) -> dict:
    studio = studio.resolve(strict=True)
    tenfold = tenfold.resolve(strict=True)
    if not (tenfold / "src/tenfold/workers.py").is_file():
        raise ValueError("Expected real Tenfold source checkout, not a mock or local copy")
    if git(studio, "status", "--porcelain"):
        raise ValueError("Creative Studio qualification requires a clean committed source head")
    head=git(studio,"rev-parse","HEAD")
    ten_head=git(tenfold,"rev-parse","HEAD")
    # Actual qualified Tenfold package; never reimplement its worker/Foreman.
    sys.path.insert(0, str(tenfold / "src"))
    from tenfold.contracts import (
        AssuranceBinding,CampaignManifest,CampaignNode,Milestone,NodeState,
        TaskPacket,canonical_digest)
    from tenfold.foreman import Foreman
    from tenfold.scheduler import ResourceCapacity,ResourceScheduler,WorkItem
    from tenfold.workers import (
        ExecutionMode,JobKind,LocalWorkerRuntime,ResourceRequest,
        WorkerJob,WorkerSpec,WorkerError)
    from tenfold.workforce import LocalWorkforce
    env=[("QT_QPA_PLATFORM","offscreen")]
    if qt_deps is not None:
        deps=qt_deps.resolve(strict=True)
        if not deps.is_dir():
            raise ValueError("External Qt dependency location is not a directory")
        env.append(("PYTHONPATH",str(deps)))
    test_files=("test_creative_acceptance.py","test_creative_instruction_bridge.py")
    blueprint=f"studio-creative-accepted-engineering-{head}"
    names=("STUDIO_PIXEL_ACCEPTANCE","STUDIO_ASSISTANT_BRIDGE")
    nodes=tuple(
        CampaignNode(name,"STUDIO_CREATIVE_INTEGRATION",(blueprint,),
                     f"Prove genuine Studio contract with {file}",
                     required_capabilities=("process",),
                     evidence_obligations=("test_stdout","exact_source","isolated_execution"),
                     stop_conditions=("source_moved","test_failure"),
                     max_useful_workers=1)
        for name,file in zip(names,test_files))
    campaign=CampaignManifest(
        "studio-creative-tenfold-qualification",1,blueprint,1,
        canonical_digest({"studio_source":head,"authority":"approved creative integration acceptance"}),
        "tenfold-gen1-manifest",1,
        canonical_digest({"compiler":"studio-creative-qualification","version":1}),
        nodes,(Milestone("STUDIO_CREATIVE_INTEGRATION",1,names),),
        AssuranceBinding(1,canonical_digest({"sergeant":"separately required"}),()))
    foreman=Foreman(campaign)
    assert foreman.frontier()["ready"]==tuple(sorted(names))
    jobs={}
    items=[]
    runtimes={}
    scheduler=ResourceScheduler()
    for n, file in zip(names, test_files):
        foreman.transition(n,NodeState.READY)
        task=TaskPacket(
            f"test-{file}",campaign.campaign_id,campaign.generation,n,f"worker-{n}",
            1,f"Run native TTG Studio {file} acceptance without source changes",
            ("src","scripts"),("process",),("read",),
            ("test_stdout","exact_source","isolated_execution"),
            ("source_moved","test_failure"),"verification",head).sealed()
        job=WorkerJob(
            f"job-{n}",task,JobKind.PROCESS,"process",".",
            argv=(sys.executable,"-B",f"scripts/{file}"),
            timeout_seconds=200,
            resource_request=ResourceRequest(cpu_slots=1,memory_mb=384),
            monitored_surfaces=("src","scripts"),
            environment=tuple(env),
            mode=ExecutionMode.ISOLATED).sealed()
        jobs[job.job_id]=job
        items.append(WorkItem(job.job_id,n,f"render-contract:{n}","process",
                              ResourceRequest(cpu_slots=1,memory_mb=384),
                              1,1,0,1).sealed())
        worker_id=f"tenfold-{n.lower()}"
        scheduler.register_worker(worker_id,frozenset({"process"}),ResourceCapacity(1,512))
        runtimes[worker_id]=LocalWorkerRuntime(
            WorkerSpec(worker_id,frozenset({"process"}),frozenset({"read"}),str(studio),
                       frozenset({"PYTHONPATH","QT_QPA_PLATFORM"})),
            source_identity=head)
        foreman.transition(n,NodeState.RUNNING)
    result=LocalWorkforce(scheduler,runtimes).run(jobs,items,max_threads=2)
    rows=[]
    if result.failures:
        raise AssertionError(f"Real Tenfold workforce failures: {result.failures!r}")
    for evidence in result.evidence:
        if evidence.status != "completed" or evidence.exit_code != 0 or not evidence.isolated:
            raise AssertionError(f"Tenfold job did not qualify: {evidence!r}")
        try:
            summary=json.loads(evidence.stdout)
        except ValueError as exc:
            raise AssertionError("Tenfold test returned no valid Studio native test evidence") from exc
        if summary.get("status")!="PASS" or summary.get("count",0)<18:
            raise AssertionError(f"Studio failed acceptance inside Tenfold: {summary!r}")
        node=jobs[evidence.job_id].task.node_id
        for state in (NodeState.EVIDENCE_PENDING,NodeState.REVIEW_PENDING,
                      NodeState.CANDIDATE,NodeState.FROZEN,NodeState.PROVING,
                      NodeState.PROVEN):
            foreman.transition(node,state)
        rows.append({"node":node,"test_count":summary["count"],
                     "tenfold_worker":evidence.worker_id,
                     "execution_status":evidence.status,
                     "isolated":evidence.isolated,
                     "result_digest":evidence.result_digest,
                     "evidence_digest":evidence.digest})
    assert all(foreman.runtime.states[n] is NodeState.PROVEN for n in names)
    # A negative stale-authority check against real Tenfold worker.
    stale=jobs[next(iter(jobs))].task
    stale_worker=LocalWorkerRuntime(
        WorkerSpec("stale",frozenset({"process"}),frozenset({"read"}),str(studio)),
        source_identity="stale-source")
    try:
        stale_worker.execute(jobs[next(iter(jobs))])
    except WorkerError:
        stale_rejected=True
    else:
        raise AssertionError("Real Tenfold admitted a stale source identity")
    return {"state":"REAL_TENFOLD_GEN1_ENGINEERING_ACCEPTANCE_PASS",
            "studio_head":head,"tenfold_head":ten_head,
            "manifest_digest":campaign.digest,
            "reconciled_states":{k:v.value for k,v in foreman.runtime.states.items()},
            "evidence":sorted(rows,key=lambda x:x["node"]),
            "stale_source_rejected":stale_rejected,
            "source_dirty":False,
            "cookpit_executed":False,
            "sergeant_approved":False,
            "semantic_photoreal_qualified":False,
            "render_owner":"TTG Creative Studio"}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--tenfold-root",type=Path,required=True)
    p.add_argument("--studio-root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--receipt",type=Path)
    p.add_argument("--qt-deps",type=Path)
    a=p.parse_args()
    receipt=qualify(a.studio_root,a.tenfold_root,a.qt_deps)
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        a.receipt.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))
if __name__=="__main__":
    main()

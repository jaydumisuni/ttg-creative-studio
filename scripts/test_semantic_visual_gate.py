#!/usr/bin/env python3
"""Actual Studio PNG/project + optional local observer contract tests.

Mock loopback endpoints verify transport only, NOT genuine model perception.
"""
import copy
import hashlib
import json
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from ttg_creative_instruction import SCHEMA, SCENE_SCHEMA, run_creative_instruction
from ttg_semantic_visual_gate import SCHEMA as VS, validate_observer
from ttg_project_schema import TTGProject

def scene():
    return {"schema":SCENE_SCHEMA,"name":"Semantic observer native proof",
            "canvas":{"width":640,"height":480,"background":"#101820"},
            "layers":[{"id":"headline","type":"text","name":"Editable title",
                       "x":320,"y":210,
                       "properties":{"text":"BUILD WHAT MATTERS","size":42,
                                     "color":"#FAFAFF","align":"center"}}]}
class Fake(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        if self.path!="/v1/models":return self.send_error(404)
        self.reply({"data":[{"id":"contract-fixture-only"}]})
    def do_POST(self):
        if self.path!="/v1/chat/completions":return self.send_error(404)
        length=int(self.headers.get("Content-Length",0))
        body=json.loads(self.rfile.read(length))
        assert body["model"]=="contract-fixture-only"
        assert body["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
        self.reply({"choices":[{"message":{"content":"FICTIONAL FIXTURE response; not genuine visual recognition"}}]})
    def reply(self,obj):
        b=json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)))
        self.end_headers()
        self.wfile.write(b)

checks=[]
def check(ok,desc):
    assert ok,desc
    checks.append(desc)
def rejected(fn,desc):
    try:fn()
    except (ValueError,TypeError):checks.append(desc)
    else:raise AssertionError(desc)
def job(root,name,spec=None):
    op={"schema":SCHEMA,"mode":"scene","instruction":"Render exact editing proof",
        "scene":scene(),"catalog_roots":[str(root)]}
    if spec:op["visual_observer"]=spec
    return {"task":"creative_execute","output":str(root/(name+".png")),"options":op}

def main():
    with tempfile.TemporaryDirectory(prefix="cs-semantic-observer-") as t:
        p=Path(t)
        spec={"schema":VS,"endpoint":"http://127.0.0.1:8000",
              "model":"unavailable-model","question":"Check text and composition."}
        native=run_creative_instruction(job(p,"native"))
        check(native["reopened_project_exact_pixels"] and native["independent_visual_observation"] is None,
              "Unmodified native rendering still works with no visual observer")
        check(native["state"]=="rendered_visual_review_required",
              "No model never constitutes semantic acceptance")
        rendered=run_creative_instruction(job(p,"missing",spec))
        receipt=rendered["independent_visual_observation"]
        check(receipt["state"]=="visual_observer_unavailable" and rendered["state"]=="visual_observer_unavailable" and not receipt["acceptance_authority"],
              "Absent real local visual model cannot silently approve")
        check(receipt["image_sha256"]==rendered["render_sha256"] and TTGProject.load(rendered["project"]).layers,
              "Observer evidence bound to real rendered image and editable Studio project")
        check(json.loads(Path(p/"missing.receipt.json").read_text())["independent_visual_observation"]["state"]=="visual_observer_unavailable",
              "Observer failure persisted in Studio receipt")
        for endpoint in ("http://evil.example:8000","https://127.0.0.1:8000",
                         "http://127.0.0.1:8000/api","http://127.0.0.1:8000@evil.example:80"):
            bad={**spec,"endpoint":endpoint}
            rejected(lambda:validate_observer(bad),"Disallowed remote/non-base URL refused: "+endpoint)
        rejected(lambda:validate_observer({**spec,"model":""}),"Missing model refused")
        rejected(lambda:validate_observer({**spec,"question":"  \n"}),"Control-character question refused")
        import subprocess
        request=job(p,"missing_cli",spec)
        (p/"request.json").write_text(json.dumps(request))
        cli=subprocess.run([sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),
            "--job",str(p/"request.json"),"--result",str(p/"response.json")],
            text=True,capture_output=True,timeout=90)
        reply=json.loads((p/"response.json").read_text())
        check(cli.returncode==0 and not reply["ok"] and
              reply["status"]=="visual_observer_unavailable" and
              Path(reply["outputPath"]).is_file(),
              "CLI explicitly rejects semantic completion but preserves rendered PNG")
        campaign=job(p,"campaign_disallowed",spec)
        campaign["options"]["mode"]="campaign"
        rejected(lambda:run_creative_instruction(campaign),
                 "Campaign mode refuses unsupported observer instead of silently dropping request")
        with ThreadingHTTPServer(("127.0.0.1",0),Fake) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            good={**spec,"endpoint":"http://127.0.0.1:"+str(server.server_port),"model":"contract-fixture-only"}
            linked=run_creative_instruction(job(p,"fake_contract",good))
            evidence=linked["independent_visual_observation"]
            check(evidence["state"]=="semantic_observation_returned_unverified" and
                  evidence["observation"].startswith("FICTIONAL FIXTURE"),
                  "Mock transport observation explicitly advisory—not proof of real semantic vision")
            check(evidence["image_sha256"]==hashlib.sha256(Path(linked["output"]).read_bytes()).hexdigest(),
                  "Successful observation bound to final native PNG digest")
            check(linked["reopened_project_exact_pixels"] and
                  linked["state"]=="rendered_visual_review_required",
                  "Fake observer cannot certify image or alter Studio's replay verification")
            server.shutdown()
    print(json.dumps({"state":"PASS","count":len(checks),"scope":"Native image and contract integration; genuine vision model not available","checks":checks},indent=2))
if __name__=="__main__":main()

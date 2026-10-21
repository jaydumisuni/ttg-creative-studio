#!/usr/bin/env python3
"""Physical native rendering tests for bounded prompt parsing and correction.

All jobs use the original Studio CLI engine and file-backed TTGProjects.
No external inference, paid calls, invented worker attestations or renderer fork.
"""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_creative_instruction import SCHEMA, SCENE_SCHEMA, CreativeInstructionError, run_creative_instruction
from ttg_project_schema import TTGProject
from ttg_creative_intent import interpret_creation,interpret_edit

tests=[]
def check(ok,msg):
    if not ok:raise AssertionError(msg)
    tests.append(msg)
def job(root,name,text,**opts):
    return {"task":"creative_execute","jobId":name,"output":str(root/(name+".png")),
            "options":{"schema":SCHEMA,"mode":"auto","instruction":text,
                       "catalog_roots":[str(root)],**opts}}

def main():
    with tempfile.TemporaryDirectory(prefix="cs-intelligence-") as dirname:
        root=Path(dirname)
        prompt='Create a dark blue social poster titled "FUTURE BEGINS HERE"'
        result=run_creative_instruction(job(root,"blue_card",prompt,auto_correct_layout=True))
        check(result["state"]=="rendered_visual_review_required" and result["mode"]=="scene","Natural-language poster produces real Studio PNG")
        check(result["natural_language_compilation"]=="bounded_native_typography" and result["reopened_project_exact_pixels"],"Original Studio editable project reopens with pixel-identical render")
        check(result["pixel_layer_review"]["state"]=="pixel_layer_visibility_pass" and result["pixel_layer_review"]["text_layers_examined"]==1,"Pixel differential proves headline is visible")
        original=TTGProject.load(result["project"])
        check(original.layers[2].properties["text"]=="FUTURE BEGINS HERE","User headline is retained precisely")
        check(result["tenfold_executed"] is False and result["cookpit_executed"] is False and result["model_inference_used"] is False,"No fabricated workforce or provider credentials")
        portrait=run_creative_instruction(job(root,"portrait","Design a portrait flyer headline: POWER IN MOTION with gold colors"))
        check(portrait["dimensions"]==[900,1200],"Portrait flyer is distinguished from portrait photograph")
        check(TTGProject.load(portrait["project"]).layers[2].properties["text"]=="POWER IN MOTION","Native title extraction without quoted phrases")
        banner=run_creative_instruction(job(root,"wide",'Make a wide banner saying "BUILD BETTER" with purple lighting'))
        check(banner["dimensions"]==[1280,720],"Landscape banners are admitted with bounded canvas")
        edited=job(root,"edit",'Change the headline to "CREATE WITHOUT LIMITS"')
        edited["input"]=result["project"]
        version=run_creative_instruction(edited)
        check(version["natural_language_compilation"]=="bounded_native_edit" and version["reopened_project_exact_pixels"],"Natural edit selects the existing compatible layer")
        check(version["render_sha256"]!=result["render_sha256"] and TTGProject.load(version["project"]).layers[2].properties["text"]=="CREATE WITHOUT LIMITS","Natural text editing genuinely changes rendered pixels")
        moved=job(root,"moved",'Move headline to (420, 395)')
        moved["input"]=version["project"]
        moveout=run_creative_instruction(moved)
        check(moveout["render_sha256"]!=version["render_sha256"],"Coordinates from plain text alter native composition")
        unqualified=run_creative_instruction(job(root,"unqualified","Create a poster showing a red car with headline \"DRIVE\""))
        check(unqualified["state"]=="needs_scene_compilation" and not (root/"unqualified.png").exists(),"Unknown picture subjects never silently disappear from rendered poster")
        unknown=run_creative_instruction(job(root,"photo","A photoreal elephant riding a helicopter above Jupiter"))
        check(unknown["state"]=="needs_scene_compilation" and not (root/"photo.png").exists(),"Unqualified photographic requests never render misleading images")
        ambiguous=job(root,"ambiguous","Change the text to 'OTHER'")
        ambiguous["input"]=portrait["project"]
        ambiguous_response=run_creative_instruction(ambiguous)
        check(ambiguous_response["state"]=="rendered_visual_review_required","One unlocked textual layer may be edited through unambiguous text alias")
        unsupported=job(root,"impossible","Replace the clouds with a mechanical phoenix in 3D")
        unsupported["input"]=result["project"]
        response=run_creative_instruction(unsupported)
        check(response["state"]=="needs_edit_compilation" and not (root/"impossible.png").exists(),"Unsupported edit fails closed without losing source")
        dry=run_creative_instruction(job(root,"dry",'Make a poster titled "PASS"',dry_run=True))
        check(dry["state"]=="planned_not_rendered" and not (root/"dry.png").exists(),"Natural-language dry-run writes no image")
        scene={"schema":SCENE_SCHEMA,"name":"Layer visibility challenge",
               "canvas":{"width":640,"height":480,"background":"#161616"},
               "layers":[{"id":"heading","type":"text","name":"Hidden headline","x":-100,"y":180,
                          "properties":{"text":"VISIBLE AFTER CORRECTION","size":32,"color":"#FFFFFF"}},
                         {"id":"blocker","type":"shape","name":"Opaque mask over text","x":0,"y":0,
                          "properties":{"shape":"rectangle","width":640,"height":480,"fill":"#1A1A1A"}}]}
        restored=run_creative_instruction(job(root,"corrected","Repair obscured text",mode="scene",scene=scene,auto_correct_layout=True))
        fix=restored["bounded_layout_corrections"]
        check(fix["correction_count"]>=1,"Bounded layout repair moves off-canvas text anchor")
        check(restored["pixel_layer_review"]["state"]=="pixel_layer_visibility_pass","Independent real-pixel test validates repaired text visibility")
        check(restored["pixel_layer_review"]["corrections"] and restored["reopened_project_exact_pixels"],"Occluded label raised above blocker and corrected project persists")
        check(TTGProject.load(restored["project"]).layers[-1].id=="heading","Verified correction is editable, not a flattened patch")
        # Regression: material-layer transforms live in a 1440x1080 authored
        # design space even when the native image is exported at 640x480.
        # Automatic correction must not collapse separate branded text lines.
        sign_prompt="Make a professional THETECHGUY office wall sign with blue lighting"
        native_sign=run_creative_instruction(job(root,"wall_baseline",sign_prompt,mode="wall_sign"))
        reviewed_sign=run_creative_instruction(job(root,"wall_reviewed",sign_prompt,
                                                   mode="wall_sign",auto_correct_layout=True))
        check(native_sign["render_sha256"]==reviewed_sign["render_sha256"],
              "Opt-in layout inspector cannot corrupt intact material-native wall signs")
        sign_project=TTGProject.load(reviewed_sign["project"])
        metal_text=[l for l in sign_project.layers if l.properties.get("cinematic_material")=="steel_text"]
        check([int(l.transform.y) for l in metal_text]==[594,729],
              "Material-native wordmark/subtitle spacing remains in 1440x1080 design coordinates")
        check(reviewed_sign["bounded_layout_corrections"]["correction_count"]==0 and
              reviewed_sign["pixel_layer_review"]["state"]=="pixel_layer_visibility_pass",
              "Normal wall-sign render requires no invented text corrections")
        no_auto=run_creative_instruction(job(root,"still_hidden","Keep hidden text",mode="scene",scene=scene))
        check(no_auto["bounded_layout_corrections"]["correction_count"]==0,"Correction never runs without explicit opt-in")
        blocked=job(root,"outside",'Move headline to (200,200)')
        blocked["input"]="/etc/passwd"
        try:run_creative_instruction(blocked)
        except (CreativeInstructionError,ValueError,TypeError):tests.append("Outside-catalog project cannot be read through natural editing")
        else:raise AssertionError("Outside-catalog read was admitted")
        invalid=job(root,"badflag","Make a poster titled 'TEST'",auto_correct_layout="yes")
        try:run_creative_instruction(invalid)
        except (CreativeInstructionError,ValueError,TypeError):tests.append("Strict correction opt-in type gate rejects strings")
        else:raise AssertionError("Correction flag validation failed")
        cli=ROOT/"src/ttg_creative_studio/cli.py"
        cli_job=job(root,"cli",'Create a poster saying "INDEPENDENT IMAGE" with gold detail')
        (root/"work.json").write_text(json.dumps(cli_job))
        run=subprocess.run([sys.executable,"-B",str(cli),"--job",str(root/"work.json"),
                            "--result",str(root/"work_result.json")],capture_output=True,text=True,timeout=90)
        response=json.loads((root/"work_result.json").read_text())
        check(run.returncode==0 and response["ok"] and response["meta"]["natural_language_compilation"]=="bounded_native_typography","Native CLI accepts plain-language job without an assistant-authored scene JSON")
    print(json.dumps({"status":"PASS","count":len(tests),"tests":tests},indent=2))

if __name__=="__main__":main()

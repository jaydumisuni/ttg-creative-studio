#!/usr/bin/env python3
"""Native Creative Studio acceptance and correction integration tests."""
import json
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_creative_instruction import SCHEMA,SCENE_SCHEMA,run_creative_instruction
from ttg_creative_acceptance import SCHEMA as AS,validate_acceptance
from ttg_project_schema import TTGProject
checks=[]
def check(v,description):
    if not v:raise AssertionError(description)
    checks.append(description)
def denied(fn,description):
    try:fn()
    except (ValueError,TypeError):checks.append(description)
    else:raise AssertionError(description)
def scene(word):
    return {"schema":SCENE_SCHEMA,"name":"Creative acceptance proof",
     "canvas":{"width":640,"height":480,"background":"#091521"},
     "layers":[{"id":"bg","type":"shape","x":15,"y":15,"name":"background",
               "properties":{"shape":"rectangle","width":610,"height":450,"fill":"#15314A"}},
               {"id":"headline","type":"text","x":320,"y":200,"name":"Exact headline",
               "properties":{"text":word,"size":40,"color":"#FFFFFF","align":"center"}}]}
def goal(value):
    return {"schema":AS,"text":[{"layer_id":"headline","value":value}]}
def job(root,name,word,**options):
    return {"task":"creative_execute","output":str(root/(name+".png")),
            "options":{"schema":SCHEMA,"mode":"scene","instruction":"Build exact editable wording",
                       "scene":scene(word),"catalog_roots":[str(root)],**options}}
def main():
    with tempfile.TemporaryDirectory(prefix="studio-acceptance-") as tmp:
        p=Path(tmp);a=goal("DESIGN WITH PURPOSE")
        good=run_creative_instruction(job(p,"good","DESIGN WITH PURPOSE",acceptance=a))
        review=good["declared_acceptance"]
        check(review["state"]=="pass" and review["checks"]==1 and review["visible_checks"]==1,"Correct visible text passes explicit user wording and native-pixel contribution")
        check(review["visible_evidence"][0]["pixel_contribution_bbox"],"Native renderer proves visible contribution from declared text")
        check(review["independent_semantic_review"]=="not_performed" and review["photorealism_certification"] is False,"Pixel test never claims independent semantic or photographic review")
        wrong=run_creative_instruction(job(p,"wrong","DESIGN WITH PROPOSE",acceptance=a))
        check(wrong["declared_acceptance"]["state"]=="correction_required","Wrong spelling fails even with valid visible PNG")
        check(wrong["state"]=="correction_required" and wrong["declared_acceptance_passed"] is False,
              "Unmet declared acceptance cannot be reported as a finished render")
        check(wrong["declared_acceptance"]["findings"][0]["reason"]=="declared_element_mismatch","Diagnostic identifies specifically incorrect source wording")
        fixed=run_creative_instruction(job(p,"fixed","DESIGN WITH PROPOSE",acceptance=a,repair_expected_text=True))
        check(fixed["declared_acceptance"]["state"]=="pass" and len(fixed["bounded_spelling_repairs"])==1,"Explicit trusted wording repairs native source")
        check(fixed["state"]=="rendered_visual_review_required" and fixed["declared_acceptance_passed"] is True,
              "Passing checks still requires separate semantic visual review")
        check(TTGProject.load(fixed["project"]).layers[-1].properties["text"]=="DESIGN WITH PURPOSE" and fixed["reopened_project_exact_pixels"] and fixed["render_sha256"]!=wrong["render_sha256"],"Correction changes pixels and editable project reopens exactly")
        legacy=run_creative_instruction(job(p,"legacy","NORMAL"))
        check(legacy["declared_acceptance"] is None and legacy["reopened_project_exact_pixels"],"Previous schema remains backward-compatible")
        bad_material={"schema":AS,"materials":[{"layer_id":"bg","value":"neon"}]}
        wrong_mat=run_creative_instruction(job(p,"mat","TITLE",acceptance=bad_material))
        check(wrong_mat["declared_acceptance"]["state"]=="correction_required","Requested material mismatch fails")
        absent={"schema":AS,"text":[{"layer_id":"absent","value":"TITLE"}]}
        missing=run_creative_instruction(job(p,"missing","TITLE",acceptance=absent))
        check(missing["declared_acceptance"]["findings"][0]["reason"]=="required_layer_missing_or_hidden","Missing subject layer is not invented")
        wall_goal={"schema":AS,"text":[{"layer_id":"pro_scene_007","value":"THETECHGUY"}],"materials":[{"layer_id":"pro_scene_004","value":"neon"},{"layer_id":"pro_scene_002","value":"steel_polygon"}]}
        wall=job(p,"wall","IGNORED",mode="wall_sign",acceptance=wall_goal)
        wall["options"].pop("scene")
        wall["options"]["instruction"]="Make a professional THETECHGUY office wall sign with blue lighting"
        wall_proof=run_creative_instruction(wall)
        check(wall_proof["declared_acceptance"]["state"]=="pass" and wall_proof["declared_acceptance"]["visible_checks"]==3,
              "Existing premium wall sign satisfies native material and branded-text visibility requirements")
        import subprocess
        cli=ROOT/"src/ttg_creative_studio/cli.py"
        cli_job=job(p,"climismatch","WRONG SOURCE TEXT",acceptance=a)
        (p/"cli_request.json").write_text(json.dumps(cli_job))
        proc=subprocess.run([sys.executable,"-B",str(cli),"--job",str(p/"cli_request.json"),
                             "--result",str(p/"cli_response.json")],capture_output=True,
                            text=True,timeout=60)
        response=json.loads((p/"cli_response.json").read_text())
        check(proc.returncode==0 and response["ok"] is False and
              response["status"]=="correction_required" and
              response["meta"]["declared_acceptance_passed"] is False,
              "Assistant-facing CLI exposes failed acceptance without claiming job success")
        denied(lambda:validate_acceptance({"schema":AS}),"Empty acceptance cannot certify")
        denied(lambda:validate_acceptance({**a,"skip_review":True}),"Unapproved acceptance fields rejected")
        denied(lambda:validate_acceptance({"schema":AS,"text":[{"layer_id":"headline","value":"one"},{"layer_id":"headline","value":"two"}]}),"Repeated target rejected")
        denied(lambda:validate_acceptance({"schema":AS,"text":[{"layer_id":"headline","value":"bad\ntext"}]}),"Control characters rejected")
        denied(lambda:run_creative_instruction(job(p,"noconsent","TITLE",repair_expected_text=True)),"No implicit correction without exact text contract")
        denied(lambda:run_creative_instruction(job(p,"badtarget","TITLE",acceptance=absent,repair_expected_text=True)),"No correction of missing layer")
        dry=run_creative_instruction(job(p,"dry","TYPO",acceptance=a,repair_expected_text=True,dry_run=True))
        check(dry["state"]=="planned_not_rendered" and not (p/"dry.png").exists() and dry["spelling_repair_plan"],"Dry run previews exact correction without rendering")
    print(json.dumps({"status":"PASS","count":len(checks),"checks":checks},indent=2))
if __name__=="__main__":main()

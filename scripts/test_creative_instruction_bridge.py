#!/usr/bin/env python3
"""Native Creative Studio scene/edit/campaign and prompt-contract integration."""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_creative_instruction import SCHEMA,SCENE_SCHEMA,CreativeInstructionError,compile_scene,run_creative_instruction
from ttg_project_schema import TTGProject

checks=[]
def require(ok,what):
    if not ok:raise AssertionError(what)
    checks.append(what)
def rejects(fn,what):
    try:fn()
    except (CreativeInstructionError,ValueError,TypeError):checks.append(what);return
    raise AssertionError("Fail-open: "+what)
def scene():
    return {"schema":SCENE_SCHEMA,"name":"THETECHGUY premium scene",
        "canvas":{"width":640,"height":480,"background":"#0B111A"},
        "layers":[
         {"id":"room","name":"Original architecture","type":"shape",
          "properties":{"cinematic_material":"architectural_lobby","seed":39,"warmth":0.65}},
         {"id":"badge","name":"Metal tag","type":"shape","x":182,"y":90,
          "properties":{"cinematic_material":"steel_polygon","points":[[0,0],[110,0],[110,55],[0,55]],"depth":8,"seed":42}},
         {"id":"wordmark","name":"Exact metallic type","type":"text3d","x":140,"y":235,
          "properties":{"cinematic_material":"steel_text","text":"THETECHGUY","size":55,"depth":5}},
         {"id":"neon","name":"LED circuit","type":"shape","x":265,"y":158,
          "properties":{"cinematic_material":"neon","points":[[0,0],[100,0],[100,28]],
                        "width":4,"led_color":"blue","terminals":True}},
         {"id":"subtitle","name":"Tagline","type":"text","x":140,"y":338,
          "properties":{"text":"ONE BRAND. ALL SOLUTIONS.","size":26,"color":"#C8DEEA"}}
        ]}
def packet(name,mode,root,**opts):
    return {"task":"creative_execute","jobId":name,"output":str(root/(name+".png")),
            "options":{"schema":SCHEMA,"mode":mode,"instruction":"THETECHGUY premium identity creation",
                       "catalog_roots":[str(root)],**opts}}
def main():
    with tempfile.TemporaryDirectory(prefix="ttg-cs-bridge-") as temp:
        root=Path(temp)
        source=packet("first","scene",root,scene=scene())
        no=copy.deepcopy(source);no["options"]["dry_run"]=True
        dry=run_creative_instruction(no)
        require(dry["state"]=="planned_not_rendered" and not list(root.glob("first*")),"Planning is side effect free")
        made=run_creative_instruction(source)
        require(made["reopened_project_exact_pixels"] and made["state"]=="rendered_visual_review_required","Native engine generated PNG and deterministic replay")
        require(made["layer_count"]==5 and made["dimensions"]==[640,480],"Scene object/layer geometry preserved")
        require(made["pixel_metrics"]["source_sha256"]==made["render_sha256"],"Pixel inspector measured real output")
        require(not made["model_inference_used"] and not made["paid_provider_used"] and not made["tenfold_executed"] and not made["cookpit_executed"],"Provenance does not fabricate workers or AI")
        edit=packet("edit","edit_project",root,edits=[
            {"op":"replace_text","layer_id":"subtitle","value":"REPAIR. BUILD. CREATE."},
            {"op":"set_neon_color","layer_id":"neon","value":"purple"},
            {"op":"move_layer","layer_id":"wordmark","x":110,"y":230}])
        edit["input"]=made["project"]
        revised=run_creative_instruction(edit)
        require(revised["render_sha256"]!=made["render_sha256"] and revised["reopened_project_exact_pixels"],"Edits change pixels and replay")
        before=TTGProject.load(made["project"]);after=TTGProject.load(revised["project"])
        require(before.layers[-1].properties["text"]=="ONE BRAND. ALL SOLUTIONS." and after.layers[-1].properties["text"]=="REPAIR. BUILD. CREATE.","Edits preserve original")
        require(after.layers[3].properties["led_color"]=="purple","Material edits persist")
        resized=packet("resize","edit_project",root,edits=[
            {"op":"set_text_size","layer_id":"wordmark","value":80}])
        resized["input"]=made["project"]
        large=run_creative_instruction(resized)
        require(large["render_sha256"]!=made["render_sha256"] and large["reopened_project_exact_pixels"],
                "Font-size edit changes physical rendered pixels and replays identically")
        changed=TTGProject.load(large["project"])
        require(changed.layers[2].properties["size"]==80 and before.layers[2].properties["size"]==55,
                "Editable text sizing is source-owned and preserves the original")
        for size in (0,231,-1,30.5,True,float("nan")):
            bad=copy.deepcopy(resized)
            bad["output"]=str(root/("invalid_size_"+str(size).replace(".","_")+".png"))
            bad["options"]["edits"]=[{"op":"set_text_size","layer_id":"wordmark","value":size}]
            rejects(lambda item=bad:run_creative_instruction(item),"Invalid text size denied "+str(size))
        bad=copy.deepcopy(resized);bad["output"]=str(root/"nontxt.png")
        bad["options"]["edits"]=[{"op":"set_text_size","layer_id":"room","value":40}]
        rejects(lambda:run_creative_instruction(bad),"Non-text geometry cannot receive font-size edits")
        rejects(lambda:run_creative_instruction(source),"Overwrite denied")
        bad=scene();bad["layers"][1]["properties"]["cinematic_material"]="external_shell"
        rejects(lambda:compile_scene(bad),"Unadmitted renderer/command rejected")
        bad=scene();bad["layers"].append(copy.deepcopy(bad["layers"][0]))
        rejects(lambda:compile_scene(bad),"Duplicate IDs rejected")
        bad=scene();bad["layers"][1]["properties"]["external_script"]="curl ..."
        rejects(lambda:compile_scene(bad),"Unadmitted source properties rejected")
        bad=scene();bad["layers"][1]["properties"]["points"]=[[0,0],[4,float("nan")],[8,8]]
        rejects(lambda:compile_scene(bad),"Nonfinite coordinates rejected")
        bad=scene();bad["layers"][0]["properties"]["seed"]=999999
        rejects(lambda:compile_scene(bad),"Over-budget seed rejected")
        bad=copy.deepcopy(edit);bad["input"]="/etc/passwd";bad["output"]=str(root/"unapproved.png")
        rejects(lambda:run_creative_instruction(bad),"Unapproved source blocked")
        bad=copy.deepcopy(edit);bad["output"]=str(root/"unapproved2.png")
        bad["options"]["edits"]=[{"op":"replace_text","layer_id":"room","value":"corrupt"}]
        rejects(lambda:run_creative_instruction(bad),"Type-incompatible edit rejected")
        bad=copy.deepcopy(edit);bad["output"]=str(root/"unapproved3.png")
        bad["options"]["edits"]=[{"op":"set_neon_color","layer_id":"neon","value":"unknown"}]
        rejects(lambda:run_creative_instruction(bad),"Unknown accent rejected")
        sign=packet("wall","wall_sign",root,
                    instruction="Make a professional THETECHGUY office wall sign with blue lighting",
                    edits=[{"op":"replace_text","layer_id":"pro_scene_007","value":"THETECHGUY"}])
        signout=run_creative_instruction(sign)
        require(signout["reopened_project_exact_pixels"] and signout["layer_count"]>=10,"Real existing wall-sign materials rendered")
        camp=packet("poster","campaign",root,campaign={
            "layout":"social","brand":"THETECHGUY","headline":"TECH WITH PURPOSE",
            "subhead":"Make it matter.","product_name":"CREATIVE STUDIO",
            "cta":"EXPLORE","website":"thetechguyds.com","accent":"aqua"})
        poster=run_creative_instruction(camp)
        require(Path(poster["bundle"]).is_file() and TTGProject.load(poster["project"]).layers,"Existing campaign composer exports portable editable art")
        auto=packet("auto_resolved","auto",root,scene=scene())
        autodone=run_creative_instruction(auto)
        require(autodone["mode"]=="scene" and autodone["reopened_project_exact_pixels"],
                "Generic assistant auto-routing executes admitted scene specification")
        unsupported=packet("unknown_image","auto",root,
                           instruction="A photoreal elephant riding a helicopter above Jupiter")
        not_done=run_creative_instruction(unsupported)
        require(not_done["state"]=="needs_scene_compilation" and
                not (root/"unknown_image.png").exists(),
                "Unfamiliar natural language demands authored scene rather than fake pixels")
        contract=not_done["supported_scene_contract"]
        require("steel_text" in contract["scene"]["native_materials"] and
                contract["acceptance"]["semantic_visual_quality"]=="separate qualified visual reviewer required",
                "Unknown instruction returns executable Studio contract and independent review boundary")
        invented=packet("not_a_sign","wall_sign",root,
                        instruction="Make a portrait photo of a dog in a lobby")
        rejects(lambda:run_creative_instruction(invented),
                "Wall-sign worker cannot repurpose unrelated portrait requests")
        cli=ROOT/"src/ttg_creative_studio/cli.py"
        advertised=subprocess.run([sys.executable,"-B",str(cli),"--catalog"],capture_output=True,text=True,timeout=28)
        require(advertised.returncode==0 and "creative_execute" in json.loads(advertised.stdout)["operations"],"AI-facing tool discovery advertises real workflow")
        metadata=json.loads(advertised.stdout)["operations"]["creative_execute"]
        require("steel_polygon" in metadata["scene_capabilities"]["scene"]["native_materials"] and
                metadata["scene_capabilities"]["execution"]["sergeant"]=="engineering review, not artistic approval",
                "Tool catalog advertises renderer contract without granting workforce review authority")
        job=packet("from_cli","scene",root,scene=scene())
        (root/"job.json").write_text(json.dumps(job))
        cmd=subprocess.run([sys.executable,"-B",str(cli),"--job",str(root/"job.json"),"--result",str(root/"result.json")],capture_output=True,text=True,timeout=80)
        cliout=json.loads((root/"result.json").read_text())
        require(cmd.returncode==0 and cliout["ok"] and cliout["meta"]["reopened_project_exact_pixels"],"Native CLI job executes assistant-authored scene spec")
    print(json.dumps({"status":"PASS","count":len(checks),"checks":checks},indent=2))
if __name__=="__main__":main()

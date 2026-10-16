#!/usr/bin/env python3
"""Qualify the Builder-owned Creative Studio release contract without publishing."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"techguy-build.json"


def check_manifest() -> dict:
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["schemaVersion"]==1
    assert data["appName"]=="TTG Creative Studio"
    assert data["publisher"]=="THETECHGUY DIGITAL SOLUTIONS"
    assert data["domain"]=="thetechguyds.com"
    assert data["repository"]=="jaydumisuni/ttg-creative-studio"
    assert data["githubRelease"]["repository"]==data["repository"]
    assert re.fullmatch(r"\d+\.\d+\.\d+-(?:alpha|beta|rc)(?:\.\d+)?",data["appVersion"])
    life=data["appLifecycle"]
    assert life=={"appId":"ttg-creative-studio","stage":"testing","public":False}
    assert data["signing"]["release_signing_required"] is True
    assert data["installer"]["requireCustomGraphicalInstaller"] is True
    assert data["installer"]["requireRegisteredUninstall"] is True
    assert data["installer"]["publisher"]==data["publisher"]
    assert data["installer"]["runAsAdmin"] is False
    assert data["output"]=={"dist":"dist","installer":"installer"}
    assert data["capabilities"]["distribution"]["providers"]==["github"]
    assert data["capabilities"]["storefront"]["enabled"] is False
    assert sorted(data["capabilities"]["platforms"])==["linux","windows"]
    assert data["maintenance"]["enabled"] is False
    assert data["maintenance"]["auto_apply"] is False
    assert data["releaseControl"]["enabled"] is False
    assert data["releaseControl"]["onlineRequired"] is False
    assert data["releaseControl"]["enabled"] is False
    assert not any(x in str(data).lower() for x in ["pfx_password","private_key_pem","ghp_","sk-proj-"])
    assert (ROOT/"sign_release.ps1").is_file()
    assert "TTG Creative Studio" in (ROOT/"build_installer.ps1").read_text(errors="replace")
    assert (ROOT/"installer/creative_studio_core.iss").is_file()
    return {
        "application":"ttg-creative-studio",
        "builder":"THETECHGUY Software Builder",
        "manifest":"techguy-build.json",
        "mode":"testing",
        "productionSigningRequired":True,
        "public":False,
        "platforms":data["capabilities"]["platforms"],
        "configuredProviders":data["capabilities"]["distribution"]["providers"],
        "productionReleaseDeclared":False,
    }


def main() -> int:
    print(json.dumps({"result":"PASS","contract":check_manifest()},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

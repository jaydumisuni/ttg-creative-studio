"""Portable binary, installer-path and app self-check release qualification."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    spec = (ROOT/"TTG Creative Studio.spec").read_text()
    assert "scripts/launch_creative_studio.py" in spec
    assert "TTG Creative Studio" in spec
    for name in ("build_exe.ps1", "build_installer.ps1", "installer/creative_studio_core.iss"):
        data = (ROOT/name).read_text()
        assert "TTG Creative Studio" in data
        assert "Background Remover" not in data
    iss = (ROOT/"installer/creative_studio_core.iss").read_text()
    assert "OutputDir=..\\dist\\installer" in iss
    env=os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    result=subprocess.run(
        [sys.executable, "-B", str(ROOT/"scripts/launch_creative_studio.py"), "--self-check"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
    assert "packaged_imports" in result.stdout
    sys.path.insert(0, str(ROOT/"scripts"))
    from install_linux_portable import install_bundle
    with tempfile.TemporaryDirectory() as temp:
        base=Path(temp)
        build=base/"fake-installed-app"
        build.mkdir()
        (build/"TTG Creative Studio").write_bytes(b"#!/bin/sh\nexit 0\n")
        installed=install_bundle(build,base/"prefix")
        assert installed.is_file()
        assert (base/"prefix"/"lib"/"ttg-creative-studio"/"TTG Creative Studio").is_file()
        try:
            install_bundle(build,base/"prefix")
        except FileExistsError:
            pass
        else:
            raise AssertionError("Portable Linux installer overwritten existing program")
    import hashlib
    import json
    sys.path.insert(0,str(ROOT/"src"))
    from ttg_update_checker import parse_notice, is_newer, verify_installer, fetch_update
    payload=b"example official installer bytes"
    record={
        "version":"0.2.0-alpha",
        "notes":"Reviewed update candidate",
        "installer_url":"https://thetechguyds.com/releases/CreativeStudio-setup.exe",
        "sha256":hashlib.sha256(payload).hexdigest(),
    }
    notice=parse_notice(json.dumps(record).encode())
    assert is_newer(notice) and verify_installer(payload,notice)
    assert not verify_installer(b"tampered",notice)
    for bad_url in [
        "http://thetechguyds.com/releases/a.exe",
        "https://evil.invalid/a.exe",
        "file:///tmp/a.exe",
        "https://thetechguyds.com.evil.invalid/a.exe",
    ]:
        record["installer_url"]=bad_url
        try:parse_notice(json.dumps(record).encode())
        except ValueError:pass
        else:raise AssertionError("Update manifest permitted untrusted installer URL")
    try:fetch_update("https://evil.invalid/latest.json")
    except ValueError:pass
    else:raise AssertionError("Untrusted update feed accepted")
    print("Creative Studio release-path and update integrity checks: PASS")


if __name__ == "__main__":
    main()

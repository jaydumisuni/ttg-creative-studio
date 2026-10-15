#!/usr/bin/env python3
"""Adversarial tests for unsigned-candidate release custody, not signing."""
from __future__ import annotations
import io
import json
import struct
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from studio_release_manifest import create, verify

SOURCE_SHA = "a" * 40
RUN_ID = "123456789"
checks=[]


def check(name: str, ok: bool) -> None:
    assert ok, name
    checks.append(name)


def expect_error(name, callback):
    try:
        callback()
    except (ValueError, FileExistsError):
        checks.append(name)
    else:
        raise AssertionError(name)


def fake_pe(path: Path, signed: bool) -> None:
    blob=bytearray(512)
    blob[0:2]=b"MZ"
    struct.pack_into("<I",blob,60,128)
    blob[128:132]=b"PE\0\0"
    struct.pack_into("<H",blob,128+24,0x20B)
    struct.pack_into("<II",blob,128+24+112+32,400 if signed else 0,
                     100 if signed else 0)
    path.write_bytes(blob)


def run():
    with tempfile.TemporaryDirectory(prefix="ttg-release-custody-") as tmp:
        base=Path(tmp)
        bundle=base/"Studio-Linux.tar.gz"
        with tarfile.open(bundle,"w:gz") as output:
            data=b"TTG application bytes"
            item=tarfile.TarInfo("TTG Creative Studio/bin/application")
            item.size=len(data)
            output.addfile(item,io.BytesIO(data))
        good=create(bundle,"linux",SOURCE_SHA,RUN_ID)
        manifest=base/"manifest.json"
        manifest.write_text(json.dumps(good))
        check("portable candidate roundtrip", verify(manifest,bundle,SOURCE_SHA)==good)
        check("unsigned archive cannot assert production trust",
              good["production_release_ready"] is False
              and good["artifact"]["trust_status"]=="UNSIGNED_ARCHIVE")
        expect_error("wrong source SHA rejected",
                     lambda:verify(manifest,bundle,"b"*40))
        good["production_release_ready"]=True
        manifest.write_text(json.dumps(good))
        expect_error("false production acceptance rejected",
                     lambda:verify(manifest,bundle,SOURCE_SHA))
        good["production_release_ready"]=False
        manifest.write_text(json.dumps(good))
        bundle.write_bytes(bundle.read_bytes()+b"tampering")
        expect_error("artifact modification rejected",
                     lambda:verify(manifest,bundle,SOURCE_SHA))
        evil=base/"malicious.tar.gz"
        with tarfile.open(evil,"w:gz") as t:
            item=tarfile.TarInfo("../outside.txt")
            item.size=1
            t.addfile(item,io.BytesIO(b"x"))
        expect_error("archive path traversal refused",
                     lambda:create(evil,"linux",SOURCE_SHA,RUN_ID))
        legitimate = base/"valid-symlink.tar.gz"
        with tarfile.open(legitimate,"w:gz") as tar:
            data=b"runtime"
            info=tarfile.TarInfo("TTG Creative Studio/lib/runtime.so")
            info.size=len(data)
            tar.addfile(info,io.BytesIO(data))
            link=tarfile.TarInfo("TTG Creative Studio/bin/runtime.so")
            link.type=tarfile.SYMTYPE
            link.linkname="../lib/runtime.so"
            tar.addfile(link)
        check("intra-bundle Linux symlink supported",
              create(legitimate,"linux",SOURCE_SHA,RUN_ID)["artifact"]["safe_tar_entries"]==2)
        badlink = base/"escaping-symlink.tar.gz"
        with tarfile.open(badlink,"w:gz") as tar:
            link=tarfile.TarInfo("TTG Creative Studio/bin/escape")
            link.type=tarfile.SYMTYPE
            link.linkname="../../../outside"
            tar.addfile(link)
        expect_error("Linux symlink escape refused",
                     lambda:create(badlink,"linux",SOURCE_SHA,RUN_ID))
        win=base/"TTG-Creative-Studio-Setup.exe"
        fake_pe(win,False)
        windows=create(win,"windows",SOURCE_SHA,RUN_ID)
        check("PE without signature explicitly unsigned",
              windows["artifact"]["trust_status"]=="UNSIGNED"
              and windows["artifact"]["authenticode_embedded"] is False)
        win_manifest=base/"win.json"
        win_manifest.write_text(json.dumps(windows))
        check("unsigned Windows manifest roundtrip",
              verify(win_manifest,win,SOURCE_SHA)==windows)
        fake_pe(win,True)
        expect_error("PE signature presence drift rejected",
                     lambda:verify(win_manifest,win,SOURCE_SHA))
        possible=create(win,"windows",SOURCE_SHA,RUN_ID)
        check("embedded signature never means trusted release",
              possible["artifact"]["trust_status"]=="UNVERIFIED_SIGNATURE"
              and possible["production_signature_validated"] is False)
        expect_error("malformed source SHA refused",
                     lambda:create(win,"windows","abc",RUN_ID))
        print(json.dumps({"result":"PASS","checks_count":len(checks),
                          "checks":checks},indent=2))


if __name__=="__main__":
    run()

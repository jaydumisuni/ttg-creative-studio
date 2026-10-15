"""Fail-closed update metadata inspection; never auto-execute remote installers."""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

CURRENT_VERSION = "0.1.0-alpha"
_ALLOWED_HOSTS = frozenset({"thetechguyds.com", "www.thetechguyds.com"})
_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)(?:\.(\d+))?)?$")


def _version(value: str) -> tuple[int, int, int, int, int]:
    match = _VERSION.fullmatch(value)
    if not match:
        raise ValueError("Invalid version identifier")
    major, minor, patch, stage, serial = match.groups()
    return int(major), int(minor), int(patch), {
        "alpha":0,"beta":1,"rc":2,None:3
    }[stage],int(serial or 0)


def _approved_https(url: str) -> bool:
    parts=urllib.parse.urlsplit(url)
    return (parts.scheme=="https" and parts.hostname in _ALLOWED_HOSTS
            and parts.username is None and parts.password is None
            and parts.port in (None,443) and not parts.fragment)


@dataclass(frozen=True)
class UpdateNotice:
    version: str
    notes: str
    installer_url: str
    sha256: str


def parse_notice(data: bytes) -> UpdateNotice:
    if len(data)>32_768:
        raise ValueError("Manifest too large")
    record=json.loads(data)
    notice=UpdateNotice(**record)
    _version(notice.version)
    if not isinstance(notice.notes,str) or len(notice.notes)>4096:
        raise ValueError("Update description invalid")
    if not _approved_https(notice.installer_url):
        raise ValueError("Installer must be published on the approved HTTPS domain")
    if not re.fullmatch(r"[a-f0-9]{64}",notice.sha256):
        raise ValueError("Installer digest invalid")
    return notice


def fetch_update(url: str) -> UpdateNotice:
    """Information-only; HTTPS cert validation by Python, no automatic install."""
    if not _approved_https(url):
        raise ValueError("Update feed must use the approved official HTTPS domain")
    req=urllib.request.Request(url,headers={"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=8) as response:
        if not _approved_https(response.geturl()):
            raise ValueError("Update feed redirected to an untrusted host")
        data=response.read(32_769)
    return parse_notice(data)


def is_newer(release: UpdateNotice, installed: str=CURRENT_VERSION) -> bool:
    return _version(release.version)>_version(installed)


def verify_installer(contents: bytes, notice: UpdateNotice) -> bool:
    return hashlib.sha256(contents).hexdigest()==notice.sha256

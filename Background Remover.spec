# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

project_root = Path(SPECPATH)
main_script_path = project_root / "bg_remover.py"
backend_script_path = project_root / "bg_backend.py"
resource_dir = project_root / "resources"
app_icon = project_root / "build_icon.ico"

datas = []
for filename in ("logo.png", "loding.gif"):
    resource_path = resource_dir / filename
    if resource_path.exists():
        datas.append((str(resource_path), "resources"))
if app_icon.exists():
    datas.append((str(app_icon), "resources"))

pymatting_datas, pymatting_binaries, pymatting_hiddenimports = collect_all("pymatting")
datas += pymatting_datas

hiddenimports = [
    "pymatting",
    "pymatting.alpha",
    "pymatting.foreground",
    "pymatting.util",
    "rembg._version",
    "rembg.bg",
    "rembg.session_factory",
    "rembg.sessions",
    "rembg.sessions.base",
    "rembg.sessions.dis_anime",
    "rembg.sessions.dis_general_use",
    "rembg.sessions.u2net_human_seg",
    "rembg.sessions.u2netp",
] + pymatting_hiddenimports + collect_submodules("pymatting")


main_analysis = Analysis(
    [str(main_script_path)],
    pathex=[str(project_root)],
    binaries=pymatting_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython",
        "PyQt5",
        "PySide2",
        "PySide6",
        "jedi",
        "matplotlib",
        "pygame",
        "tkinter",
        "torch",
    ],
    noarchive=False,
    optimize=0,
)
main_pyz = PYZ(main_analysis.pure)

main_exe = EXE(
    main_pyz,
    main_analysis.scripts,
    main_analysis.binaries,
    main_analysis.datas,
    [],
    name="TheTechGuy Image Editor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(app_icon) if app_icon.exists() else None,
)

backend_analysis = Analysis(
    [str(backend_script_path)],
    pathex=[str(project_root)],
    binaries=pymatting_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "jedi",
        "matplotlib",
        "pygame",
        "tkinter",
        "torch",
    ],
    noarchive=False,
    optimize=0,
)
backend_pyz = PYZ(backend_analysis.pure)

backend_exe = EXE(
    backend_pyz,
    backend_analysis.scripts,
    backend_analysis.binaries,
    backend_analysis.datas,
    [],
    name="TheTechGuy Image Editor Backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(app_icon) if app_icon.exists() else None,
)

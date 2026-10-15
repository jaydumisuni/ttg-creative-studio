# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
    ['scripts/launch_creative_studio.py'],
    pathex=['src'],
    binaries=[],
    datas=[('resources', 'resources'), ('templates', 'templates'), ('packs/manifests', 'packs/manifests')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Neither the native editor nor the self-check imports setuptools.
    # Prevent PyInstaller's pkg_resources runtime hook from pulling an
    # incomplete setuptools vendor/backports namespace into a frozen bundle.
    excludes=['setuptools', 'pkg_resources', 'backports'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TTG Creative Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TTG Creative Studio',
)

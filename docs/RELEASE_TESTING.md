# TTG Creative Studio Release Testing

This document is for the final Athena release test stage.

## 1. Pull latest source

```powershell
cd "D:\projects\TTG-Creative-Studio"
git pull
```

## 2. Create clean virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Run alpha verification

```powershell
scripts\test_alpha.cmd
```

This validates project schema, rendering, editing actions, undo/redo, property editing, canvas selection, release-track implementation files, templates, and pack manifests.

## 4. Launch source app

```powershell
python scripts\launch_creative_studio.py
```

Check:

- New project opens.
- Add Text works.
- Add Shape works.
- Add Image works.
- Click layer selects it.
- Drag layer moves it with snap grid.
- Editable properties apply changes.
- Timeline shows keyframes after applying Fly/Fade/Pulse.
- PNG export works.
- Frame export works.
- MP4 export shows FFmpeg ready or clean Video Export Pack message.
- Background Remove opens existing background remover flow and inserts cutout as a layer.
- Pack list shows optional packs.
- Install Pack warns cleanly when placeholder release URLs are still in manifests.

## 5. Build executable

```powershell
scripts\build_creative_studio.cmd
```

Expected output:

```text
dist\TTG Creative Studio\TTG Creative Studio.exe
```

## 6. Run built executable

```powershell
"dist\TTG Creative Studio\TTG Creative Studio.exe"
```

Repeat the basic app checks.

## 7. Build small core installer

Open Inno Setup and compile:

```text
installer\creative_studio_core.iss
```

The installer must include only the core app and small resources. Heavy packs remain optional downloads.

## Release rule

Do not mark release-ready until:

- `scripts\test_alpha.cmd` passes.
- Source app launches.
- Built executable launches.
- Core installer installs and launches.
- Optional pack placeholders are replaced with real release URLs or clearly blocked as dev-only.

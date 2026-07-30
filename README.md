# GrainScan

<p align="center">
  <img src="GUI/Mark%20Generation.png" alt="GrainScan — Automated Rice Quality Inspection" width="100%">
</p>

**Automated rice quality inspection** with YOLO image processing and data analytics.

GrainScan detects and classifies individual rice grains from photos or a live camera, measures size metrics, and grades overall sample quality — through a desktop GUI or a Windows installer build.

## Features

- **Grain detection & classification** — Long, Medium, Short, Broken, Discolored
- **Quality scoring** — High / Medium / Low grades from composition rules
- **Desktop GUI** — scan images, view analytics, export reports, train/fine-tune models
- **Live camera capture** — snap frames and run the same analysis pipeline
- **Packaging** — PyInstaller + Inno Setup for a Windows installer

## Quick start

### Requirements

- Windows 10/11 (recommended for the GUI and installer)
- Python 3.9+
- See [docs/SYSTEM_REQUIREMENTS.md](docs/SYSTEM_REQUIREMENTS.md) for hardware notes

### Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
python grainscan.py
```

Or analyze a single image from the CLI:

```bash
python grainscan.py test_main.py path\to\rice_image.jpg
```

Default model weights live in `dataset/` (`weightsV9highres.pt`). Paths are set in `config.json`.

## Project layout

```
GrainScan/
├── grainscan.py            # App launcher (GUI + frozen exe entry)
├── test_gui.py             # Tkinter desktop UI
├── test_main.py            # Detection / measurement pipeline
├── live_camera.py          # Live camera capture
├── quality_assessment.py   # Quality grading logic
├── config.json             # Active model path
├── requirements.txt
├── GUI/                    # Icons, logos, README banner
├── dataset/                # YOLO weights (.pt)
├── docs/                   # Manuals & build guides
├── GrainScan.spec          # PyInstaller spec
├── GrainScan.iss           # Inno Setup script
├── build_exe.bat
└── build_installer.bat
```

## Quality assessment

Samples are scored from class counts (Long / Medium / Short / Broken / Discolored) and mapped to **High**, **Medium**, or **Low** grades.

Details: [docs/QUALITY_ASSESSMENT.md](docs/QUALITY_ASSESSMENT.md)

Smoke-test the grader:

```bash
python test_quality_system.py
```

## Build Windows EXE / installer

```bash
build_exe.bat
build_installer.bat
```

Full packaging notes: [docs/BUILD_EXE.md](docs/BUILD_EXE.md)

## Documentation

| Doc | Description |
|-----|-------------|
| [User Manual](docs/USER_MANUAL.txt) | End-user guide |
| [System Requirements](docs/SYSTEM_REQUIREMENTS.md) | Hardware & software |
| [Quality Assessment](docs/QUALITY_ASSESSMENT.md) | Grading algorithm |
| [Build EXE](docs/BUILD_EXE.md) | Packaging & installer |

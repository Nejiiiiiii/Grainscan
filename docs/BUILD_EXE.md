# Packaging GrainScan as a Windows Executable

This document explains how to turn the GrainScan source tree into a stand-alone
Windows application (`GrainScan.exe`) using **PyInstaller**.

The build produces a folder, **`dist/GrainScan/`**, that contains the
executable plus everything it needs to run on any modern Windows 10 / 11
machine — no Python installation required on the target.

---

## 1. Files added for packaging

| File                  | Purpose                                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------- |
| `grainscan.py`        | Unified launcher. Dispatches to the GUI by default, or to `test_main` worker logic when the GUI re-invokes itself via `subprocess.run([sys.executable, "test_main.py", ...])`. Also fixes up the working directory and Tcl/Tk paths for the frozen build, and hides the helper console window on Windows. |
| `GrainScan.spec`      | PyInstaller spec. Pulls in the heavy ML/imaging dependencies (`ultralytics`, `torch`, `opencv-python`, `scikit-image`, `scikit-learn`, `matplotlib`, `PIL`, `pandas`, `h5py`, …) and excludes the unused TensorFlow stack. |
| `build_exe.bat`       | One-click Windows build script: provisions a fresh build venv, installs `requirements.txt` + PyInstaller, and runs `pyinstaller GrainScan.spec`. |
| `docs/BUILD_EXE.md`   | This file.                                                                               |

> **Note** — the existing `test_gui.py`, `test_main.py`, `live_camera.py`, and
> `quality_assessment.py` files are **not modified**. The launcher works around
> the existing `subprocess.run([sys.executable, "test_main.py", ...])` pattern
> by interpreting `"test_main.py"` as a first CLI argument inside the frozen
> executable.

---

## 2. Prerequisites

1. **Windows 10 / 11 x64**.
2. **Python 3.9 – 3.11** installed (3.9.13 matches the original
   `.venv` exactly, but any 3.9 / 3.10 / 3.11 build works). Download from
   <https://www.python.org/downloads/>. During install, tick:
   - ☑ *Add python.exe to PATH*
   - ☑ *Install py launcher*
3. **~6–8 GB of free disk space** during the build (the heavy dependencies are
   unpacked twice — once into the build venv, once into `dist/`).
4. Internet access on the first run so `pip` can download wheels.

> The pre-existing `.venv` folder in this project is **broken** — it points at
> `C:\Users\Neji\Desktop\Python\Rice\.venv` which no longer exists. The build
> script creates its own fresh venv at `.venv_build/` and leaves your existing
> `.venv` untouched.

---

## 3. Building

### Quick path

From this folder, in a normal `cmd.exe` (not PowerShell):

```
build_exe.bat --clean
```

The `--clean` flag wipes `build/`, `dist/`, and `.venv_build/` before starting
so you get a reproducible build. Drop the flag for incremental rebuilds.

### Manual path (if you'd rather drive `pip` yourself)

```powershell
# 1. Create an isolated build venv
py -3.11 -m venv .venv_build
.\.venv_build\Scripts\Activate.ps1

# 2. Install everything
python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
pip install "pyinstaller>=6.6,<7.0"

# 3. Build
pyinstaller --noconfirm GrainScan.spec
```

When PyInstaller finishes you'll see:

```
dist\
  GrainScan\
    GrainScan.exe        <-- run this
    _internal\           <-- bundled Python runtime, libs, data
    GUI\                 <-- icons (also mirrored into _internal\)
    dataset\             <-- model weights (if you let the spec bundle them)
    config.json
```

Double-click `GrainScan.exe` to launch.

---

## 4. What ends up in the bundle

The spec bundles:

- All Python source files in this folder (`grainscan.py`, `test_gui.py`,
  `test_main.py`, `live_camera.py`, `quality_assessment.py`).
- The entire `GUI/` folder of icons / logos.
- `config.json` (treated as a template — copied next to the executable on
  first launch if one doesn't already exist).
- The default model weights, if present:
  - `dataset/weightsV9.1Object.pt`
  - `dataset/weightsV9highres.pt`
- All transitive native binaries / data files for: `ultralytics`, `torch`,
  `opencv-python`, `Pillow`, `pandas`, `matplotlib`, `scikit-image`,
  `scikit-learn`, `numpy`, `scipy`, `h5py`, `networkx`, `fsspec`, `jinja2`,
  `imageio`, `joblib`.

The spec **excludes** packages listed in `requirements.txt` that aren't
actually imported anywhere in the project:

- `tensorflow`, `tensorflow-intel`, `tensorboard`
- `keras`, `tf_keras`

…and a handful of dev/test/Qt packages. This trims roughly 1 GB off the
bundle.

### Adding more model weights

The spec only bundles two `.pt` files by default. After building, drop any
additional weights into `dist\GrainScan\dataset\` and they'll show up in the
GUI's *Choose Model* screen exactly like during development.

If you'd rather bundle a different default, edit the `_DEFAULT_WEIGHTS` list
at the top of `GrainScan.spec` and rebuild.

---

## 5. Distributing the application

### Option A — portable zip

1. Build with `build_exe.bat --clean`.
2. Zip the entire `dist\GrainScan\` folder (not just `GrainScan.exe` —
   `_internal\` is mandatory).
3. Ship the zip. End users unzip and double-click `GrainScan.exe`.

### Option B — single-file Windows installer (recommended)

After running `build_exe.bat`, you can wrap the bundle into a single
`GrainScan-Setup-X.Y.Z.exe` installer with Inno Setup:

```cmd
build_installer.bat
```

What this produces:

- `installer_output\GrainScan-Setup-1.0.0.exe` (~400 MB, LZMA2/max compressed).
- Installs per-user into `%LOCALAPPDATA%\Programs\GrainScan` by default — **no
  admin rights required**. The user can pick a different folder during the
  wizard (including Program Files if they grant admin).
- Lays out the application so every runtime folder (`GUI\`, `dataset\`,
  `report\`, `runs\`, `analytics_exports\`) lives **at the install root**, not
  hidden inside `_internal\`. Everything GrainScan ever creates — scan
  reports, training runs, exports — stays next to `GrainScan.exe`.
- Creates Start Menu entries (and optional Desktop / Quick Launch shortcuts).
- Ships a standard Add/Remove Programs uninstaller (`unins000.exe`) that
  removes the bundled files but **preserves the user's scan results** in
  `report\`, `runs\`, `analytics_exports\`, and `dataset\` (because those
  folders are marked `uninsneveruninstall` in `GrainScan.iss`).

Prerequisites:

- Inno Setup 6 installed (`winget install -e --id JRSoftware.InnoSetup`).
- The PyInstaller bundle from step A already built at
  `F:\GrainScanBuild\dist\GrainScan\` (or pass `--bundle <other-dir>`).

Override the AppVersion or other defaults from the command line:

```cmd
build_installer.bat --version 1.1.0
build_installer.bat --bundle "F:\GrainScanBuild\dist\GrainScan" --version 1.1.0
build_installer.bat --iscc "C:\Path\To\ISCC.exe"
```

Files added for installer support:

| File                   | Purpose                                                                                |
| ---------------------- | -------------------------------------------------------------------------------------- |
| `GrainScan.iss`        | Inno Setup script. Bundles all icons, models, and user-data folders; writes a clean `config.json` with relative paths via the `[Code]` section. |
| `build_installer.bat`  | One-click installer builder. Auto-locates ISCC.exe. |

---

## 6. Troubleshooting

| Symptom                                                                                            | Fix                                                                                                                                                                                                       |
| -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[ERROR] No working Python 3.9-3.11 found`                                                         | Install Python from python.org and re-run, or pass `--python "C:\Path\To\python.exe"`.                                                                                                                    |
| `pip install` fails on `torch==2.2.2`                                                              | Make sure you're on Python 3.9 / 3.10 / 3.11. `torch==2.2.2` does not have wheels for 3.12+.                                                                                                              |
| `ModuleNotFoundError: ultralytics.utils.X` at runtime                                              | Add the missing submodule to `hiddenimports` inside `GrainScan.spec` and rebuild. The spec already calls `collect_all('ultralytics')`, but a new ultralytics version may introduce dynamic imports.       |
| GUI launches but a black console window flashes briefly                                            | Expected on first run; the launcher hides it within a few milliseconds. The flash happens because PyInstaller currently has no way to *both* hide the console *and* keep stdout usable for worker mode.   |
| `[ERROR] No rice grains detected` for every image                                                  | The bundle could not find a `.pt` model. Copy a known-good weights file into `dist\GrainScan\dataset\` and update `dist\GrainScan\config.json` to point at it.                                             |
| Reports / analytics CSV files don't appear                                                         | The app writes them next to `GrainScan.exe` in `report\`, `runs\`, and `analytics_exports\`. The launcher sets the working directory to the executable's folder, so look there — not in `_internal\`.    |
| Antivirus quarantines `GrainScan.exe`                                                              | PyInstaller bootloaders are sometimes flagged. Either sign the executable, or whitelist the folder. Building with UPX disabled (which the spec already does) reduces false positives.                     |

If you hit a "missing module" error at runtime, the standard fix is to add the
import name to the `hiddenimports` list at the bottom of `GrainScan.spec` and
rebuild.

---

## 7. Cleaning up

```cmd
rmdir /s /q build
rmdir /s /q dist
rmdir /s /q .venv_build
```

That's it. Re-running `build_exe.bat --clean` does the same automatically.

# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the GrainScan rice quality desktop application.

Build (from project root, with PyInstaller installed in the active venv):

    pyinstaller --noconfirm GrainScan.spec

Outputs `dist/GrainScan/GrainScan.exe` together with a `_internal/` directory
containing all bundled dependencies and data files.
"""

from __future__ import annotations

import os
import sys

from PyInstaller.utils.hooks import collect_all


block_cipher = None


# ---------------------------------------------------------------------------
# Resolve project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.dirname(SPEC) if "SPEC" in globals() else os.getcwd())


def _abs(rel: str) -> str:
    return os.path.join(PROJECT_ROOT, rel)


# ---------------------------------------------------------------------------
# Data files to bundle next to the application
# ---------------------------------------------------------------------------
datas: list[tuple[str, str]] = []

# Static GUI assets (icons, logos)
if os.path.isdir(_abs("GUI")):
    datas.append((_abs("GUI"), "GUI"))

# A template config.json — copied to the executable directory on first launch.
if os.path.isfile(_abs("config.json")):
    datas.append((_abs("config.json"), "."))

# Optional: bundle the default model weights if they exist next to the project.
# Comment these out to keep the executable small and ship weights separately.
_DEFAULT_WEIGHTS = [
    "dataset/weightsV9highres.pt",
    "dataset/weightsV9.1Object.pt",
]
for w in _DEFAULT_WEIGHTS:
    if os.path.isfile(_abs(w)):
        datas.append((_abs(w), "dataset"))


# ---------------------------------------------------------------------------
# Heavy third-party libraries — pull in everything they ship so dynamic
# imports inside ultralytics / torch / matplotlib don't fail at runtime.
# ---------------------------------------------------------------------------
binaries: list = []
hiddenimports: list[str] = []

_HEAVY_PACKAGES = [
    "ultralytics",
    "torch",
    "torchvision",
    "cv2",
    "skimage",
    "sklearn",
    "matplotlib",
    "pandas",
    "PIL",
    "h5py",
    "networkx",
    "fsspec",
    "jinja2",
    "imageio",
    "lazy_loader",
    "joblib",
    "scipy",
    "numpy",
]

for _pkg in _HEAVY_PACKAGES:
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        binaries += _b
        hiddenimports += _h
    except Exception as exc:  # noqa: BLE001
        print(f"[GrainScan.spec] WARNING: could not collect {_pkg}: {exc}", file=sys.stderr)


# Make sure tkinter sub-modules referenced dynamically are included.
hiddenimports += [
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "PIL.ImageTk",
    "PIL._tkinter_finder",
    "matplotlib.backends.backend_tkagg",
]

# Local modules that PyInstaller might miss because they're discovered via
# `from test_main import ...` at runtime in the launcher.
hiddenimports += [
    "test_gui",
    "test_main",
    "live_camera",
    "quality_assessment",
]


# ---------------------------------------------------------------------------
# Excludes — keep the binary as small as we can without breaking ultralytics.
# Tensorflow / Keras are listed in requirements.txt but never imported in the
# project, so we drop them. PyQt/PySide are not used. Test/dev frameworks
# don't belong in a production binary.
# ---------------------------------------------------------------------------
excludes = [
    "tensorflow",
    "tensorflow_intel",
    "tensorboard",
    "tensorboardX",
    "keras",
    "tf_keras",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "IPython",
    "ipykernel",
    "jupyter",
    "jupyterlab",
    "notebook",
    "nbconvert",
    "pytest",
    "sphinx",
    "pylint",
    "black",
    "isort",
    "mypy",
]


a = Analysis(
    ["grainscan.py"],
    pathex=[PROJECT_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


_ICON_CANDIDATES = [
    _abs("GUI/logo4.ico"),
    _abs("GUI/icon.ico"),
    _abs("GUI/icon2.ico"),
]
_icon_path = next((p for p in _ICON_CANDIDATES if os.path.isfile(p)), None)


exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GrainScan",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,           # Worker subprocesses need a usable stdout/stderr;
                            # the launcher hides this console on GUI startup.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GrainScan",
)

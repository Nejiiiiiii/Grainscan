"""
GrainScan unified launcher.

When run directly, it opens the Tkinter GUI (test_gui.build_gui).

When invoked with "test_main.py" (or "test_main") as the first CLI argument,
it dispatches to the same logic as running `python test_main.py <image>`. This
lets the GUI's existing `subprocess.run([sys.executable, "test_main.py", ...])`
calls continue to work transparently after the project is packaged with
PyInstaller (where `sys.executable` becomes the bundled GrainScan.exe).

The launcher also normalises the working directory and the Tcl/Tk environment
when running as a frozen executable so that:
  * Relative paths to bundled assets (GUI/, config.json, dataset/) resolve
    correctly regardless of where the user launches the .exe from.
  * tkinter can locate its `tcl` / `tk` runtime that PyInstaller ships next to
    the executable.
"""

from __future__ import annotations

import json
import os
import sys


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _exe_dir() -> str:
    """Directory containing the running .exe (frozen) or this script (source)."""
    if _is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _hide_owned_console() -> None:
    """Hide the console window when we own it (frozen GUI mode on Windows).

    The bundled executable is built with ``console=True`` so that the worker
    mode (`test_main`) can write its JSON output back to the parent process
    over a pipe. When the user double-clicks GrainScan.exe a console window
    appears alongside the GUI which is ugly, so we hide it — but only when
    GrainScan is the sole owner of the console (i.e. not when the user
    launched it from an existing cmd.exe / PowerShell session, where hiding
    the window would also hide their shell).
    """
    if sys.platform != "win32" or not _is_frozen():
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        proc_list = (ctypes.c_uint32 * 8)()
        attached = kernel32.GetConsoleProcessList(proc_list, len(proc_list))
        if attached > 1:
            return

        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            SW_HIDE = 0
            user32.ShowWindow(hwnd, SW_HIDE)
    except Exception:
        pass


def _materialize_bundle_assets(exe_dir: str, meipass: str) -> None:
    """Copy bundled data (GUI/, dataset/, config.json) out of `_MEIPASS` into
    the executable's directory so the GUI's relative paths (``"GUI/icon.png"``,
    ``"dataset/<weights>.pt"``, etc.) resolve correctly.

    This is the part the installer effectively does at install time, but it is
    also needed when the application is distributed as a portable folder.
    Using ``shutil.copytree`` instead of ``os.symlink`` because symlinks on
    Windows require administrator privileges or Developer Mode, which we
    cannot assume the end user has.

    The copy is conditional — it only runs if the destination is missing.
    """
    import shutil

    for sub in ("GUI", "dataset"):
        src = os.path.join(meipass, sub)
        dst = os.path.join(exe_dir, sub)
        if os.path.isdir(src) and not os.path.isdir(dst):
            try:
                shutil.copytree(src, dst)
            except (OSError, shutil.Error):
                pass

    for sub in ("report", "runs", "analytics_exports"):
        try:
            os.makedirs(os.path.join(exe_dir, sub), exist_ok=True)
        except OSError:
            pass

    bundled_cfg = os.path.join(meipass, "config.json")
    local_cfg = os.path.join(exe_dir, "config.json")
    if os.path.isfile(bundled_cfg) and not os.path.isfile(local_cfg):
        try:
            shutil.copyfile(bundled_cfg, local_cfg)
        except OSError:
            pass


def _self_heal_config(exe_dir: str) -> None:
    """If ``config.json`` references model files that don't exist on disk,
    rewrite the keys to point at whichever bundled ``.pt`` weight file we can
    actually find.

    The original ``config.json`` shipped with the source tree contains
    absolute paths to the developer's machine
    (``C:/Users/Neji/Desktop/Python/Rice/dataset/...``) that obviously won't
    exist on an end user's computer. ``test_main.get_model_path`` does have a
    fallback list, but none of its candidates match the file names we ship
    (``weightsV9.1Object.pt`` / ``weightsV9highres.pt``), so without this
    self-heal the YOLO model would fail to load on the first launch.
    """
    cfg_path = os.path.join(exe_dir, "config.json")
    if not os.path.isfile(cfg_path):
        return

    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            data = json.load(fh) or {}
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    dataset_dir = os.path.join(exe_dir, "dataset")
    preferred_order = [
        "weightsV9highres.pt",
        "weightsV9highres - Copy.pt",
        "weightsV9.1Object.pt",
        "weightsV9.1Object - Copy.pt",
        "weightsV8.pt",
        "weightsV6.pt",
        "weightsV4.1.pt",
        "weightsV4.pt",
        "weightsV2.pt",
        "weightsV1.pt",
    ]
    existing = [
        os.path.join(dataset_dir, name)
        for name in preferred_order
        if os.path.isfile(os.path.join(dataset_dir, name))
    ]
    if not existing:
        try:
            for entry in os.listdir(dataset_dir):
                if entry.lower().endswith(".pt"):
                    existing.append(os.path.join(dataset_dir, entry))
        except OSError:
            pass

    if not existing:
        return

    def _as_relative(abs_path: str) -> str:
        try:
            rel = os.path.relpath(abs_path, exe_dir)
        except ValueError:
            return abs_path
        return rel.replace(os.sep, "/")

    primary = _as_relative(existing[0])
    secondary = _as_relative(existing[1] if len(existing) > 1 else existing[0])

    def _resolves(p: object) -> bool:
        if not (isinstance(p, str) and p.strip()):
            return False
        if os.path.isabs(p):
            return os.path.isfile(p)
        return os.path.isfile(os.path.join(exe_dir, p))

    changed = False
    for key, default in (("model_path", primary), ("default_model_path", secondary)):
        if not _resolves(data.get(key)):
            data[key] = default
            changed = True

    if changed:
        try:
            with open(cfg_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except OSError:
            pass


def _bootstrap_frozen_environment() -> None:
    """Prepare cwd and Tcl/Tk env so the bundled app behaves like the source."""
    if not _is_frozen():
        return

    exe_dir = _exe_dir()

    try:
        os.chdir(exe_dir)
    except OSError:
        pass

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and os.path.isdir(meipass):
        tcl_dir = os.path.join(meipass, "tcl")
        tk_dir = os.path.join(meipass, "tk")
        if os.path.isdir(tcl_dir):
            os.environ.setdefault("TCL_LIBRARY", tcl_dir)
        if os.path.isdir(tk_dir):
            os.environ.setdefault("TK_LIBRARY", tk_dir)

        _materialize_bundle_assets(exe_dir, meipass)
        _self_heal_config(exe_dir)


def _run_test_main(image_args: list[str]) -> int:
    """Replicate the `if __name__ == '__main__'` block of test_main.py."""
    from test_main import (
        InferenceError,
        NoRiceDetectedError,
        process_image,
        select_image,
    )

    image_path = image_args[0] if image_args else select_image()
    if not image_path:
        return 0

    try:
        result = process_image(image_path)
        print(json.dumps(result))
        return 0
    except NoRiceDetectedError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    except InferenceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - mirror original behaviour
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _run_gui() -> int:
    from test_gui import build_gui

    build_gui()
    return 0


def _is_worker_invocation(argv: list[str]) -> bool:
    if not argv:
        return False
    first = os.path.basename(argv[0]).lower()
    return first in {"test_main", "test_main.py"}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not _is_worker_invocation(argv):
        _hide_owned_console()

    _bootstrap_frozen_environment()

    if _is_worker_invocation(argv):
        return _run_test_main(argv[1:])

    return _run_gui()


if __name__ == "__main__":
    raise SystemExit(main())

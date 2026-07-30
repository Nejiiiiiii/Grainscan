# GrainScan — System Requirements

**Application:** GrainScan — Automated Rice Quality Inspection with Image Processing and Data Analytics
**Version:** 1.0.0
**Distribution:** Single-file Windows installer (`GrainScan-Setup-1.0.0.exe`, ~402 MB)
**Target platform:** Windows desktop, x86-64 (no GPU required)

---

## 0. Basic system requirements (at a glance)

| Component        | Minimum                                            | Recommended                                  |
| ---------------- | -------------------------------------------------- | -------------------------------------------- |
| **OS**           | Windows 10 (64-bit), build 1809+                   | Windows 11 (64-bit)                          |
| **CPU**          | x86-64 with **AVX2** (Intel Haswell 2013+ / AMD 2015+) | 4-core CPU at 3.0 GHz+ (Intel i5 / Ryzen 5) |
| **RAM**          | 4 GB                                                | 8 GB or more                                 |
| **GPU**          | Not required — training and inference run on CPU   | Any GPU (used only for the Windows desktop / GUI rendering, not ML) |
| **Storage**      | 2 GB free disk space                                | 5 GB free disk space                         |
| **Display**      | 1280 × 720, 24-bit color                            | 1920 × 1080 or higher                        |
| **Input device** | Keyboard and mouse                                  | Keyboard, mouse, and a UVC webcam for the Live Camera feature |
| **Network**      | Not required — the app runs fully offline           | Internet only if you want Ultralytics to auto-download external YOLO base models during training |
| **Privileges**   | Standard user (no admin needed for default install) | Same                                         |
| **Software**     | Nothing — Python, VC++ Redistributable, PyTorch and all other dependencies are bundled in the installer | Same |

> **GPU note.** The shipped installer contains the CPU-only build of PyTorch (`torch 2.2.2+cpu`), so the application uses your CPU for both inference and model training even if your machine has an NVIDIA GPU. A separate CUDA-enabled build can be produced if GPU acceleration is needed — see Section 11 for details.

---

## 0.1 Minimum and Recommended Specifications

The same information as Section 0, presented in the classic Minimum / Recommended layout for easy forwarding to end users.

### Minimum specifications

> *Enough to launch GrainScan and scan rice grain images. Training will work but will be slow.*

- **OS:** Windows 10 (64-bit), build 1809 or later
- **Processor:** Any x86-64 CPU supporting **AVX2** (Intel Haswell 2013+ / AMD Excavator 2015+) — for example, Intel Core i3-4xxx or any newer i3 / i5 / i7 / Ryzen
- **Memory (RAM):** 4 GB
- **Graphics (GPU):** Not required — any DirectX-9-capable adapter for the GUI is sufficient (integrated Intel HD, AMD Vega, etc.)
- **Storage:** 2 GB of free disk space on the install drive
- **Display:** 1280 × 720 resolution, 24-bit color
- **Input device:** Keyboard and mouse
- **Network:** Not required — the application runs fully offline
- **Software:** Nothing — Python, the Visual C++ runtime, PyTorch, and every other dependency are bundled inside `GrainScan-Setup-1.0.0.exe`
- **Privileges:** Standard user account (no administrator password needed for the default per-user install path)

### Recommended specifications

> *Comfortable single-image scans, fast batch scans, and acceptable on-CPU model training (~20–40 min for a small run).*

- **OS:** Windows 11 (64-bit), or fully-updated Windows 10 (64-bit) 22H2
- **Processor:** 4-core / 8-thread x86-64 CPU at 3.0 GHz or higher — for example, Intel Core i5 (10th gen or newer), Intel Core i7, AMD Ryzen 5, or Ryzen 7
- **Memory (RAM):** 8 GB or more
- **Graphics (GPU):** Any modern integrated or discrete GPU; the installer's CPU-only PyTorch build ignores the GPU for ML — see the GPU note above if you want CUDA acceleration on NVIDIA hardware
- **Storage:** 5 GB of free disk space, on an internal SSD ideally (loading PyTorch's ~700 MB of DLLs is much faster from SSD than HDD or USB stick)
- **Display:** 1920 × 1080 (Full HD) or higher, 100–150% DPI scaling
- **Input device:** Keyboard, mouse, and a UVC-compatible webcam (built-in laptop camera or USB webcam) if you intend to use the **Live Camera** feature; 1080p or higher webcam preferred
- **Network:** Optional — only needed if you want Ultralytics to auto-download external YOLO base models the first time you train with a model name that isn't already in `dataset\`
- **Software:** Same as Minimum — everything is still bundled; nothing additional to install

---

## 1. Operating system

| Item                          | Minimum                          | Recommended                  |
| ----------------------------- | -------------------------------- | ---------------------------- |
| OS                            | Windows 10 (64-bit), build 1809+ | Windows 11 (64-bit)          |
| Architecture                  | x86-64 (AMD64)                   | x86-64                       |
| Editions supported            | Home, Pro, Education, Enterprise | Same                         |
| .NET Framework                | Not required                     | —                            |
| Visual C++ Redistributable    | Bundled — no separate install    | —                            |
| Windows update level          | Latest cumulative recommended    | Same                         |

**Not supported:**

- 32-bit Windows (x86)
- Windows 7, 8, or 8.1 — Python 3.11 and `vcruntime140_1.dll` require Windows 10 or newer
- Windows on ARM (ARM64) — PyInstaller and bundled PyTorch/OpenCV wheels are x86-64 only
- Windows Server core editions without desktop experience (no Tk/GUI subsystem)
- macOS and Linux — would require a separate platform build of the installer

---

## 2. CPU

| Item                   | Minimum                                 | Recommended                              |
| ---------------------- | --------------------------------------- | ---------------------------------------- |
| Architecture           | x86-64                                  | x86-64                                   |
| Instruction sets       | SSE2 + SSE4.2 + AVX + **AVX2**          | AVX2 + FMA3 (any modern CPU)             |
| Cores / threads        | 2 cores / 4 threads                     | 4+ cores / 8+ threads                    |
| Clock                  | 2.0 GHz                                 | 3.0 GHz+                                 |
| Example                | Intel Core i3-4xxx (Haswell, 2013)      | Intel Core i5 / Ryzen 5 of any year      |

> **AVX2 is hard-required.** PyTorch 2.2.2 (CPU build) is compiled with AVX2 intrinsics. CPUs older than Intel Haswell (2013) or AMD Excavator (2015) will crash on `import torch`. Almost every laptop or desktop sold since 2014 is fine; only very old Atom / Celeron / older Pentium chips fail.

---

## 3. GPU

GrainScan ships with the **CPU build of PyTorch**. No GPU, no NVIDIA driver, no CUDA, and no cuDNN are required.

- Integrated graphics (Intel UHD, AMD Vega, Apple Silicon under emulation) are sufficient for the GUI — they only render Tkinter widgets and Matplotlib charts.
- A discrete NVIDIA GPU **will not** speed up inference; the bundle has no CUDA binaries. A future build could be re-packaged with the CUDA wheel of PyTorch if GPU acceleration is desired.

---

## 4. Memory (RAM)

| Workload                                 | Minimum free RAM |
| ---------------------------------------- | ---------------- |
| GUI idle (after first launch)            | ~250 MB          |
| Single image scan (≤ 1080p)              | ~600 MB          |
| Single image scan (4K / 12 MP)           | ~1.2 GB          |
| Batch scan of 50 images                  | ~1.5 GB          |
| Model training (`Train Model` screen)    | ~3 GB            |
| Live Camera feed (1080p)                 | ~800 MB          |

| Item                       | Minimum     | Recommended |
| -------------------------- | ----------- | ----------- |
| Installed system RAM       | 4 GB        | 8 GB+       |
| Free RAM before launching  | 1.5 GB      | 4 GB        |

---

## 5. Storage

| Phase                                 | Disk space            |
| ------------------------------------- | --------------------- |
| Installer (`GrainScan-Setup-1.0.0.exe`) | ~402 MB              |
| Install footprint (after wizard runs) | ~1.65 GB              |
| First-launch staging (GUI + dataset copy) | +52 MB             |
| Per scan report (CSV + annotated JPG) | 0.2 – 5 MB per image  |
| Training run artefacts                | 100 MB – 2 GB per run |
| Analytics CSV exports                 | < 1 MB                |
| Recommended free space at install     | **2 GB**              |
| Recommended free space for daily use  | **5 GB**              |

User-generated data lives **next to `GrainScan.exe`** in:

```
%LOCALAPPDATA%\Programs\GrainScan\
  ├── report\               (per-scan CSV + annotated JPG)
  ├── runs\                 (training runs)
  ├── analytics_exports\    (exported analytics CSVs)
  └── dataset\              (model weights, both bundled and user-added)
```

The uninstaller deletes the application but **preserves these four folders** (marked `uninsneveruninstall` in the Inno Setup script).

### Filesystem

- Local NTFS or ReFS disk. The installer can target external drives but the path must remain reachable at launch time.
- USB flash drives work for the install location but will run noticeably slower (PyTorch loads ~700 MB of DLLs at startup; flash speed matters).
- Network shares / OneDrive / Google Drive folders are **not recommended** — high file count (~19 000 files) makes initial sync extremely slow.

---

## 6. Display

| Item                | Minimum                     | Recommended                |
| ------------------- | --------------------------- | -------------------------- |
| Resolution          | 1280 × 720                  | 1920 × 1080 or higher       |
| Color depth         | 24-bit                       | 32-bit                     |
| DPI scaling         | 100%                         | 100% – 150%                 |
| Multi-monitor       | Supported                    | Supported                  |

Tkinter's high-DPI handling is rudimentary; at 200%+ scaling some labels appear small. Set the display scale to **125% or 150%** for the best balance of UI size and screen real estate.

---

## 7. Input devices

| Device          | Required for                            | Notes                                                                 |
| --------------- | --------------------------------------- | --------------------------------------------------------------------- |
| Keyboard, mouse | All features                             | —                                                                     |
| Touchscreen     | Optional                                 | The Tkinter GUI works with touch but is not optimised for it.         |
| Webcam          | "Live Camera" feature only               | Any UVC-compatible camera (built-in laptop camera, USB webcam, etc.). |

### Camera details (Live Camera feature)

| Property                  | Value                                                          |
| ------------------------- | -------------------------------------------------------------- |
| Driver model              | USB Video Class (UVC) — Windows built-in driver is sufficient  |
| Preferred resolution      | 4K UHD (3840 × 2160) if supported, falls back automatically to 1440p → 1080p → 720p → SVGA → VGA |
| Frame rate                | Any (capture is single-frame on user "Capture" press)           |
| Lighting                  | Bright, even, diffuse lighting on a uniform background          |
| Background                | Single-colour (white sheet of paper / plain table) recommended  |

A typical built-in laptop webcam (720p / 1080p) is sufficient for prototyping; a 4K USB webcam improves the detection accuracy of small / discoloured grains.

---

## 8. Network

GrainScan is fully **offline-capable**.

| Activity                       | Network required? |
| ------------------------------ | ----------------- |
| Installer                      | No                |
| Application launch             | No                |
| Image scan, batch scan         | No                |
| Live Camera capture            | No                |
| Quality assessment, reports    | No                |
| Analytics export               | No                |
| **Model training**             | **Sometimes**     |
| Telemetry / phone-home         | None              |

> *Training note:* the bundled `ultralytics` library will only contact the internet if you choose a starting model that is *not* present in `dataset\`. It tries to auto-download official YOLO weights from Ultralytics' Hugging Face mirror. Pre-populate `dataset\yolov8n-seg.pt` (or another `.pt` you trust) to keep training fully offline.

---

## 9. Privileges and permissions

| Action                                            | Privilege                          |
| ------------------------------------------------- | ---------------------------------- |
| Run the installer (default location)              | Standard user — no UAC prompt      |
| Run the installer (Program Files location)        | Administrator — UAC elevation      |
| Launch GrainScan                                  | Standard user                      |
| Read & write inside the install folder            | Standard user (granted by installer) |
| Use the webcam                                    | Standard user — but Windows 10/11 may prompt the first time per the Camera privacy setting under Settings → Privacy → Camera |
| Uninstall                                         | Same privilege level as the install |

---

## 10. Security / antivirus interactions

| Software                  | Likely behaviour                                                                 | Workaround                                                                 |
| ------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Windows Defender SmartScreen | "Windows protected your PC" on first run because the installer is unsigned    | Click **More info → Run anyway**. Persists until you obtain a code-signing certificate. |
| Windows Defender (real-time)  | Scans the installer (~30–90 s) then allows it. No quarantining observed.     | Add `%LOCALAPPDATA%\Programs\GrainScan\` to scan exclusions for faster launch. |
| Third-party AV (e.g. Avast, Bitdefender, McAfee) | Some occasionally flag PyInstaller's bootloader as suspicious heuristic | Whitelist the install folder; the spec already builds without UPX to minimise this. |
| Corporate AppLocker / SRP  | May block unsigned executables                                                  | Have IT sign the binary or whitelist the publisher hash.                  |
| Group Policy: ASR rules   | Some Attack Surface Reduction rules block scripts executing from `%LOCALAPPDATA%` | Either install to `Program Files` (admin) or have IT add an exclusion.    |

---

## 11. Bundled runtime stack

The installer is self-contained. The target machine **does not** need any of these installed separately — they're shipped inside `_internal\` next to the executable.

| Component                              | Version             | Size (compressed) |
| -------------------------------------- | ------------------- | ----------------- |
| Python                                 | 3.11.9              | ~30 MB            |
| Microsoft VC++ Redistributable         | 14.x runtime DLLs   | ~2 MB             |
| Tcl/Tk (Tkinter backend)               | 8.6                 | ~6 MB             |
| PyTorch                                | 2.2.2 (CPU build)   | ~244 MB           |
| TorchVision                            | 0.17.2              | ~6 MB             |
| Ultralytics YOLO                       | 8.3.99              | ~1 MB Python + ~10 MB models |
| OpenCV (`opencv-python`)               | 4.11.0.86           | ~70 MB            |
| NumPy                                  | 1.26.4 (build venv) / 2.4.4 (bundled by ultralytics) | ~16 MB |
| SciPy                                  | 1.17.1              | ~40 MB            |
| scikit-image                           | 0.26.0              | ~30 MB            |
| scikit-learn                           | 1.8.0               | ~30 MB            |
| Pandas                                 | 3.0.3               | ~12 MB            |
| Matplotlib                             | 3.10.9              | ~25 MB            |
| Pillow (PIL)                           | 12.2.0              | ~3 MB             |
| h5py                                   | 3.16.0              | ~3 MB             |
| Joblib, threadpoolctl, sympy, networkx, …| latest at build time | ~30 MB            |

Total bundled native + Python footprint after extraction: **~1.6 GB**.

Excluded from the bundle (listed in `requirements.txt` but never imported by the application code): TensorFlow, Keras, TensorBoard. Removing these saves roughly 1 GB.

---

## 12. Supported input / output formats

### Image inputs

| Property              | Value                                                |
| --------------------- | ---------------------------------------------------- |
| Extensions            | `.jpg`, `.jpeg`, `.png`, `.bmp`                       |
| Color space           | RGB / BGR (auto-handled)                              |
| Bit depth             | 8-bit per channel                                     |
| Min resolution        | 320 × 240 (smaller will still run but accuracy drops) |
| Max resolution        | Auto-downscaled to 1920 × 1080 for inference (4K supported for camera capture, then resized) |
| Aspect ratio          | Any                                                    |
| EXIF                  | Honoured for rotation                                  |

### Outputs

| Artifact                                  | Format               | Location                  |
| ----------------------------------------- | -------------------- | ------------------------- |
| Per-scan detection report                 | CSV                  | `report\measurements_<image>.csv` |
| Per-scan annotated image                  | JPEG                  | `report\measurements_<image>.jpg` |
| Batch report                               | CSV + per-image JSON  | `report\`                  |
| Training run                               | folder with `weights\best.pt`, `last.pt`, metrics | `runs\<run_name>\` |
| Analytics export                          | CSV                  | `analytics_exports\<timestamp>.csv` |
| Quality grade JSON (in-memory)            | JSON                 | (printed to stdout by `test_main`) |

---

## 13. Performance expectations (CPU build)

These are rough numbers on a modern mid-range laptop CPU (Intel i5-1240P / Ryzen 5 5600U class). Older CPUs scale roughly linearly with single-thread performance.

| Operation                                        | Typical time        |
| ------------------------------------------------ | ------------------- |
| Cold app launch (first time after install)       | 8 – 12 s            |
| Warm app launch (subsequent launches)            | 4 – 7 s             |
| Single image scan (1920 × 1080)                  | 1 – 3 s             |
| Single image scan (4K capture)                   | 3 – 6 s             |
| Batch scan, per image                            | 1 – 3 s             |
| Model training, 50 epochs, 640 px, 100 images    | 20 – 40 min         |
| Live camera viewfinder                           | 15 – 30 fps         |

---

## 14. Compatibility matrix (tested / expected)

| Configuration                                      | Status              |
| -------------------------------------------------- | ------------------- |
| Windows 11 22H2, x64, 16 GB RAM, Ryzen 7           | ✅ Verified         |
| Windows 11 24H2, x64, 8 GB RAM, Intel i5-1240P     | ✅ Expected to work  |
| Windows 10 22H2, x64, 8 GB RAM                     | ✅ Expected to work  |
| Windows 10 1809 LTSC                               | ⚠️  Should work; AVX2 CPU required |
| Windows 10 1607 (pre-1809)                         | ❌ Missing UCRT updates required by Python 3.11 |
| Windows on ARM (Surface Pro X, etc.) via emulation | ❌ AMD64 emulation cannot run AVX2 instructions reliably |
| Windows Server 2019 / 2022 (with Desktop Experience) | ⚠️  Should work; not tested |
| Wine on Linux                                      | ⚠️  PyTorch + Tk may run but not officially supported |

---

## 15. Quick checklist for end users

Before sending GrainScan to a user, confirm their machine has:

- [ ] Windows 10 or 11, **64-bit**
- [ ] CPU made in 2013 or later (supports **AVX2**)
- [ ] **4 GB** RAM (8 GB recommended)
- [ ] **2 GB** free disk space on `C:` (or wherever they install)
- [ ] An account that can install per-user software (no admin needed for default install)
- [ ] A webcam — only if they want to use the *Live Camera* feature

That's the whole list. They double-click `GrainScan-Setup-1.0.0.exe`, the wizard runs for ~5–10 minutes (extracting 1.6 GB takes the bulk of the time), and they're done.

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import subprocess
import os
import shutil
import csv
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime
import live_camera  # Import the live camera module
import sys
import json
from quality_assessment import RiceQualityAssessor
import zipfile
import threading
import tempfile
import time
from ultralytics import YOLO
import re


# Define color scheme
COLORS = {
    'primary': '#B7C02B',      # Original green
    'secondary': '#a4ad29',    # Darker green for hover
    'accent': '#E74C3C',       # Red for errors
    'background': '#FFFFFF',   # White
    'text': '#2C3E50',         # Dark blue-gray for text
    'white': '#FFFFFF',        # White
    'success': '#27AE60',      # Green for success/Long grains
    'warning': '#F1C40F',      # Yellow for warnings
    'error': '#E74C3C',        # Red for errors/Broken grains
    'card_bg': '#F8F9FA',      # Light gray for cards
    'border': '#E9ECEF',       # Border color
    'hover': '#F1F3F5',        # Hover state color
    'shadow': '#E2E6EA',       # Shadow color
    'orange': '#FF8C00',       # Orange for Medium grains
    'purple': '#B400B4'        # Purple for Discolored grains
}

def create_rounded_button(parent, text, command, bg=COLORS['primary'], fg=COLORS['white'], icon_path=None, compact=False):
    # Create a frame to hold the button (for shadow effect)
    button_frame = tk.Frame(parent, bg=bg if compact else COLORS['primary'])
    if compact:
        button_frame.pack(pady=5)
    else:
        button_frame.pack(fill='x', pady=5)
    
    # Add icon if provided
    icon_img = None
    if icon_path and os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path)
            icon = icon.resize((24, 24), Image.LANCZOS)
            icon_img = ImageTk.PhotoImage(icon)
        except Exception as e:
            print(f"Error loading icon {icon_path}: {str(e)}")
            icon_img = None
    
    # Create the actual button
    button = tk.Button(
        button_frame,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        font=('Helvetica', 12, 'bold'),
        relief='flat',
        bd=0,
        cursor='hand2',
        image=icon_img,
        compound='left',
        padx=18,
        anchor='center' if compact else 'w',
        justify='center' if compact else 'left',
        highlightthickness=0
    )
    if icon_img:
        button.image = icon_img  # Keep reference
    
    # Add rounded corners and border for compact button
    if compact:
        button.configure(
            highlightbackground=bg,
            highlightcolor=bg,
            borderwidth=0,
            relief='flat',
            padx=20,
            pady=8
        )
        button.configure(
            activebackground=COLORS['secondary'],
            activeforeground=fg
        )
        # Add a border frame for rounded effect
        button_frame.configure(bg=COLORS['white'], highlightbackground=COLORS['border'], highlightthickness=1)
        button.pack(padx=2, pady=2)
    else:
        # Sidebar style
        def on_enter(e):
            button.configure(bg=COLORS['secondary'])
            button.configure(highlightbackground=COLORS['shadow'], highlightthickness=1)
        def on_leave(e):
            button.configure(bg=COLORS['primary'])
            button.configure(highlightbackground=COLORS['primary'], highlightthickness=0)
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)
        button.pack(fill='x', padx=0, pady=2)
    return button_frame

def create_card(parent, bg=COLORS['card_bg']):
    # Create a frame with rounded corners and shadow effect
    card = tk.Frame(parent, bg=bg, padx=20, pady=20)
    card.configure(highlightbackground=COLORS['border'], highlightthickness=1)
    return card

def create_style():
    style = ttk.Style()
    style.theme_use('clam')
    
    # Configure Treeview
    style.configure("Treeview",
                   background=COLORS['white'],
                   foreground=COLORS['text'],
                   rowheight=25,
                   fieldbackground=COLORS['white'])
    style.map('Treeview',
              background=[('selected', COLORS['primary'])],
              foreground=[('selected', COLORS['white'])])
    
    # Configure Notebook
    style.configure("TNotebook",
                   background=COLORS['background'],
                   borderwidth=0)
    style.configure("TNotebook.Tab",
                   background=COLORS['white'],
                   foreground=COLORS['text'],
                   padding=[10, 5],
                   font=('Helvetica', 10))
    style.map("TNotebook.Tab",
              background=[("selected", COLORS['primary'])],
              foreground=[("selected", COLORS['white'])])
    
    # Configure LabelFrame
    style.configure("TLabelframe",
                   background=COLORS['background'],
                   foreground=COLORS['text'])
    style.configure("TLabelframe.Label",
                   background=COLORS['background'],
                   foreground=COLORS['text'],
                   font=('Helvetica', 10, 'bold'))

# Progress helpers

def create_progress_window(title="Processing", mode="indeterminate", maximum=100):
    win = tk.Toplevel(root)
    win.title(title)
    win.configure(bg=COLORS['background'])
    win.resizable(False, False)
    # Center relative to root
    win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - 150
    y = root.winfo_y() + (root.winfo_height() // 2) - 40
    win.geometry(f"300x80+{x}+{y}")

    lbl = tk.Label(win, text=title, bg=COLORS['background'], fg=COLORS['text'], font=('Helvetica', 11))
    lbl.pack(pady=(12, 6))

    bar = ttk.Progressbar(win, orient='horizontal', length=260, mode=mode, maximum=maximum)
    bar.pack(pady=(0, 12))
    win.update_idletasks()
    return win, bar, lbl

def close_progress_window(win):
    try:
        win.destroy()
    except Exception:
        pass

def browse_image():
    global status_label
    file_path = filedialog.askopenfilename(
        title="Insert Rice Grain",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
    )
    if not file_path:
        return

    status_label.config(text="Processing image...", fg=COLORS['primary'])
    root.update()

    try:
        # Show progress window (indeterminate)
        prog_win, prog_bar, prog_lbl = create_progress_window("Scanning image...", mode="indeterminate")
        try:
            prog_bar.start(10)
        except Exception:
            pass
        root.update()

        # Run detector; set env so it doesn't open a blocking cv2 window
        env = os.environ.copy()
        env["GRAINSCAN_GUI"] = "1"
        result = subprocess.run(
            [sys.executable if 'sys' in globals() else r"C:\\Users\\Neji\\Desktop\\Python\\Rice\\.venv\\Scripts\\python.exe", "test_main.py", file_path],
            capture_output=True, text=True, env=env
        )

        # Handle return codes first
        if result.returncode == 0:
            status_label.config(text="Processing complete ✔", fg=COLORS['success'])
            # Parse JSON summary from stdout
            summary = None
            try:
                summary = json.loads(result.stdout.strip())
                show_result_window(summary)
            except json.JSONDecodeError as e:
                messagebox.showerror("JSON Error", f"Failed to parse JSON response: {str(e)}")
                return
            except Exception as e:
                messagebox.showerror("Error", f"Unexpected error parsing response: {str(e)}")
                return

        elif result.returncode == 3:
            status_label.config(text="❌ No rice grains detected", fg=COLORS['error'])
            messagebox.showerror("No Rice Detected", "No rice grains were detected. Please use a clear rice grain image.")
        elif result.returncode == 2:
            status_label.config(text="❌ Model inference failed", fg=COLORS['error'])
            messagebox.showerror("Model Error", "The model failed during inference. Please check the weights path or try another image.")
        else:
            status_label.config(text="❌ Processing failed", fg=COLORS['error'])
            message = result.stderr.strip() or "Unknown error."
            messagebox.showerror("Error", f"An error occurred while processing the image:\n\n{message}")

    except Exception as e:
        status_label.config(text="❌ Processing failed", fg=COLORS['error'])
        messagebox.showerror("Error", f"An error occurred while processing the image: {str(e)}")
    finally:
        try:
            prog_bar.stop()
        except Exception:
            pass
        try:
            close_progress_window(prog_win)
        except Exception:
            pass


def browse_images_batch_files():
    files = filedialog.askopenfilenames(
        title="Select Rice Grain Images",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
    )
    if not files:
        return
    process_batch(list(files))


def browse_images_batch_folder():
    folder = filedialog.askdirectory(title="Select Folder Containing Rice Grain Images")
    if not folder:
        return
    exts = (".jpg", ".jpeg", ".png", ".bmp")
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)]
    if not files:
        messagebox.showwarning("No Images", "No supported image files found in the selected folder.")
        return
    process_batch(files)


def process_batch(files):
    global status_label
    status_label.config(text=f"Processing batch of {len(files)} images...", fg=COLORS['primary'])
    root.update()

    # Ensure GUI mode for subprocesses
    env = os.environ.copy()
    env["GRAINSCAN_GUI"] = "1"

    combined_rows = []
    errors = []
    annotated_images = []
    batch_items = []

    # Progress window (determinate)
    prog_win, prog_bar, prog_lbl = create_progress_window("Batch scanning...", mode="determinate", maximum=len(files))
    try:
        prog_bar['value'] = 0
    except Exception:
        pass
    root.update_idletasks()

    for file_path in files:
        try:
            result = subprocess.run(
                [sys.executable if 'sys' in globals() else r"C:\\Users\\Neji\\Desktop\\Python\\Rice\\.venv\\Scripts\\python.exe", "test_main.py", file_path],
                capture_output=True, text=True, env=env
            )
            if result.returncode != 0:
                errors.append((file_path, result.stderr.strip()))
                # still advance progress and continue
            else:
                # Read the saved CSV for this image and accumulate
                base_name = os.path.basename(file_path)
                csv_name = f"measurements_{os.path.splitext(base_name)[0]}.csv"
                csv_path = os.path.join("report", csv_name)
                if os.path.exists(csv_path):
                    try:
                        df = pd.read_csv(csv_path)
                        combined_rows.append(df)
                        # Capture annotated image path if available
                        jpg_name = f"measurements_{os.path.splitext(base_name)[0]}.jpg"
                        jpg_path = os.path.join("report", jpg_name)
                        if os.path.exists(jpg_path):
                            annotated_images.append(jpg_path)
                        # Per-image quick assessment for organized batch report
                        try:
                            assessor_item = RiceQualityAssessor()
                            item_result = assessor_item.get_detailed_analysis(df)
                            batch_items.append({
                                'file': os.path.basename(file_path),
                                'csv_path': csv_path,
                                'image_path': jpg_path if os.path.exists(jpg_path) else '',
                                'grade': item_result.get('grade', 'Unknown'),
                                'total': item_result.get('total', 0),
                                'counts': item_result.get('counts', {}),
                                'percents': item_result.get('percents', {})
                            })
                        except Exception:
                            pass
                    except Exception as e:
                        errors.append((file_path, f"CSV read error: {str(e)}"))
                else:
                    errors.append((file_path, "CSV not found after processing"))
        except Exception as e:
            errors.append((file_path, str(e)))

        # Update progress
        try:
            prog_bar['value'] = min(prog_bar['value'] + 1, prog_bar['maximum'])
            prog_lbl.config(text=f"Batch scanning... {int(prog_bar['value'])}/{int(prog_bar['maximum'])}")
            prog_win.update_idletasks()
        except Exception:
            pass

    if not combined_rows:
        status_label.config(text="❌ Batch processing failed", fg=COLORS['error'])
        message = "\n".join([f"{os.path.basename(fp)}: {err}" for fp, err in errors]) or "No valid results."
        messagebox.showerror("Batch Error", f"Could not process any images in the batch.\n\n{message}")
        try:
            close_progress_window(prog_win)
        except Exception:
            pass
        return

    combined_df = pd.concat(combined_rows, ignore_index=True)
    assessor = RiceQualityAssessor()
    quality_result = assessor.get_detailed_analysis(combined_df)
    quality_result['annotated_image_path'] = None
    if annotated_images:
        quality_result['annotated_images'] = annotated_images
    if batch_items:
        quality_result['batch_items'] = batch_items
    quality_result['explanation'] = f"Batch result across {len(files)} image(s). " + quality_result.get('explanation', '')

    # Write batch manifest for Reports organization
    try:
        os.makedirs("report", exist_ok=True)
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        manifest = {
            'batch_id': batch_id,
            'created_at': batch_id,
            'items': batch_items
        }
        manifest_path = os.path.join('report', f'batch_{batch_id}.json')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        quality_result['batch_manifest'] = manifest_path
    except Exception:
        pass

    status_label.config(text="Batch processing complete ✔", fg=COLORS['success'])
    try:
        close_progress_window(prog_win)
    except Exception:
        pass
    show_result_window(quality_result)


def show_result_window(summary):
    # summary keys: grade, explanation, total, counts{}, percents{}, annotated_image_path, score, premium_percent
    top = tk.Toplevel(root)
    top.title("Scan Result - Rice Quality Assessment")
    top.configure(bg=COLORS['background'])
    
    # Make the window larger and more prominent
    # Get screen dimensions
    screen_width = top.winfo_screenwidth()
    screen_height = top.winfo_screenheight()
    
    # Set window size to 80% of screen size for better visibility
    window_width = int(screen_width * 0.8)
    window_height = int(screen_height * 0.8)
    
    # Calculate position for center of screen
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    
    # Set window size and position
    top.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Make window resizable
    top.resizable(True, True)

    # Create scrollable container for better content management
    canvas = tk.Canvas(top, bg=COLORS['background'], highlightthickness=0)
    scrollbar = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLORS['background'])

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Pack scrollbar and canvas
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    # Add mouse wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    # Unbind mouse wheel when window is closed
    def on_closing():
        canvas.unbind_all("<MouseWheel>")
        top.destroy()
    
    top.protocol("WM_DELETE_WINDOW", on_closing)

    # Card container
    card = create_card(scrollable_frame, bg=COLORS['white'])
    card.pack(fill="both", expand=True, padx=20, pady=20)

    # 1) Big grade with score
    grade = summary.get("grade", "Unknown")
    score = summary.get("score", 0.0)
    color = COLORS['success'] if grade == "High" else (COLORS['warning'] if grade == "Medium" else COLORS['error'])
    
    grade_frame = tk.Frame(card, bg=COLORS['white'])
    grade_frame.pack(anchor="w", pady=(0, 10))
    
    tk.Label(grade_frame, text=f"Overall Quality: {grade}",
             font=("Helvetica", 22, "bold"), bg=COLORS['white'], fg=color).pack(side="left")
    
    if score > 0:
        tk.Label(grade_frame, text=f" (Score: {score:.3f})",
                 font=("Helvetica", 16), bg=COLORS['white'], fg=COLORS['text']).pack(side="left", padx=(10, 0))

    # 2) One-line explanation
    tk.Label(card, text=summary.get("explanation", ""),
             font=("Helvetica", 12), bg=COLORS['white'], fg=COLORS['text']).pack(anchor="w", pady=(4, 12))

    # 3) Detailed breakdown
    counts = summary.get("counts", {})
    perc = summary.get("percents", {})
    premium_percent = summary.get("premium_percent", 0)
    
    # Quality breakdown frame
    breakdown_frame = tk.Frame(card, bg=COLORS['card_bg'])
    breakdown_frame.pack(fill="x", pady=(0, 12))
    
    # Premium grains section
    premium_frame = tk.Frame(breakdown_frame, bg=COLORS['card_bg'])
    premium_frame.pack(fill="x", pady=(10, 5))
    tk.Label(premium_frame, text="Premium Grains:", font=("Helvetica", 14, "bold"), 
             bg=COLORS['card_bg'], fg=COLORS['success']).pack(anchor="w")
    
    premium_line = tk.Frame(premium_frame, bg=COLORS['card_bg'])
    premium_line.pack(anchor="w", pady=(2, 0))
    tk.Label(premium_line, text=f"Long + Medium: {counts.get('Long',0)+counts.get('Medium',0)} grains ({premium_percent:.1f}%)", 
             font=("Helvetica", 12), bg=COLORS['card_bg'], fg=COLORS['text']).pack(anchor="w")
    
    # Defect grains section (Broken + Discolored only)
    defect_frame = tk.Frame(breakdown_frame, bg=COLORS['card_bg'])
    defect_frame.pack(fill="x", pady=(10, 5))
    tk.Label(defect_frame, text="Defect Grains:", font=("Helvetica", 14, "bold"), 
             bg=COLORS['card_bg'], fg=COLORS['error']).pack(anchor="w")
    
    defect_lines = [
        f"Broken grains: {counts.get('Broken',0)} ({perc.get('Broken',0):.1f}%)",
        f"Discolored grains: {counts.get('Discolored',0)} ({perc.get('Discolored',0):.1f}%)"
    ]
    
    for line in defect_lines:
        tk.Label(defect_frame, text=line, font=("Helvetica", 12), 
                bg=COLORS['card_bg'], fg=COLORS['text']).pack(anchor="w", pady=(2, 0))
    
    # Total grains
    total_frame = tk.Frame(breakdown_frame, bg=COLORS['card_bg'])
    total_frame.pack(fill="x", pady=(10, 0))
    tk.Label(total_frame, text=f"Total grains analyzed: {summary.get('total',0)}", 
             font=("Helvetica", 12, "bold"), bg=COLORS['card_bg'], fg=COLORS['primary']).pack(anchor="w")

    # 4) (Removed) Batch items summary table – navigation via next/previous is sufficient

    # 5) Annotated image(s) display with optional batch carousel
    annotated_list = summary.get("annotated_images")
    if annotated_list and isinstance(annotated_list, list) and len(annotated_list) > 0:
        # Batch carousel
        images = [p for p in annotated_list if os.path.exists(p)]
        if images:
            image_frame = tk.Frame(card, bg=COLORS['white'], relief='solid', bd=1)
            image_frame.pack(fill="x", pady=(12, 8))
            tk.Label(image_frame, text="Detected Rice Grains Analysis", 
                     font=("Helvetica", 14, "bold"), bg=COLORS['white'], fg=COLORS['primary']).pack(pady=(8, 4))

            display_label = tk.Label(image_frame, bg=COLORS['white'])
            display_label.pack(pady=(4, 8))

            info_label = tk.Label(image_frame, font=("Helvetica", 10), bg=COLORS['white'], fg=COLORS['text'])
            info_label.pack(pady=(0, 8))

            nav_frame = tk.Frame(image_frame, bg=COLORS['white'])
            nav_frame.pack(pady=(0, 10))

            idx = {'i': 0}

            def render_current():
                try:
                    path = images[idx['i']]
                    img = Image.open(path)
                    w, h = img.size
                    max_w, max_h = 1200, 600
                    scale = min(max_w / w, max_h / h, 1.0)
                    img_disp = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img_disp)
                    display_label.configure(image=tk_img)
                    display_label.image = tk_img
                    info_label.configure(text=f"{os.path.basename(path)}  ({idx['i']+1}/{len(images)})  -  Original: {w}×{h}  Display: {int(w*scale)}×{int(h*scale)}")
                except Exception as e:
                    info_label.configure(text=f"Error loading image: {str(e)}")

            # Click to maximize current batch image
            def on_display_click(event=None):
                try:
                    path = images[idx['i']]
                    img = Image.open(path)
                    w, h = img.size
                    top = tk.Toplevel(root)
                    top.title("Maximized Report Image")
                    screen_w = top.winfo_screenwidth()
                    screen_h = top.winfo_screenheight()
                    scale_max = min((screen_w-100) / w, (screen_h-100) / h, 1.0)
                    img_max = img.resize((int(w * scale_max), int(h * scale_max)), Image.LANCZOS)
                    img_max_tk = ImageTk.PhotoImage(img_max)
                    label = tk.Label(top, image=img_max_tk, bg=COLORS['background'])
                    label.image = img_max_tk
                    label.pack(expand=True)
                    top.update_idletasks()
                    x = (screen_w - top.winfo_width()) // 2
                    y = (screen_h - top.winfo_height()) // 2
                    top.geometry(f"+{x}+{y}")
                except Exception:
                    pass

            display_label.bind("<Button-1>", on_display_click)

            def go_prev():
                if len(images) == 0:
                    return
                idx['i'] = (idx['i'] - 1) % len(images)
                render_current()

            def go_next():
                if len(images) == 0:
                    return
                idx['i'] = (idx['i'] + 1) % len(images)
                render_current()

            prev_btn = tk.Button(nav_frame, text="◀ Previous", command=go_prev, bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'), relief='flat', padx=12, pady=6, cursor='hand2')
            next_btn = tk.Button(nav_frame, text="Next ▶", command=go_next, bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'), relief='flat', padx=12, pady=6, cursor='hand2')
            prev_btn.pack(side='left', padx=6)
            next_btn.pack(side='left', padx=6)

            render_current()
    else:
        img_path = summary.get("annotated_image_path")
        if img_path and os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                
                # Show full image instead of cropping
                w, h = img.size
                
                # Calculate optimal display size - make it larger and more prominent
                # Use more screen real estate for the image
                max_w, max_h = 1200, 600
                scale = min(max_w / w, max_h / h, 1.0)
                
                # Resize image for display
                img_disp = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                tk_img = ImageTk.PhotoImage(img_disp)
                
                # Create a frame for the image with better styling
                image_frame = tk.Frame(card, bg=COLORS['white'], relief='solid', bd=1)
                image_frame.pack(fill="x", pady=(12, 8))
                
                # Add a title for the image
                tk.Label(image_frame, text="Detected Rice Grains Analysis", 
                         font=("Helvetica", 14, "bold"), bg=COLORS['white'], fg=COLORS['primary']).pack(pady=(8, 4))
                
                # Display the image
                panel = tk.Label(image_frame, image=tk_img, bg=COLORS['white'])
                panel.image = tk_img
                panel.pack(pady=(4, 8))
                
                # Click to maximize single image
                def on_single_click(event=None, _img=img, _w=w, _h=h):
                    try:
                        top = tk.Toplevel(root)
                        top.title("Maximized Report Image")
                        screen_w = top.winfo_screenwidth()
                        screen_h = top.winfo_screenheight()
                        scale_max = min((screen_w-100) / _w, (screen_h-100) / _h, 1.0)
                        img_max = _img.resize((int(_w * scale_max), int(_h * scale_max)), Image.LANCZOS)
                        img_max_tk = ImageTk.PhotoImage(img_max)
                        label = tk.Label(top, image=img_max_tk, bg=COLORS['background'])
                        label.image = img_max_tk
                        label.pack(expand=True)
                        top.update_idletasks()
                        x = (screen_w - top.winfo_width()) // 2
                        y = (screen_h - top.winfo_height()) // 2
                        top.geometry(f"+{x}+{y}")
                    except Exception:
                        pass

                panel.bind("<Button-1>", on_single_click)

                # Add image info
                info_text = f"Image size: {w}×{h} pixels | Display size: {int(w * scale)}×{int(h * scale)} pixels"
                tk.Label(image_frame, text=info_text, 
                         font=("Helvetica", 10), bg=COLORS['white'], fg=COLORS['text']).pack(pady=(0, 8))
            except Exception as e:
                # Show error message if image loading fails
                error_frame = tk.Frame(card, bg=COLORS['white'])
                error_frame.pack(fill="x", pady=(12, 8))
                tk.Label(error_frame, text="⚠️ Could not load analysis image", 
                         font=("Helvetica", 12), bg=COLORS['white'], fg=COLORS['error']).pack()
                tk.Label(error_frame, text=f"Error: {str(e)}", 
                         font=("Helvetica", 10), bg=COLORS['white'], fg=COLORS['text']).pack()

    # Close button
    close_btn = tk.Button(card, text="Close", command=on_closing, bg=COLORS['primary'], fg=COLORS['white'],
                          font=('Helvetica', 11, 'bold'), relief='flat', padx=16, pady=8, cursor='hand2')
    close_btn.pack(pady=(14,0), anchor="e")


def start_live_camera():
    global status_label
    status_label.config(text="Starting live camera...", fg=COLORS['primary'])
    root.update()
    try:
        # Pass the GUI callbacks so capture shows result window and errors display in GUI
        def on_no_rice():
            try:
                messagebox.showerror("No Rice Detected", "No rice grains were detected. Please use a clear rice grain image.")
            except Exception:
                pass
        success = live_camera.start_live_camera(show_result_window, on_no_rice)
        if success:
            status_label.config(text="Live camera session ended", fg=COLORS['success'])
        else:
            status_label.config(text="❌ Live camera failed", fg=COLORS['error'])
            messagebox.showerror("Camera Error", "Failed to start live camera. Please ensure your camera is connected and not in use by another application.")
    except Exception as e:
        status_label.config(text="❌ Live camera failed", fg=COLORS['error'])
        messagebox.showerror("Error", f"An error occurred while using the live camera: {str(e)}")

def show_analytics():
    # Clear main content
    for widget in main.winfo_children():
        widget.destroy()

    # --- Scrollable canvas setup ---
    canvas = tk.Canvas(main, bg=COLORS['background'], highlightthickness=0)
    canvas.pack(side='left', fill='both', expand=True)
    vscroll = tk.Scrollbar(main, orient='vertical', command=canvas.yview)
    vscroll.pack(side='right', fill='y')
    canvas.configure(yscrollcommand=vscroll.set)

    # Mouse wheel scrolling (cross-platform)
    def _on_mousewheel(event):
        if event.num == 5 or event.delta == -120:
            canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            canvas.yview_scroll(-1, "units")
    canvas.bind_all('<MouseWheel>', _on_mousewheel)      # Windows, Mac
    canvas.bind_all('<Button-4>', _on_mousewheel)        # Linux scroll up
    canvas.bind_all('<Button-5>', _on_mousewheel)        # Linux scroll down

    # Create a frame inside the canvas
    analytics_card = create_card(canvas, bg=COLORS['white'])
    analytics_card_id = canvas.create_window((0, 0), window=analytics_card, anchor='nw')

    def on_configure(event):
        # Update scrollregion to match the size of the frame
        canvas.configure(scrollregion=canvas.bbox('all'))
        # Make the card width match the canvas width
        canvas.itemconfig(analytics_card_id, width=canvas.winfo_width())
    analytics_card.bind('<Configure>', on_configure)
    canvas.bind('<Configure>', on_configure)

    # Title
    title = tk.Label(analytics_card,
                    text="Analytics Dashboard",
                    font=("Helvetica", 28, "bold"),
                    bg=COLORS['white'],
                    fg=COLORS['primary'])
    title.pack(pady=(0, 30))

    try:
        # Load all CSV files from report directory
        report_dir = "report"
        if not os.path.exists(report_dir):
            tk.Label(analytics_card, 
                    text="No data available for analysis. Please scan some grains first.",
                    font=("Helvetica", 14),
                    fg=COLORS['error'],
                    bg=COLORS['white']).pack(pady=30)
            return

        csv_files = [f for f in os.listdir(report_dir) if f.startswith("measurements_") and f.endswith(".csv")]
        if not csv_files:
            tk.Label(analytics_card,
                    text="No measurement reports found. Please scan some grains first.",
                    font=("Helvetica", 14),
                    fg=COLORS['error'],
                    bg=COLORS['white']).pack(pady=30)
            return

        # Combine all CSV data with error handling
        all_data = []
        file_to_df = {}
        for file in csv_files:
            try:
                df = pd.read_csv(os.path.join(report_dir, file))
                # Calendar-based file date from modification time (normalized to date)
                file_path = os.path.join(report_dir, file)
                mod_time = os.path.getmtime(file_path)
                file_dt = pd.to_datetime(mod_time, unit='s').normalize()
                # Keep both a date column used for charts and an internal file date
                df['Date'] = file_dt
                df['__file_date__'] = file_dt
                df['__source_file__'] = file
                all_data.append(df)
                file_to_df[file] = df
            except Exception as e:
                print(f"Error reading file {file}: {str(e)}")
                continue

        if not all_data:
            tk.Label(analytics_card,
                    text="Could not read any measurement data.",
                    font=("Helvetica", 14),
                    fg=COLORS['error'],
                    bg=COLORS['white']).pack(pady=30)
            return

        combined_df = pd.concat(all_data, ignore_index=True)

        # --- Controls: Time range and Clear analytics ---
        controls_frame = tk.Frame(analytics_card, bg=COLORS['white'])
        controls_frame.pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(controls_frame, text="Time Range:", font=("Helvetica", 10, "bold"),
                 bg=COLORS['white'], fg=COLORS['text']).pack(side='left', padx=(0,6))
        time_range_var = tk.StringVar(value='All time')
        time_range_dropdown = ttk.Combobox(
            controls_frame,
            values=['All time', 'Last 7 days', 'Last 30 days', 'Today'],
            textvariable=time_range_var,
            state='readonly', width=18
        )
        time_range_dropdown.pack(side='left')

        def clear_analytics():
            try:
                if not messagebox.askyesno("Clear Analytics", "This will archive all measurement files (CSV/JPG) into a dated backup folder. Continue?"):
                    return
                moved = 0
                backup_root = os.path.join(report_dir, "backup")
                os.makedirs(backup_root, exist_ok=True)
                for f in os.listdir(report_dir):
                    is_measurement = f.startswith("measurements_") and (f.endswith(".csv") or f.endswith(".jpg"))
                    is_batch_manifest = f.startswith("batch_") and f.endswith(".json")
                    if is_measurement or is_batch_manifest:
                        src = os.path.join(report_dir, f)
                        try:
                            # Use file creation time for folder naming (fallback to modified time)
                            try:
                                ts = os.path.getctime(src)
                            except Exception:
                                ts = os.path.getmtime(src)
                            from datetime import datetime
                            folder = datetime.fromtimestamp(ts).strftime('%d-%m-%Y')
                            dest_dir = os.path.join(backup_root, folder)
                            os.makedirs(dest_dir, exist_ok=True)
                            shutil.move(src, os.path.join(dest_dir, f))
                            moved += 1
                        except Exception:
                            pass
                messagebox.showinfo("Analytics Archived", f"Moved {moved} file(s) to backup.")
                # Refresh analytics view
                for widget in analytics_card.winfo_children():
                    if widget not in (title, controls_frame):
                        widget.destroy()
                # Re-run show_analytics by simulating reload
                show_analytics()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear analytics: {str(e)}")

        clear_btn = tk.Button(controls_frame, text="Clear analytics", command=clear_analytics,
                               bg=COLORS['accent'], fg=COLORS['white'], relief='flat', padx=12, pady=4, cursor='hand2')
        clear_btn.pack(side='right')

        # --- Analytics content update function ---
        def update_analytics(*args):
            # Remove old notebook if exists
            for widget in analytics_card.winfo_children():
                if isinstance(widget, ttk.Notebook):
                    widget.destroy()
            # Remove old Export buttons (no longer needed, but keep for safety)
            for widget in analytics_card.winfo_children():
                if isinstance(widget, tk.Button) and widget.cget('text') == 'Export Analytics Data':
                    widget.destroy()
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Button) and child.cget('text') == 'Export Analytics Data':
                            child.destroy()
            
            # Calendar-based ranges
            today = pd.Timestamp.now().normalize()
            start_7 = today - pd.Timedelta(days=6)   # inclusive today + previous 6
            start_30 = today - pd.Timedelta(days=29) # inclusive today + previous 29

            # Prepare comparison datasets
            recent_7_days = combined_df[(combined_df['__file_date__'] >= start_7) & (combined_df['__file_date__'] <= today)].copy()
            recent_30_days = combined_df[(combined_df['__file_date__'] >= start_30) & (combined_df['__file_date__'] <= today)].copy()

            # Apply selected time range to main df
            tr = time_range_var.get()
            if tr == 'Last 7 days':
                df = recent_7_days.copy()
            elif tr == 'Last 30 days':
                df = recent_30_days.copy()
            elif tr == 'Today':
                df = combined_df[combined_df['__file_date__'] == today].copy()
            else:
                df = combined_df.copy()
            
            # Create notebook for tabs
            notebook = ttk.Notebook(analytics_card)
            notebook.pack(fill="both", expand=True, padx=10, pady=5)

            # Determine class column name
            class_col = 'Class' if 'Class' in df.columns else ('Type' if 'Type' in df.columns else None)

            # KPI Overview Tab (NEW)
            kpi_tab = tk.Frame(notebook, bg=COLORS['background'])
            notebook.add(kpi_tab, text='KPI Overview')

            kpi_card = create_card(kpi_tab, bg=COLORS['white'])
            kpi_card.pack(fill="both", expand=True, padx=10, pady=10)
            kpi_frame = tk.Frame(kpi_card, bg=COLORS['white'])
            kpi_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Calculate KPIs
            if len(df) > 0 and class_col:
                total_grains = len(df)
                class_counts = df[class_col].value_counts()
                class_percentages = df[class_col].value_counts(normalize=True) * 100
                
                # Premium vs Defect calculation (Long + Medium only)
                premium_count = class_counts.get('Long', 0) + class_counts.get('Medium', 0)
                premium_percent = (premium_count / total_grains * 100) if total_grains > 0 else 0
                defect_count = class_counts.get('Broken', 0) + class_counts.get('Discolored', 0)
                defect_percent = (defect_count / total_grains * 100) if total_grains > 0 else 0
                
                # Calculate comparison with recent data
                def calculate_comparison_metrics(compare_df):
                    if len(compare_df) == 0:
                        return None
                    try:
                        compare_counts = compare_df[class_col].value_counts()
                        compare_total = len(compare_df)
                        compare_premium = compare_counts.get('Long', 0) + compare_counts.get('Medium', 0)
                        compare_premium_pct = (compare_premium / compare_total * 100) if compare_total > 0 else 0
                        compare_broken_pct = (compare_counts.get('Broken', 0) / compare_total * 100) if compare_total > 0 else 0
                        compare_discolored_pct = (compare_counts.get('Discolored', 0) / compare_total * 100) if compare_total > 0 else 0
                        return {
                            'premium_pct': compare_premium_pct,
                            'broken_pct': compare_broken_pct,
                            'discolored_pct': compare_discolored_pct
                        }
                    except Exception:
                        return None
                
                recent_7_metrics = calculate_comparison_metrics(recent_7_days)
                recent_30_metrics = calculate_comparison_metrics(recent_30_days)
                
                # KPI Strip
                kpi_strip_frame = tk.Frame(kpi_frame, bg=COLORS['white'])
                kpi_strip_frame.pack(fill="x", pady=(0, 20))
                
                tk.Label(kpi_strip_frame, text="Today vs Last 7 Days", 
                         font=("Helvetica", 16, "bold"), bg=COLORS['white'], fg=COLORS['primary']).pack(pady=(0, 10))
                
                # KPI Grid
                kpi_grid = tk.Frame(kpi_strip_frame, bg=COLORS['white'])
                kpi_grid.pack(fill="x")
                
                # Premium Grains KPI
                premium_frame = tk.Frame(kpi_grid, bg=COLORS['card_bg'], relief='solid', bd=1)
                premium_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
                tk.Label(premium_frame, text="Premium Grains", font=("Helvetica", 12, "bold"), 
                         bg=COLORS['card_bg'], fg=COLORS['success']).pack(pady=(10, 5))
                tk.Label(premium_frame, text=f"{premium_percent:.1f}%", font=("Helvetica", 20, "bold"), 
                         bg=COLORS['card_bg'], fg=COLORS['success']).pack()
                if recent_7_metrics:
                    change = premium_percent - recent_7_metrics['premium_pct']
                    change_text = f"{change:+.1f}%" if abs(change) > 0.1 else "No change"
                    change_color = COLORS['success'] if change >= 0 else COLORS['error']
                    tk.Label(premium_frame, text=change_text, font=("Helvetica", 10), 
                             bg=COLORS['card_bg'], fg=change_color).pack(pady=(0, 10))
                
                # Broken Grains KPI
                broken_frame = tk.Frame(kpi_grid, bg=COLORS['card_bg'], relief='solid', bd=1)
                broken_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
                tk.Label(broken_frame, text="Broken Grains", font=("Helvetica", 12, "bold"), 
                         bg=COLORS['card_bg'], fg=COLORS['error']).pack(pady=(10, 5))
                broken_pct = class_percentages.get('Broken', 0)
                tk.Label(broken_frame, text=f"{broken_pct:.1f}%", font=("Helvetica", 20, "bold"), 
                         bg=COLORS['card_bg'], fg=COLORS['error']).pack()
                if recent_7_metrics:
                    change = broken_pct - recent_7_metrics['broken_pct']
                    change_text = f"{change:+.1f}%" if abs(change) > 0.1 else "No change"
                    change_color = COLORS['error'] if change >= 0 else COLORS['success']
                    tk.Label(broken_frame, text=change_text, font=("Helvetica", 10), 
                             bg=COLORS['card_bg'], fg=change_color).pack(pady=(0, 10))
                
                # Discolored Grains KPI
                discolored_frame = tk.Frame(kpi_grid, bg=COLORS['card_bg'], relief='solid', bd=1)
                discolored_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
                tk.Label(discolored_frame, text="Discolored Grains", font=("Helvetica", 12, "bold"), 
                         bg=COLORS['card_bg'], fg=COLORS['error']).pack(pady=(10, 5))
                discolored_pct = class_percentages.get('Discolored', 0)
                tk.Label(discolored_frame, text=f"{discolored_pct:.1f}%", font=("Helvetica", 20, "bold"), 
                         bg=COLORS['card_bg'], fg=COLORS['error']).pack()
                if recent_7_metrics:
                    change = discolored_pct - recent_7_metrics['discolored_pct']
                    change_text = f"{change:+.1f}%" if abs(change) > 0.1 else "No change"
                    change_color = COLORS['error'] if change >= 0 else COLORS['success']
                    tk.Label(discolored_frame, text=change_text, font=("Helvetica", 10), 
                             bg=COLORS['card_bg'], fg=change_color).pack(pady=(0, 10))
                
                # Total Grains KPI
                total_frame = tk.Frame(kpi_grid, bg=COLORS['card_bg'], relief='solid', bd=1)
                total_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
                tk.Label(total_frame, text="Total Grains", font=("Helvetica", 12, "bold"), 
                         bg=COLORS['card_bg'], fg=COLORS['primary']).pack(pady=(10, 5))
                tk.Label(total_frame, text=f"{total_grains}", font=("Helvetica", 20, "bold"), 
                         bg=COLORS['card_bg'], fg=COLORS['primary']).pack()
                if recent_7_metrics:
                    avg_grains_7d = len(recent_7_days) / 7 if len(recent_7_days) > 0 else 0
                    change = total_grains - avg_grains_7d
                    change_text = f"{change:+.0f}" if abs(change) > 1 else "No change"
                    change_color = COLORS['success'] if change >= 0 else COLORS['error']
                    tk.Label(total_frame, text=change_text, font=("Helvetica", 10), 
                             bg=COLORS['card_bg'], fg=change_color).pack(pady=(0, 10))
                
                # Premium vs Defect Donut Chart
                donut_frame = tk.Frame(kpi_frame, bg=COLORS['white'])
                donut_frame.pack(fill="x", pady=(20, 0))
                
                tk.Label(donut_frame, text="Grain Composition Overview", 
                         font=("Helvetica", 16, "bold"), bg=COLORS['white'], fg=COLORS['primary']).pack(pady=(0, 10))
                
                # Create donut chart
                fig_donut = Figure(figsize=(8, 4), facecolor=COLORS['white'])
                ax_donut = fig_donut.add_subplot(121)
                ax_bars = fig_donut.add_subplot(122)
                
                # Donut chart data
                donut_data = [premium_percent, defect_percent]
                donut_labels = ['Premium Grains', 'Defect Grains']
                donut_colors = [COLORS['success'], COLORS['error']]
                
                # Create donut chart
                wedges, texts, autotexts = ax_donut.pie(donut_data, labels=donut_labels, colors=donut_colors, 
                                                        autopct='%1.1f%%', startangle=90)
                ax_donut.set_title('Premium vs Defect Grains', color=COLORS['text'], fontsize=13, fontweight='bold')
                
                # Add center circle for donut effect
                centre_circle = plt.Circle((0,0), 0.70, fc=COLORS['white'])
                ax_donut.add_patch(centre_circle)
                
                # Defect threshold bars
                broken_threshold = 5.0  # Target threshold
                discolored_threshold = 3.0  # Target threshold
                
                defect_types = ['Broken', 'Discolored']
                defect_values = [broken_pct, discolored_pct]
                defect_thresholds = [broken_threshold, discolored_threshold]
                defect_colors = []
                
                for val, threshold in zip(defect_values, defect_thresholds):
                    if val <= threshold:
                        defect_colors.append(COLORS['success'])  # Green
                    elif val <= threshold * 1.5:
                        defect_colors.append(COLORS['warning'])   # Yellow
                    else:
                        defect_colors.append(COLORS['error'])     # Red
                
                bars = ax_bars.bar(defect_types, defect_values, color=defect_colors, alpha=0.7)
                ax_bars.axhline(y=broken_threshold, color=COLORS['success'], linestyle='--', alpha=0.8, label='Broken Target')
                ax_bars.axhline(y=discolored_threshold, color=COLORS['success'], linestyle='--', alpha=0.8, label='Discolored Target')
                ax_bars.set_title('Defect Grains vs Targets', color=COLORS['text'], fontsize=13, fontweight='bold')
                ax_bars.set_ylabel('Percentage (%)', color=COLORS['text'], fontsize=11)
                ax_bars.set_ylim(0, max(max(defect_values) * 1.2, 10))
                
                # Add value labels on bars
                for bar, value in zip(bars, defect_values):
                    height = bar.get_height()
                    ax_bars.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
                
                fig_donut.tight_layout()
                canvas_donut = FigureCanvasTkAgg(fig_donut, donut_frame)
                canvas_donut.draw()
                canvas_donut.get_tk_widget().pack(pady=10)
                
                # Add explanatory captions
                caption_frame = tk.Frame(kpi_frame, bg=COLORS['white'])
                caption_frame.pack(fill="x", pady=(10, 0))
                
                tk.Label(caption_frame, text="💡 Premium grains (Long + Medium) are your high-quality rice. Keep defect grains (Broken + Discolored) below targets for best quality.", 
                         font=("Helvetica", 10), bg=COLORS['white'], fg=COLORS['text'], wraplength=800, justify='left').pack(anchor='w')
                
                # Quality Status Summary
                status_frame = tk.Frame(kpi_frame, bg=COLORS['white'])
                status_frame.pack(fill="x", pady=(20, 0))
                
                tk.Label(status_frame, text="Quality Status", 
                         font=("Helvetica", 16, "bold"), bg=COLORS['white'], fg=COLORS['primary']).pack(pady=(0, 10))
                
                # Determine overall status
                overall_status = "Good"
                status_color = COLORS['success']
                status_message = "Quality metrics are within acceptable ranges."
                
                if broken_pct > broken_threshold or discolored_pct > discolored_threshold:
                    overall_status = "Needs Attention"
                    status_color = COLORS['warning']
                    status_message = "Some defect levels are above target thresholds."
                
                if broken_pct > broken_threshold * 2 or discolored_pct > discolored_threshold * 2:
                    overall_status = "Critical"
                    status_color = COLORS['error']
                    status_message = "Defect levels are significantly above targets. Immediate action recommended."
                
                status_card = tk.Frame(status_frame, bg=status_color, relief='solid', bd=2)
                status_card.pack(fill="x", pady=5)
                
                tk.Label(status_card, text=overall_status, font=("Helvetica", 14, "bold"), 
                         bg=status_color, fg=COLORS['white']).pack(pady=(10, 5))
                tk.Label(status_card, text=status_message, font=("Helvetica", 11), 
                         bg=status_color, fg=COLORS['white'], wraplength=700).pack(pady=(0, 10))
                
            else:
                tk.Label(kpi_frame, text="No data available for KPI analysis.", 
                         font=("Helvetica", 12), bg=COLORS['white'], fg=COLORS['error']).pack(pady=10)

        # Initial analytics and bind changes
        update_analytics()
        time_range_var.trace_add('write', lambda *a: update_analytics())

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while generating analytics: {str(e)}")


def show_report():
    # Clear main content
    for widget in main.winfo_children():
        widget.destroy()

    # Create scrollable report container
    canvas = tk.Canvas(main, bg=COLORS['background'], highlightthickness=0)
    scrollbar = tk.Scrollbar(main, orient="vertical", command=canvas.yview)
    report_frame = tk.Frame(canvas, bg=COLORS['background'])

    report_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=report_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    # Mouse wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # Header Card with Title and Actions
    header_card = create_card(report_frame, bg=COLORS['white'])
    header_card.pack(fill="x", padx=20, pady=(20, 10))

    # Title with icon and description
    title_row = tk.Frame(header_card, bg=COLORS['white'])
    title_row.pack(fill='x', pady=(0, 5))
    
    title = tk.Label(title_row,
                    text="🌾 Rice Grain Quality Reports",
                    font=("Helvetica", 28, "bold"),
                    bg=COLORS['white'],
                    fg=COLORS['primary'])
    title.pack(side='left')
    
    # Subtitle/description
    subtitle = tk.Label(header_card,
                       text="Comprehensive quality analysis and measurement data from scanned rice samples",
                       font=("Helvetica", 11),
                       bg=COLORS['white'],
                       fg=COLORS['text'])
    subtitle.pack(anchor='w', pady=(0, 15))

    # Mode selector with better styling
    mode_container = tk.Frame(header_card, bg=COLORS['card_bg'], relief='solid', bd=1)
    mode_container.pack(fill='x', pady=(0, 10))
    
    mode_inner = tk.Frame(mode_container, bg=COLORS['card_bg'])
    mode_inner.pack(fill='x', padx=15, pady=10)
    
    tk.Label(mode_inner, text="View Mode:", font=("Helvetica", 11, "bold"),
            bg=COLORS['card_bg'], fg=COLORS['text']).pack(side='left', padx=(0, 15))
    
    report_mode = tk.StringVar(value='single')
    
    single_radio = tk.Radiobutton(mode_inner, text="📄 Single Report Analysis", variable=report_mode, 
                                  value='single', bg=COLORS['card_bg'], font=("Helvetica", 11),
                                  selectcolor=COLORS['white'], activebackground=COLORS['card_bg'])
    single_radio.pack(side='left', padx=(0, 20))
    
    batch_radio = tk.Radiobutton(mode_inner, text="📁 Batch Report Comparison", variable=report_mode, 
                                 value='batch', bg=COLORS['card_bg'], font=("Helvetica", 11),
                                 selectcolor=COLORS['white'], activebackground=COLORS['card_bg'])
    batch_radio.pack(side='left')

    report_dir = "report"
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    # Will create cards after navigation sections are defined
    
    csv_files = sorted(
        [f for f in os.listdir(report_dir) if f.startswith("measurements_") and f.endswith(".csv")],
        key=lambda x: os.path.getctime(os.path.join(report_dir, x)),
        reverse=True
    )
    batch_manifests = sorted(
        [f for f in os.listdir(report_dir) if f.startswith("batch_") and f.endswith(".json")],
        key=lambda x: os.path.getctime(os.path.join(report_dir, x)),
        reverse=True
    )

    if not csv_files:
        no_reports_card = create_card(report_frame, bg=COLORS['white'])
        no_reports_card.pack(fill="x", padx=20, pady=20)
        tk.Label(no_reports_card,
                text="📭 No reports found",
                font=("Helvetica", 16, "bold"),
                fg=COLORS['error'],
                bg=COLORS['white']).pack(pady=20)
        tk.Label(no_reports_card,
                text="Scan some rice grains to generate reports.",
                font=("Helvetica", 12),
                fg=COLORS['text'],
                bg=COLORS['white']).pack(pady=(0, 20))
        return

    # Create all content cards (will be packed by toggle_mode in correct order)
    # Summary Statistics Card (will be populated when report is loaded)
    summary_card = create_card(report_frame, bg=COLORS['white'])
    
    # Initial placeholder
    tk.Label(summary_card, text="📈 Report Summary", 
            font=("Helvetica", 16, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
    tk.Label(summary_card, text="Select a report to view quality analysis and statistics", 
            font=("Helvetica", 11), 
            bg=COLORS['white'], fg=COLORS['text']).pack(pady=30)

    # Image Analysis Section Card
    image_analysis_card = create_card(report_frame, bg=COLORS['white'])
    
    # Initial placeholder
    tk.Label(image_analysis_card, text="🔬 Detected Grains - Visual Analysis", 
            font=("Helvetica", 16, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
    tk.Label(image_analysis_card, text="Annotated image with detected rice grains will appear here", 
            font=("Helvetica", 11), 
            bg=COLORS['white'], fg=COLORS['text']).pack(pady=30)

    # Export Actions Card
    export_card = create_card(report_frame, bg=COLORS['card_bg'])
    
    # Pack cards in initial order (navigation frame will be inserted before these by toggle_mode)
    summary_card.pack(fill="x", padx=20, pady=10)
    image_analysis_card.pack(fill="x", padx=20, pady=10)
    export_card.pack(fill="x", padx=20, pady=10)

    export_title = tk.Label(export_card, text="📥 Export Options", 
                           font=("Helvetica", 14, "bold"), 
                           bg=COLORS['card_bg'], fg=COLORS['text'])
    export_title.pack(anchor='w', pady=(0, 10))

    export_buttons_frame = tk.Frame(export_card, bg=COLORS['card_bg'])
    export_buttons_frame.pack(fill='x')

    def export_to_csv():
        try:
            if report_mode.get() == 'single':
                # Single mode: export individual report
                selected = selected_file.get()
                if not selected:
                    messagebox.showwarning("No Selection", "Please select a report first.")
                    return
                
                csv_path = os.path.join(report_dir, selected)
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    initialfile=f"export_{selected}"
                )
                if save_path:
                    shutil.copy(csv_path, save_path)
                    messagebox.showinfo("Export Successful", f"Report exported to:\n{save_path}")
            else:
                # Batch mode: export COMBINED data from all images
                if 'overall_quality' not in batch_items_current or not batch_items_current.get('items'):
                    messagebox.showwarning("No Batch Data", "Please load a batch report first.")
                    return
                
                # Combine all CSVs in the batch
                all_dfs = []
                for item in batch_items_current['items']:
                    cpath = item.get('csv_path', '')
                    if cpath and os.path.exists(cpath):
                        df = pd.read_csv(cpath)
                        # Add source file column
                        df['Source_Image'] = item.get('file', 'Unknown')
                        all_dfs.append(df)
                
                if not all_dfs:
                    messagebox.showerror("Error", "No data found in batch.")
                    return
                
                combined_df = pd.concat(all_dfs, ignore_index=True)
                
                batch_name = selected_batch.get() if 'selected_batch' in dir() else "batch"
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    initialfile=f"export_combined_{batch_name.replace('.json', '')}.csv"
                )
                if save_path:
                    combined_df.to_csv(save_path, index=False)
                    messagebox.showinfo("Export Successful", f"Combined batch report exported to:\n{save_path}\n\nTotal grains: {len(combined_df)}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export: {str(e)}")

    def export_to_excel():
        try:
            if report_mode.get() == 'single':
                # Single mode: export individual report
                selected = selected_file.get()
                if not selected:
                    messagebox.showwarning("No Selection", "Please select a report first.")
                    return
                
                csv_path = os.path.join(report_dir, selected)
                df = pd.read_csv(csv_path)
                
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                    initialfile=f"export_{os.path.splitext(selected)[0]}.xlsx"
                )
                if save_path:
                    df.to_excel(save_path, index=False, engine='openpyxl')
                    messagebox.showinfo("Export Successful", f"Report exported to:\n{save_path}")
            else:
                # Batch mode: export COMBINED data
                if 'overall_quality' not in batch_items_current or not batch_items_current.get('items'):
                    messagebox.showwarning("No Batch Data", "Please load a batch report first.")
                    return
                
                # Combine all CSVs in the batch
                all_dfs = []
                for item in batch_items_current['items']:
                    cpath = item.get('csv_path', '')
                    if cpath and os.path.exists(cpath):
                        df = pd.read_csv(cpath)
                        df['Source_Image'] = item.get('file', 'Unknown')
                        all_dfs.append(df)
                
                if not all_dfs:
                    messagebox.showerror("Error", "No data found in batch.")
                    return
                
                combined_df = pd.concat(all_dfs, ignore_index=True)
                
                batch_name = selected_batch.get() if 'selected_batch' in dir() else "batch"
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                    initialfile=f"export_combined_{batch_name.replace('.json', '')}.xlsx"
                )
                if save_path:
                    combined_df.to_excel(save_path, index=False, engine='openpyxl')
                    messagebox.showinfo("Export Successful", f"Combined batch report exported to:\n{save_path}\n\nTotal grains: {len(combined_df)}")
        except ImportError:
            messagebox.showerror("Missing Library", "Please install openpyxl: pip install openpyxl")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export: {str(e)}")

    def export_to_pdf():
        try:
            if report_mode.get() == 'single':
                messagebox.showinfo("PDF Export", "PDF export will create a comprehensive 3-page report:\n• Page 1: Header with Image & Summary\n• Page 2: Grain Distribution Chart\n• Page 3: Detailed Data Table")
            else:
                messagebox.showinfo("PDF Export", "PDF export will create a comprehensive 2-page report:\n• Page 1: Header with Overall Batch Chart & Summary\n• Page 2: Combined Data Table (all images)")
            
            if report_mode.get() == 'single':
                # Single mode: export individual report
                selected = selected_file.get()
                if not selected:
                    messagebox.showwarning("No Selection", "Please select a report first.")
                    return
                
                # Read data
                csv_path = os.path.join(report_dir, selected)
                df = pd.read_csv(csv_path)
                
                # Get image path
                base_name = os.path.splitext(selected)[0]
                img_path = os.path.join(report_dir, f"{base_name}.jpg")
                report_title = selected
            else:
                # Batch mode: export combined data
                if 'overall_quality' not in batch_items_current or not batch_items_current.get('items'):
                    messagebox.showwarning("No Batch Data", "Please load a batch report first.")
                    return
                
                # Combine all CSVs in the batch
                all_dfs = []
                for item in batch_items_current['items']:
                    cpath = item.get('csv_path', '')
                    if cpath and os.path.exists(cpath):
                        df_item = pd.read_csv(cpath)
                        df_item['Source_Image'] = item.get('file', 'Unknown')
                        all_dfs.append(df_item)
                
                if not all_dfs:
                    messagebox.showerror("Error", "No data found in batch.")
                    return
                
                df = pd.concat(all_dfs, ignore_index=True)
                img_path = None  # No single image for batch
                batch_name = selected_batch.get() if 'selected_batch' in dir() else "batch"
                report_title = f"Combined Batch: {batch_name}"
            
            # Create safe filename
            safe_name = report_title.replace('.csv', '').replace('.json', '').replace('/', '_').replace('\\', '_')
            save_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=f"export_{safe_name}.pdf"
            )
            
            if save_path:
                from matplotlib.backends.backend_pdf import PdfPages
                
                with PdfPages(save_path) as pdf:
                    # Page 1: Report Header and Image/Chart
                    fig = Figure(figsize=(8.5, 11), facecolor='white')
                    
                    # Title
                    fig.text(0.5, 0.95, 'GrainScan - Rice Quality Report', 
                            ha='center', fontsize=20, fontweight='bold', color=COLORS['primary'])
                    fig.text(0.5, 0.92, f'Report: {report_title}', 
                            ha='center', fontsize=12, color=COLORS['text'])
                    fig.text(0.5, 0.90, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                            ha='center', fontsize=10, color=COLORS['text'])
                    
                    # For single mode: show image; For batch mode: show overall chart
                    if report_mode.get() == 'batch' and 'Class' in df.columns:
                        # Show overall grain distribution chart for batch
                        ax_chart = fig.add_axes([0.15, 0.45, 0.7, 0.35])
                        
                        class_counts = df['Class'].value_counts()
                        grain_types = [g for g in class_counts.keys() if g != 'Short']
                        grain_counts_list = [class_counts[g] for g in grain_types]
                        
                        color_map = {
                            'Long': COLORS['success'],
                            'Medium': COLORS['orange'],
                            'Broken': COLORS['error'],
                            'Discolored': COLORS['purple']
                        }
                        colors_list = [color_map.get(g, COLORS['text']) for g in grain_types]
                        
                        bars = ax_chart.bar(grain_types, grain_counts_list, color=colors_list, alpha=0.8, edgecolor='black', linewidth=1.5)
                        ax_chart.set_ylabel('Count', fontsize=12, color=COLORS['text'], fontweight='bold')
                        ax_chart.set_xlabel('Grain Type', fontsize=12, color=COLORS['text'], fontweight='bold')
                        ax_chart.set_title('Overall Batch Grain Distribution', fontsize=13, fontweight='bold', color=COLORS['text'], pad=15)
                        ax_chart.spines['top'].set_visible(False)
                        ax_chart.spines['right'].set_visible(False)
                        ax_chart.grid(axis='y', alpha=0.3, linestyle='--')
                        
                        total = len(df)
                        for bar, count in zip(bars, grain_counts_list):
                            height = bar.get_height()
                            pct = (count / total) * 100
                            ax_chart.text(bar.get_x() + bar.get_width()/2., height,
                                        f'{int(count)}\n({pct:.1f}%)', 
                                        ha='center', va='bottom', fontweight='bold', fontsize=10)
                    elif img_path and os.path.exists(img_path):
                        # Show image for single mode
                        ax_img = fig.add_axes([0.1, 0.45, 0.8, 0.4])
                        img = plt.imread(img_path)
                        ax_img.imshow(img)
                        ax_img.axis('off')
                        ax_img.set_title('Detected Rice Grains', fontsize=12, fontweight='bold', pad=10)
                    
                    # Summary statistics
                    if 'Class' in df.columns:
                        class_counts = df['Class'].value_counts()
                        total = len(df)
                        
                        summary_text = f"Total Grains: {total}\n"
                        if report_mode.get() == 'batch':
                            batch_size = batch_items_current.get('overall_quality', {}).get('batch_size', 0)
                            summary_text = f"Batch Size: {batch_size} images\nTotal Grains: {total}\n"
                        summary_text += "\nGrain Distribution:\n"
                        for grain_class, count in class_counts.items():
                            if grain_class == 'Short':  # Skip Short grains
                                continue
                            pct = (count / total) * 100
                            summary_text += f"  {grain_class}: {count} ({pct:.1f}%)\n"
                        
                        fig.text(0.1, 0.35, summary_text, fontsize=10, 
                                verticalalignment='top', family='monospace',
                                bbox=dict(boxstyle='round', facecolor=COLORS['card_bg'], alpha=0.8))
                    
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                    
                    # Page 2: Grain Distribution Chart (only for single mode, batch already has it on page 1)
                    if report_mode.get() == 'single' and 'Class' in df.columns:
                        fig_chart = Figure(figsize=(8.5, 11), facecolor='white')
                        
                        # Title
                        fig_chart.text(0.5, 0.95, 'Grain Distribution Analysis', 
                                      ha='center', fontsize=18, fontweight='bold', color=COLORS['primary'])
                        
                        # Create chart - centered on page
                        ax_chart = fig_chart.add_axes([0.15, 0.35, 0.7, 0.5])
                        
                        # Get grain counts (exclude Short)
                        class_counts = df['Class'].value_counts()
                        grain_types = [g for g in class_counts.keys() if g != 'Short']
                        grain_counts_list = [class_counts[g] for g in grain_types]
                        
                        # Color mapping
                        color_map = {
                            'Long': COLORS['success'],
                            'Medium': COLORS['orange'],
                            'Broken': COLORS['error'],
                            'Discolored': COLORS['purple']
                        }
                        colors_list = [color_map.get(g, COLORS['text']) for g in grain_types]
                        
                        # Create bar chart
                        bars = ax_chart.bar(grain_types, grain_counts_list, color=colors_list, alpha=0.8, edgecolor='black', linewidth=1.5)
                        ax_chart.set_ylabel('Count', fontsize=13, color=COLORS['text'], fontweight='bold')
                        ax_chart.set_xlabel('Grain Type', fontsize=13, color=COLORS['text'], fontweight='bold')
                        ax_chart.set_title('Grain Type Distribution', fontsize=15, fontweight='bold', color=COLORS['text'], pad=20)
                        ax_chart.spines['top'].set_visible(False)
                        ax_chart.spines['right'].set_visible(False)
                        ax_chart.grid(axis='y', alpha=0.3, linestyle='--')
                        
                        # Add value labels on bars
                        total = len(df)
                        for bar, count in zip(bars, grain_counts_list):
                            height = bar.get_height()
                            pct = (count / total) * 100
                            ax_chart.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                                        f'{int(count)}\n({pct:.1f}%)', 
                                        ha='center', va='bottom', fontweight='bold', fontsize=11)
                        
                        # Add total grains info at bottom
                        fig_chart.text(0.5, 0.15, f'Total Grains Analyzed: {total}',
                                     ha='center', fontsize=13, fontweight='bold', color=COLORS['primary'])
                        
                        pdf.savefig(fig_chart, bbox_inches='tight')
                        plt.close(fig_chart)
                    
                    # Last Page: Data Table
                    fig2 = Figure(figsize=(8.5, 11), facecolor='white')
                    ax = fig2.add_subplot(111)
                    ax.axis('tight')
                    ax.axis('off')
                    
                    # Create table
                    table_data = [df.columns.tolist()] + df.values.tolist()
                    table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                                    colWidths=[0.12] * len(df.columns))
                    table.auto_set_font_size(False)
                    table.set_fontsize(8)
                    table.scale(1, 1.5)
                    
                    # Style header row
                    for i in range(len(df.columns)):
                        cell = table[(0, i)]
                        cell.set_facecolor(COLORS['primary'])
                        cell.set_text_props(weight='bold', color='white')
                    
                    fig2.text(0.5, 0.95, 'Measurement Data', 
                             ha='center', fontsize=16, fontweight='bold')
                    
                    pdf.savefig(fig2, bbox_inches='tight')
                    plt.close(fig2)
                
                if report_mode.get() == 'single':
                    pages_count = "3 pages: Header with Image, Chart, and Data Table"
                else:
                    pages_count = "2 pages: Header with Overall Chart, and Combined Data Table"
                messagebox.showinfo("Export Successful", f"PDF report exported to:\n{save_path}\n\n{pages_count}")
                
        except ImportError as e:
            messagebox.showerror("Missing Library", f"Please install required libraries:\npip install matplotlib openpyxl\n\nError: {str(e)}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export PDF: {str(e)}")

    # Export buttons
    csv_btn = tk.Button(export_buttons_frame, text="📄 Export CSV", command=export_to_csv,
                       bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'),
                       relief='flat', padx=16, pady=8, cursor='hand2')
    csv_btn.pack(side='left', padx=(0, 10))

    excel_btn = tk.Button(export_buttons_frame, text="📊 Export Excel", command=export_to_excel,
                         bg=COLORS['success'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'),
                         relief='flat', padx=16, pady=8, cursor='hand2')
    excel_btn.pack(side='left', padx=(0, 10))

    pdf_btn = tk.Button(export_buttons_frame, text="📑 Export PDF", command=export_to_pdf,
                       bg=COLORS['secondary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'),
                       relief='flat', padx=16, pady=8, cursor='hand2')
    pdf_btn.pack(side='left')

    def show_report_image(selected_file):
        """Display the annotated image in the image analysis card."""
        # Clear existing content
        for widget in image_analysis_card.winfo_children():
            widget.destroy()
        
        # Card title
        tk.Label(image_analysis_card, text="🔬 Detected Grains - Visual Analysis", 
                font=("Helvetica", 16, "bold"), 
                bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
        
        # Derive image path from CSV filename
        base_name = os.path.splitext(selected_file)[0]
        img_path = os.path.join(report_dir, f"{base_name}.jpg")
        
        if os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                w, h = img.size
                
                # Image info banner
                info_banner = tk.Frame(image_analysis_card, bg=COLORS['card_bg'], relief='solid', bd=1)
                info_banner.pack(fill='x', pady=(0, 10))
                
                info_inner = tk.Frame(info_banner, bg=COLORS['card_bg'])
                info_inner.pack(fill='x', padx=15, pady=8)
                
                tk.Label(info_inner, text=f"📐 Image Resolution: {w}×{h} pixels", 
                        font=("Helvetica", 10), bg=COLORS['card_bg'], fg=COLORS['text']).pack(side='left', padx=(0, 20))
                tk.Label(info_inner, text="💡 Click image to view full size", 
                        font=("Helvetica", 10, "italic"), bg=COLORS['card_bg'], fg=COLORS['primary']).pack(side='left')
                
                # Image container with border
                image_container = tk.Frame(image_analysis_card, bg=COLORS['white'], relief='solid', bd=2)
                image_container.pack(fill='x', pady=(0, 10))
                
                # Resize for display
                max_w, max_h = 1000, 500
                scale = min(max_w / w, max_h / h, 1.0)
                img_disp = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img_disp)
                
                image_label = tk.Label(image_container, image=img_tk, bg=COLORS['white'], cursor='hand2')
                image_label.image = img_tk
                image_label.pack(padx=5, pady=5)

                def on_image_click(event=None):
                    # Open maximized image in a new window
                    top = tk.Toplevel(root)
                    top.title("Full Size Analysis Image")
                    top.configure(bg=COLORS['background'])
                    screen_w = top.winfo_screenwidth()
                    screen_h = top.winfo_screenheight()
                    scale_max = min((screen_w-100) / w, (screen_h-100) / h, 1.0)
                    img_max = img.resize((int(w * scale_max), int(h * scale_max)), Image.LANCZOS)
                    img_max_tk = ImageTk.PhotoImage(img_max)
                    label = tk.Label(top, image=img_max_tk, bg=COLORS['background'])
                    label.image = img_max_tk
                    label.pack(expand=True, padx=20, pady=20)
                    top.update_idletasks()
                    x = (screen_w - top.winfo_width()) // 2
                    y = (screen_h - top.winfo_height()) // 2
                    top.geometry(f"+{x}+{y}")

                image_label.bind("<Button-1>", on_image_click)
                
                # Legend for grain classes - matching actual detection colors
                legend_frame = tk.Frame(image_analysis_card, bg=COLORS['card_bg'], relief='solid', bd=1)
                legend_frame.pack(fill='x', pady=(0, 0))
                
                legend_inner = tk.Frame(legend_frame, bg=COLORS['card_bg'])
                legend_inner.pack(fill='x', padx=15, pady=10)
                
                tk.Label(legend_inner, text="Detection Color Legend:", font=("Helvetica", 10, "bold"),
                        bg=COLORS['card_bg'], fg=COLORS['text']).pack(side='left', padx=(0, 15))
                
                # Color legend items - matching actual YOLO detection colors
                legend_items = [
                    ("● Long Grain", COLORS['success']),      # Green
                    ("● Medium Grain", COLORS['orange']),     # Orange
                    ("● Broken Grain", COLORS['error']),      # Red
                    ("● Discolored Grain", COLORS['purple'])  # Purple
                ]
                
                for text, color in legend_items:
                    tk.Label(legend_inner, text=text, font=("Helvetica", 10, "bold"),
                            bg=COLORS['card_bg'], fg=color).pack(side='left', padx=(0, 15))
                
            except Exception as e:
                tk.Label(image_analysis_card, text=f"⚠️ Could not load analysis image: {str(e)}", 
                        font=("Helvetica", 11), bg=COLORS['white'], fg=COLORS['error']).pack(pady=20)
        else:
            # No image found
            tk.Label(image_analysis_card, text="⚠️ No analysis image available for this report", 
                    font=("Helvetica", 12), bg=COLORS['white'], fg=COLORS['warning']).pack(pady=30)
            tk.Label(image_analysis_card, text="The image file may have been moved or deleted.", 
                    font=("Helvetica", 10), bg=COLORS['white'], fg=COLORS['text']).pack(pady=(0, 30))

    def load_csv_data(selected_file):
        """Load and display report data with full analysis."""
        for row in tree.get_children():
            tree.delete(row)
        full_path = os.path.join(report_dir, selected_file)
        
        # Load and display data
        df = pd.read_csv(full_path)
        with open(full_path, newline='') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                tree.insert("", "end", values=row)
        
        # Update all report sections
        update_summary_card(df, selected_file)
        show_report_image(selected_file)

        # Update counter if in single mode
        try:
            if hasattr(single_frame, 'update_counter'):
                single_frame.update_counter()
        except:
            pass
        
        # Scroll to top after loading
        try:
            canvas.yview_moveto(0)
        except:
            pass
    
    def update_summary_card_batch(overall_quality, current_image_name):
        """Update summary card for batch mode - shows overall batch quality."""
        # Clear existing content
        for widget in summary_card.winfo_children():
            widget.destroy()
        
        # Title with batch indicator
        title_frame = tk.Frame(summary_card, bg=COLORS['white'])
        title_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(title_frame, text="📈 Overall Batch Quality Summary", 
                font=("Helvetica", 16, "bold"), 
                bg=COLORS['white'], fg=COLORS['primary']).pack(side='left')
        
        # Batch info banner
        batch_info_frame = tk.Frame(summary_card, bg=COLORS['card_bg'], relief='solid', bd=1)
        batch_info_frame.pack(fill='x', pady=(0, 15))
        
        batch_info_inner = tk.Frame(batch_info_frame, bg=COLORS['card_bg'])
        batch_info_inner.pack(fill='x', padx=15, pady=10)
        
        batch_size = overall_quality.get('batch_size', 0)
        total_grains = overall_quality.get('total', 0)
        
        tk.Label(batch_info_inner, text=f"📦 Batch Size: {batch_size} images", 
                font=("Helvetica", 11, "bold"), bg=COLORS['card_bg'], fg=COLORS['text']).pack(side='left', padx=(0, 20))
        tk.Label(batch_info_inner, text=f"📊 Total Grains: {total_grains} (all images)", 
                font=("Helvetica", 11, "bold"), bg=COLORS['card_bg'], fg=COLORS['primary']).pack(side='left', padx=(0, 20))
        tk.Label(batch_info_inner, text=f"👁️ Viewing: {current_image_name}", 
                font=("Helvetica", 10), bg=COLORS['card_bg'], fg=COLORS['text']).pack(side='left')
        
        # Quality grade banner (overall batch)
        grade = overall_quality.get('grade', 'Unknown')
        score = overall_quality.get('score', 0.0)
        color = COLORS['success'] if grade == "High" else (COLORS['warning'] if grade == "Medium" else COLORS['error'])
        
        grade_frame = tk.Frame(summary_card, bg=color, relief='solid', bd=2)
        grade_frame.pack(fill='x', pady=(0, 15))
        
        grade_inner = tk.Frame(grade_frame, bg=color)
        grade_inner.pack(fill='x', padx=15, pady=10)
        
        tk.Label(grade_inner, text=f"Overall Batch Quality: {grade}", 
                font=("Helvetica", 14, "bold"), bg=color, fg=COLORS['white']).pack(side='left')
        
        tk.Label(grade_inner, text=f"Score: {score:.3f}", 
                font=("Helvetica", 12), bg=color, fg=COLORS['white']).pack(side='left', padx=(20, 0))
        
        # Statistics grid (overall batch statistics)
        stats_frame = tk.Frame(summary_card, bg=COLORS['white'])
        stats_frame.pack(fill='x', pady=(0, 10))
        
        counts = overall_quality.get('counts', {})
        percents = overall_quality.get('percents', {})
        premium_percent = overall_quality.get('premium_percent', 0)
        
        # Create stat cards in a grid (without Short)
        stat_items = [
            ("Premium Grains\n(Batch Total)", f"{premium_percent:.1f}%", COLORS['success']),
            ("Long Grains\n(Batch)", f"{counts.get('Long', 0)} ({percents.get('Long', 0):.1f}%)", COLORS['success']),
            ("Medium Grains\n(Batch)", f"{counts.get('Medium', 0)} ({percents.get('Medium', 0):.1f}%)", COLORS['orange']),
            ("Broken Grains\n(Batch)", f"{counts.get('Broken', 0)} ({percents.get('Broken', 0):.1f}%)", COLORS['error']),
            ("Discolored Grains\n(Batch)", f"{counts.get('Discolored', 0)} ({percents.get('Discolored', 0):.1f}%)", COLORS['purple'])
        ]
        
        for i, (label, value, color) in enumerate(stat_items):
            stat_card = tk.Frame(stats_frame, bg=COLORS['card_bg'], relief='solid', bd=1)
            # Arrange in 2 rows: 3 items in first row, 2 in second row
            if i < 3:
                stat_card.grid(row=0, column=i, padx=5, pady=5, sticky='ew')
            else:
                # Center the last 2 items
                stat_card.grid(row=1, column=i-3, padx=5, pady=5, sticky='ew')
            
            tk.Label(stat_card, text=label, font=("Helvetica", 9, "bold"), 
                    bg=COLORS['card_bg'], fg=COLORS['text'], justify='center').pack(pady=(8, 2))
            tk.Label(stat_card, text=value, font=("Helvetica", 12, "bold"), 
                    bg=COLORS['card_bg'], fg=color).pack(pady=(2, 8))
        
        # Configure grid weights - 3 columns
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(1, weight=1)
        stats_frame.grid_columnconfigure(2, weight=1)
        
        # Add a mini chart for batch
        try:
            chart_frame = tk.Frame(summary_card, bg=COLORS['white'])
            chart_frame.pack(fill='x', pady=(10, 0))
            
            fig = Figure(figsize=(10, 3), facecolor=COLORS['white'])
            ax = fig.add_subplot(111)
            
            # Grain distribution bar chart with proper colors (exclude Short)
            grain_types = [g for g in counts.keys() if g != 'Short']
            grain_counts = [counts[g] for g in grain_types]
            # Map each grain type to its detection color
            color_map = {
                'Long': COLORS['success'],
                'Medium': COLORS['orange'],
                'Broken': COLORS['error'],
                'Discolored': COLORS['purple']
            }
            colors_list = [color_map.get(g, COLORS['text']) for g in grain_types]
            
            bars = ax.bar(grain_types, grain_counts, color=colors_list, alpha=0.7)
            ax.set_ylabel('Count (Entire Batch)', fontsize=10, color=COLORS['text'])
            ax.set_title('Batch Grain Distribution (All Images Combined)', fontsize=12, fontweight='bold', color=COLORS['primary'], pad=10)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            # Add value labels on bars
            for bar, count in zip(bars, grain_counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(count)}', ha='center', va='bottom', fontweight='bold', fontsize=9)
            
            canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
            canvas_widget.draw()
            canvas_widget.get_tk_widget().pack(fill='x', pady=5)
            
        except Exception as e:
            print(f"Chart error: {e}")

    def update_summary_card(df, filename):
        """Update the summary statistics card with report data."""
        # Clear existing content
        for widget in summary_card.winfo_children():
            widget.destroy()
        
        # Title
        tk.Label(summary_card, text="📈 Report Summary", 
                font=("Helvetica", 16, "bold"), 
                bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
        
        # Metadata row
        meta_frame = tk.Frame(summary_card, bg=COLORS['white'])
        meta_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(meta_frame, text=f"📄 File: {filename}", 
                font=("Helvetica", 10), bg=COLORS['white'], fg=COLORS['text']).pack(side='left', padx=(0, 20))
        
        # Get file modification time
        try:
            file_path = os.path.join(report_dir, filename)
            mod_time = os.path.getmtime(file_path)
            date_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            tk.Label(meta_frame, text=f"🕒 Date: {date_str}", 
                    font=("Helvetica", 10), bg=COLORS['white'], fg=COLORS['text']).pack(side='left', padx=(0, 20))
        except:
            pass
        
        tk.Label(meta_frame, text=f"📊 Total Grains: {len(df)}", 
                font=("Helvetica", 10, "bold"), bg=COLORS['white'], fg=COLORS['primary']).pack(side='left')
        
        # Quality Assessment
        if 'Class' in df.columns:
            try:
                assessor = RiceQualityAssessor()
                quality_result = assessor.get_detailed_analysis(df)
                
                # Quality grade banner
                grade = quality_result.get('grade', 'Unknown')
                score = quality_result.get('score', 0.0)
                color = COLORS['success'] if grade == "High" else (COLORS['warning'] if grade == "Medium" else COLORS['error'])
                
                grade_frame = tk.Frame(summary_card, bg=color, relief='solid', bd=2)
                grade_frame.pack(fill='x', pady=(0, 15))
                
                grade_inner = tk.Frame(grade_frame, bg=color)
                grade_inner.pack(fill='x', padx=15, pady=10)
                
                tk.Label(grade_inner, text=f"Quality Grade: {grade}", 
                        font=("Helvetica", 14, "bold"), bg=color, fg=COLORS['white']).pack(side='left')
                
                tk.Label(grade_inner, text=f"Score: {score:.3f}", 
                        font=("Helvetica", 12), bg=color, fg=COLORS['white']).pack(side='left', padx=(20, 0))
                
                # Statistics grid
                stats_frame = tk.Frame(summary_card, bg=COLORS['white'])
                stats_frame.pack(fill='x', pady=(0, 10))
                
                counts = quality_result.get('counts', {})
                percents = quality_result.get('percents', {})
                premium_percent = quality_result.get('premium_percent', 0)
                
                # Create stat cards in a grid (without Short)
                stat_items = [
                    ("Premium Grains", f"{premium_percent:.1f}%", COLORS['success']),
                    ("Long", f"{counts.get('Long', 0)} ({percents.get('Long', 0):.1f}%)", COLORS['success']),
                    ("Medium", f"{counts.get('Medium', 0)} ({percents.get('Medium', 0):.1f}%)", COLORS['orange']),
                    ("Broken", f"{counts.get('Broken', 0)} ({percents.get('Broken', 0):.1f}%)", COLORS['error']),
                    ("Discolored", f"{counts.get('Discolored', 0)} ({percents.get('Discolored', 0):.1f}%)", COLORS['purple'])
                ]
                
                for i, (label, value, color) in enumerate(stat_items):
                    stat_card = tk.Frame(stats_frame, bg=COLORS['card_bg'], relief='solid', bd=1)
                    # Arrange in 2 rows: 3 items in first row, 2 in second row
                    if i < 3:
                        stat_card.grid(row=0, column=i, padx=5, pady=5, sticky='ew')
                    else:
                        # Center the last 2 items
                        stat_card.grid(row=1, column=i-3, padx=5, pady=5, sticky='ew')
                    
                    tk.Label(stat_card, text=label, font=("Helvetica", 9, "bold"), 
                            bg=COLORS['card_bg'], fg=COLORS['text']).pack(pady=(8, 2))
                    tk.Label(stat_card, text=value, font=("Helvetica", 12, "bold"), 
                            bg=COLORS['card_bg'], fg=color).pack(pady=(2, 8))
                
                # Configure grid weights - 3 columns
                stats_frame.grid_columnconfigure(0, weight=1)
                stats_frame.grid_columnconfigure(1, weight=1)
                stats_frame.grid_columnconfigure(2, weight=1)
                
                # Add a mini chart
                try:
                    chart_frame = tk.Frame(summary_card, bg=COLORS['white'])
                    chart_frame.pack(fill='x', pady=(10, 0))
                    
                    fig = Figure(figsize=(10, 3), facecolor=COLORS['white'])
                    ax = fig.add_subplot(111)
                    
                    # Grain distribution bar chart with proper colors (exclude Short)
                    grain_types = [g for g in counts.keys() if g != 'Short']
                    grain_counts = [counts[g] for g in grain_types]
                    # Map each grain type to its detection color
                    color_map = {
                        'Long': COLORS['success'],
                        'Medium': COLORS['orange'],
                        'Broken': COLORS['error'],
                        'Discolored': COLORS['purple']
                    }
                    colors_list = [color_map.get(g, COLORS['text']) for g in grain_types]
                    
                    bars = ax.bar(grain_types, grain_counts, color=colors_list, alpha=0.7)
                    ax.set_ylabel('Count', fontsize=10, color=COLORS['text'])
                    ax.set_title('Grain Distribution', fontsize=12, fontweight='bold', color=COLORS['primary'], pad=10)
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    
                    # Add value labels on bars
                    for bar, count in zip(bars, grain_counts):
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{int(count)}', ha='center', va='bottom', fontweight='bold', fontsize=9)
                    
                    canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
                    canvas_widget.draw()
                    canvas_widget.get_tk_widget().pack(fill='x', pady=5)
                    
                except Exception as e:
                    print(f"Chart error: {e}")
                
            except Exception as e:
                tk.Label(summary_card, text=f"⚠️ Quality assessment unavailable: {str(e)}", 
                        font=("Helvetica", 10), bg=COLORS['white'], fg=COLORS['error']).pack(pady=10)

    # Single file selection card with navigation (will be positioned at top by toggle_mode)
    single_frame = create_card(report_frame, bg=COLORS['white'])

    tk.Label(single_frame, text="📄 Browse Reports", 
            font=("Helvetica", 14, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 10))

    # Dropdown selector row
    selector_frame = tk.Frame(single_frame, bg=COLORS['white'])
    selector_frame.pack(fill='x', pady=(0, 10))

    selected_file = tk.StringVar()
    current_single_index = {'index': 0}
    
    if csv_files:
        selected_file.set(csv_files[0])
        current_single_index['index'] = 0
    
    tk.Label(selector_frame, text="Report:", font=("Helvetica", 10), 
            bg=COLORS['white'], fg=COLORS['text']).pack(side='left', padx=(0, 10))
    
    single_dropdown = ttk.Combobox(selector_frame, values=csv_files, textvariable=selected_file, 
                                   state="readonly", width=60, font=("Helvetica", 10))
    single_dropdown.pack(side='left', fill='x', expand=True)

    def on_file_select(event=None):
        if selected_file.get():
            # Update index
            try:
                current_single_index['index'] = csv_files.index(selected_file.get())
            except:
                pass
            load_csv_data(selected_file.get())

    single_dropdown.bind("<<ComboboxSelected>>", on_file_select)

    # Navigation buttons row (separate, more visible)
    nav_row = tk.Frame(single_frame, bg=COLORS['white'])
    nav_row.pack(fill='x', pady=(0, 10))
    
    tk.Label(nav_row, text="Navigate Reports:", font=("Helvetica", 10, "bold"), 
            bg=COLORS['white'], fg=COLORS['text']).pack(side='left', padx=(0, 15))
    
    def go_prev_single():
        if not csv_files:
            return
        current_single_index['index'] = (current_single_index['index'] - 1) % len(csv_files)
        selected_file.set(csv_files[current_single_index['index']])
        load_csv_data(csv_files[current_single_index['index']])
    
    def go_next_single():
        if not csv_files:
            return
        current_single_index['index'] = (current_single_index['index'] + 1) % len(csv_files)
        selected_file.set(csv_files[current_single_index['index']])
        load_csv_data(csv_files[current_single_index['index']])
    
    prev_single_btn = tk.Button(nav_row, text="◀ Previous Report", command=go_prev_single,
                                bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'),
                                relief='flat', padx=16, pady=8, cursor='hand2')
    prev_single_btn.pack(side='left', padx=(0, 10))
    
    next_single_btn = tk.Button(nav_row, text="Next Report ▶", command=go_next_single,
                                bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'),
                                relief='flat', padx=16, pady=8, cursor='hand2')
    next_single_btn.pack(side='left', padx=(0, 15))
    
    tk.Label(nav_row, text="(or use Left/Right arrow keys)",
            font=("Helvetica", 9, "italic"), bg=COLORS['white'], fg=COLORS['text']).pack(side='left')
    
    # Report counter
    counter_frame = tk.Frame(single_frame, bg=COLORS['card_bg'], relief='solid', bd=1)
    counter_frame.pack(fill='x', pady=(0, 10))
    
    counter_label = tk.Label(counter_frame, text=f"Viewing report 1 of {len(csv_files)}" if csv_files else "No reports",
                            font=("Helvetica", 11, "bold"), bg=COLORS['card_bg'], fg=COLORS['primary'])
    counter_label.pack(pady=8)
    
    def update_counter():
        if csv_files:
            counter_label.config(text=f"Viewing report {current_single_index['index'] + 1} of {len(csv_files)}")
    
    # Store update function for later use
    single_frame.update_counter = update_counter

    # Batch selection card (don't pack initially, toggle_mode will handle it)
    batch_frame = create_card(report_frame, bg=COLORS['white'])

    tk.Label(batch_frame, text="📁 Select Batch Report", 
            font=("Helvetica", 14, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 10))

    batch_selector_frame = tk.Frame(batch_frame, bg=COLORS['white'])
    batch_selector_frame.pack(fill='x', pady=(0, 15))
    
    tk.Label(batch_selector_frame, text="Batch:", font=("Helvetica", 10), 
            bg=COLORS['white'], fg=COLORS['text']).pack(side='left', padx=(0, 10))

    selected_batch = tk.StringVar()
    if batch_manifests:
        selected_batch.set(batch_manifests[0])
    batch_dropdown = ttk.Combobox(batch_selector_frame, values=batch_manifests, textvariable=selected_batch, 
                                  state="readonly", width=70, font=("Helvetica", 10))
    batch_dropdown.pack(side='left', fill='x', expand=True)

    # Per-batch item selector
    item_selector_frame = tk.Frame(batch_frame, bg=COLORS['white'])
    item_selector_frame.pack(fill='x', pady=(0, 10))
    
    tk.Label(item_selector_frame, text="Image:", font=("Helvetica", 10), 
            bg=COLORS['white'], fg=COLORS['text']).pack(side='left', padx=(0, 10))
    
    selected_batch_item = tk.StringVar()
    batch_item_dropdown = ttk.Combobox(item_selector_frame, values=[], textvariable=selected_batch_item, 
                                       state="readonly", width=70, font=("Helvetica", 10))
    batch_item_dropdown.pack(side='left', fill='x', expand=True)

    # Navigation buttons for batch items - more prominent
    nav_frame = tk.Frame(batch_frame, bg=COLORS['white'])
    nav_frame.pack(fill='x', pady=(0, 10))
    
    tk.Label(nav_frame, text="Navigate Batch Items:", font=("Helvetica", 10, "bold"), 
            bg=COLORS['white'], fg=COLORS['text']).pack(side='left', padx=(0, 15))
    
    prev_btn = tk.Button(nav_frame, text="◀ Previous Image", command=None, bg=COLORS['primary'], fg=COLORS['white'], 
                        font=('Helvetica', 10, 'bold'), relief='flat', padx=16, pady=8, cursor='hand2')
    next_btn = tk.Button(nav_frame, text="Next Image ▶", command=None, bg=COLORS['primary'], fg=COLORS['white'], 
                        font=('Helvetica', 10, 'bold'), relief='flat', padx=16, pady=8, cursor='hand2')
    prev_btn.pack(side='left', padx=(0, 10))
    next_btn.pack(side='left', padx=(0, 15))
    
    tk.Label(nav_frame, text="(or use Left/Right arrow keys)",
            font=("Helvetica", 9, "italic"), bg=COLORS['white'], fg=COLORS['text']).pack(side='left')

    batch_items_current = {'items': [], 'index': 0}

    def calculate_batch_overall_quality(items):
        """Calculate overall quality for entire batch from all items."""
        try:
            # Combine all CSVs
            all_dfs = []
            for item in items:
                cpath = item.get('csv_path', '')
                if cpath and os.path.exists(cpath):
                    df = pd.read_csv(cpath)
                    all_dfs.append(df)
            
            if not all_dfs:
                return None
            
            # Combine all data
            combined_df = pd.concat(all_dfs, ignore_index=True)
            
            # Calculate overall quality
            assessor = RiceQualityAssessor()
            overall_quality = assessor.get_detailed_analysis(combined_df)
            
            # Add batch info
            overall_quality['is_batch'] = True
            overall_quality['batch_size'] = len(items)
            
            return overall_quality
        except Exception as e:
            print(f"Error calculating batch quality: {e}")
            return None

    def load_batch_item_by_name(name):
        """Load a specific item from a batch report (shows overall batch quality)."""
        try:
            item = next((it for it in batch_items_current['items'] if it.get('file') == name), None)
            if not item:
                return
            
            # Load table from that CSV only (shows individual item data)
            for row in tree.get_children():
                tree.delete(row)
            cpath = item.get('csv_path', '')
            if cpath and os.path.exists(cpath):
                df = pd.read_csv(cpath)
                with open(cpath, newline='') as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    for r in reader:
                        tree.insert("", "end", values=r)
                
                # Show OVERALL BATCH quality in summary (not individual item)
                if 'overall_quality' in batch_items_current and batch_items_current['overall_quality']:
                    update_summary_card_batch(batch_items_current['overall_quality'], name)
                else:
                    # Fallback: calculate on the fly
                    overall_quality = calculate_batch_overall_quality(batch_items_current['items'])
                    if overall_quality:
                        batch_items_current['overall_quality'] = overall_quality
                        update_summary_card_batch(overall_quality, name)
                    else:
                        # Show individual if overall calculation fails
                        update_summary_card(df, name)
                
                # Show the batch item's image
                img_path = item.get('image_path', '')
                if img_path and os.path.exists(img_path):
                    csv_filename = os.path.basename(cpath)
                    show_report_image(csv_filename)
                
                # Scroll to top
                try:
                    canvas.yview_moveto(0)
                except:
                    pass
        except Exception as e:
            print(f"Error loading batch item: {e}")

    def load_batch_manifest(fname):
        """Load batch manifest and calculate overall batch quality."""
        try:
            with open(os.path.join(report_dir, fname), 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            items = manifest.get('items', [])
            batch_items_current['items'] = items
            
            # Calculate overall batch quality
            overall_quality = calculate_batch_overall_quality(items)
            batch_items_current['overall_quality'] = overall_quality
            
            names = [it.get('file', '') for it in items]
            batch_item_dropdown.configure(values=names)
            if names:
                selected_batch_item.set(names[0])
                batch_items_current['index'] = 0
                load_batch_item_by_name(names[0])
        except Exception as e:
            print(f"Error loading batch manifest: {e}")

    def on_batch_select(event=None):
        if selected_batch.get():
            load_batch_manifest(selected_batch.get())

    def on_batch_item_select(event=None):
        if selected_batch_item.get():
            name = selected_batch_item.get()
            # keep index in sync
            try:
                names = [it.get('file','') for it in batch_items_current['items']]
                if name in names:
                    batch_items_current['index'] = names.index(name)
            except Exception:
                pass
            load_batch_item_by_name(name)

    def go_prev_batch_item():
        items = batch_items_current['items']
        if not items:
            return
        batch_items_current['index'] = (batch_items_current['index'] - 1) % len(items)
        name = items[batch_items_current['index']].get('file','')
        selected_batch_item.set(name)
        load_batch_item_by_name(name)

    def go_next_batch_item():
        items = batch_items_current['items']
        if not items:
            return
        batch_items_current['index'] = (batch_items_current['index'] + 1) % len(items)
        name = items[batch_items_current['index']].get('file','')
        selected_batch_item.set(name)
        load_batch_item_by_name(name)

    batch_dropdown.bind("<<ComboboxSelected>>", on_batch_select)
    batch_item_dropdown.bind("<<ComboboxSelected>>", on_batch_item_select)
    prev_btn.configure(command=go_prev_batch_item)
    next_btn.configure(command=go_next_batch_item)

    # Treeview frame - styled card
    tree_card = create_card(report_frame, bg=COLORS['white'])
    tree_card.pack(fill="both", expand=True, padx=20, pady=10)

    tk.Label(tree_card, text="📋 Detailed Measurement Data", 
            font=("Helvetica", 16, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))

    # Create inner frame for table
    tree_frame = tk.Frame(tree_card, bg=COLORS['white'], relief='solid', bd=1)
    tree_frame.pack(fill="both", expand=True)

    # Treeview Table
    tree = ttk.Treeview(tree_frame, columns=("Grain#", "Class", "Confidence", "Center X", "Center Y", "X1", "Y1", "X2", "Y2"), 
                       show="headings", height=15)
    
    # Add scrollbars
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # Grid layout for tree and scrollbars
    tree.grid(column=0, row=0, sticky='nsew')
    vsb.grid(column=1, row=0, sticky='ns')
    hsb.grid(column=0, row=1, sticky='ew')

    tree_frame.grid_columnconfigure(0, weight=1)
    tree_frame.grid_rowconfigure(0, weight=1)

    # Configure columns with better widths
    column_widths = {
        "Grain#": 80,
        "Class": 100,
        "Confidence": 100,
        "Center X": 90,
        "Center Y": 90,
        "X1": 70,
        "Y1": 70,
        "X2": 70,
        "Y2": 70
    }

    for col in tree["columns"]:
        tree.heading(col, text=col)
        width = column_widths.get(col, 100)
        tree.column(col, anchor="center", width=width, minwidth=60)

    # Toggle visibility based on mode
    def toggle_mode(*args):
        if report_mode.get() == 'single':
            # Hide batch frame
            try:
                batch_frame.pack_forget()
            except Exception:
                pass
            # Show single frame AT THE TOP (before summary_card)
            try:
                single_frame.pack_forget()
            except Exception:
                pass
            single_frame.pack(fill="x", padx=20, pady=10, before=summary_card)
            # Load first report only when switching modes (args from trace_add)
            if csv_files and len(args) > 0:
                root.after(50, lambda: load_csv_data(csv_files[0]))
        else:
            # Hide single frame
            try:
                single_frame.pack_forget()
            except Exception:
                pass
            # Show batch frame AT THE TOP (before summary_card)
            try:
                batch_frame.pack_forget()
            except Exception:
                pass
            batch_frame.pack(fill="x", padx=20, pady=10, before=summary_card)
            # Load first batch only when switching modes (args from trace_add)
            if batch_manifests and len(args) > 0:
                root.after(50, lambda: load_batch_manifest(batch_manifests[0]))

    # Keyboard shortcuts for navigation
    def on_key_press(event):
        """Handle keyboard shortcuts for report navigation."""
        try:
            if report_mode.get() == 'single':
                if event.keysym == 'Left':
                    go_prev_single()
                elif event.keysym == 'Right':
                    go_next_single()
            elif report_mode.get() == 'batch':
                if event.keysym == 'Left':
                    go_prev_batch_item()
                elif event.keysym == 'Right':
                    go_next_batch_item()
        except:
            pass
    
    # Bind keyboard shortcuts
    canvas.bind('<Left>', on_key_press)
    canvas.bind('<Right>', on_key_press)
    canvas.focus_set()
    
    # Initialize the view
    report_mode.trace_add('write', toggle_mode)
    toggle_mode()  # Pack the navigation frame
    
    # Load initial data after layout is set up
    if report_mode.get() == 'single' and csv_files:
        root.after(100, lambda: load_csv_data(csv_files[0]))
    elif report_mode.get() == 'batch' and batch_manifests:
        root.after(100, lambda: load_batch_manifest(batch_manifests[0]))

def show_training():
    # Clear main content
    for widget in main.winfo_children():
        widget.destroy()

    # Create scrollable container
    canvas = tk.Canvas(main, bg=COLORS['background'], highlightthickness=0)
    scrollbar = tk.Scrollbar(main, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLORS['background'])

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    # Mouse wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # Header Card
    header_card = create_card(scrollable_frame, bg=COLORS['white'])
    header_card.pack(fill="x", padx=20, pady=(20, 10))

    title = tk.Label(header_card,
                     text="🎯 Fine-Tune Model (YOLOv8)",
                     font=("Helvetica", 28, "bold"),
                     bg=COLORS['white'], fg=COLORS['primary'])
    title.pack(pady=(0, 10))

    # Subtitle with better formatting
    subtitle = tk.Label(header_card,
                   text="Improve your existing rice grain segmentation model with additional training data",
                   font=("Helvetica", 12), bg=COLORS['white'], fg=COLORS['text'])
    subtitle.pack(pady=(0, 10))
    
    # Info banner - Fine-tuning explanation
    info_banner = tk.Frame(header_card, bg='#E3F2FD', relief='solid', bd=1)
    info_banner.pack(fill='x', pady=(0, 10))
    
    info_inner = tk.Frame(info_banner, bg='#E3F2FD')
    info_inner.pack(fill='x', padx=15, pady=10)
    
    tk.Label(info_inner, text="💡 Fine-Tuning with Instance Segmentation:", font=("Helvetica", 10, "bold"),
            bg='#E3F2FD', fg='#1565C0').pack(side='left', padx=(0, 10))
    tk.Label(info_inner, text="Start from your best trained segmentation model (e.g., weights.pt) and improve it with new data. This is more effective than training from scratch!",
            font=("Helvetica", 10), bg='#E3F2FD', fg='#1565C0', wraplength=900, justify='left').pack(side='left', fill='x', expand=True)

    # Configuration Card
    config_card = create_card(scrollable_frame, bg=COLORS['white'])
    config_card.pack(fill="x", padx=20, pady=10)
    
    tk.Label(config_card, text="⚙️ Training Configuration", 
            font=("Helvetica", 18, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))

    # State
    selected_zip = tk.StringVar(value="")
    # Default to best trained segmentation model for fine-tuning
    if os.path.exists("dataset/weightsV6.pt"):
        default_weights = "dataset/weightsV6.pt"
    elif os.path.exists("yolov8n-seg.pt"):
        default_weights = "yolov8n-seg.pt"
    else:
        default_weights = "yolov8n-seg.pt"  # Will download if needed
    selected_weights = tk.StringVar(value=default_weights)
    epochs_var = tk.StringVar(value="10")  # Lower epochs for fine-tuning
    imgsz_var = tk.StringVar(value="640")

    # 1. Dataset Selection Section
    ds_section = tk.Frame(config_card, bg=COLORS['white'])
    ds_section.pack(fill='x', pady=(0, 15))
    
    tk.Label(ds_section, text="📦 Dataset", 
            font=("Helvetica", 14, "bold"), 
            bg=COLORS['white'], fg=COLORS['text']).pack(anchor='w', pady=(0, 8))
    
    ds_frame = tk.Frame(ds_section, bg=COLORS['card_bg'], relief='solid', bd=1)
    ds_frame.pack(fill='x')
    
    ds_inner = tk.Frame(ds_frame, bg=COLORS['card_bg'])
    ds_inner.pack(fill='x', padx=15, pady=12)
    
    tk.Label(ds_inner, text="Dataset Zip File:", font=("Helvetica", 11, 'bold'), 
            bg=COLORS['card_bg'], fg=COLORS['text']).pack(anchor='w', pady=(0, 6))
    
    ds_path_frame = tk.Frame(ds_inner, bg=COLORS['card_bg'])
    ds_path_frame.pack(fill='x')
    
    ds_entry = tk.Entry(ds_path_frame, textvariable=selected_zip, font=("Helvetica", 10), 
                       bg=COLORS['white'], relief='solid', bd=1)
    ds_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))

    def pick_zip():
        path = filedialog.askopenfilename(title="Select YOLOv8 dataset zip", filetypes=[("Zip files", "*.zip")])
        if path:
            selected_zip.set(path)
            start_btn.config(state='normal')
    
    tk.Button(ds_path_frame, text="📂 Browse Files", command=pick_zip, 
             bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'),
             relief='flat', padx=16, pady=8, cursor='hand2').pack(side='left')
    
    tk.Label(ds_inner, text="💡 Dataset must contain data.yaml file with train/val splits", 
            font=("Helvetica", 9, "italic"), bg=COLORS['card_bg'], fg=COLORS['text']).pack(anchor='w', pady=(6, 0))

    # 2. Weights Selection Section - Fine-tuning from existing model
    wt_section = tk.Frame(config_card, bg=COLORS['white'])
    wt_section.pack(fill='x', pady=(0, 15))
    
    tk.Label(wt_section, text="🎯 Base Model for Fine-Tuning", 
            font=("Helvetica", 14, "bold"), 
            bg=COLORS['white'], fg=COLORS['text']).pack(anchor='w', pady=(0, 8))
    
    # Info box
    wt_info = tk.Frame(wt_section, bg='#E3F2FD', relief='solid', bd=1)
    wt_info.pack(fill='x', pady=(0, 8))
    wt_info_inner = tk.Frame(wt_info, bg='#E3F2FD')
    wt_info_inner.pack(fill='x', padx=10, pady=8)
    tk.Label(wt_info_inner, text="💡 Fine-tuning improves your existing model with new data. Start from your best trained model for best results.", 
            font=("Helvetica", 9, "italic"), bg='#E3F2FD', fg='#1565C0').pack(anchor='w')
    
    wt_frame = tk.Frame(wt_section, bg=COLORS['card_bg'], relief='solid', bd=1)
    wt_frame.pack(fill='x')
    
    wt_inner = tk.Frame(wt_frame, bg=COLORS['card_bg'])
    wt_inner.pack(fill='x', padx=15, pady=12)
    
    tk.Label(wt_inner, text="Starting Model Weights (.pt):", font=("Helvetica", 11, 'bold'), 
            bg=COLORS['card_bg'], fg=COLORS['text']).pack(anchor='w', pady=(0, 6))
    
    wt_path_frame = tk.Frame(wt_inner, bg=COLORS['card_bg'])
    wt_path_frame.pack(fill='x')
    
    wt_entry = tk.Entry(wt_path_frame, textvariable=selected_weights, font=("Helvetica", 10), 
                       bg=COLORS['white'], relief='solid', bd=1)
    wt_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
    
    def pick_weights():
        path = filedialog.askopenfilename(title="Select starting weights (.pt)", filetypes=[("PyTorch weights", "*.pt")])
        if path:
            selected_weights.set(path)
    
    tk.Button(wt_path_frame, text="📂 Browse Files", command=pick_weights, 
             bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'),
             relief='flat', padx=16, pady=8, cursor='hand2').pack(side='left')
    
    # Model type and status indicator
    model_status_frame = tk.Frame(wt_inner, bg=COLORS['card_bg'])
    model_status_frame.pack(fill='x', pady=(6, 0))
    
    model_type_label = tk.Label(model_status_frame, text="", font=("Helvetica", 9, "bold"), 
                               bg=COLORS['card_bg'], fg=COLORS['text'])
    model_type_label.pack(anchor='w')
    
    model_exists_label = tk.Label(model_status_frame, text="", font=("Helvetica", 9), 
                                 bg=COLORS['card_bg'], fg=COLORS['text'])
    model_exists_label.pack(anchor='w')
    
    def check_model_type():
        """Check if selected weights are appropriate for instance segmentation."""
        try:
            weights = selected_weights.get().strip()
            if not weights:
                model_type_label.config(text="💡 Recommended: Use your best trained segmentation model (e.g., weights.pt) for fine-tuning", 
                                       fg=COLORS['text'])
                model_exists_label.config(text="")
                return
            
            # Check if file exists
            if os.path.exists(weights):
                size_mb = os.path.getsize(weights) / (1024 * 1024)
                model_exists_label.config(text=f"✓ File found ({size_mb:.2f} MB)", fg=COLORS['success'])
            else:
                model_exists_label.config(text=f"⚠️ File not found - will attempt to download if it's a standard model", fg=COLORS['warning'])
            
            # Check model type - FOR SEGMENTATION
            weights_lower = weights.lower()
            if 'weightsv' in weights_lower or 'rice' in weights_lower:
                # Custom rice grain model (assumed to be segmentation)
                model_type_label.config(text="✓ Rice grain segmentation model - Perfect for fine-tuning!", 
                                       fg=COLORS['success'])
            elif '-seg' in weights_lower or 'segment' in weights_lower:
                # YOLOv8 segmentation model - CORRECT for instance segmentation
                model_type_label.config(text="✓ YOLOv8 segmentation model - Compatible with your dataset!", 
                                       fg=COLORS['success'])
            elif 'yolov8' in weights_lower and '-seg' not in weights_lower:
                # Detection only model - WRONG for segmentation
                model_type_label.config(text="⚠️ This is a DETECTION-only model. Use '-seg' models for segmentation datasets!", 
                                       fg=COLORS['error'])
            else:
                model_type_label.config(text="⚠️ Unknown model type - ensure it supports instance segmentation", 
                                       fg=COLORS['warning'])
        except:
            model_type_label.config(text="💡 Recommended: Use your best trained segmentation model for fine-tuning", 
                                   fg=COLORS['text'])
            model_exists_label.config(text="")
    
    # Update model type indicator when weights change
    selected_weights.trace_add('write', lambda *args: check_model_type())
    check_model_type()

    # 3. Hyperparameters Section
    hp_section = tk.Frame(config_card, bg=COLORS['white'])
    hp_section.pack(fill='x', pady=(0, 15))
    
    tk.Label(hp_section, text="🔧 Training Parameters", 
            font=("Helvetica", 14, "bold"), 
            bg=COLORS['white'], fg=COLORS['text']).pack(anchor='w', pady=(0, 8))
    
    hp_frame = tk.Frame(hp_section, bg=COLORS['card_bg'], relief='solid', bd=1)
    hp_frame.pack(fill='x')
    
    hp_inner = tk.Frame(hp_frame, bg=COLORS['card_bg'])
    hp_inner.pack(fill='x', padx=15, pady=12)
    
    # Create parameter grid
    param_grid = tk.Frame(hp_inner, bg=COLORS['card_bg'])
    param_grid.pack(fill='x')
    
    # Epochs
    epochs_frame = tk.Frame(param_grid, bg=COLORS['card_bg'])
    epochs_frame.pack(side='left', padx=(0, 30))
    tk.Label(epochs_frame, text="Epochs:", font=("Helvetica", 11, 'bold'), 
            bg=COLORS['card_bg'], fg=COLORS['text']).pack(side='left', padx=(0, 10))
    epochs_entry = tk.Entry(epochs_frame, textvariable=epochs_var, width=8, font=("Helvetica", 10),
                           bg=COLORS['white'], relief='solid', bd=1)
    epochs_entry.pack(side='left')
    
    # Image Size
    imgsz_frame = tk.Frame(param_grid, bg=COLORS['card_bg'])
    imgsz_frame.pack(side='left')
    tk.Label(imgsz_frame, text="Image Size:", font=("Helvetica", 11, 'bold'), 
            bg=COLORS['card_bg'], fg=COLORS['text']).pack(side='left', padx=(0, 10))
    imgsz_entry = tk.Entry(imgsz_frame, textvariable=imgsz_var, width=8, font=("Helvetica", 10),
                          bg=COLORS['white'], relief='solid', bd=1)
    imgsz_entry.pack(side='left')
    
    tk.Label(hp_inner, text="💡 For fine-tuning: Epochs=5-20 (fewer than training from scratch), Image Size=640 (standard)", 
            font=("Helvetica", 9, "italic"), bg=COLORS['card_bg'], fg=COLORS['text']).pack(anchor='w', pady=(10, 0))

    # 4. Action Button
    action_card = create_card(scrollable_frame, bg=COLORS['white'])
    action_card.pack(fill='x', padx=20, pady=10)
    
    action_frame = tk.Frame(action_card, bg=COLORS['white'])
    action_frame.pack(fill='x')

    # Status/log area (Section)
    status_card = create_card(scrollable_frame, bg=COLORS['white'])
    status_card.pack(fill='both', expand=True, padx=20, pady=10)
    
    tk.Label(status_card, text="📊 Training Progress", 
            font=("Helvetica", 16, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
    
    status = tk.Label(status_card, text="✓ Ready to train. Configure your dataset and parameters above, then click Start Training.", 
                     font=("Helvetica", 11), bg=COLORS['white'], fg=COLORS['text'])
    status.pack(pady=(0, 10), anchor='w')

    log_frame = tk.Frame(status_card, bg=COLORS['card_bg'], relief='solid', bd=1)
    log_frame.pack(fill='both', expand=True, pady=(0, 10))
    
    log = tk.Text(log_frame, height=12, bg=COLORS["white"], fg=COLORS['text'], 
                 relief='flat', bd=0, font=("Consolas", 9))
    log.pack(fill='both', expand=True, padx=10, pady=10)
    log.configure(state='disabled')

    # Placeholder for results image
    result_img_label = tk.Label(status_card, bg=COLORS['white'])
    result_img_label.pack(pady=(10, 10))
    result_img_label.image_ref = None

    def append_log(msg):
        try:
            log.configure(state='normal')
            log.insert('end', msg + "\n")
            log.see('end')
            log.configure(state='disabled')
            card.update_idletasks()
        except Exception:
            pass

    def find_data_yaml(root_dir):
        for r, _d, files in os.walk(root_dir):
            if 'data.yaml' in files:
                return os.path.join(r, 'data.yaml')
        return None

    def _is_abs_like(p: str) -> bool:
        try:
            return os.path.isabs(p) or re.match(r'^[A-Za-z]:[\\/]', p) is not None or p.startswith('/')
        except Exception:
            return False

    def normalize_data_yaml_paths(data_yaml_path: str):
        """Normalize data.yaml paths to absolute and anchored to its folder.
        - Force `path` to the absolute directory containing data.yaml
        - Convert train/val/valid/test to absolute paths
        - Strip any redundant leading segments like 'dataset/training/...'
        Returns True if the file was modified.
        """
        root_dir = os.path.dirname(data_yaml_path)
        modified = False
        try:
            try:
                import yaml  # type: ignore
            except Exception:
                yaml = None

            if yaml is not None:
                with open(data_yaml_path, 'r', encoding='utf-8') as f:
                    y = yaml.safe_load(f) or {}
                # Ensure dict
                if not isinstance(y, dict):
                    raise ValueError('data.yaml not a mapping')
                # Always anchor path to the extracted dataset folder
                abs_root = os.path.normpath(root_dir).replace('\\', '/')
                if str(y.get('path', '')) != abs_root:
                    y['path'] = abs_root
                    modified = True

                def _fix_subpath(v: str) -> str:
                    s = v.strip().strip('"\'')
                    # If value already absolute, just normalize separators
                    if _is_abs_like(s):
                        return os.path.normpath(s).replace('\\', '/')
                    # Common patterns inside zipped datasets that include redundant prefixes
                    # Try to collapse to one of the canonical subpaths relative to root
                    canonical_keys = ['train/images', 'val/images', 'valid/images', 'test/images']
                    for ck in canonical_keys:
                        idx = s.replace('\\', '/').lower().rfind(ck)
                        if idx != -1:
                            sub = s[idx:].replace('\\', '/')
                            return os.path.normpath(os.path.join(root_dir, sub)).replace('\\', '/')
                    # Fallback: join with root
                    return os.path.normpath(os.path.join(root_dir, s)).replace('\\', '/')

                base = y.get('path', abs_root)
                for k in ('train', 'val', 'valid', 'test'):
                    if k in y and isinstance(y[k], str):
                        new_v = _fix_subpath(y[k])
                        if y[k] != new_v:
                            y[k] = new_v
                            modified = True
                if modified:
                    with open(data_yaml_path, 'w', encoding='utf-8') as f:
                        yaml.safe_dump(y, f, sort_keys=False)
                return modified
        except Exception as e:
            append_log(f"YAML normalization via loader failed: {e}")

        # Fallback: simple line-based replacement
        try:
            with open(data_yaml_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('path:'):
                    # Force absolute path to the data.yaml folder
                    new_lines.append("path: " + os.path.abspath(root_dir).replace("\\", "/"))
                    modified = True
                    continue
                m = re.match(r'^(train|val|valid|test):\s*(.+)$', stripped)
                if m:
                    key, val = m.group(1), m.group(2).strip().strip('"\'')
                    # Normalize and collapse any redundant prefixes
                    if not _is_abs_like(val):
                        vnorm = val.replace('\\', '/')
                        for ck in ('train/images', 'val/images', 'valid/images', 'test/images'):
                            idx = vnorm.lower().rfind(ck)
                            if idx != -1:
                                vnorm = vnorm[idx:]
                                break
                        abs_p = os.path.normpath(os.path.join(os.path.abspath(root_dir), vnorm)).replace('\\', '/')
                        new_lines.append(f"{key}: {abs_p}")
                        modified = True
                        continue
                new_lines.append(line)
            if modified:
                with open(data_yaml_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(new_lines) + "\n")
        except Exception as e:
            append_log(f"Line-based YAML normalization failed: {e}")
        return modified

    def attempt_repair_dataset_yaml(data_yaml_path: str):
        """Try to locate typical YOLO folder structures and rewrite train/val accordingly.
        Returns True if the YAML was changed to existing paths.
        """
        try:
            try:
                import yaml  # type: ignore
            except Exception:
                yaml = None
            with open(data_yaml_path, 'r', encoding='utf-8') as f:
                original = f.read()
            y = None
            if yaml is not None:
                y = yaml.safe_load(original) or {}
            if not isinstance(y, dict):
                y = {}

            # Candidate roots: data.yaml dir, its parent, and grandparent
            d0 = os.path.dirname(data_yaml_path)
            candidates = [d0, os.path.dirname(d0), os.path.dirname(os.path.dirname(d0))]

            found = None
            def exists(p):
                return os.path.isdir(p)
            for root in candidates:
                imgs_train = os.path.join(root, 'images', 'train')
                imgs_val = os.path.join(root, 'images', 'val')
                imgs_valid = os.path.join(root, 'images', 'valid')
                timgs = os.path.join(root, 'train', 'images')
                vimgs = os.path.join(root, 'val', 'images')
                vidimgs = os.path.join(root, 'valid', 'images')
                if exists(imgs_train) and (exists(imgs_val) or exists(imgs_valid)):
                    found = (root, imgs_train, imgs_val if exists(imgs_val) else imgs_valid)
                    break
                if exists(timgs) and (exists(vimgs) or exists(vidimgs)):
                    found = (root, timgs, vimgs if exists(vimgs) else vidimgs)
                    break
            if not found:
                return False

            root, train_dir, val_dir = found
            # Ensure absolute paths are written to YAML
            root_abs = os.path.abspath(root)
            train_abs = os.path.abspath(train_dir)
            val_abs = os.path.abspath(val_dir)
            # Rewrite YAML
            y['path'] = os.path.normpath(root_abs).replace('\\', '/')
            y['train'] = os.path.normpath(train_abs).replace('\\', '/')
            y['val'] = os.path.normpath(val_abs).replace('\\', '/')

            # Write back
            if yaml is not None:
                with open(data_yaml_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(y, f, sort_keys=False)
            else:
                lines = []
                for k, v in y.items():
                    lines.append(f"{k}: {v}")
                with open(data_yaml_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(lines) + "\n")
            return True
        except Exception as e:
            append_log(f"Dataset YAML auto-repair failed: {e}")
            return False

    def verify_dataset_paths(data_yaml_path: str):
        """Return (ok, message). Checks that train/val(valid) images dirs exist."""
        try:
            try:
                import yaml  # type: ignore
            except Exception:
                yaml = None
            y = None
            if yaml is not None:
                with open(data_yaml_path, 'r', encoding='utf-8') as f:
                    y = yaml.safe_load(f) or {}
            if not isinstance(y, dict):
                # fallback parse
                y = {}
                with open(data_yaml_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        m = re.match(r'^(train|val|valid|test|path):\s*(.+)$', line.strip())
                        if m:
                            y[m.group(1)] = m.group(2).strip().strip('"\'')
            keys = []
            for k in ('train','val','valid'):
                if k in y and isinstance(y[k], str):
                    keys.append((k, y[k]))
            missing = []
            for k, p in keys:
                # Accept both filelist text files and folders; if folder, ensure exists
                p = p.strip()
                # If points to a text file of image list (.txt), accept
                if p.lower().endswith('.txt'):
                    if not os.path.exists(p):
                        missing.append(f"{k}: {p} (missing)")
                    continue
                if not os.path.isdir(p):
                    missing.append(f"{k}: {p} (directory missing)")
            if missing:
                return False, "Dataset paths not found: " + "; ".join(missing)
            return True, "OK"
        except Exception as e:
            return False, f"Could not verify dataset paths: {e}"

    def unzip_dataset(zip_path, dest_root):
        os.makedirs(dest_root, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest_root)
        return dest_root

    def display_results(save_dir):
        # Show metrics from results.csv and the results.png graph if present
        results_csv = os.path.join(save_dir, 'results.csv')
        results_png = os.path.join(save_dir, 'results.png')
        metrics_text = ""
        if os.path.exists(results_csv):
            try:
                df = pd.read_csv(results_csv)
                if len(df) > 0:
                    last = df.iloc[-1].to_dict()
                    # choose available keys
                    def pick(keys):
                        for k in keys:
                            if k in last and pd.notna(last[k]):
                                return float(last[k])
                        return None
                    map5095 = pick(['metrics/mAP50-95(B)', 'metrics/mAP50-95', 'mAP50-95'])
                    map50 = pick(['metrics/mAP50(B)', 'metrics/mAP50', 'mAP50'])
                    prec = pick(['metrics/precision(B)', 'precision'])
                    rec = pick(['metrics/recall(B)', 'recall'])
                    if map5095 is not None or map50 is not None or prec is not None or rec is not None:
                        parts = []
                        if map5095 is not None: parts.append(f"mAP50-95: {map5095:.4f}")
                        if map50 is not None: parts.append(f"mAP50: {map50:.4f}")
                        if prec is not None: parts.append(f"P: {prec:.4f}")
                        if rec is not None: parts.append(f"R: {rec:.4f}")
                        metrics_text = " | ".join(parts)
                    else:
                        metrics_text = "Training complete. See graph below."
            except Exception as e:
                metrics_text = f"Finished. Could not parse metrics: {e}"
        else:
            metrics_text = "Training complete. Results file not found."

        status.config(text=metrics_text, fg=COLORS['primary'])

        if os.path.exists(results_png):
            try:
                img = Image.open(results_png)
                max_w = 900
                new_w = min(max_w, img.width)
                new_h = int(new_w * img.height / img.width)
                img = img.resize((new_w, new_h), Image.LANCZOS)
                imgtk = ImageTk.PhotoImage(img)
                result_img_label.configure(image=imgtk)
                result_img_label.image_ref = imgtk
            except Exception as e:
                append_log(f"Could not display results graph: {e}")

    def start_training():
        zpath = selected_zip.get().strip()
        if not zpath or not os.path.exists(zpath):
            messagebox.showerror("Dataset Missing", "Please select a valid dataset zip file.")
            return
        try:
            ep = int(epochs_var.get())
            sz = int(imgsz_var.get())
        except Exception:
            messagebox.showerror("Invalid Params", "Epochs and Image Size must be integers.")
            return

        weights_path = selected_weights.get().strip()
        if not weights_path:
            messagebox.showerror("Weights Missing", "Please specify starting weights (.pt).")
            return
        
        # Check for detection-only model (wrong for segmentation)
        weights_lower = weights_path.lower()
        if 'yolov8' in weights_lower and '-seg' not in weights_lower and 'segment' not in weights_lower:
            # This is a detection-only YOLOv8 model
            if not messagebox.askyesno("Detection Model Warning", 
                               "⚠️ You selected a DETECTION-only model (without '-seg').\n\n"
                               "For instance segmentation datasets, you should use:\n"
                               "• yolov8n-seg.pt (nano segmentation)\n"
                               "• yolov8s-seg.pt (small segmentation)\n"
                               "• Your trained segmentation models (e.g., weights.pt)\n\n"
                               "Continue anyway? (May cause errors)"):
                return
        
        if not os.path.exists(weights_path):
            # Warn user this may trigger a download which might fail without internet
            if not messagebox.askokcancel("Weights Not Found", "Weights file not found. Ultralytics may try to download the model (requires internet). Continue?"):
                return

        # Progress window
        prog_win, prog_bar, prog_lbl = create_progress_window("Training model...", mode="indeterminate")
        try:
            prog_bar.start(10)
        except Exception:
            pass

        start_btn.config(state='disabled')

        def worker():
            save_dir = None
            try:
                ts = time.strftime('%Y%m%d_%H%M%S')
                work_root = os.path.join('dataset', 'training', ts)
                append_log(f"Unzipping dataset to {work_root} ...")
                unzip_dataset(zpath, work_root)
                data_yaml = find_data_yaml(work_root)
                if not data_yaml:
                    raise RuntimeError('data.yaml not found inside the zip.')
                append_log(f"Found data.yaml at {data_yaml}")
                try:
                    if normalize_data_yaml_paths(data_yaml):
                        append_log("Normalized data.yaml paths to absolute.")
                except Exception as e:
                    append_log(f"Warning: could not normalize data.yaml: {e}")

                # Prepare YOLO model
                append_log(f"Loading model weights: {weights_path}")
                # Ensure Ultralytics uses our singular 'dataset' directory, not '~\\Ultralytics\\datasets'
                try:
                    # Try multiple settings hooks across UL versions
                    updated = False
                    try:
                        from ultralytics.utils import SETTINGS as YSETTINGS  # type: ignore
                        YSETTINGS['datasets_dir'] = os.path.abspath('dataset')
                        updated = True
                    except Exception:
                        pass
                    if not updated:
                        try:
                            from ultralytics.utils import settings as ysettings  # older import path
                            ysettings.update({'datasets_dir': os.path.abspath('dataset')})
                            updated = True
                        except Exception:
                            pass
                    if not updated:
                        try:
                            from ultralytics import settings as ysettings  # newer import path
                            ysettings.update({'datasets_dir': os.path.abspath('dataset')})
                            updated = True
                        except Exception:
                            pass
                    if not updated:
                        raise RuntimeError('no settings backend available')
                except Exception as e:
                    append_log(f"Warning: could not update Ultralytics datasets_dir: {e}")
                mdl = YOLO(weights_path)

                project = os.path.join('runs')
                name = f"rice_train_{ts}"
                save_dir = os.path.join(project, name)
                os.makedirs(save_dir, exist_ok=True)

                # Quick dataset verification for clearer errors
                # Try a structural repair first to be extra robust, then verify
                repaired_once = False
                if attempt_repair_dataset_yaml(data_yaml):
                    repaired_once = True
                    append_log("Auto-repaired data.yaml paths based on detected folder structure.")
                ok, vmsg = verify_dataset_paths(data_yaml)
                if not ok:
                    append_log(f"Dataset verification failed: {vmsg}")
                    # Try one more time if not already attempted
                    if not repaired_once and attempt_repair_dataset_yaml(data_yaml):
                        append_log("Auto-repaired data.yaml paths based on detected folder structure.")
                        ok, vmsg = verify_dataset_paths(data_yaml)
                    if not ok:
                        raise RuntimeError(vmsg)

                # Show resolved dataset paths for clarity
                try:
                    import yaml  # type: ignore
                    with open(data_yaml, 'r', encoding='utf-8') as f:
                        y = yaml.safe_load(f) or {}
                    tr = y.get('train') or y.get('train_dir')
                    vl = y.get('val') or y.get('valid')
                    append_log(f"Using dataset: train={tr}; val={vl}")
                except Exception:
                    pass

                append_log("Starting training ... this can take a while.")
                # Pass an absolute path to avoid any prefixing by Ultralytics settings
                mdl.train(data=os.path.abspath(data_yaml), epochs=ep, imgsz=sz, project=project, name=name, exist_ok=True, verbose=False)
                append_log("Training finished.")

                def on_done():
                    close_progress_window(prog_win)
                    display_results(save_dir)
                    messagebox.showinfo("Training Complete", f"Training finished. Results saved to: {save_dir}")
                    start_btn.config(state='normal')
                root.after(0, on_done)
            except Exception as e:
                # capture message before leaving except block (exception vars are cleared)
                import traceback
                err_msg = str(e)
                err_tb = traceback.format_exc()
                def on_err(msg=err_msg, tb=err_tb):
                    close_progress_window(prog_win)
                    append_log(f"Error: {msg}")
                    if tb:
                        append_log(tb)
                    status.config(text=f"Training failed: {msg}", fg=COLORS['error'])
                    start_btn.config(state='normal')
                root.after(0, on_err)

        threading.Thread(target=worker, daemon=True).start()

    # Start Training Button (in action_card)
    start_btn = tk.Button(action_frame, text="🚀 Start Training", command=start_training, 
                         bg=COLORS['success'], fg=COLORS['white'], font=('Helvetica', 13, 'bold'),
                         relief='flat', padx=30, pady=12, cursor='hand2', state='disabled')
    start_btn.pack(side='left', pady=10)
    
    status_indicator = tk.Label(action_frame, text="⏳ Waiting for dataset selection...", 
                               font=("Helvetica", 10, "italic"), bg=COLORS['white'], fg=COLORS['warning'])
    status_indicator.pack(side='left', padx=(20, 0))
    
    # Update pick_zip to change status indicator
    original_pick_zip = pick_zip
    def pick_zip_with_status():
        original_pick_zip()
        if selected_zip.get():
            status_indicator.config(text="✓ Ready to train!", fg=COLORS['success'])
    
    # Replace the button command
    for widget in ds_path_frame.winfo_children():
        if isinstance(widget, tk.Button):
            widget.config(command=pick_zip_with_status)
            break
    
    # Important Notice Card - Instance Segmentation
    notice_card = create_card(scrollable_frame, bg='#E3F2FD')
    notice_card.pack(fill='x', padx=20, pady=10)
    notice_card.configure(highlightbackground='#2196F3', highlightthickness=3)
    
    notice_header = tk.Frame(notice_card, bg='#2196F3')
    notice_header.pack(fill='x', pady=(0, 10))
    
    tk.Label(notice_header, text="🎯 Instance Segmentation Models", 
            font=("Helvetica", 16, "bold"), 
            bg='#2196F3', fg='#FFFFFF').pack(padx=15, pady=10)
    
    notice_content = tk.Frame(notice_card, bg='#E3F2FD')
    notice_content.pack(fill='x', padx=15, pady=(0, 10))
    
    # What to use
    use_frame = tk.Frame(notice_content, bg='#D4EDDA', relief='solid', bd=1)
    use_frame.pack(fill='x', pady=(0, 10))
    use_inner = tk.Frame(use_frame, bg='#D4EDDA')
    use_inner.pack(fill='x', padx=10, pady=10)
    
    tk.Label(use_inner, text="✅ FOR INSTANCE SEGMENTATION DATASETS, USE:", 
            font=("Helvetica", 11, "bold"), bg='#D4EDDA', fg='#155724').pack(anchor='w', pady=(0, 5))
    tk.Label(use_inner, text="• yolov8n-seg.pt (nano segmentation - fastest)", 
            font=("Helvetica", 10), bg='#D4EDDA', fg='#155724').pack(anchor='w', padx=(15, 0))
    tk.Label(use_inner, text="• yolov8s-seg.pt (small segmentation)", 
            font=("Helvetica", 10), bg='#D4EDDA', fg='#155724').pack(anchor='w', padx=(15, 0))
    tk.Label(use_inner, text="• yolov8m-seg.pt (medium segmentation)", 
            font=("Helvetica", 10), bg='#D4EDDA', fg='#155724').pack(anchor='w', padx=(15, 0))
    tk.Label(use_inner, text="• Your own trained segmentation models (e.g., weights.pt)", 
            font=("Helvetica", 10, "bold"), bg='#D4EDDA', fg='#155724').pack(anchor='w', padx=(15, 0))
    
    
    # Help/Guide Card
    help_card = create_card(scrollable_frame, bg=COLORS['card_bg'])
    help_card.pack(fill='x', padx=20, pady=10)
    
    tk.Label(help_card, text="📚 Training Guide", 
            font=("Helvetica", 16, "bold"), 
            bg=COLORS['card_bg'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
    
    guide_items = [
        ("1️⃣ Prepare New Dataset", "Organize your additional training data in YOLO format with data.yaml and compress as .zip"),
        ("2️⃣ Select Base Model", "Choose your best existing model (e.g., weights.pt) to improve with new data"),
        ("3️⃣ Set Parameters", "Configure epochs (5-20 for fine-tuning) and image size (typically 640)"),
        ("4️⃣ Monitor Progress", "Watch the training log below for real-time updates and performance metrics"),
        ("5️⃣ View Results", "After fine-tuning completes, results graph will show improvement in metrics"),
        ("6️⃣ Use Improved Model", "Navigate to 'Choose Model' to activate your newly fine-tuned model for scanning")
    ]
    
    for step, desc in guide_items:
        guide_frame = tk.Frame(help_card, bg=COLORS['card_bg'])
        guide_frame.pack(fill='x', pady=(0, 8))
        
        tk.Label(guide_frame, text=step, font=("Helvetica", 10, "bold"),
                bg=COLORS['card_bg'], fg=COLORS['primary']).pack(anchor='w')
        tk.Label(guide_frame, text=desc, font=("Helvetica", 9),
                bg=COLORS['card_bg'], fg=COLORS['text'], wraplength=900, justify='left').pack(anchor='w', padx=(25, 0))

def show_settings():
    # Clear main content
    for widget in main.winfo_children():
        widget.destroy()

    # Create scrollable container
    canvas = tk.Canvas(main, bg=COLORS['background'], highlightthickness=0)
    scrollbar = tk.Scrollbar(main, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLORS['background'])

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    # Mouse wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # Header Card
    header_card = create_card(scrollable_frame, bg=COLORS['white'])
    header_card.pack(fill="x", padx=20, pady=(20, 10))

    title = tk.Label(header_card,
                     text="⚙️ Model Configuration",
                     font=("Helvetica", 28, "bold"),
                     bg=COLORS['white'], fg=COLORS['primary'])
    title.pack(pady=(0, 10))
    
    subtitle = tk.Label(header_card,
                       text="Configure which YOLO model to use for rice grain detection across the entire system",
                       font=("Helvetica", 12), bg=COLORS['white'], fg=COLORS['text'])
    subtitle.pack(pady=(0, 15))

    # Helpers to read/write config.json at project root
    def _config_path():
        try:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        except Exception:
            return 'config.json'

    def _read_model_from_config():
        try:
            p = _config_path()
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
                    v = data.get('model_path')
                    if isinstance(v, str) and v.strip():
                        return v.strip()
        except Exception:
            pass
        return ''

    def _write_model_to_config(path_val: str):
        try:
            cfg_path = _config_path()
            data = {}
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        data = json.load(f) or {}
                except Exception:
                    data = {}
            if path_val:
                data['model_path'] = path_val
            else:
                # remove key if present
                if 'model_path' in data:
                    del data['model_path']
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
            return False
    
    def _read_default_model_from_config():
        try:
            cfg_path = _config_path()
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
                    v = data.get('default_model_path')
                    if isinstance(v, str) and v.strip():
                        return v.strip()
        except Exception:
            pass
        return ''
    
    def _write_default_model_to_config(path_val: str):
        try:
            cfg_path = _config_path()
            data = {}
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        data = json.load(f) or {}
                except Exception:
                    data = {}
            if path_val:
                data['default_model_path'] = path_val
            else:
                if 'default_model_path' in data:
                    del data['default_model_path']
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save default model: {str(e)}")
            return False

    # Current model path state
    model_var = tk.StringVar(value=_read_model_from_config() or os.environ.get('GRAINSCAN_MODEL', ''))

    # Info banner
    info_banner = tk.Frame(header_card, bg=COLORS['card_bg'], relief='solid', bd=1)
    info_banner.pack(fill='x', pady=(0, 10))
    
    info_inner = tk.Frame(info_banner, bg=COLORS['card_bg'])
    info_inner.pack(fill='x', padx=15, pady=10)
    
    tk.Label(info_inner, text="🔍 Scope:", font=("Helvetica", 10, "bold"),
            bg=COLORS['card_bg'], fg=COLORS['primary']).pack(side='left', padx=(0, 10))
    tk.Label(info_inner, text="This model will be used for: Single image scans, Batch processing, Live camera capture, and Analytics.",
            font=("Helvetica", 10), bg=COLORS['card_bg'], fg=COLORS['text'], wraplength=900, justify='left').pack(side='left', fill='x', expand=True)

    # Default Model Configuration Card (NEW) - Moved to top

    default_card = create_card(scrollable_frame, bg=COLORS['white'])
    default_card.pack(fill='x', padx=20, pady=10)
    
    tk.Label(default_card, text="🔧 Default Model Configuration", 
            font=("Helvetica", 18, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
    
    # Info banner
    default_info = tk.Frame(default_card, bg='#E8F5E9', relief='solid', bd=1)
    default_info.pack(fill='x', pady=(0, 15))
    
    default_info_inner = tk.Frame(default_info, bg='#E8F5E9')
    default_info_inner.pack(fill='x', padx=15, pady=10)
    
    tk.Label(default_info_inner, text="💡 How it works:", font=("Helvetica", 10, "bold"),
            bg='#E8F5E9', fg='#2E7D32').pack(side='left', padx=(0, 10))
    tk.Label(default_info_inner, text="Configure your preferred 'go-to' model here. When you click '🔄 Use Default Model', it will switch to this model automatically.",
            font=("Helvetica", 10), bg='#E8F5E9', fg='#2E7D32', wraplength=800, justify='left').pack(side='left', fill='x', expand=True)
    
    # Default model input
    default_section = tk.Frame(default_card, bg=COLORS['white'])
    default_section.pack(fill='x', pady=(0, 15))
    
    tk.Label(default_section, text="Default Model Path:", font=("Helvetica", 12, 'bold'), 
            bg=COLORS['white'], fg=COLORS['text']).pack(anchor='w', pady=(0, 8))
    
    default_frame = tk.Frame(default_section, bg=COLORS['card_bg'], relief='solid', bd=1)
    default_frame.pack(fill='x')
    
    default_inner = tk.Frame(default_frame, bg=COLORS['card_bg'])
    default_inner.pack(fill='x', padx=15, pady=12)
    
    default_model_var = tk.StringVar(value=_read_default_model_from_config())
    
    default_entry = tk.Entry(default_inner, textvariable=default_model_var, font=("Helvetica", 10), 
                    bg=COLORS['white'], relief='solid', bd=1)
    default_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))

    def pick_default_model():
        path = filedialog.askopenfilename(title="Select Default YOLO weights (.pt)", filetypes=[("PyTorch weights", "*.pt")])
        if path:
            default_model_var.set(path)

    tk.Button(default_inner, text="📂 Browse Files", command=pick_default_model, 
             bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'),
             relief='flat', padx=16, pady=8, cursor='hand2').pack(side='right')
    
    # Save default button
    def save_default_model():
        path = default_model_var.get().strip()
        if not path:
            messagebox.showwarning("Empty Path", "Please specify a default model path.")
            return
        if not os.path.exists(path):
            if not messagebox.askyesno("File Not Found", "The specified file doesn't exist. Save anyway?"):
                return
        ok = _write_default_model_to_config(path)
        if ok:
            refresh_default_display()
            messagebox.showinfo("Success", f"Default model set to:\n{path}\n\nClick 'Use Default Model' button to apply this model.")
    
    default_btns_frame = tk.Frame(default_card, bg=COLORS['white'])
    default_btns_frame.pack(fill='x', pady=(0, 10))
    
    save_default_btn = tk.Button(default_btns_frame, text="💾 Save as Default", command=save_default_model, 
                                bg=COLORS['secondary'], fg=COLORS['white'], font=('Helvetica', 11, 'bold'),
                                relief='flat', padx=20, pady=10, cursor='hand2')
    save_default_btn.pack(side='left', padx=(0, 10))
    
    def use_current_as_default():
        """Set the current active model as the default."""
        current_path = model_var.get().strip() or _read_model_from_config()
        if current_path:
            default_model_var.set(current_path)
            save_default_model()
        else:
            messagebox.showwarning("No Active Model", "Please select and save a model first, then set it as default.")
    
    tk.Button(default_btns_frame, text="⭐ Use Current as Default", command=use_current_as_default, 
             bg=COLORS['warning'], fg=COLORS['text'], font=('Helvetica', 11, 'bold'),
             relief='flat', padx=20, pady=10, cursor='hand2').pack(side='left')
    
    # Show current default
    current_default_label = tk.Label(default_card, text="", font=("Helvetica", 9, "italic"), 
                                     bg=COLORS['white'], fg=COLORS['text'])
    current_default_label.pack(anchor='w')
    
    def refresh_default_display():
        default_path = _read_default_model_from_config()
        if default_path:
            current_default_label.config(text=f"✓ Current default: {default_path}", fg=COLORS['success'])
        else:
            current_default_label.config(text="⚠️ No default configured - click 'Save as Default' to set one", fg=COLORS['warning'])
    
    refresh_default_display()

    # Model Selection Card
    selection_card = create_card(scrollable_frame, bg=COLORS['white'])
    selection_card.pack(fill='x', padx=20, pady=10)
    
    tk.Label(selection_card, text="🤖 Select Model", 
            font=("Helvetica", 18, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
    
    # Model path input
    path_section = tk.Frame(selection_card, bg=COLORS['white'])
    path_section.pack(fill='x', pady=(0, 15))
    
    tk.Label(path_section, text="Model Weights File (.pt):", font=("Helvetica", 12, 'bold'), 
            bg=COLORS['white'], fg=COLORS['text']).pack(anchor='w', pady=(0, 8))
    
    path_frame = tk.Frame(path_section, bg=COLORS['card_bg'], relief='solid', bd=1)
    path_frame.pack(fill='x')
    
    path_inner = tk.Frame(path_frame, bg=COLORS['card_bg'])
    path_inner.pack(fill='x', padx=15, pady=12)
    
    entry = tk.Entry(path_inner, textvariable=model_var, font=("Helvetica", 10), 
                    bg=COLORS['white'], relief='solid', bd=1)
    entry.pack(side='left', fill='x', expand=True, padx=(0, 10))

    def pick_model():
        path = filedialog.askopenfilename(title="Select YOLO weights (.pt)", filetypes=[("PyTorch weights", "*.pt")])
        if path:
            model_var.set(path)

    tk.Button(path_inner, text="📂 Browse Files", command=pick_model, 
             bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 10, 'bold'),
             relief='flat', padx=16, pady=8, cursor='hand2').pack(side='right')

    # Status Card
    status_section_card = create_card(scrollable_frame, bg=COLORS['white'])
    status_section_card.pack(fill='x', padx=20, pady=10)
    
    tk.Label(status_section_card, text="📊 Current Status", 
            font=("Helvetica", 18, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))

    status = tk.Label(status_section_card, text="", font=("Helvetica", 11), bg=COLORS['white'], fg=COLORS['text'])
    status.pack(pady=(0, 10), anchor='w')

    # Active model preview with status indicator
    preview_card = tk.Frame(status_section_card, bg=COLORS['card_bg'], relief='solid', bd=1)
    preview_card.pack(fill='x', pady=(0, 15))
    
    preview_inner = tk.Frame(preview_card, bg=COLORS['card_bg'])
    preview_inner.pack(fill='x', padx=15, pady=12)
    
    tk.Label(preview_inner, text="🎯 Active Model:", font=("Helvetica", 11, "bold"),
            bg=COLORS['card_bg'], fg=COLORS['text']).pack(anchor='w', pady=(0, 6))
    
    active_lbl = tk.Label(preview_inner, text="", font=("Helvetica", 10), bg=COLORS['card_bg'], fg=COLORS['text'], wraplength=800, justify='left')
    active_lbl.pack(anchor='w')
    def refresh_active_preview():
        try:
            cur = model_var.get().strip() or _read_model_from_config() or os.environ.get('GRAINSCAN_MODEL', '')
            if cur:
                if os.path.exists(cur):
                    active_lbl.config(text=f"✓ {cur}", fg=COLORS['success'])
                    # Add file size info
                    try:
                        size_mb = os.path.getsize(cur) / (1024 * 1024)
                        size_info = tk.Label(preview_inner, text=f"📁 Size: {size_mb:.2f} MB", 
                                           font=("Helvetica", 9), bg=COLORS['card_bg'], fg=COLORS['text'])
                        # Remove old size labels
                        for w in preview_inner.winfo_children():
                            if isinstance(w, tk.Label) and w != active_lbl and '📁 Size:' in w.cget('text'):
                                w.destroy()
                        size_info.pack(anchor='w', pady=(4, 0))
                    except:
                        pass
                else:
                    active_lbl.config(text=f"⚠️ {cur} (file not found)", fg=COLORS['warning'])
            else:
                active_lbl.config(text="Using default model (first available)", fg=COLORS['text'])
        except Exception:
            active_lbl.config(text="Using default model", fg=COLORS['text'])
    refresh_active_preview()

    def save_model():
        path = model_var.get().strip()
        if not path:
            messagebox.showwarning("Empty Path", "Please specify a model path or use 'Use Default Model' button.")
            return
        if not os.path.exists(path):
            messagebox.showerror("Invalid Path", "Selected model file does not exist.")
            return
        ok = _write_model_to_config(path)
        if ok:
            # Also set env for current session so subsequent subprocesses use it immediately
            try:
                os.environ['GRAINSCAN_MODEL'] = path
            except Exception:
                pass
            status.config(text=f"✓ Model configuration saved successfully!", fg=COLORS['success'])
            refresh_active_preview()
            refresh_default_display()

    # Action Buttons Card
    actions_card = create_card(scrollable_frame, bg=COLORS['white'])
    actions_card.pack(fill='x', padx=20, pady=10)
    
    tk.Label(actions_card, text="💾 Actions", 
            font=("Helvetica", 18, "bold"), 
            bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
    
    btns = tk.Frame(actions_card, bg=COLORS['white'])
    btns.pack(fill='x', pady=(0, 10))
    
    tk.Button(btns, text="💾 Save Configuration", command=save_model, 
             bg=COLORS['success'], fg=COLORS['white'], font=('Helvetica', 12, 'bold'),
             relief='flat', padx=20, pady=10, cursor='hand2').pack(side='left', padx=(0, 10))
    
    def reset_default():
        """Apply the configured default model."""
        default_path = _read_default_model_from_config()
        if default_path:
            model_var.set(default_path)
            # Auto-save when using default
            ok = _write_model_to_config(default_path)
            if ok:
                try:
                    os.environ['GRAINSCAN_MODEL'] = default_path
                except Exception:
                    pass
                status.config(text=f"✓ Switched to default model: {default_path}", fg=COLORS['success'])
                refresh_active_preview()
                refresh_default_display()
        else:
            # No default configured - offer to clear or configure
            response = messagebox.askyesnocancel("No Default Configured", 
                                  "No default model is configured yet.\n\n"
                                  "• Click 'Yes' to configure a default model now\n"
                                  "• Click 'No' to clear the current model\n"
                                  "• Click 'Cancel' to do nothing")
            if response is None:  # Cancel
                return
            elif response:  # Yes - scroll to default config
                messagebox.showinfo("Configure Default", "Use the 'Default Model Configuration' section above to set your default model.")
            else:  # No - clear model
                ok = _write_model_to_config('')
                if ok:
                    try:
                        if 'GRAINSCAN_MODEL' in os.environ:
                            del os.environ['GRAINSCAN_MODEL']
                    except Exception:
                        pass
                    model_var.set('')
                    status.config(text="✓ Model cleared. Using system fallback.", fg=COLORS['warning'])
                    refresh_active_preview()
    
    tk.Button(btns, text="🔄 Use Default Model", command=reset_default, 
             bg=COLORS['primary'], fg=COLORS['white'], font=('Helvetica', 12, 'bold'),
             relief='flat', padx=20, pady=10, cursor='hand2').pack(side='left')
    
    tk.Label(btns, text="Changes apply to all scans and camera operations", 
            font=("Helvetica", 9, "italic"), bg=COLORS['white'], fg=COLORS['text']).pack(side='left', padx=(20, 0))
    
    # Help/Info Card
    help_card = create_card(scrollable_frame, bg=COLORS['card_bg'])
    help_card.pack(fill='x', padx=20, pady=10)
    
    tk.Label(help_card, text="💡 Model Selection Guide", 
            font=("Helvetica", 16, "bold"), 
            bg=COLORS['card_bg'], fg=COLORS['primary']).pack(anchor='w', pady=(0, 15))
    
    tips = [
        ("🎯 For Best Results", "Use a model specifically trained on rice grain images (e.g., weights.pt)"),
        ("🔧 Set Default Model", "Configure a default model above - it will be used when you click 'Use Default Model'"),
        ("⚡ Quick Switch", "Use '⭐ Use Current as Default' to quickly save your active model as the default"),
        ("🔄 After Training", "Navigate to 'Train Model' to create custom models, then select them here"),
        ("✅ Recommended", "Use the latest trained model from your training runs for optimal detection")
    ]
    
    for title, desc in tips:
        tip_frame = tk.Frame(help_card, bg=COLORS['card_bg'])
        tip_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(tip_frame, text=title, font=("Helvetica", 10, "bold"),
                bg=COLORS['card_bg'], fg=COLORS['text']).pack(anchor='w')
        tk.Label(tip_frame, text=desc, font=("Helvetica", 9),
                bg=COLORS['card_bg'], fg=COLORS['text'], wraplength=900, justify='left').pack(anchor='w', padx=(15, 0))

def show_home():
    # Clear main content
    for widget in main.winfo_children():
        widget.destroy()

    # Welcome section with modern card design
    welcome_card = create_card(main)
    welcome_card.pack(fill="x", pady=(0, 40), padx=20)

    title = tk.Label(welcome_card,
                    text="Welcome to GrainScan",
                    font=("Helvetica", 32, "bold"),
                    bg=COLORS['card_bg'],
                    fg=COLORS['primary'])
    title.pack(pady=(0, 10))

    subtitle = tk.Label(welcome_card,
                       text="Automated Rice Quality Inspection with Image Processing and Data Analytics",
                       font=("Helvetica", 16),
                       bg=COLORS['card_bg'],
                       fg=COLORS['text'])
    subtitle.pack()

    # Upload section with modern card design
    upload_card = create_card(main)
    upload_card.pack(fill="both", expand=True, padx=20, pady=20)

    # Add a subtle gradient effect to the upload card
    upload_card.configure(bg=COLORS['white'])

    try:
        upload_icon = Image.open("GUI/icon2.png")
        upload_icon = upload_icon.resize((150, 150), Image.LANCZOS)
        upload_img = ImageTk.PhotoImage(upload_icon)
        icon_label = tk.Label(upload_card, image=upload_img, bg=COLORS['white'])
        icon_label.image = upload_img
        icon_label.pack(pady=(20, 30))
    except:
        upload_label = tk.Label(upload_card,
                              text="📁",
                              font=("Helvetica", 64),
                              bg=COLORS['white'])
        upload_label.pack(pady=(20, 30))

    upload_text = tk.Label(upload_card,
                          text="Upload Rice Grain Image",
                          font=("Helvetica", 24, "bold"),
                          bg=COLORS['white'],
                          fg=COLORS['primary'])
    upload_text.pack(pady=(0, 30))

    # Add a description text
    description = tk.Label(upload_card,
                          text="Choose an option below to analyze rice grains",
                          font=("Helvetica", 12),
                          bg=COLORS['white'],
                          fg=COLORS['text'])
    description.pack(pady=(0, 20))

    # Create a frame for buttons
    button_frame = tk.Frame(upload_card, bg=COLORS['white'])
    button_frame.pack(pady=10)

    # Add both buttons side by side
    upload_button = create_rounded_button(button_frame,
                                        "Select Image",
                                        browse_image,
                                        bg=COLORS['primary'],
                                        fg=COLORS['white'],
                                        compact=True)
    upload_button.pack(side='left', padx=10)

    camera_button = create_rounded_button(button_frame,
                                        "Live Camera",
                                        start_live_camera,
                                        bg=COLORS['secondary'],
                                        fg=COLORS['white'],
                                        compact=True)
    camera_button.pack(side='left', padx=10)

    # Batch buttons
    batch_files_btn = create_rounded_button(button_frame,
                                         "Batch Scan (Files)",
                                         browse_images_batch_files,
                                         bg=COLORS['primary'],
                                         fg=COLORS['white'],
                                         compact=True)
    batch_files_btn.pack(side='left', padx=10)

    batch_folder_btn = create_rounded_button(button_frame,
                                          "Batch Scan (Folder)",
                                          browse_images_batch_folder,
                                          bg=COLORS['primary'],
                                          fg=COLORS['white'],
                                          compact=True)
    batch_folder_btn.pack(side='left', padx=10)

    global status_label
    status_label = tk.Label(upload_card,
                          text="",
                          font=("Helvetica", 12),
                          bg=COLORS['white'])
    status_label.pack(pady=20)

    # Footer with modern design
    footer = create_card(main)
    footer.pack(fill="x", pady=(20, 0), padx=20)
    
    footer_text = tk.Label(footer,
                          text="© 2025 GrainScan - Automated Rice Quality Inspection",
                          font=("Helvetica", 10),
                          bg=COLORS['card_bg'],
                          fg=COLORS['text'])
    footer_text.pack()

def build_gui():
    global root, status_label, main
    root = tk.Tk()
    root.title("GrainScan")
    
    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Set window size to 90% of screen size
    window_width = int(screen_width * 1)
    window_height = int(screen_height * 1)
    
    # Calculate position for center of screen
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    
    # Set window size and position
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Configure background color
    root.configure(bg=COLORS['background'])

    # Create and apply custom style
    create_style()

    # Sidebar
    sidebar = tk.Frame(root, bg=COLORS['primary'], width=250)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    # Logo
    try:
        logo = Image.open("GUI/logo1.png")
        logo = logo.resize((150, 150), Image.LANCZOS)
        logo_img = ImageTk.PhotoImage(logo)
        logo_label = tk.Label(sidebar, image=logo_img, bg=COLORS['primary'])
        logo_label.image = logo_img
        logo_label.pack(pady=(30, 20))
    except:
        title_label = tk.Label(sidebar, text="GrainScan", 
                             font=("Helvetica", 24, "bold"),
                             bg=COLORS['primary'],
                             fg=COLORS['white'])
        title_label.pack(pady=(30, 20))

    # Navigation buttons
    nav_items = [
        ("Scan Image", lambda: show_home(), "GUI/scan.png"),
        ("Analytics", show_analytics, "GUI/analytics.png"),
        ("Reports", show_report, "GUI/report.png"),
        ("Train Model", lambda: show_training(), "GUI/graph.png"),
        ("Choose Model", show_settings, "GUI/blockchain1.png")
    ]

    # Create a frame for navigation buttons with padding
    nav_frame = tk.Frame(sidebar, bg=COLORS['primary'])
    nav_frame.pack(fill="both", expand=True, padx=10, pady=20)

    for text, command, icon_path in nav_items:
        btn = create_rounded_button(nav_frame, text, 
                                  command if command else lambda: None,
                                  bg=COLORS['primary'],
                                  icon_path=icon_path)
        btn.pack(fill='x', pady=5, padx=0)

    # Main content area
    main = tk.Frame(root, bg=COLORS['background'])
    main.pack(fill="both", expand=True, padx=40, pady=40)

    # Show home page initially
    show_home()

    root.mainloop()

if __name__ == "__main__":
    build_gui()

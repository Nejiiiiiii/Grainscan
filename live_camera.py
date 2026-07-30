import cv2
import numpy as np
from ultralytics import YOLO
import os
from datetime import datetime
import csv
import time
import traceback
import tempfile
try:
    from tkinter import messagebox as tk_messagebox
except Exception:
    tk_messagebox = None
from test_main import process_image as process_captured_image, NoRiceDetectedError

# Configuration
MAX_WIDTH = 3840  # Support up to 4K resolution
MAX_HEIGHT = 2160  # Support up to 4K resolution
PROCESS_EVERY_N_FRAMES = 1  # Show all frames; processing happens on capture
DISPLAY_SCALE = 0.9  # Scale factor for display window

# Try different common resolutions if the preferred one fails
CAMERA_RESOLUTIONS = [
    (3840, 2160),  # 4K UHD - Highest quality
    (2560, 1440),  # 2K QHD
    (1920, 1080),  # Full HD
    (1280, 720),   # HD - Fallback for performance
    (800, 600),    # SVGA
    (640, 480)     # VGA
]

class LiveCameraError(Exception):
    """Custom exception for live camera failures"""
    pass

def resize_image(image):
    height, width = image.shape[:2]
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        scale = min(MAX_WIDTH / width, MAX_HEIGHT / height)
        return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    return image

# Removed coin-based scaling for live capture; the classification pipeline
# from test_main will handle detection/analytics like normal image scan.

def draw_overlay(frame, text, color=(0, 255, 0)):
    try:
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    except Exception:
        pass

def capture_and_process(frame_bgr):
    """Save a captured frame and run the standard processing pipeline."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Save the raw capture to a temporary folder instead of report/
        tmp_dir = tempfile.gettempdir()
        img_path = os.path.join(tmp_dir, f"capture_{timestamp}.jpg")
        cv2.imwrite(img_path, frame_bgr)
        # Ensure GUI mode for processing (suppresses extra windows)
        os.environ["GRAINSCAN_GUI"] = "1"
        # Pass through selected model if set in config.json
        try:
            import json
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cfg_path = os.path.join(base_dir, 'config.json')
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
                    m = data.get('model_path')
                    if isinstance(m, str) and m.strip():
                        os.environ['GRAINSCAN_MODEL'] = m.strip()
        except Exception:
            pass
        result = process_captured_image(img_path)
        try:
            os.remove(img_path)
        except Exception:
            pass
        return True, result
    except NoRiceDetectedError as e:
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except Exception:
            pass
        return False, str(e)
    except Exception as e:
        traceback.print_exc()
        try:
            if 'img_path' in locals() and os.path.exists(img_path):
                os.remove(img_path)
        except Exception:
            pass
        return False, f"Error: {str(e)}"

def save_frame_measurements(*args, **kwargs):
    # Deprecated in new live capture flow
    return None

def initialize_camera():
    """Try to initialize camera with different resolutions"""
    for width, height in CAMERA_RESOLUTIONS:
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Try DirectShow backend on Windows
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)  # Try default backend if DirectShow fails
                if not cap.isOpened():
                    continue

            # Try to set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Verify if the resolution was set correctly
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # Convert to int
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # Convert to int
            
            # Read a test frame
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"Camera initialized successfully at {actual_width}x{actual_height}")
                return cap, actual_width, actual_height
            
            cap.release()
        except Exception as e:
            print(f"Failed to initialize camera at {width}x{height}: {str(e)}")
            if 'cap' in locals():
                cap.release()
            continue
    
    raise LiveCameraError("Could not initialize camera with any supported resolution")

def start_live_camera(show_result_window=None, on_no_rice=None):
    cap = None
    try:
        # Initialize camera with retry logic
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                cap, actual_width, actual_height = initialize_camera()
                break
            except LiveCameraError as e:
                if attempt < max_retries - 1:
                    print(f"Camera initialization attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise LiveCameraError(f"Failed to initialize camera after {max_retries} attempts: {str(e)}")

        # Create window with instructions
        window_name = 'Live Rice Grain Capture'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        display_width = int(actual_width * DISPLAY_SCALE)
        display_height = int(actual_height * DISPLAY_SCALE)
        cv2.resizeWindow(window_name, (display_width, display_height))
        
        # Try to bring window to front (Windows-specific)
        try:
            import platform
            if platform.system() == 'Windows':
                import ctypes
                hwnd = ctypes.windll.user32.FindWindowW(None, window_name)
                if hwnd:
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

        last_message = "Press 'C' to Capture, 'Q' or ESC to Quit"
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame, retrying...")
                time.sleep(0.1)
                continue

            frame_count += 1
            
            # Convert to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Draw overlay message
            draw_overlay(frame, last_message, (0, 255, 0))

            # Resize for display
            display_frame = cv2.resize(frame, (display_width, display_height))
            cv2.imshow(window_name, cv2.cvtColor(display_frame, cv2.COLOR_RGB2BGR))

            # Check for key press - use longer delay for better key detection
            # Also check for both uppercase and lowercase, and ESC key
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q') or key == ord('Q') or key == 27:  # Quit (Q or ESC)
                print("Quit key pressed")
                break
            elif key == ord('c') or key == ord('C'):  # Capture
                print("Capture key pressed")
                # Convert back to BGR for saving
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                success, result = capture_and_process(frame_bgr)
                if success:
                    try:
                        img_path = result.get('annotated_image_path')
                        grade = result.get('grade', 'Unknown')
                        msg = f"Captured ✓ | Grade: {grade}"
                        last_message = msg
                        # Invoke GUI callback to show standard result window if provided
                        if callable(show_result_window):
                            try:
                                show_result_window(result)
                            except Exception:
                                traceback.print_exc()
                        # Close after single capture
                        break
                    except Exception:
                        last_message = "Captured ✓"
                        break
                else:
                    # result contains error message string
                    last_message = "No rice grains detected"
                    try:
                        if tk_messagebox:
                            tk_messagebox.showerror("No Rice Detected", "No rice grains were detected. Please use a clear rice grain image.")
                        elif callable(on_no_rice):
                            try:
                                on_no_rice()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # Close after single failed capture as well
                    break

    except LiveCameraError as e:
        print(f"Camera Error: {str(e)}")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
    return True

if __name__ == "__main__":
    start_live_camera()
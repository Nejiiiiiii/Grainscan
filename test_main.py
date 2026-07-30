import cv2
import numpy as np
from tkinter import Tk, filedialog
from ultralytics import YOLO
import csv
import os
import sys
import json
import pandas as pd
from quality_assessment import RiceQualityAssessor

# Configuration
MAX_WIDTH = 1920
MAX_HEIGHT = 1080
STRICT_MODE = False
MIN_GRAINS_REQUIRED = 1
MIN_PREFILTER_GRAINS = 30 if STRICT_MODE else 3
MIN_WHITE_RATIO = 0.05 if STRICT_MODE else 0.005  # at least white/low-sat pixels overall

# Dynamic model loading
# The model path can be provided via env var GRAINSCAN_MODEL or config.json at project root
_MODEL_INSTANCE = None
_MODEL_PATH_ACTIVE = None

def _config_path():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, 'config.json')
    except Exception:
        return 'config.json'

def _read_config_model_path():
    try:
        cfg_p = _config_path()
        if os.path.exists(cfg_p):
            with open(cfg_p, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
                p = data.get('model_path')
                if isinstance(p, str) and p.strip():
                    return p.strip()
    except Exception:
        pass
    return None

def _fallback_model_candidates():
    return [
        'dataset/weightsV6.pt',
        'dataset/weightsV4.pt',
        'dataset/weightsV4.1.pt',
        'dataset/weightsV2.pt',
        'dataset/weightsV1.pt',
        'yolov8n-seg.pt',  # Segmentation model (for instance segmentation)
        'yolov8s-seg.pt',
        'yolov8m-seg.pt',
        'yolov8n.pt',      # Detection fallback
        'yolov8s.pt'
    ]

def get_model_path():
    env_path = os.environ.get('GRAINSCAN_MODEL')
    if isinstance(env_path, str) and env_path.strip():
        return env_path.strip()
    cfg_path = _read_config_model_path()
    if cfg_path:
        return cfg_path
    # choose first existing fallback if any; otherwise return the first as a hint
    for cand in _fallback_model_candidates():
        try:
            if os.path.exists(cand):
                return cand
        except Exception:
            continue
    return _fallback_model_candidates()[0]

def get_model():
    global _MODEL_INSTANCE, _MODEL_PATH_ACTIVE
    try:
        desired_path = get_model_path()
        if (_MODEL_INSTANCE is None) or (_MODEL_PATH_ACTIVE != desired_path):
            # Attempt to load/reload model
            _MODEL_INSTANCE = YOLO(desired_path)
            _MODEL_PATH_ACTIVE = desired_path
            if not os.environ.get("GRAINSCAN_GUI"):
                print(f"YOLOv8 model loaded: {_MODEL_PATH_ACTIVE}")
        return _MODEL_INSTANCE
    except Exception as e:
        _MODEL_INSTANCE = None
        _MODEL_PATH_ACTIVE = None
        raise InferenceError(f"Failed to load model '{get_model_path()}': {e}")

class InferenceError(Exception):
    """Custom exception for inference failures"""
    pass

class NoRiceDetectedError(Exception):
    """Raised when the model finds no rice grains in the image"""
    pass

def select_image():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select an image",
        filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.bmp")]
    )
    root.destroy()
    return file_path

def resize_image(image):
    height, width = image.shape[:2]
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        scale = min(MAX_WIDTH / width, MAX_HEIGHT / height)
        return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    return image

def run_yolo_classification(image):
    """Run YOLO inference and return annotated image and detections.

    Returns (annotated_bgr_image, detections_list)
    detections_list items: (label:str, confidence:float, (cx:int, cy:int), (x1:int,y1:int,x2:int,y2:int))
    """
    mdl = get_model()

    h_img, w_img = image.shape[:2]
    # Run inference
    # Run with higher confidence in strict mode
    conf_th = 0.85 if STRICT_MODE else 0.4
    # Suppress verbose output in GUI mode
    verbose = not os.environ.get("GRAINSCAN_GUI")
    results = mdl(image, conf=conf_th, iou=0.45, verbose=verbose)
    res = results[0]

    if res.boxes is None or len(res.boxes) == 0:
        # No detections
        return image.copy(), []

    xyxy = res.boxes.xyxy.cpu().numpy()
    confs = res.boxes.conf.cpu().numpy()
    classes = res.boxes.cls.cpu().numpy().astype(int)

    # Allowed classes from your rice model and color mapping
    allowed_lower = {"long", "medium", "short", "discolored", "broken"}
    canonical_map = {
        "long": "Long",
        "medium": "Medium",
        "short": "Short",
        "discolored": "Discolored",
        "broken": "Broken",
    }
    # Color mapping per class label
    # Default colors if unknown labels appear
    class_to_color = {
        'Long': (0, 200, 0),          # green
        'Medium': (0, 165, 255),      # orange (BGR)
        'Short': (255, 140, 0),       # blue-ish
        'Discolored': (180, 0, 180),  # purple
        'Broken': (0, 0, 255),        # red
    }

    output = image.copy()
    detections = []

    # Heuristic filters for rice grains (primary strict pass)
    image_area = w_img * h_img
    min_area_ratio = 8e-6      # allow smaller grains after resize
    max_area_ratio = 0.25      # avoid huge boxes
    min_aspect_ratio = 1.0     # grains are generally elongated, but allow ~needle=1.0
    max_aspect_ratio = 18.0

    primary_conf_threshold = conf_th

    primary_detections = []

    for (x1, y1, x2, y2), conf, cls in zip(xyxy, confs, classes):
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        raw_label = str(mdl.names[cls]).strip()
        raw_label_lower = raw_label.lower()
        if raw_label_lower not in allowed_lower:
            continue
        label = canonical_map[raw_label_lower]

        # Size and aspect ratio checks
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        area_ratio = (bw * bh) / max(1, image_area)
        aspect_ratio = max(bw, bh) / max(1, min(bw, bh))
        # Geometry/shape validation using contour + ellipse
        shape_ok = False
        try:
            roi = image[max(0, y1):min(h_img, y2), max(0, x1):min(w_img, x2)]
            if roi.size > 0:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (5, 5), 0)
                edges = cv2.Canny(gray, 50, 150)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    largest = max(contours, key=cv2.contourArea)
                    area = cv2.contourArea(largest)
                    if area > 20:
                        ellipse_ok = False
                        if len(largest) >= 5:
                            ellipse = cv2.fitEllipse(largest)
                            (_, _), (maj, minr), _ = ellipse
                            if minr > 0:
                                ellipse_ratio = max(maj, minr) / max(1e-6, min(maj, minr))
                                # rice grains elongated: prefer >= 1.6
                                if ellipse_ratio >= 1.6:
                                    ellipse_ok = True
                        # solidity and edge density checks
                        hull = cv2.convexHull(largest)
                        hull_area = cv2.contourArea(hull)
                        solidity = area / max(1.0, hull_area)
                        edge_density = (edges > 0).mean()
                        # thresholds chosen to reject random textures/shapes
                        if ellipse_ok and solidity >= (0.8 if STRICT_MODE else 0.65) and 0.01 <= edge_density <= (0.20 if STRICT_MODE else 0.30):
                            shape_ok = True
        except Exception:
            shape_ok = False

        # Per-ROI color validation: require low saturation and high value on average
        roi_ok = False
        try:
            roi = image[max(0, y1):min(h_img, y2), max(0, x1):min(w_img, x2)]
            if roi.size > 0:
                hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                mean_s = float(hsv_roi[:, :, 1].mean())
                mean_v = float(hsv_roi[:, :, 2].mean())
                s_thr = 70 if STRICT_MODE else 110
                v_thr = 170 if STRICT_MODE else 130
                if mean_s <= s_thr and mean_v >= v_thr:
                    roi_ok = True
        except Exception:
            roi_ok = False

        # Accept policy:
        # - In STRICT_MODE: require geometry AND color checks
        # - In non-strict mode: accept by confidence and coarse size/aspect only
        accept_non_strict = (not STRICT_MODE) and (conf >= primary_conf_threshold) and (min_area_ratio <= area_ratio <= max_area_ratio) and (min_aspect_ratio <= aspect_ratio <= max_aspect_ratio)
        accept_strict = STRICT_MODE and (conf >= primary_conf_threshold) and (min_area_ratio <= area_ratio <= max_area_ratio) and (min_aspect_ratio <= aspect_ratio <= max_aspect_ratio) and (shape_ok and roi_ok)
        if accept_non_strict or accept_strict:
            # Do not draw yet; collect for class-agnostic NMS first
            primary_detections.append((label, float(conf), (cx, cy), (x1, y1, x2, y2)))
            continue

        # Collect candidates list (for potential future diagnostics)
        detections.append((label, float(conf), (cx, cy), (x1, y1, x2, y2)))

    # Secondary NMS on primary detections to drop duplicate overlaps
    def iou(a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter = inter_w * inter_h
        area_a = max(0, (ax2 - ax1)) * max(0, (ay2 - ay1))
        area_b = max(0, (bx2 - bx1)) * max(0, (by2 - by1))
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0

    if primary_detections:
        # sort by confidence desc
        primary_detections.sort(key=lambda d: d[1], reverse=True)
        kept = []
        for det in primary_detections:
            _, conf, _, (x1, y1, x2, y2) = det
            drop = False
            for k in kept:
                _, kc, _, (kx1, ky1, kx2, ky2) = k
                if iou((x1, y1, x2, y2), (kx1, ky1, kx2, ky2)) > 0.5:
                    drop = True
                    break
            if not drop:
                kept.append(det)
        # Now draw only the NMS-kept boxes
        for label, conf, (cx, cy), (x1, y1, x2, y2) in kept:
            color = class_to_color.get(label, (255, 255, 0))
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            cv2.putText(output, f"{label} {conf:.2f}", (x1, max(0, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return output, kept

    # No allowed detections at all
    return image.copy(), []

def is_rice_like_image(image_bgr):
    """Fast pre-filter: returns True if the image likely contains rice grains.

    Heuristics:
    - Light, low-saturation pixels segmented in HSV
    - Contours elongated (aspect >= 1.6) and not too small/large
    - Require at least MIN_PREFILTER_GRAINS such contours
    """
    try:
        h_img, w_img = image_bgr.shape[:2]
        image_area = max(1, h_img * w_img)

        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        # Light and low saturation mask (typical for rice on contrasting background)
        light_mask = cv2.inRange(hsv, (0, 0, 165), (179, 90, 255))
        # Global coverage check: if there are too few white-ish pixels, likely not rice
        white_ratio = float((light_mask > 0).sum()) / float(h_img * w_img)
        if white_ratio < MIN_WHITE_RATIO:
            return False
        # Clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        light_mask = cv2.morphologyEx(light_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(light_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 15:
                continue
            rect = cv2.minAreaRect(cnt)
            (cx, cy), (w, h), angle = rect
            if w <= 0 or h <= 0:
                continue
            a = max(w, h) / max(1e-6, min(w, h))
            # Area ratio vs image to avoid huge shapes
            area_ratio = (w * h) / image_area
            if a >= 1.6 and 1e-6 <= area_ratio <= 0.15:
                valid += 1
                if valid >= MIN_PREFILTER_GRAINS:
                    return True
        return False
    except Exception:
        # On failure, do not block; allow model to decide
        return True

    return output, detections

def mask_coin(image, coin_params, margin=1.5):
    x, y, r = coin_params
    mask = np.ones(image.shape, dtype=np.uint8) * 255
    cv2.circle(mask, (x, y), int(r * margin), (0, 0, 0), -1)
    return cv2.bitwise_and(image, mask)

def mask_coin(*args, **kwargs):
    # Deprecated; kept for backward import safety if referenced elsewhere
    return args[0]

def save_detections_csv(detections, image_path):
    # Create 'report' folder if it doesn't exist
    output_folder = "report"
    os.makedirs(output_folder, exist_ok=True)

    # Save as report/measurements_<image_name>.csv to keep GUI compatibility
    base_name = os.path.basename(image_path)
    csv_name = f"measurements_{os.path.splitext(base_name)[0]}.csv"
    csv_path = os.path.join(output_folder, csv_name)

    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Grain#", "Class", "Confidence", "Center X", "Center Y", "X1", "Y1", "X2", "Y2"]) 
        for i, (label, conf, (cx, cy), (x1, y1, x2, y2)) in enumerate(detections, start=1):
            writer.writerow([i, label, f"{conf:.4f}", int(cx), int(cy), x1, y1, x2, y2])

    if not os.environ.get("GRAINSCAN_GUI"):
        print(f"Detection results saved to: {csv_path}")
    
    # Return the CSV path for quality assessment
    return csv_path


def process_image(image_path):
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError("Image not found!")

    image_bgr = resize_image(image_bgr)

    # Fast pre-filter (advisory): if it says not rice, still allow YOLO to try
    prefilter_ok = is_rice_like_image(image_bgr)

    annotated_bgr, detections = run_yolo_classification(image_bgr)

    # If YOLO fails but prefilter thought it was rice, allow error as 'no grains'.
    # If both fail, return the 'not a rice image' error.
    if not detections or len(detections) < MIN_GRAINS_REQUIRED:
        if not prefilter_ok:
            raise NoRiceDetectedError("The provided image does not appear to contain rice grains.")
        # Do not save report artifacts; signal error to caller
        raise NoRiceDetectedError("No rice grains detected in the image. Please use a rice grain image.")

    # Save CSV and annotated image when detections exist
    csv_path = save_detections_csv(detections, image_path)

    # Save the annotated image in the report directory (keeps same naming convention)
    output_folder = "report"
    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.basename(image_path)
    img_name = f"measurements_{os.path.splitext(base_name)[0]}.jpg"
    img_path = os.path.join(output_folder, img_name)
    cv2.imwrite(img_path, annotated_bgr)

    # Perform quality assessment
    try:
        assessor = RiceQualityAssessor()
        df = pd.read_csv(csv_path)
        quality_result = assessor.get_detailed_analysis(df)
        
        # Add annotated image path to result
        quality_result['annotated_image_path'] = img_path
        
        # Only print quality assessment result if not in GUI mode
        if not os.environ.get("GRAINSCAN_GUI"):
            print("Quality Assessment Result:")
            print(json.dumps(quality_result, indent=2))
        
        # Return JSON result for GUI
        return quality_result
        
    except Exception as e:
        if not os.environ.get("GRAINSCAN_GUI"):
            print(f"Warning: Quality assessment failed: {str(e)}")
        # Return basic result without quality assessment
        return {
            'grade': 'Unknown',
            'score': 0.0,
            'explanation': 'Quality assessment failed',
            'counts': {},
            'percents': {},
            'total': len(detections),
            'annotated_image_path': img_path
        }

    # Also show the image for manual review (only if not in GUI mode)
    if not os.environ.get("GRAINSCAN_GUI"):
        cv2.imshow('Rice Classification', annotated_bgr)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else select_image()
    if image_path:
        try:
            result = process_image(image_path)
            # Print JSON result for GUI consumption (only the JSON, nothing else)
            print(json.dumps(result))
        except NoRiceDetectedError as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(3)
        except InferenceError as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(2)
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)
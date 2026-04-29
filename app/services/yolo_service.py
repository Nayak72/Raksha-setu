"""
RakshaSetu — YOLO Detection Service
Downloads zone images from the Supabase 'Input Images' bucket
and runs YOLOv8 inference using the custom-trained best.pt model
to produce detection_data for the agent pipeline + live dashboard.

Custom Model Classes:
  0: person
  1: vehicle
  2: flooded_area
  3: fire_smoke
  4: damaged_struct
  5: safe_struct
"""

import io
import base64
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger("raksha.yolo")
settings = get_settings()

# ── Model path ──────────────────────────────────────────────
MODEL_PATH = str(Path(__file__).resolve().parent.parent.parent / "model_pipeline" / "weights" / "best.pt")

# ── Custom class definitions ────────────────────────────────
CLASS_NAMES = ['person', 'vehicle', 'flooded_area', 'fire_smoke', 'damaged_struct', 'safe_struct']

# Disaster-type classes (non person/vehicle)
DISASTER_CLASSES = {'flooded_area', 'fire_smoke', 'damaged_struct'}

# Color palette for bounding box rendering (BGR for OpenCV, but we use PIL)
CLASS_COLORS = {
    'person':         (59, 130, 246),   # blue
    'vehicle':        (249, 115, 22),   # orange
    'flooded_area':   (14, 165, 233),   # cyan
    'fire_smoke':     (239, 68, 68),    # red
    'damaged_struct': (168, 85, 247),   # purple
    'safe_struct':    (34, 197, 94),    # green
}

# ── YOLO Model (lazy-loaded) ────────────────────────────────
_yolo_model = None


def _get_yolo_model():
    """Lazy-load the custom-trained YOLOv8 model."""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO(MODEL_PATH)
            logger.info("yolo.model_loaded", extra={"model": MODEL_PATH, "classes": CLASS_NAMES})
        except ImportError:
            logger.warning(
                "yolo.ultralytics_not_installed — falling back to mock detection. "
                "Install with: pip install ultralytics"
            )
            _yolo_model = None
        except Exception as e:
            logger.error(f"yolo.model_load_failed: {e}")
            _yolo_model = None
    return _yolo_model


# ── Zone-to-Folder Mapping ─────────────────────────────────
# Maps zone_id (UUID from simulation) to the Supabase storage folder
# These UUIDs match KARNATAKA_DISASTER_ZONES in app/services/zones.py
ZONE_FOLDER_MAP = {
    # Mangalore Coastal Flood Zone
    "11111111-1111-4111-8111-111111111111": "zone1",
    # Udupi-Malpe Cyclone Zone
    "22222222-2222-4222-8222-222222222222": "zone2",
    # Karwar Storm Surge Zone
    "33333333-3333-4333-8333-333333333333": "zone3",
    # Chikkamagaluru Landslide Zone
    "44444444-4444-4444-8444-444444444444": "zone4",
    # DK-Puttur Flood Zone
    "55555555-5555-4555-8555-555555555555": "zone5",
    # Ankola Cyclone Zone
    "66666666-6666-4666-8666-666666666666": "zone6",
    # Sringeri Landslide Zone
    "77777777-7777-4777-8777-777777777777": "zone7",
    # Legacy short IDs (keep for backward compatibility)
    "zone_001": "zone1",
    "zone_002": "zone2",
    "zone_003": "zone3",
    "zone_004": "zone4",
    "zone_005": "zone5",
    "zone_006": "zone6",
    "zone_007": "zone7",
}


def _get_zone_folder(zone_id: str) -> str:
    """
    Map a zone_id to a Supabase storage folder name.
    Falls back to a deterministic zone if the zone_id is unknown.
    """
    if zone_id in ZONE_FOLDER_MAP:
        return ZONE_FOLDER_MAP[zone_id]
    # For unknown zone_ids, deterministically pick a zone
    # based on a hash of the zone_id
    zone_num = (hash(zone_id) % 7) + 1
    return f"zone{zone_num}"


def list_zone_images(zone_id: str) -> list[dict]:
    """
    List all images in a zone's folder from the Supabase bucket.
    Returns list of dicts with name, size, mimetype, public_url.
    """
    from app.db.supabase_client import get_supabase
    sb = get_supabase()

    folder = _get_zone_folder(zone_id)
    bucket_name = "Input Images"

    try:
        files = sb.storage.from_(bucket_name).list(folder)
        results = []
        for f in files:
            if f.get("id") is None:
                continue  # Skip sub-folders
            name = f.get("name", "")
            meta = f.get("metadata", {}) or {}
            mimetype = meta.get("mimetype", "")
            if not mimetype.startswith("image/"):
                continue
            public_url = sb.storage.from_(bucket_name).get_public_url(f"{folder}/{name}")
            results.append({
                "name": name,
                "size": meta.get("size", 0),
                "mimetype": mimetype,
                "url": public_url,
                "path": f"{folder}/{name}",
            })
        logger.info(f"yolo.listed_images zone={zone_id} folder={folder} count={len(results)}")
        return results
    except Exception as e:
        logger.error(f"yolo.list_images_failed: {e}")
        return []


def list_all_bucket_images() -> list[dict]:
    """
    List all images across all zone folders in the Supabase bucket.
    Returns list of dicts with zone, name, url.
    """
    from app.db.supabase_client import get_supabase
    sb = get_supabase()
    bucket_name = "Input Images"
    all_images = []

    # Deduplicate folders (multiple zone IDs may map to the same folder)
    seen_folders = set()
    for zone_id, folder in ZONE_FOLDER_MAP.items():
        if folder in seen_folders:
            continue
        seen_folders.add(folder)
        try:
            files = sb.storage.from_(bucket_name).list(folder)
            for f in files:
                if f.get("id") is None:
                    continue
                name = f.get("name", "")
                meta = f.get("metadata", {}) or {}
                mimetype = meta.get("mimetype", "")
                if not mimetype.startswith("image/"):
                    continue
                public_url = sb.storage.from_(bucket_name).get_public_url(f"{folder}/{name}")
                all_images.append({
                    "zone_id": zone_id,
                    "zone_folder": folder,
                    "name": name,
                    "url": public_url,
                    "path": f"{folder}/{name}",
                })
        except Exception as e:
            logger.warning(f"yolo.list_bucket_failed folder={folder}: {e}")

    return all_images


def download_image(source: str) -> Optional[bytes]:
    """Download an image from a public URL or a Supabase bucket path."""
    if source.startswith("http://") or source.startswith("https://"):
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(source)
                resp.raise_for_status()
                return resp.content
        except Exception as e:
            logger.warning(f"yolo.download_failed url={source}: {e}")
            return None
    else:
        # Assume it's a Supabase bucket path
        try:
            from app.db.supabase_client import get_supabase
            sb = get_supabase()
            return sb.storage.from_("Input Images").download(source)
        except Exception as e:
            logger.warning(f"yolo.download_supabase_failed path={source}: {e}")
            return None


def run_yolo_on_image(image_bytes: bytes, conf_threshold: float = 0.25) -> dict:
    """
    Run YOLOv8 inference on a single image using the custom best.pt model.
    Returns raw detection results with bounding boxes.
    """
    model = _get_yolo_model()
    if model is None:
        return {"error": "YOLO model not available"}

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        img_width, img_height = img.size

        results = model(img, verbose=False, conf=conf_threshold)
        detections = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names.get(cls_id, f"class_{cls_id}")
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                detections.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(float(box.conf[0]), 4),
                    "bbox": [round(v, 1) for v in [x1, y1, x2, y2]],
                    # Normalized bbox for frontend overlay
                    "bbox_norm": {
                        "x": round(x1 / img_width, 4),
                        "y": round(y1 / img_height, 4),
                        "w": round((x2 - x1) / img_width, 4),
                        "h": round((y2 - y1) / img_height, 4),
                    },
                })

        return {
            "detections": detections,
            "num_detections": len(detections),
            "image_size": {"width": img_width, "height": img_height},
        }
    except Exception as e:
        logger.error(f"yolo.inference_failed: {e}")
        return {"error": str(e), "detections": [], "num_detections": 0}


def run_yolo_with_annotated_image(image_bytes: bytes, conf_threshold: float = 0.25) -> dict:
    """
    Run YOLOv8 inference and return both detections AND an annotated image
    with bounding boxes drawn on it (as base64).
    """
    model = _get_yolo_model()
    if model is None:
        return {"error": "YOLO model not available"}

    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_width, img_height = img.size

        results = model(img, verbose=False, conf=conf_threshold)
        detections = []
        draw = ImageDraw.Draw(img)

        # Try to use a reasonable font size
        font_size = max(12, min(img_width, img_height) // 40)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names.get(cls_id, f"class_{cls_id}")
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                color = CLASS_COLORS.get(cls_name, (255, 255, 255))
                label = f"{cls_name} {conf:.2f}"

                # Draw bounding box
                line_width = max(2, min(img_width, img_height) // 200)
                draw.rectangle([x1, y1, x2, y2], outline=color, width=line_width)

                # Draw label background
                text_bbox = draw.textbbox((x1, y1), label, font=font)
                text_w = text_bbox[2] - text_bbox[0]
                text_h = text_bbox[3] - text_bbox[1]
                label_y = max(0, y1 - text_h - 4)
                draw.rectangle([x1, label_y, x1 + text_w + 6, label_y + text_h + 4],
                               fill=color)
                draw.text((x1 + 3, label_y + 2), label, fill=(255, 255, 255), font=font)

                detections.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(conf, 4),
                    "bbox": [round(v, 1) for v in [x1, y1, x2, y2]],
                    "bbox_norm": {
                        "x": round(x1 / img_width, 4),
                        "y": round(y1 / img_height, 4),
                        "w": round((x2 - x1) / img_width, 4),
                        "h": round((y2 - y1) / img_height, 4),
                    },
                })

        # Encode annotated image as base64 JPEG
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        annotated_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        # Classify disaster type from detections
        disaster_types = set()
        for d in detections:
            if d["class_name"] in DISASTER_CLASSES:
                disaster_types.add(d["class_name"])

        return {
            "detections": detections,
            "num_detections": len(detections),
            "image_size": {"width": img_width, "height": img_height},
            "annotated_image": f"data:image/jpeg;base64,{annotated_b64}",
            "disaster_types": list(disaster_types),
            "summary": _summarize_detections(detections),
        }
    except Exception as e:
        logger.error(f"yolo.annotated_inference_failed: {e}")
        return {"error": str(e), "detections": [], "num_detections": 0}


def _summarize_detections(detections: list[dict]) -> dict:
    """Build a summary of detection counts by class."""
    summary = {}
    for d in detections:
        cls = d["class_name"]
        if cls not in summary:
            summary[cls] = {"count": 0, "avg_conf": 0.0, "max_conf": 0.0}
        summary[cls]["count"] += 1
        summary[cls]["avg_conf"] += d["confidence"]
        summary[cls]["max_conf"] = max(summary[cls]["max_conf"], d["confidence"])

    for cls in summary:
        if summary[cls]["count"] > 0:
            summary[cls]["avg_conf"] = round(summary[cls]["avg_conf"] / summary[cls]["count"], 4)

    return summary


def _detections_to_metrics(all_detections: list[dict]) -> dict:
    """
    Convert raw YOLO detections into the detection_data metrics
    expected by the Triage agent.

    Custom model class mapping:
      0: person       → crowd_density
      1: vehicle      → vehicle_count
      2: flooded_area → flood_level
      3: fire_smoke   → fire_detected
      4: damaged_struct → structural_damage
      5: safe_struct   → (positive indicator)
    """
    person_count = 0
    vehicle_count = 0
    flood_indicators = 0
    fire_indicators = 0
    damage_indicators = 0
    safe_indicators = 0
    total_confidence = 0.0
    detection_count = 0

    for det in all_detections:
        cls = det.get("class_name", "").lower()
        conf = det.get("confidence", 0)
        total_confidence += conf
        detection_count += 1

        if cls == "person":
            person_count += 1
        elif cls == "vehicle":
            vehicle_count += 1
        elif cls == "flooded_area":
            flood_indicators += 1
        elif cls == "fire_smoke":
            fire_indicators += 1
        elif cls == "damaged_struct":
            damage_indicators += 1
        elif cls == "safe_struct":
            safe_indicators += 1

    # Normalize to 0-1 range
    crowd_density = min(1.0, person_count / 50.0)
    flood_level = min(1.0, flood_indicators / 3.0)
    structural_damage = min(1.0, damage_indicators / 3.0)
    avg_confidence = total_confidence / max(detection_count, 1)

    return {
        "crowd_density": round(crowd_density, 3),
        "flood_level": round(flood_level, 3),
        "structural_damage": round(structural_damage, 3),
        "fire_detected": fire_indicators > 0,
        "fire_count": fire_indicators,
        "vehicle_count": vehicle_count,
        "safe_structures": safe_indicators,
        "confidence": round(avg_confidence, 3),
        "person_count": person_count,
        "total_detections": detection_count,
    }


def analyze_zone_images(zone_id: str, max_images: int = 5) -> dict:
    """
    Full pipeline: list images → download → run YOLO → aggregate metrics.
    This is the main entry point that replaces generate_mock_detection().

    Args:
        zone_id: The zone identifier
        max_images: Max number of images to analyze (for speed)

    Returns:
        detection_data dict compatible with the Triage agent
    """
    logger.info(f"yolo.analyzing_zone zone={zone_id}")

    # 1. List available images
    images = list_zone_images(zone_id)
    if not images:
        logger.warning(f"yolo.no_images zone={zone_id} — falling back to mock detection")
        from app.shared.tools import generate_mock_detection
        return generate_mock_detection(zone_id)

    # 2. Sample a subset for analysis
    sample = random.sample(images, min(max_images, len(images)))

    # 3. Download and analyze each image
    all_detections = []
    analyzed_count = 0

    for img_info in sample:
        image_bytes = download_image(img_info.get("path") or img_info["url"])
        if image_bytes is None:
            continue

        result = run_yolo_on_image(image_bytes)
        if "error" not in result:
            all_detections.extend(result.get("detections", []))
            analyzed_count += 1

    if analyzed_count == 0:
        logger.warning(f"yolo.no_successful_analysis zone={zone_id} — falling back to mock")
        from app.shared.tools import generate_mock_detection
        return generate_mock_detection(zone_id)

    # 4. Aggregate into detection metrics
    metrics = _detections_to_metrics(all_detections)
    metrics["zone_id"] = zone_id
    metrics["timestamp"] = datetime.now(timezone.utc).isoformat()
    metrics["images_analyzed"] = analyzed_count
    metrics["source"] = "yolo_v8_custom"

    logger.info(
        f"yolo.analysis_complete zone={zone_id} "
        f"images={analyzed_count} crowd={metrics['crowd_density']:.3f} "
        f"flood={metrics['flood_level']:.3f} damage={metrics['structural_damage']:.3f}"
    )

    return metrics


def detect_single_image(image_source: str, zone_id: str = "unknown") -> dict:
    """
    Download a single image and run full annotated detection.
    Used by the /api/v1/yolo/detect endpoint.
    """
    image_bytes = download_image(image_source)
    if image_bytes is None:
        return {"error": f"Failed to download image from {image_source}"}

    result = run_yolo_with_annotated_image(image_bytes)
    result["zone_id"] = zone_id
    result["source_url"] = image_source
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    result["model"] = "best.pt (RakshaSetu custom)"
    result["classes"] = CLASS_NAMES
    return result


def detect_zone(zone_id: str, max_images: int = 4) -> list[dict]:
    """
    Run annotated detection on multiple images from a zone.
    Returns a list of detection results with annotated images.
    """
    images = list_zone_images(zone_id)
    if not images:
        return []

    sample = random.sample(images, min(max_images, len(images)))
    results = []

    for img_info in sample:
        result = detect_single_image(img_info.get("path") or img_info["url"], zone_id)
        result["image_name"] = img_info["name"]
        results.append(result)

    return results

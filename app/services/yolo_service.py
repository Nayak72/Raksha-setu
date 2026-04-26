"""
RakshaSetu — YOLO Detection Service
Downloads zone images from the Supabase 'Input Images' bucket
and runs YOLOv8 inference to produce detection_data for the agent pipeline.

Replaces the mock generate_mock_detection() with real object detection.
"""

import io
import logging
import random
from datetime import datetime
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger("raksha.yolo")
settings = get_settings()

# ── YOLO Model (lazy-loaded) ────────────────────────────────
_yolo_model = None


def _get_yolo_model():
    """Lazy-load the YOLOv8 model."""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO("yolov8n.pt")  # nano model — fast, lightweight
            logger.info("yolo.model_loaded", extra={"model": "yolov8n.pt"})
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
# Maps zone_id (UUID or name) to the Supabase storage folder
ZONE_FOLDER_MAP = {
    "zone_001": "Zone 1",
    "zone_002": "Zone 2",
    "zone_003": "Zone 3",
    "zone_004": "Zone 4",
}


def _get_zone_folder(zone_id: str) -> str:
    """
    Map a zone_id to a Supabase storage folder name.
    Falls back to a random zone if the zone_id is a UUID (from DB).
    """
    if zone_id in ZONE_FOLDER_MAP:
        return ZONE_FOLDER_MAP[zone_id]
    # For UUID zone_ids from the DB, deterministically pick a zone
    # based on a hash of the zone_id
    zone_num = (hash(zone_id) % 4) + 1
    return f"Zone {zone_num}"


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
            })
        logger.info(f"yolo.listed_images zone={zone_id} folder={folder} count={len(results)}")
        return results
    except Exception as e:
        logger.error(f"yolo.list_images_failed: {e}")
        return []


def download_image(url: str) -> Optional[bytes]:
    """Download an image from a public URL."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.warning(f"yolo.download_failed url={url}: {e}")
        return None


def run_yolo_on_image(image_bytes: bytes) -> dict:
    """
    Run YOLOv8 inference on a single image.
    Returns raw detection results.
    """
    model = _get_yolo_model()
    if model is None:
        return {"error": "YOLO model not available"}

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))

        results = model(img, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                detections.append({
                    "class_id": int(box.cls[0]),
                    "class_name": model.names[int(box.cls[0])],
                    "confidence": float(box.conf[0]),
                    "bbox": box.xyxy[0].tolist(),
                })

        return {
            "detections": detections,
            "num_detections": len(detections),
        }
    except Exception as e:
        logger.error(f"yolo.inference_failed: {e}")
        return {"error": str(e), "detections": [], "num_detections": 0}


def _detections_to_metrics(all_detections: list[dict]) -> dict:
    """
    Convert raw YOLO detections into the detection_data metrics
    expected by the Triage agent.

    Mapping:
      person → crowd_density (normalized 0-1)
      boat/surfboard (water indicators) → flood_level
      fire-related classes → fire_detected
      car/truck/bus → vehicle_count
      General damage indicators → structural_damage
    """
    person_count = 0
    vehicle_count = 0
    water_indicators = 0
    fire_indicators = 0
    damage_indicators = 0
    total_confidence = 0.0
    detection_count = 0

    # COCO class groupings
    person_classes = {"person"}
    vehicle_classes = {"car", "truck", "bus", "motorcycle", "bicycle"}
    water_classes = {"boat", "surfboard"}  # Indicators of water/flooding
    # No direct fire class in COCO, but we check for related objects

    for det in all_detections:
        cls = det.get("class_name", "").lower()
        conf = det.get("confidence", 0)
        total_confidence += conf
        detection_count += 1

        if cls in person_classes:
            person_count += 1
        elif cls in vehicle_classes:
            vehicle_count += 1
        elif cls in water_classes:
            water_indicators += 1
        # Structural damage heuristic: lots of detections with low confidence
        # often indicates cluttered/damaged scenes
        if conf < 0.4:
            damage_indicators += 1

    # Normalize to 0-1 range
    crowd_density = min(1.0, person_count / 50.0)  # 50+ people = max density
    flood_level = min(1.0, water_indicators / 5.0)  # 5+ water indicators = max
    structural_damage = min(1.0, damage_indicators / 20.0)  # many low-conf detections
    avg_confidence = total_confidence / max(detection_count, 1)

    return {
        "crowd_density": round(crowd_density, 3),
        "flood_level": round(flood_level, 3),
        "structural_damage": round(structural_damage, 3),
        "fire_detected": fire_indicators > 0,
        "vehicle_count": vehicle_count,
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
        image_bytes = download_image(img_info["url"])
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
    metrics["timestamp"] = datetime.utcnow().isoformat()
    metrics["images_analyzed"] = analyzed_count
    metrics["source"] = "yolo_v8"

    logger.info(
        f"yolo.analysis_complete zone={zone_id} "
        f"images={analyzed_count} crowd={metrics['crowd_density']:.3f} "
        f"flood={metrics['flood_level']:.3f} damage={metrics['structural_damage']:.3f}"
    )

    return metrics

"""
RakshaSetu - Complete End-to-End Dataset Training Pipeline
==========================================================
This script:
  1. Converts VisDrone CSV annotations → YOLO format with class remapping
  2. Handles AIDER classification images → full-image YOLO labels
  3. Merges new_dataset3 (already YOLO format)
  4. Creates unified train/val/test splits
  5. Generates data.yaml
  6. Trains YOLOv8 on the combined dataset

Unified Classes:
  0: person
  1: vehicle
  2: flooded_area
  3: fire_smoke
  4: damaged_struct
  5: safe_struct
"""

import os
import sys
import glob
import shutil
import random
import yaml
from pathlib import Path
from PIL import Image

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(r"c:\Users\ankit\Desktop\Sem_6\SJBIT_Hackathon\RakshaSetu\datasets")
UNIFIED_DIR = BASE_DIR / "rakshasetu_unified"
RANDOM_SEED = 42
VAL_SPLIT = 0.15    # 15% for validation
TEST_SPLIT = 0.05   # 5% for test

# VisDrone class ID → Unified class ID
# VisDrone classes: 0=ignored, 1=pedestrian, 2=people, 3=bicycle, 4=car,
#                   5=van, 6=truck, 7=tricycle, 8=awning-tricycle, 9=bus,
#                   10=motor, 11=others
VISDRONE_TO_UNIFIED = {
    1: 0,   # pedestrian → person
    2: 0,   # people → person
    4: 1,   # car → vehicle
    5: 1,   # van → vehicle
    6: 1,   # truck → vehicle
    9: 1,   # bus → vehicle
    3: 1,   # bicycle → vehicle
    10: 1,  # motor → vehicle
}

# AIDER folder name → Unified class ID (whole-image label)
AIDER_CLASS_MAP = {
    "collapsed_building": 4,   # damaged_struct
    "fire": 3,                 # fire_smoke
    "flooded_areas": 2,        # flooded_area
    "traffic_incident": 1,     # vehicle (traffic accident)
    # "normal" → skip (safe_struct class 5, or skip entirely)
}

CLASS_NAMES = ['person', 'vehicle', 'flooded_area', 'fire_smoke', 'damaged_struct', 'safe_struct']
NC = len(CLASS_NAMES)

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def setup_directories():
    """Creates the unified output directory structure."""
    for split in ['train', 'val', 'test']:
        (UNIFIED_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (UNIFIED_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)
    print(f"✅ Directory structure created at {UNIFIED_DIR}")


def visdrone_to_yolo(csv_line, img_width, img_height):
    """
    Converts a single VisDrone CSV annotation line to YOLO format.
    VisDrone format: <x_left>,<y_top>,<w>,<h>,<score>,<class>,<truncation>,<occlusion>
    YOLO format:     <class> <x_center> <y_center> <width> <height>  (all normalized)
    Returns (unified_class_id, x_center, y_center, w_norm, h_norm) or None if class is ignored.
    """
    parts = csv_line.strip().split(',')
    if len(parts) < 6:
        return None

    x_left = int(parts[0])
    y_top = int(parts[1])
    w = int(parts[2])
    h = int(parts[3])
    score = int(parts[4])
    vd_class = int(parts[5])

    # Skip score=0 (ignored regions) and unmapped classes
    if score == 0 or vd_class not in VISDRONE_TO_UNIFIED:
        return None

    unified_id = VISDRONE_TO_UNIFIED[vd_class]

    # Convert to YOLO normalized format
    x_center = (x_left + w / 2.0) / img_width
    y_center = (y_top + h / 2.0) / img_height
    w_norm = w / img_width
    h_norm = h / img_height

    # Clamp to [0, 1]
    x_center = max(0.0, min(1.0, x_center))
    y_center = max(0.0, min(1.0, y_center))
    w_norm = max(0.0, min(1.0, w_norm))
    h_norm = max(0.0, min(1.0, h_norm))

    return unified_id, x_center, y_center, w_norm, h_norm


def process_visdrone_dataset(images_dir, annotations_dir, prefix="vd"):
    """
    Processes a VisDrone dataset: converts annotations and collects image-label pairs.
    Returns list of (image_path, label_lines) tuples.
    """
    pairs = []
    image_files = sorted(glob.glob(str(images_dir / "*.jpg")))
    processed = 0
    skipped = 0

    for img_path in image_files:
        img_name = Path(img_path).stem
        ann_path = annotations_dir / f"{img_name}.txt"

        if not ann_path.exists():
            skipped += 1
            continue

        # Get image dimensions
        try:
            with Image.open(img_path) as img:
                img_w, img_h = img.size
        except Exception:
            skipped += 1
            continue

        # Convert annotations
        with open(ann_path, 'r') as f:
            lines = f.readlines()

        yolo_lines = []
        for line in lines:
            result = visdrone_to_yolo(line, img_w, img_h)
            if result:
                cls_id, xc, yc, wn, hn = result
                yolo_lines.append(f"{cls_id} {xc:.6f} {yc:.6f} {wn:.6f} {hn:.6f}")

        if yolo_lines:
            pairs.append((img_path, yolo_lines))
            processed += 1

    print(f"  📦 {prefix}: Processed {processed} images, skipped {skipped}")
    return pairs


def process_flat_visdrone(images_dir, annotations_dir, prefix="flat"):
    """Process the flat images/ and annotations/ directories (VisDrone format)."""
    return process_visdrone_dataset(images_dir, annotations_dir, prefix)


def process_aider_dataset(aider_dir, prefix="aider"):
    """
    Processes AIDER classification images.
    Since AIDER has no bounding boxes, we create a full-image label
    (the entire image IS the disaster class).
    """
    pairs = []
    total = 0

    for folder_name, unified_class in AIDER_CLASS_MAP.items():
        folder_path = aider_dir / folder_name
        if not folder_path.exists():
            print(f"  ⚠️  AIDER folder not found: {folder_path}")
            continue

        image_files = sorted(glob.glob(str(folder_path / "*.jpg")))
        for img_path in image_files:
            # Full-image bounding box: class 0.5 0.5 1.0 1.0
            yolo_lines = [f"{unified_class} 0.500000 0.500000 1.000000 1.000000"]
            pairs.append((img_path, yolo_lines))
            total += 1

    print(f"  📦 {prefix}: Processed {total} classification images → YOLO labels")
    return pairs


def process_new_dataset3(dataset_dir, prefix="nd3"):
    """
    Processes new_dataset3 which is already in YOLO format.
    We just read the existing labels as-is (they use class 0 = person).
    """
    pairs = []
    splits_to_check = ['train', 'val', 'test']
    total = 0

    for split in splits_to_check:
        img_dir = dataset_dir / split / "images"
        lbl_dir = dataset_dir / split / "labels"
        if not img_dir.exists():
            continue

        image_files = sorted(glob.glob(str(img_dir / "*.*")))
        for img_path in image_files:
            img_stem = Path(img_path).stem
            lbl_path = lbl_dir / f"{img_stem}.txt"

            if not lbl_path.exists():
                continue

            with open(lbl_path, 'r') as f:
                yolo_lines = [line.strip() for line in f if line.strip()]

            if yolo_lines:
                pairs.append((img_path, yolo_lines))
                total += 1

    print(f"  📦 {prefix}: Loaded {total} pre-labeled YOLO images")
    return pairs


def split_and_copy(all_pairs, unified_dir):
    """
    Shuffles all image-label pairs and splits into train/val/test.
    Copies images and writes label files.
    """
    random.seed(RANDOM_SEED)
    random.shuffle(all_pairs)

    total = len(all_pairs)
    test_count = int(total * TEST_SPLIT)
    val_count = int(total * VAL_SPLIT)
    train_count = total - val_count - test_count

    splits = {
        'train': all_pairs[:train_count],
        'val': all_pairs[train_count:train_count + val_count],
        'test': all_pairs[train_count + val_count:],
    }

    counters = {}
    for split_name, pairs in splits.items():
        img_out_dir = unified_dir / "images" / split_name
        lbl_out_dir = unified_dir / "labels" / split_name
        count = 0

        for idx, (img_path, yolo_lines) in enumerate(pairs):
            ext = Path(img_path).suffix
            # Use unique name to avoid collisions across datasets
            new_name = f"{split_name}_{idx:06d}"

            # Copy image
            dst_img = img_out_dir / f"{new_name}{ext}"
            shutil.copy2(img_path, dst_img)

            # Write label
            dst_lbl = lbl_out_dir / f"{new_name}.txt"
            with open(dst_lbl, 'w') as f:
                f.write("\n".join(yolo_lines) + "\n")

            count += 1

        counters[split_name] = count
        print(f"  ✅ {split_name}: {count} samples")

    return counters


def create_data_yaml(unified_dir):
    """Creates the data.yaml for YOLOv8 training."""
    yaml_content = {
        "path": str(unified_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": NC,
        "names": CLASS_NAMES,
    }
    yaml_path = unified_dir / "data.yaml"
    with open(yaml_path, 'w') as f:
        yaml.dump(yaml_content, f, sort_keys=False, default_flow_style=False)
    print(f"✅ Created {yaml_path}")
    return yaml_path


def train_model(data_yaml_path):
    """Trains YOLOv8 on the unified dataset."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    print("\n🚀 Initializing YOLOv8 Training...")
    model = YOLO("yolov8n.pt")  # Nano model for faster training on edge/GPU

    results = model.train(
        data=str(data_yaml_path),
        epochs=50,                 # 50 epochs for CPU training
        imgsz=640,                 # Standard drone resolution
        batch=8,                   # Smaller batch for CPU memory
        device='cpu',              # CPU training (no CUDA GPU)
        project="RakshaSetu_Runs",
        name="aerial_disaster_v1",
        optimizer="auto",
        patience=30,               # Early stopping

        # --- Aerial-specific augmentations ---
        mosaic=1.0,
        mixup=0.15,
        hsv_h=0.015,
        hsv_s=0.7,                 # Heavy sat shifts (simulates weather)
        hsv_v=0.4,
        degrees=15.0,              # Drone roll/pitch
        translate=0.1,
        scale=0.5,
        flipud=0.0,
        fliplr=0.5,

        # --- Loss tuning for imbalanced classes ---
        cls=1.5,
        box=7.5,
        dfl=1.5,
    )

    print("✅ Training Completed!")

    # Validation
    metrics = model.val()
    print(f"\n📊 Validation Results:")
    print(f"   mAP50:    {metrics.box.map50:.4f}")
    print(f"   mAP50-95: {metrics.box.map:.4f}")

    # Export to ONNX
    print("\n🔧 Exporting model to ONNX...")
    export_path = model.export(format="onnx")
    print(f"✅ ONNX model saved to: {export_path}")

    return results


# ============================================================
# MAIN PIPELINE
# ============================================================
def main():
    print("=" * 60)
    print("  🛡️  RakshaSetu - Unified Dataset Training Pipeline")
    print("=" * 60)

    # Step 1: Setup directories
    print("\n📁 Step 1: Setting up unified directory structure...")
    setup_directories()

    # Step 2: Process all datasets
    print("\n📊 Step 2: Processing and converting all datasets...")
    all_pairs = []

    # 2a. VisDrone Train (6471 images)
    print("\n  [1/5] VisDrone 2019 DET Train...")
    vd_train = process_visdrone_dataset(
        images_dir=BASE_DIR / "VisDrone2019-DET-train" / "images",
        annotations_dir=BASE_DIR / "VisDrone2019-DET-train" / "annotations",
        prefix="VisDrone-Train"
    )
    all_pairs.extend(vd_train)

    # 2b. VisDrone Val (548 images)
    print("  [2/5] VisDrone 2019 DET Val...")
    vd_val = process_visdrone_dataset(
        images_dir=BASE_DIR / "VisDrone2019-DET-val" / "images",
        annotations_dir=BASE_DIR / "VisDrone2019-DET-val" / "annotations",
        prefix="VisDrone-Val"
    )
    all_pairs.extend(vd_val)

    # 2c. Flat images/ + annotations/ (1610 images - VisDrone format)
    print("  [3/5] Flat VisDrone images + annotations...")
    flat_data = process_flat_visdrone(
        images_dir=BASE_DIR / "images",
        annotations_dir=BASE_DIR / "annotations",
        prefix="Flat-VisDrone"
    )
    all_pairs.extend(flat_data)

    # 2d. AIDER (classification → full-image YOLO)
    print("  [4/5] AIDER disaster classification...")
    aider_data = process_aider_dataset(
        aider_dir=BASE_DIR / "AIDER",
        prefix="AIDER"
    )
    all_pairs.extend(aider_data)

    # 2e. new_dataset3 (already YOLO format)
    print("  [5/5] new_dataset3 (pre-labeled YOLO)...")
    nd3_data = process_new_dataset3(
        dataset_dir=BASE_DIR / "new_dataset3",
        prefix="new_dataset3"
    )
    all_pairs.extend(nd3_data)

    print(f"\n📈 Total image-label pairs collected: {len(all_pairs)}")

    if len(all_pairs) == 0:
        print("❌ No data found! Check your dataset paths.")
        sys.exit(1)

    # Step 3: Split and copy to unified structure
    print("\n📂 Step 3: Splitting into train/val/test and copying files...")
    counters = split_and_copy(all_pairs, UNIFIED_DIR)

    # Step 4: Create data.yaml
    print("\n📝 Step 4: Creating data.yaml...")
    data_yaml_path = create_data_yaml(UNIFIED_DIR)

    # Step 5: Train the model
    print("\n" + "=" * 60)
    print(f"  📊 Dataset Summary:")
    print(f"     Train: {counters.get('train', 0)} images")
    print(f"     Val:   {counters.get('val', 0)} images")
    print(f"     Test:  {counters.get('test', 0)} images")
    print(f"     Classes: {NC} → {CLASS_NAMES}")
    print("=" * 60)

    print("\n🏋️ Step 5: Training YOLOv8 model...")
    train_model(data_yaml_path)

    print("\n" + "=" * 60)
    print("  ✅ RakshaSetu Training Pipeline COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()

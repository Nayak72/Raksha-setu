import os
import glob
import shutil
from pathlib import Path

# Unified Class Schema
# 0: person
# 1: vehicle
# 2: flooded_area
# 3: fire_smoke
# 4: damaged_struct
# 5: safe_struct

# Mapping from original dataset class names to unified IDs
# This is a hypothetical map assuming original datasets used these IDs
# You will need to adjust the keys based on the exact classes.txt of each dataset
CLASS_MAP = {
    # VisDrone & C2A
    'pedestrian': 0, 'people': 0, 'person': 0,
    'car': 1, 'van': 1, 'truck': 1, 'bus': 1, 'motor': 1,
    # FloodNet
    'water': 2, 'flooded_road': 2,
    'flooded_building': 4,
    'building': 5, 'non_flooded_building': 5,
    # AIDER
    'fire': 3, 'smoke': 3,
    'collapsed_building': 4
}

# Example specific mappings if we are dealing with pure ID conversions 
# assuming we know the original ID mapping for a specific dataset like VisDrone
VISDRONE_TO_UNIFIED = {
    1: 0, # pedestrian -> person
    2: 0, # people -> person
    4: 1, # car -> vehicle
    5: 1, # van -> vehicle
    6: 1, # truck -> vehicle
    9: 1  # bus -> vehicle
}

def setup_directories(base_dir: str):
    """Creates the unified directory structure."""
    splits = ['train', 'val', 'test']
    for split in splits:
        Path(f"{base_dir}/images/{split}").mkdir(parents=True, exist_ok=True)
        Path(f"{base_dir}/labels/{split}").mkdir(parents=True, exist_ok=True)

def process_dataset(source_labels_dir: str, target_labels_dir: str, id_map: dict):
    """Reads YOLO format labels, remaps IDs, and writes to unified directory."""
    print(f"Processing dataset from {source_labels_dir}...")
    label_files = glob.glob(f"{source_labels_dir}/*.txt")
    
    valid_files_count = 0
    for label_path in label_files:
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue
                
            orig_id = int(parts[0])
            if orig_id in id_map:
                new_id = id_map[orig_id]
                new_line = f"{new_id} {' '.join(parts[1:])}\n"
                new_lines.append(new_line)
        
        # Only save if there are valid mapped annotations
        if new_lines:
            target_file = os.path.join(target_labels_dir, os.path.basename(label_path))
            with open(target_file, 'w') as f:
                f.writelines(new_lines)
            valid_files_count += 1
            
    print(f"Processed {len(label_files)} files. Kept {valid_files_count} files with valid classes.")

def copy_images(source_images_dir: str, target_images_dir: str, target_labels_dir: str):
    """Copies only the images that have corresponding valid label files."""
    valid_label_files = [Path(f).stem for f in glob.glob(f"{target_labels_dir}/*.txt")]
    image_files = glob.glob(f"{source_images_dir}/*.*") # Matches .jpg, .png
    
    copied = 0
    for img_path in image_files:
        if Path(img_path).stem in valid_label_files:
            shutil.copy(img_path, target_images_dir)
            copied += 1
    print(f"Copied {copied} corresponding images.")

if __name__ == "__main__":
    print("🚀 RakshaSetu Dataset Merger Tool")
    unified_dir = "../datasets/rakshasetu_unified"
    setup_directories(unified_dir)
    
    # ---------------------------------------------------------
    # Example Usage (You must provide actual paths to datasets):
    # ---------------------------------------------------------
    
    # 1. Process VisDrone (Assuming IDs map using VISDRONE_TO_UNIFIED)
    # process_dataset("../datasets/VisDrone/train/labels", f"{unified_dir}/labels/train", VISDRONE_TO_UNIFIED)
    # copy_images("../datasets/VisDrone/train/images", f"{unified_dir}/images/train", f"{unified_dir}/labels/train")
    
    print("\n✅ Setup complete. To run the merge, populate the paths and uncomment the process calls.")

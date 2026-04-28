from ultralytics import YOLO

def train_rakshasetu_model():
    """
    Trains the RakshaSetu YOLOv8 model for unified aerial disaster detection.
    """
    print("🚀 Initializing YOLOv8 Model Training for RakshaSetu...")
    
    # Load a pretrained model (YOLOv8 medium is recommended for a balance of speed and accuracy)
    model = YOLO("yolov8m.pt")
    
    # Train the model with RakshaSetu-specific hyper-parameters
    results = model.train(
        data="../datasets/data.yaml",   # Path to the unified dataset config
        epochs=150,                     # 150 epochs usually sufficient for converging
        imgsz=640,                      # 640x640 input resolution for drones
        batch=32,                       # Adjust based on GPU VRAM (16 for 12GB, 32 for 24GB)
        device=0,                       # Uses GPU 0
        project="RakshaSetu",
        name="aerial_v1",
        
        # --- Aggressive Augmentation for Aerial Data ---
        mosaic=1.0,                     # Forces mosaic mapping to help with small objects
        mixup=0.2,                      # Reduces overfitting
        hsv_h=0.015,                    # Hue variance
        hsv_s=0.7,                      # Saturation variance (simulates rain/fog)
        hsv_v=0.4,                      # Brightness variance
        degrees=10.0,                   # Simulates drone roll
        perspective=0.0005,             # Perspective distortion
        
        # --- Class Balancing ---
        # Classes: ['person', 'vehicle', 'flooded_area', 'fire_smoke', 'damaged_struct', 'safe_struct']
        # Fire/Smoke is often a minority class, applying focal loss or specific class weights can help.
        # YOLOv8 handles focal loss automatically if configured in loss func, but we ensure high batch sizes
        # to expose minority classes frequently.
    )
    
    print("✅ Training Completed. Exporting to ONNX for production inference...")
    # Export the best model to ONNX for faster CPU/GPU inference in production
    success = model.export(format="onnx")
    print(f"Export Success: {success}")

if __name__ == "__main__":
    train_rakshasetu_model()

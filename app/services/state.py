from typing import Dict, List, Any

class GlobalState:
    def __init__(self):
        self.zones: List[Dict[str, Any]] = []
        self.shelters: List[Dict[str, Any]] = []
        self.allocations: List[Dict[str, Any]] = []
        self.evacuations: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []
        self.routes: Dict[str, Any] = {} # zone_id -> routes
        self.cycle_count = 0

        # ── Broadcast tracking ──────────────────────
        self.broadcasts: List[Dict[str, Any]] = []   # Recent UDP broadcast records
        self.broadcast_count: int = 0                 # Total broadcasts sent
        self.broadcast_acks: List[Dict[str, Any]] = []  # Device acknowledgments
        self.devices_reached: int = 0                 # Unique devices that ACK'd

        # ── YOLO Detection tracking ─────────────────
        self.yolo_results: List[Dict[str, Any]] = []  # Recent YOLO detection results
        self.yolo_scan_count: int = 0                  # Total scans performed
        self.yolo_total_detections: int = 0            # Total objects detected across all scans

state = GlobalState()

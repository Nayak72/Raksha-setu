import asyncio
from typing import Dict, List, Any
import math

class GlobalState:
    def __init__(self):
        self.zones: List[Dict[str, Any]] = []
        self.shelters: List[Dict[str, Any]] = []
        self.allocations: List[Dict[str, Any]] = []
        self.evacuations: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []
        self.routes: Dict[str, Any] = {} # zone_id -> routes
        self.cycle_count = 0

state = GlobalState()

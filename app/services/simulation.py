import asyncio
import logging
from app.services.state import state
from app.services.zones import init_zones, update_zones
from app.services.shelters import init_shelters, update_shelters
from app.services.evacuation import init_evacuations, update_evacuations
from app.services.allocation import init_allocations, update_allocations
from app.services.routing import init_routes, update_routes
from app.services.agent import run_agent_decisions
from app.services.logs import init_logs

logger = logging.getLogger(__name__)

class SimulationEngine:
    def __init__(self):
        self._running = False
        self._task = None

    def start(self):
        if self._running:
            return
            
        logger.info("Initializing Simulation Engine...")
        init_zones()
        init_shelters()
        init_evacuations()
        init_allocations()
        init_routes()
        init_logs()
        
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        while self._running:
            try:
                # 1. Update environments
                update_zones()
                update_shelters()
                update_evacuations()
                update_allocations()
                update_routes()
                
                # 2. Run agents
                run_agent_decisions()
                
                state.cycle_count += 1
                logger.info(f"Simulation cycle {state.cycle_count} completed.")
                
                # Wait 5 seconds
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Simulation error: {e}")
                await asyncio.sleep(5) # Continue on error

engine = SimulationEngine()

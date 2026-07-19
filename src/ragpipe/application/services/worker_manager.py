import time
from typing import Dict, Any

class WorkerManager:
    """Mock Worker Manager for unified single-process architecture."""
    def __init__(self) -> None:
        self.workers: Dict[str, Dict[str, Any]] = {
            "worker-primary": {
                "id": "worker-primary",
                "status": "active",
                "uptime_seconds": 0,
                "start_time": time.time(),
                "current_job_id": None
            }
        }

    def list_workers(self) -> list[Dict[str, Any]]:
        now = time.time()
        result = []
        for w in self.workers.values():
            w["uptime_seconds"] = int(now - w["start_time"])
            result.append(w.copy())
        return result

    def pause_worker(self, worker_id: str) -> bool:
        if worker_id in self.workers:
            self.workers[worker_id]["status"] = "paused"
            return True
        return False

    def resume_worker(self, worker_id: str) -> bool:
        if worker_id in self.workers:
            self.workers[worker_id]["status"] = "active"
            return True
        return False

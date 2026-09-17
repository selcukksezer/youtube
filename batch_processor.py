"""
Batch Video Processor — Queue & CSV/Excel bulk video generation (Items 70, 78, 85)
Supports:
- Parsing topic lists from CSV / plain text
- Sequential queue processing with warm-up rate limits (Item 85)
- Automated retry on failure (Item 72)
"""
import os, csv, time, json, threading
from typing import List, Dict, Any, Optional
import config

class BatchQueueManager:
    def __init__(self):
        self.queue_path = os.path.join(config.BASE_DIR, "batch_queue.json")
        self.queue: List[Dict[str, Any]] = self._load_queue()
        self.is_running = False
        self.current_job: Optional[Dict[str, Any]] = None
        self.completed_jobs: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def _load_queue(self) -> List[Dict[str, Any]]:
        try:
            with open(self.queue_path, "r", encoding="utf-8") as queue_file:
                queue = json.load(queue_file)
            return queue if isinstance(queue, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save_queue(self) -> None:
        temp_path = f"{self.queue_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as queue_file:
            json.dump(self.queue, queue_file, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.queue_path)

    def parse_csv_topics(self, file_path: str) -> List[Dict[str, Any]]:
        """Parses CSV file containing columns: topic, niche (optional), language (optional)."""
        jobs = []
        if not os.path.exists(file_path):
            return jobs
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic = row.get("topic") or row.get("keyword") or row.get("title")
                if topic and topic.strip():
                    jobs.append({
                        "id": f"batch_{int(time.time()*1000)}_{len(jobs)}",
                        "topic": topic.strip(),
                        "niche": row.get("niche", "1_news_flash").strip(),
                        "language": row.get("language", "tr").strip(),
                        "split_screen": row.get("split_screen", "").lower() in ("true", "1", "yes"),
                        "status": "queued",
                        "created_at": time.time()
                    })
        return jobs

    def parse_text_lines(self, raw_text: str, default_niche: str = "1_news_flash", language: str = "tr") -> List[Dict[str, Any]]:
        """Parses multiple topics separated by newlines."""
        jobs = []
        for line in raw_text.splitlines():
            line = line.strip()
            if line:
                jobs.append({
                    "id": f"batch_{int(time.time()*1000)}_{len(jobs)}",
                    "topic": line,
                    "niche": default_niche,
                    "language": language,
                    "split_screen": False,
                    "status": "queued",
                    "created_at": time.time()
                })
        return jobs

    def add_jobs(self, jobs: List[Dict[str, Any]]):
        with self._lock:
            self.queue.extend(jobs)
            self._save_queue()
            print(f"  [Batch] Enqueued {len(jobs)} jobs (Total in queue: {len(self.queue)})")

    def get_queue_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_running": self.is_running,
                "queue_count": len(self.queue),
                "current_job": self.current_job,
                "completed_count": len(self.completed_jobs),
                "queue": list(self.queue)
            }

    def take_next_job(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self.queue:
                self.is_running = False
                self.current_job = None
                return None
            self.current_job = self.queue.pop(0)
            self.current_job["status"] = "processing"
            self.is_running = True
            self._save_queue()
            return dict(self.current_job)

    def finish_current_job(self, status: str) -> None:
        with self._lock:
            if self.current_job:
                self.current_job["status"] = status
                self.completed_jobs.append(self.current_job)
            self.current_job = None
            self.is_running = bool(self.queue)

    def clear_queue(self):
        with self._lock:
            self.queue.clear()
            self._save_queue()

batch_manager = BatchQueueManager()

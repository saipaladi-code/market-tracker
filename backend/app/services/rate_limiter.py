import time
import threading
from typing import Dict, List, Tuple
from fastapi import HTTPException

class AuthRateLimiter:
    """
    In-memory sliding-window rate limiter to protect authentication endpoints
    against brute-force and credential-stuffing attacks.
    """
    def __init__(self):
        self._lock = threading.Lock()
        # Key: str -> List[float (timestamp)]
        self._attempts: Dict[str, List[float]] = {}

    def _cleanup_old(self, key: str, window_seconds: int, now: float) -> List[float]:
        if key not in self._attempts:
            return []
        cutoff = now - window_seconds
        valid = [t for t in self._attempts[key] if t > cutoff]
        if valid:
            self._attempts[key] = valid
        else:
            self._attempts.pop(key, None)
        return valid

    def check_rate_limit(self, key: str, max_attempts: int, window_seconds: int, action_name: str = "request"):
        now = time.time()
        with self._lock:
            valid = self._cleanup_old(key, window_seconds, now)
            if len(valid) >= max_attempts:
                oldest = valid[0]
                retry_after = int(window_seconds - (now - oldest)) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many {action_name} attempts. Please try again in {max(retry_after, 1)} seconds.",
                    headers={"Retry-After": str(max(retry_after, 1))}
                )

    def record_attempt(self, key: str):
        now = time.time()
        with self._lock:
            if key not in self._attempts:
                self._attempts[key] = []
            self._attempts[key].append(now)

    def reset_key(self, key: str):
        with self._lock:
            self._attempts.pop(key, None)

auth_rate_limiter = AuthRateLimiter()

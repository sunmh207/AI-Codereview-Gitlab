"""Lazy local clone/fetch of repositories for agentic review."""
from __future__ import annotations

import errno
import fcntl
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

from biz.utils.log import logger


def _sanitize_key(key: str) -> str:
    """Turn a project key into a safe directory name."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", key)


class LocalRepoSyncer:
    """Lazily clone (first sync) or fetch+checkout (subsequent) a remote repo.

    State lives under `cache_root`. Each project has:
        cache_root/<safe_key>/        — git working tree
        cache_root/<safe_key>.lock    — fcntl file lock
    """

    def __init__(
        self,
        cache_root: Path | str,
        *,
        clone_timeout: int = 300,
        lock_wait_seconds: int = 60,
    ) -> None:
        self.cache_root = Path(cache_root)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.clone_timeout = clone_timeout
        self.lock_wait_seconds = lock_wait_seconds

    def sync_to(self, *, url: str, key: str, ref: str) -> Path:
        """Ensure repo for `key` is locally available and `ref` is checked out.

        Returns the local repo path (working tree).
        Raises RuntimeError on failure.
        """
        safe = _sanitize_key(key)
        target = self.cache_root / safe
        lock_path = self.cache_root / f"{safe}.lock"

        with self._lock(lock_path):
            if not (target / ".git").exists():
                self._clone(url, target)
            self._fetch_and_checkout(target, ref)
        return target

    @contextmanager
    def _lock(self, lock_path: Path):
        lock_path.touch(exist_ok=True)
        f = open(lock_path, "w")
        deadline = time.monotonic() + self.lock_wait_seconds
        while True:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise
                if time.monotonic() >= deadline:
                    logger.warning("could not acquire lock %s within %ds, proceeding without lock",
                                   lock_path, self.lock_wait_seconds)
                    break
                time.sleep(0.5)
        try:
            yield
        finally:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            f.close()

    def _clone(self, url: str, target: Path) -> None:
        logger.info("cloning %s -> %s", url, target)
        try:
            subprocess.run(
                ["git", "clone", url, str(target)],
                check=True,
                capture_output=True,
                text=True,
                timeout=self.clone_timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"git clone timed out after {self.clone_timeout}s") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"git clone failed: {e.stderr.strip()}") from e

    def _fetch_and_checkout(self, target: Path, ref: str) -> None:
        try:
            subprocess.run(
                ["git", "fetch", "--all", "--prune"],
                cwd=target, check=True, capture_output=True, text=True, timeout=self.clone_timeout,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"git fetch failed: {e.stderr.strip()}") from e
        # Determine if ref looks like a SHA (hex, length >= 7) or a branch name.
        is_sha = bool(re.fullmatch(r"[0-9a-fA-F]{7,40}", ref))
        if is_sha:
            cmd = ["git", "reset", "--hard", ref]
        else:
            # Use origin/<ref> as the source of truth so the working tree
            # tracks new commits pushed to the remote since the last sync.
            cmd = ["git", "reset", "--hard", f"origin/{ref}"]
        try:
            subprocess.run(
                cmd, cwd=target, check=True, capture_output=True, text=True, timeout=self.clone_timeout,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"git checkout failed: {e.stderr.strip()}") from e

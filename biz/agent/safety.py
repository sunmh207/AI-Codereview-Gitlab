"""Path sandboxing and sensitive path detection for agent tools."""
import re
from pathlib import Path

# Patterns matched anywhere in the path (case-sensitive on POSIX).
# Each entry is a regex compiled at import time.
SENSITIVE_PATH_PATTERNS: tuple[re.Pattern, ...] = tuple(
    re.compile(p) for p in (
        r"(^|/)(\.env|\.env\.[^/]+)$",
        r"(^|/)id_rsa(\.pub)?$",
        r"(^|/)\.git/",
        r"(^|/)\.ssh/",
        r"\.pem$",
        r"\.key$",
    )
)


def is_path_safe(candidate: Path | str, repo_root: Path | str) -> bool:
    """Return True iff `candidate` resolves to a path inside `repo_root`.

    Both arguments are resolved (symlinks followed, .. normalized) before comparison.
    """
    try:
        candidate_resolved = Path(candidate).resolve(strict=False)
        root_resolved = Path(repo_root).resolve(strict=False)
        # Path.is_relative_to is available in Python 3.9+
        return candidate_resolved.is_relative_to(root_resolved)
    except (OSError, ValueError):
        return False


def is_sensitive_path(path: Path | str) -> bool:
    """Return True iff `path` matches any SENSITIVE_PATH_PATTERNS.

    Uses forward-slash POSIX form for matching, regardless of host OS.
    """
    p = Path(path)
    # Use as_posix so regex matches behave the same on Windows and POSIX.
    posix = p.as_posix()
    return any(pat.search(posix) for pat in SENSITIVE_PATH_PATTERNS)

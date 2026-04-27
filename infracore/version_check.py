from __future__ import annotations


def normalize_version(raw: str) -> str:
    """Pad a version string to X.Y.Z. Rejects non-numeric and suffix-bearing strings."""
    raw = raw.strip()
    parts = raw.split(".")
    if len(parts) > 3:
        raise ValueError(f"Too many version components: {raw!r}")
    for part in parts:
        if not part.isdigit() or (part != str(int(part))):
            raise ValueError(f"Non-numeric version component in {raw!r}")
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts)


def caret_match(required: str, candidate: str) -> bool:
    """Return True if candidate satisfies the caret range ^required."""
    if not required.startswith("^"):
        raise ValueError(f"required must start with '^', got {required!r}")
    req = normalize_version(required[1:])
    cand = normalize_version(candidate)
    req_parts = [int(x) for x in req.split(".")]
    cand_parts = [int(x) for x in cand.split(".")]
    if cand_parts < req_parts:
        return False
    if cand_parts[0] >= req_parts[0] + 1:
        return False
    return True

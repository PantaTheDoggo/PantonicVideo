from __future__ import annotations

from pathlib import Path

from contracts.subtitle import SrtOptions


def _ms_to_srt_ts(ms: int) -> str:
    h = ms // 3_600_000
    m = (ms % 3_600_000) // 60_000
    s = (ms % 60_000) // 1_000
    millis = ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > max_chars:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines or [""]


class SubtitleServiceImpl:
    def __init__(self, filesystem_service: object) -> None:
        self._fs = filesystem_service

    def text_to_srt(self, text: str, output: Path, opts: SrtOptions) -> None:
        lines = _wrap_text(text, opts.max_line_chars)
        blocks: list[tuple[int, int, str]] = []
        t = 0
        for line in lines:
            duration = max(
                int(len(line) / opts.cps * 1000),
                opts.min_duration_ms,
            )
            blocks.append((t, t + duration, line))
            t += duration + opts.gap_ms

        parts: list[str] = []
        for i, (start, end, line) in enumerate(blocks, 1):
            parts.append(
                f"{i}\n{_ms_to_srt_ts(start)} --> {_ms_to_srt_ts(end)}\n{line}\n"
            )

        content = "\n".join(parts)
        self._fs.write(output, content.encode("utf-8"))

"""Pattern definitions: small Python modules with a ``find(video)`` function.

A pattern is plain Python code stored in ``patterns/<slug>.py``. It must define

    NAME = "Human readable name"          # optional, defaults to the slug
    def find(video) -> list[Hit]: ...

``video`` is an :class:`explorer.data.Video`. ``Hit`` (and ``Video``/``Shot``)
are injected into the namespace, so the code does not need to import them.
"""

from __future__ import annotations

import re
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from explorer.data import SHOT_SCALES, Shot, Video

PATTERNS_DIR = Path(__file__).resolve().parent.parent / "patterns"


@dataclass
class Hit:
    """One occurrence of a pattern: a contiguous or non-contiguous shot sequence.

    shots   -- shot indices (into ``video.shots``) that make up the hit
    persons -- person (cluster) ids involved, used for grouping and display
    label   -- short text shown on the timeline, e.g. "A-B-A-B"
    group   -- hits with the same group share a colour (default: the persons)
    """

    shots: list[int]
    persons: list[str] = field(default_factory=list)
    label: str | None = None
    group: str | None = None


@dataclass
class Pattern:
    slug: str
    name: str
    code: str

    @property
    def path(self) -> Path:
        return PATTERNS_DIR / f"{self.slug}.py"


class PatternError(Exception):
    pass


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "pattern"


def _namespace() -> dict:
    return {"Hit": Hit, "Video": Video, "Shot": Shot, "SHOT_SCALES": SHOT_SCALES,
            "__name__": "pattern"}


def compile_pattern(code: str) -> dict:
    ns = _namespace()
    try:
        exec(compile(code, "<pattern>", "exec"), ns)
    except Exception as e:  # noqa: BLE001 - surface any error to the user
        raise PatternError(_format(e, code)) from e
    if not callable(ns.get("find")):
        raise PatternError("The pattern code must define a function `find(video)`.")
    return ns


def run_pattern(code: str, video: Video) -> list[Hit]:
    ns = compile_pattern(code)
    try:
        raw = ns["find"](video) or []
    except Exception as e:  # noqa: BLE001
        raise PatternError(_format(e, code)) from e
    return [_normalize(h, video) for h in raw]


def _normalize(h, video: Video) -> Hit:
    if isinstance(h, dict):
        h = Hit(**h)
    elif not isinstance(h, Hit):
        h = Hit(shots=list(h))
    h.shots = [s.index if isinstance(s, Shot) else int(s) for s in h.shots]
    if not h.persons:
        seen = []
        for i in h.shots:
            p = video.shots[i].main_person
            if p is not None and p not in seen:
                seen.append(p)
        h.persons = seen
    if h.label is None:
        h.label = "-".join(video.label(video.shots[i].main_person) for i in h.shots)
    if h.group is None:
        h.group = "↔".join(sorted(video.label(p) for p in h.persons)) or "hit"
    return h


def _format(e: Exception, code: str) -> str:
    src = code.splitlines()
    tb = traceback.extract_tb(e.__traceback__)
    lines = [f"line {f.lineno}: {src[f.lineno - 1].strip()}"
             for f in tb if f.filename == "<pattern>" and f.lineno and f.lineno <= len(src)]
    if isinstance(e, SyntaxError) and e.lineno:
        lines.append(f"line {e.lineno}: {(e.text or '').strip()}")
    where = f"\n{lines[-1]}" if lines else ""
    return f"{type(e).__name__}: {e}{where}"


def load_patterns() -> list[Pattern]:
    patterns = []
    for path in sorted(PATTERNS_DIR.glob("*.py")):
        code = path.read_text()
        m = re.search(r'^NAME\s*=\s*["\'](.+?)["\']', code, re.M)
        patterns.append(Pattern(path.stem, m.group(1) if m else path.stem, code))
    return patterns


def save_pattern(slug: str, code: str) -> Path:
    PATTERNS_DIR.mkdir(exist_ok=True)
    path = PATTERNS_DIR / f"{slugify(slug)}.py"
    path.write_text(code)
    return path

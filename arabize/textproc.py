"""OCR text clean-up, grouping into blocks, and "is this new text?" tracking."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

_WS = re.compile(r"\s+")
_QUOTES = str.maketrans({"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "`": "'", "´": "'"})
_JUNK = re.compile(r"^[\W_\d]{0,3}$", re.UNICODE)


def clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").translate(_QUOTES)
    text = text.replace("|", "I") if re.search(r"[A-Za-z]\|[A-Za-z]", text or "") else text
    return _WS.sub(" ", text).strip()


def normalize_key(text: str) -> str:
    """Comparison key: case-folded, punctuation-light, whitespace-collapsed."""
    t = clean(text).casefold()
    t = re.sub(r"[\"'.,!?…:;()\[\]{}<>«»\-–—_*~]+", " ", t)
    return _WS.sub(" ", t).strip()


def is_noise(text: str) -> bool:
    t = clean(text)
    if not t or _JUNK.match(t):
        return True
    letters = sum(ch.isalpha() for ch in t)
    return letters < 2 or letters / max(1, len(t)) < 0.35


def similarity(a: str, b: str) -> float:
    a, b = normalize_key(a), normalize_key(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


@dataclass
class Line:
    text: str
    conf: float
    x: float
    y: float
    w: float
    h: float


@dataclass
class Block:
    lines: list[Line] = field(default_factory=list)
    label: str = ""          # speaker name or header ("Captain Mara", "QUEST") shown before the text

    @property
    def text(self) -> str:
        return " ".join(l.text for l in self.lines)

    @property
    def full_text(self) -> str:
        return f"{self.label}: {self.text}" if self.label else self.text

    @property
    def box(self) -> tuple[float, float, float, float]:
        x0 = min(l.x for l in self.lines); y0 = min(l.y for l in self.lines)
        x1 = max(l.x + l.w for l in self.lines); y1 = max(l.y + l.h for l in self.lines)
        return x0, y0, x1 - x0, y1 - y0


def group_lines(lines: list[Line]) -> list[Block]:
    """Merge OCR lines that belong to the same paragraph (dialogue box, quest text...)."""
    lines = sorted((l for l in lines if not is_noise(l.text)), key=lambda l: (round(l.y / 4), l.x))
    blocks: list[Block] = []
    for ln in lines:
        target = None
        for b in reversed(blocks[-4:]):
            last = b.lines[-1]
            gap = ln.y - (last.y + last.h)
            h = max(last.h, ln.h)
            overlap = min(last.x + last.w, ln.x + ln.w) - max(last.x, ln.x)
            left_aligned = abs(ln.x - last.x) < h * 1.5
            centered = abs((ln.x + ln.w / 2) - (last.x + last.w / 2)) < h * 2
            # a finished sentence followed by a capitalised line = separate item (menu entries, choices)
            new_item = last.text.rstrip()[-1:] in ".!?。؟…" and (ln.text[:1].isupper() or ln.text[:1].isdigit())
            if -h * 0.5 < gap < h * 0.9 and abs(ln.h - last.h) < h * 0.45 and (overlap > 0 or left_aligned or centered) and not new_item:
                target = b
                break
        if target:
            target.lines.append(ln)
        else:
            blocks.append(Block([ln]))
    for b in blocks:
        _split_label(b)
    return blocks


def _split_label(b: Block) -> None:
    """A short first line above a much wider text is a speaker name or a header."""
    if len(b.lines) < 2:
        return
    first, rest = b.lines[0], b.lines[1:]
    t = first.text.strip()
    widest = max(l.w for l in rest)
    if (len(t.split()) <= 3 and len(t) <= 26 and t[-1:] not in ".!?,;" and first.w < widest * 0.6):
        b.label = t.rstrip(":：")
        b.lines = rest


class TextTracker:
    """Remembers what is on screen so the same text is not translated again and again."""

    def __init__(self, same_ratio: float = 0.9):
        self.same_ratio = same_ratio
        self.current: list[str] = []

    def is_new(self, blocks: list[str]) -> bool:
        joined = "\n".join(blocks)
        prev = "\n".join(self.current)
        if not blocks:
            return False
        if similarity(joined, prev) >= self.same_ratio:
            return False
        self.current = list(blocks)
        return True

    def reset(self) -> None:
        self.current = []

    def new_blocks(self, blocks: list[str], seen: list[str]) -> list[str]:
        """Blocks that are not near-duplicates of already shown ones (for partial updates)."""
        return [b for b in blocks if all(similarity(b, s) < self.same_ratio for s in seen)]

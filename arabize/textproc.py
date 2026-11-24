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
    head: "Line | None" = None   # the line the label was read from (still part of the block's area)

    @property
    def text(self) -> str:
        out = ""
        for l in self.lines:
            t = l.text.strip()
            if out.endswith("-") and t[:1].islower() and out[-2:-1].isalpha():
                out = out[:-1] + t            # a word broken over two lines: "adven-" + "ture"
            else:
                out = f"{out} {t}" if out else t
        return out

    @property
    def full_text(self) -> str:
        return f"{self.label}: {self.text}" if self.label else self.text

    @property
    def box(self) -> tuple[float, float, float, float]:
        ls = self.lines + ([self.head] if self.head else [])
        x0 = min(l.x for l in ls); y0 = min(l.y for l in ls)
        x1 = max(l.x + l.w for l in ls); y1 = max(l.y + l.h for l in ls)
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
        b.head = first
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


# ------------------------------------------------------------------ what kind of text is this?
_QUEST = re.compile(r"^(current\s+)?(quest|quests|objective|objectives|mission|missions|task|tasks|goal|goals|journal|"
                    r"main\s+quest|side\s+quest|new\s+quest|quest\s+updated|objective\s+updated|المهمة|المهام|الهدف)\b", re.I)
_CHOICE_MARK = re.compile(r"^\s*(\d{1,2}[.)\]:-]|[-•●◆▶►>*]|\[[A-Za-z0-9]\])\s*")


def _short(text: str) -> bool:
    return len(text) <= 64 and len(text.split()) <= 10


def classify(items: list[dict]) -> list[str]:
    """Sort each piece of screen text into a layer: dialogue, quest, choices or other.

    items are dicts with "label", "src" and optional "box" (x, y, w, h). The rules are geometric and simple on
    purpose, so they behave the same in every game and never need a network call:
      * a header like QUEST / Objective / Mission           -> quest
      * a speaker name above the text                        -> dialogue
      * 2+ short lines stacked in a column, or "1." / "-"    -> choices
      * the longest sentence-like text                       -> dialogue
      * anything else (prompts, hints, menu titles)          -> other
    """
    kinds = ["other"] * len(items)
    for i, it in enumerate(items):
        label, src = (it.get("label") or "").strip(), (it.get("src") or "").strip()
        if label and _QUEST.match(label) or (not label and _QUEST.match(src) and len(src.split()) <= 3):
            kinds[i] = "quest"
        elif label:
            kinds[i] = "dialogue"
        elif _CHOICE_MARK.match(src) and _short(_CHOICE_MARK.sub("", src)):
            kinds[i] = "choices"

    # a column of short, unlabelled lines with the same left/right edge = a list of choices
    idx = [i for i, it in enumerate(items) if kinds[i] == "other" and it.get("box") and _short(it.get("src", ""))
           and not it.get("label")]
    for i in idx:
        x, y, w, h = items[i]["box"]
        mates = 0
        for j in idx:
            if j == i:
                continue
            x2, y2, w2, h2 = items[j]["box"]
            hh = max(h, h2)
            same_edge = abs(x - x2) < hh * 1.6 or abs((x + w) - (x2 + w2)) < hh * 1.6
            close = abs(y - y2) < hh * 4.5
            if same_edge and close:
                mates += 1
        if mates >= 1:
            kinds[i] = "choices"

    # the quest header can be its own line ("QUEST") with the goal on the next block
    for i, it in enumerate(items):
        if kinds[i] == "quest" and not it.get("label") and i + 1 < len(items) and kinds[i + 1] == "other":
            kinds[i + 1] = "quest"

    # if nothing has a speaker, the longest sentence on screen is the dialogue / narration
    if "dialogue" not in kinds:
        best, best_len = -1, 0
        for i, it in enumerate(items):
            n = len(it.get("src", ""))
            if kinds[i] == "other" and (n > best_len) and (len(it.get("src", "").split()) >= 4):
                best, best_len = i, n
        if best >= 0:
            kinds[best] = "dialogue"
    return kinds

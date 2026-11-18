"""Candidate spans: runs of 1..N consecutive words on the same visual line."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from extractor.parsing.layout import TextLine
from extractor.parsing.words import Word, union_box

MAX_WINDOW_WORDS = 8


@dataclass(frozen=True)
class Window:
    line_index: int  # index into ParsedDocument.lines (reading order)
    words: tuple[Word, ...]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def page(self) -> int:
        return self.words[0].page

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return union_box(list(self.words))

    @property
    def ocr_conf(self) -> float:
        return mean(w.conf for w in self.words)


def build_windows(lines: list[TextLine], max_words: int = MAX_WINDOW_WORDS) -> list[Window]:
    windows = []
    for line_index, line in enumerate(lines):
        words = line.words
        for start in range(len(words)):
            for size in range(1, min(max_words, len(words) - start) + 1):
                windows.append(Window(line_index, tuple(words[start : start + size])))
    return windows

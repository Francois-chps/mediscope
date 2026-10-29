"""Pure text splitting: pack sentences into bounded, overlapping windows."""

import re

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split text into windows of at most max_chars, overlapping by up to overlap_chars.

    Sentences are kept whole when possible; longer ones are cut on words,
    and words longer than the window are sliced.
    """
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return [normalized] if normalized else []

    units = [
        piece
        for sentence in _SENTENCE_END.split(normalized)
        for piece in _hard_split(sentence, max_chars)
    ]
    chunks: list[str] = []
    window: list[str] = []
    for unit in units:
        if window and _length([*window, unit]) > max_chars:
            chunks.append(" ".join(window))
            window = _tail(window, overlap_chars)
            while window and _length([*window, unit]) > max_chars:
                window.pop(0)
        window.append(unit)
    chunks.append(" ".join(window))
    return chunks


def _length(units: list[str]) -> int:
    return sum(map(len, units)) + max(len(units) - 1, 0)


def _tail(units: list[str], budget: int) -> list[str]:
    """Last units fitting in budget: the overlap carried into the next window."""
    tail: list[str] = []
    for unit in reversed(units):
        if _length([unit, *tail]) > budget:
            break
        tail.insert(0, unit)
    return tail


def _hard_split(sentence: str, max_chars: int) -> list[str]:
    """Cut an oversized sentence on words, slicing words longer than the window."""
    if len(sentence) <= max_chars:
        return [sentence]
    pieces: list[str] = []
    current = ""
    for word in sentence.split(" "):
        remaining = word
        while len(remaining) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(remaining[:max_chars])
            remaining = remaining[max_chars:]
        candidate = f"{current} {remaining}" if current else remaining
        if len(candidate) > max_chars:
            pieces.append(current)
            current = remaining
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces

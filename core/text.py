"""Text normalisation and best-match selection (same rules as the browser extension)."""
from __future__ import annotations

import re
from typing import Iterable, Sequence

_APOSTROPHES = re.compile(r"[’'`]")
_DASHES_SLASHES = re.compile(r"[-–—/_]")
_SPACES = re.compile(r"\s+")


def normalize(text: str | None) -> str:
    """Lowercase; ignore apostrophes, dashes, slashes and repeated whitespace."""
    t = (text or "").lower()
    t = _APOSTROPHES.sub("", t)
    t = _DASHES_SLASHES.sub(" ", t)
    return _SPACES.sub(" ", t).strip()


def digits(text: str | None) -> str:
    return re.sub(r"\D", "", text or "")


def split_list(value: str | Sequence[str] | None, sep: str = ";") -> list[str]:
    """'A; B ;C' → ['A', 'B', 'C']. Lists pass through. Empty → []."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(sep) if part.strip()]


def match_score(candidate: str, label: str) -> int:
    """3 = exact, 2 = label starts with candidate, 1 = label contains candidate, 0 = no match."""
    c, l = normalize(candidate), normalize(label)
    if not c or not l:
        return 0
    if l == c:
        return 3
    if l.startswith(c):
        return 2
    if c in l:
        return 1
    return 0


def best_match(candidates: Iterable[str], labels: Sequence[str]) -> tuple[int, str] | None:
    """Try each candidate in order; return (index, label) of the best label for the first candidate
    that matches anything. Exact beats starts-with beats contains."""
    for candidate in candidates:
        scored = [(match_score(candidate, label), i) for i, label in enumerate(labels)]
        scored = [s for s in scored if s[0] > 0]
        if scored:
            score, idx = max(scored, key=lambda s: (s[0], -s[1]))
            return idx, labels[idx]
    return None


def same(a: str | None, b: str | None) -> bool:
    return normalize(a) == normalize(b)


_STOPWORDS = {"and", "of", "the", "in", "for", "to", "a", "an", "with", "on", "or", "studies", "general"}


# Words too generic to count as "similar" on their own: "Data Science" shouldn't match
# "Computer Science" just because both say "science".
_GENERIC = {"science", "sciences", "engineering", "technology", "technologies", "management", "arts",
            "administration", "systems", "program", "programming", "language", "degree", "certificate"}


def key_words(text: str | None) -> list[str]:
    """Distinctive whole words, longest first: 'Data Analytics' → ['analytics', 'data'],
    'Data Science' → ['data']. Generic words are kept only if there is nothing else."""
    words = [w for w in re.findall(r"[a-z0-9+#]+", normalize(text)) if w not in _STOPWORDS and len(w) >= 2]
    distinctive = [w for w in words if w not in _GENERIC] or words
    return sorted(dict.fromkeys(distinctive), key=len, reverse=True)


def word_overlap(candidate: str, label: str) -> float:
    """Share of the candidate's key words that appear as whole words in the label (0..1)."""
    want = key_words(candidate)
    have = set(re.findall(r"[a-z0-9+#]+", normalize(label)))
    return sum(w in have for w in want) / len(want) if want else 0.0


def closest_by_words(candidate: str, labels: Sequence[str]) -> tuple[int, str] | None:
    """Option sharing the most key words with the candidate; ties go to the shorter label."""
    scored = [(word_overlap(candidate, l), -len(l), i) for i, l in enumerate(labels)]
    scored = [s for s in scored if s[0] > 0]
    if not scored:
        return None
    _, _, i = max(scored)
    return i, labels[i]

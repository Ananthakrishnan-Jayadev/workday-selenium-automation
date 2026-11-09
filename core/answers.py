"""Question → answer rules from the Questions sheet.

Keywords cell syntax:
    "authorized to work; eligible to work"          any of these phrases
    "relative; family member + td"                   (relative OR family member) AND td
Phrases match whole words in the normalised question text (case, apostrophes, dashes ignored), so
"td" doesn't match "outdoor". Rules are checked top to bottom; a rule for this company beats a
rule with a blank Company. Page limits a rule to "Application", "Disclosure" or "SelfIdentify"
(blank = any page).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.text import normalize, split_list


@dataclass
class QuestionRule:
    keywords: str
    answer: str
    company: str = ""
    page: str = ""
    row: int | None = None
    groups: list[list[str]] = field(default_factory=list)

    def __post_init__(self):
        self.groups = [[normalize(k) for k in split_list(part)] for part in self.keywords.split("+")]
        self.groups = [g for g in self.groups if g]

    def matches(self, question: str) -> bool:
        q = normalize(question)
        return bool(self.groups) and all(any(_has_phrase(q, k) for k in group) for group in self.groups)

    @property
    def answers(self) -> list[str]:
        return split_list(self.answer)


def _has_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def find_rule(rules: list[QuestionRule], question: str, company: str = "", page: str = "") -> QuestionRule | None:
    """Best rule for a question: company-specific first, then general; first match in sheet order."""
    company_n, page_n = normalize(company), normalize(page)
    candidates = [r for r in rules if r.matches(question)
                  and (not r.page or normalize(r.page) == page_n)
                  and (not r.company or normalize(r.company) == company_n)]
    candidates.sort(key=lambda r: 0 if r.company else 1)  # stable: keeps sheet order within each group
    return candidates[0] if candidates else None

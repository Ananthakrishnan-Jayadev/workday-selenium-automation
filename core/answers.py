"""Question → answer rules from the Questions sheet.

Keywords cell syntax:
    "authorized to work; eligible to work"          any of these phrases
    "relative; family member + td"                   (relative OR family member) AND td
    "worked for {company}"                           {company} = the job's company (BMO, CIBC, ...)
Phrases match whole words in the normalised question text (case, apostrophes, dashes ignored), so
"td" doesn't match "outdoor".

Answers: the Answer column, then Fallback 1, Fallback 2, ... (tried in order; the first option the
company's form has wins). A ';' inside a cell also separates fallbacks.

Which rule wins (find_rule):
  1. Rules are matched against the question's FIRST CLAUSE (text before the first '?', '(', '.' or
     ':'). If several match, a rule for this company beats a general one, then the phrase that ends
     closest to the end of that clause wins ("What is your gender identity?" → the 'gender identity'
     row, not 'what is your gender'), then the longer phrase, then sheet order.
  2. Only if nothing matches the first clause is the whole question text used (sheet order).
Page limits a rule to "Application", "Disclosure" or "SelfIdentify" (blank = any page).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.text import normalize, split_list

_CLAUSE_END = re.compile(r"[?(.:]")


@dataclass
class QuestionRule:
    keywords: str
    answer: str                       # all answers, '; '-joined: Answer, Fallback 1, Fallback 2, ...
    company: str = ""
    page: str = ""
    row: int | None = None
    groups: list[list[str]] = field(default_factory=list)

    def __post_init__(self):
        self.groups = [[normalize(k) for k in split_list(part)] for part in self.keywords.split("+")]
        self.groups = [g for g in self.groups if g]

    def match(self, text: str, company: str = "") -> tuple[int, int] | None:
        """(end position, phrase length) of this rule's match in `text`, or None."""
        q = normalize(text)
        company_n = normalize(company)
        ends, lengths = [], []
        for group in self.groups:
            best = None
            for k in group:
                if "{company}" in k:
                    if not company_n:
                        continue
                    k = k.replace("{company}", company_n)
                m = re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", q)
                if m and (best is None or m.end() > best[0]):
                    best = (m.end(), len(k))
            if best is None:
                return None
            ends.append(best[0])
            lengths.append(best[1])
        return (max(ends), sum(lengths)) if ends else None

    def matches(self, question: str, company: str = "") -> bool:
        return self.match(question, company) is not None

    @property
    def answers(self) -> list[str]:
        return split_list(self.answer)


def first_clause(question: str) -> str:
    return _CLAUSE_END.split(question, 1)[0]


def find_rule(rules: list[QuestionRule], question: str, company: str = "", page: str = "") -> QuestionRule | None:
    """Best rule for a question (see the module docstring for the order)."""
    company_n, page_n = normalize(company), normalize(page)
    eligible = [(i, r) for i, r in enumerate(rules)
                if (not r.page or normalize(r.page) == page_n)
                and (not r.company or normalize(r.company) == company_n)]

    head = first_clause(question)
    scored = [(i, r, m) for i, r in eligible if (m := r.match(head, company))]
    if scored:
        scored.sort(key=lambda x: (0 if x[1].company else 1, -x[2][0], -x[2][1], x[0]))
        return scored[0][1]

    full = [(i, r) for i, r in eligible if r.matches(question, company)]
    full.sort(key=lambda x: (0 if x[1].company else 1, x[0]))
    return full[0][1] if full else None

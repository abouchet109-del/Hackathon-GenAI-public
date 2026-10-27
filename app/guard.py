"""Input guard: incoming text is data, never instructions.

A light, deterministic screen in the spirit of Meterless Scout Intent's injection guard
(not the Scout engine itself). It flags prompt-injection patterns; flagged items can
never lead to an action that moves money or sends data.
"""
from __future__ import annotations

import re

PATTERNS = {
    "instruction_override": re.compile(r"ignore (all |your |the )?(previous|prior) instructions", re.I),
    "addresses_the_ai": re.compile(r"\b(note|message|instruction)s? to the (ai|assistant|agent)\b|\bas an ai\b", re.I),
    "role_markers": re.compile(r"</?system>|\[/?inst\]|^\s*system\s*:", re.I | re.M),
    "exfiltration": re.compile(r"\bsend (the )?(owner'?s )?(card|password|credentials|bank)", re.I),
}


def screen(text: str) -> list[str]:
    return [name for name, pattern in PATTERNS.items() if pattern.search(text or "")]

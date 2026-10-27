"""The agents' prompts, versioned in the repo and reviewed like code.

Each prompt is a Markdown file whose first line is "version: N"; the version
goes into the trace so a run says which prompt produced each output.
"""
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent


def load(name):
    """(version, text) of atlas/prompts/<name>.md."""
    first, _, text = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8").partition("\n")
    key, _, version = first.partition(":")
    if key.strip() != "version" or not version.strip():
        raise ValueError(f"atlas/prompts/{name}.md must start with 'version: N'")
    return version.strip(), text.strip()

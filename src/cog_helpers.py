# pragma: no cover
# No coverage for these cog-based README-only functions.

# std
from pathlib import Path
from typing import Dict

# lib
import cog  # type: ignore


def fenced_block(text: str, lang: str = "") -> None:
    """Generate a fenced code block."""
    cog.outl(f"\n```{lang or 'text'}\n{text}```\n")


def insert_file(location: str, lang: str = "") -> None:
    """Insert the contents of a file wrapping it in a fenced code block."""
    path = Path(location)
    fenced_block(path.read_text(), lang or path.suffix[1:])


def replace_many(text: str, needles: Dict[str, str]) -> str:
    """Return a cleaned up string after making substitutions."""
    for needle, replacement in needles.items():
        text = text.replace(needle, replacement)
    return text


def snip_file(path: str, beg: str, end: str, skip_beg: bool = False) -> str:
    """Return part of a file."""
    text = Path(path).read_text()
    pos_beg = text.find(beg)
    if skip_beg:
        pos_beg += len(beg)
    pos_end = text.find(end, pos_beg)
    return text[pos_beg:pos_end]

"""Find directories, files, file sections."""

# std
from fnmatch import fnmatch
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union
import logging

# pkg
from .symbols import KEY_DELIMITER
from .symbols import GLOB_ALL
from .symbols import GLOB_EXCLUDE
from .symbols import starts

log = logging.getLogger(__name__)

GlobMatches = Dict[Path, bool]
"""Mapping a path to whether it should be included."""


def walk_parents(start: Path, names: Iterable[str]) -> Iterator[Path]:
    """Yield name matches as you walk up parents."""
    for path in (start / "x").resolve().parents:
        for name in names:
            check = path / name
            log.debug(f"check {check}")
            if not check.exists():
                continue
            yield check


def get_key(
    src: Dict[str, Any], name: Union[str, List[str]], default: Optional[Any] = None
) -> Any:
    """Return value of `name` within `src` or `default` if it's missing.

    >>> get_key({"a": {"b": {"c": 1}}}, "a.b.c") == 1
    True
    >>> get_key({"a": {"b": {"c": 1}}}, ["a", "b", "c"]) == 1
    True
    """
    path: List[str] = []
    if isinstance(name, str):
        path = name.split(KEY_DELIMITER)
    elif isinstance(name, list):
        path = name
    else:  # pragma: no cover
        # No coverage for using a bad type.
        raise TypeError("Unknown type of key:", type(name))

    result: Any = default
    try:
        for key in path:
            result = src[key]  # take step
            src = result  # preserve context
    except (KeyError, IndexError, TypeError):
        # key doesn't exist, index is unreachable, or item is not indexable
        result = default
    return result


def glob_names(names: Iterable[str], patterns: List[str]) -> List[str]:
    """Return the names of `tasks` that match `patterns`.

    Prefixing a pattern with `!` will remove that matched pattern
    from the result.

    >>> names = ['cab', 'car', 'cat', 'crab']
    >>> glob_names(names, ['c?r', 'c*b'])
    ['cab', 'car', 'crab']

    >>> glob_names(names, ['*', '!crab'])
    ['cab', 'car', 'cat']
    """
    result: Dict[str, bool] = {name: False for name in names}
    for pattern in patterns:
        exclude, pattern = starts(pattern, GLOB_EXCLUDE)
        for name in result:
            if fnmatch(name, pattern):
                result[name] = not exclude
    return [name for name, include in result.items() if include]


def glob_apply(
    path: Path, patterns: List[str], matches: Optional[GlobMatches] = None
) -> GlobMatches:
    """Apply glob `patterns` to `path`."""
    result = {} if not matches else matches.copy()
    for pattern in patterns:
        exclude, pattern = starts(pattern, GLOB_EXCLUDE)
        for match in sorted(path.glob(pattern)):
            result[match] = not exclude
    return result


def glob_refine(path: Path, patterns: List[str], matches: GlobMatches) -> GlobMatches:
    """Apply glob-like `patterns` to `path` to refine `matches`."""
    result = matches.copy()
    for pattern in patterns:
        exclude, pattern = starts(pattern, GLOB_EXCLUDE)
        if pattern == GLOB_ALL:
            for match in result:
                result[match] = not exclude
            continue

        for match in sorted(path.glob(pattern)):
            if match in result:  # no new entries
                result[match] = not exclude
    return result

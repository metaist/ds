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
from typing import Tuple
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


def glob_parents(start: Path, patterns: Dict[str, str]) -> Iterator[Tuple[str, Path]]:
    """Yield glob matches in every parent."""
    for path in (start / "x").resolve().parents:
        for key, pattern in patterns.items():
            log.debug(f"check {path / pattern}")
            if "*" in pattern or "?" in pattern or "[" in pattern or "/" in pattern:
                for check in sorted(path.glob(pattern)):
                    yield key, check
            else:  # just normal check
                check = path / pattern
                if check.exists():
                    yield key, check


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


def glob_paths(
    path: Path,
    patterns: List[str],
    *,
    allow_all: bool = False,  # special all pattern
    allow_excludes: bool = False,  # special exclude prefix
    allow_new: bool = False,  # expand the set
    previous: Optional[GlobMatches] = None,
) -> GlobMatches:
    """Apply glob `patterns` to `path`."""
    result = previous.copy() if previous else {}
    for pattern in patterns:
        exclude = False

        # extension: special exclusion prefix
        if allow_excludes:
            exclude, pattern = starts(pattern, GLOB_EXCLUDE)

        # extension: special all pattern
        if allow_all and pattern == GLOB_ALL:
            for match in result:
                result[match] = not exclude
            continue

        hits = sorted(path.glob(pattern))
        if not hits:
            log.warning(f"No results for {pattern} in {path}")

        for match in hits:
            if allow_new or match in result:
                # Either new entries are allowed,
                # or this entry was already there.
                result[match] = not exclude
    return result

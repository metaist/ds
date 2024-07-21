#!/usr/bin/env python
"""Run developer scripts.

.. include:: ../README.md
   :start-line: 2
"""

from typing import List
from typing import Optional

__version__ = "0.1.0"


def main(argv: Optional[List[str]] = None) -> None:
    """Run developer scripts."""
    print("args:", argv)


if __name__ == "__main__":  # pragma: no cover
    main()

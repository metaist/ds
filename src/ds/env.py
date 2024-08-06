"""Work with shell environment variables."""

# std
from os import environ as ENV


class TempEnv:
    """Temporary environment variables."""

    def __init__(self, **initial):
        """Construct a temporary environment object.

        Args:
            **initial (str): initial environment variables to set

        Examples:
        >>> with TempEnv(foo="bar") as env1:
        ...     env1["foo"] == "bar"
        True
        >>> with TempEnv(a="b", c="d", x=None) as env1:
        ...     with TempEnv(a=None, c="e", f="g") as env2:
        ...         env2["a"] is None and env2["c"] == "e"
        True
        """
        self.saved = {}
        for key, value in initial.items():
            if value is None:
                del self[key]
            else:
                self[key] = value

    def __enter__(self):
        """Return self when entering a context."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Reset all keys back to their previous values/existence."""
        for key, old in self.saved.items():
            if old is None:
                if key in ENV:
                    del ENV[key]
            else:
                ENV[key] = old

    def __iter__(self):
        """Return the iterator for ENV.

        >>> list(TempEnv()) != []
        True
        """
        return ENV.__iter__()

    def __len__(self):
        """Return len(ENV).

        >>> len(TempEnv()) > 0
        True
        """
        return len(ENV)

    def __contains__(self, key: str) -> bool:
        """Return True if the key is in ENV.

        >>> with TempEnv(a="b") as env1:
        ...     "a" in env1
        True
        """
        return key in ENV

    def __getitem__(self, key: str) -> str:
        """Return the current value of `key` or `None` if it isn't set."""
        return ENV.get(key, None)

    def __setitem__(self, key: str, value: str):
        """Set the value of an environment variable.

        >>> with TempEnv(a="b") as env1:
        ...     env1["a"] = "c"
        """
        if key not in self.saved:
            self.saved[key] = ENV.get(key)
        ENV[key] = str(value)

    def __delitem__(self, key: str):
        """Delete an environment variable.

        >>> with TempEnv(a=None) as env1:
        ...     del env1["a"]
        """
        if key not in self.saved:
            self.saved[key] = ENV.get(key)
        if key in ENV:
            del ENV[key]

"""Custom exceptions for ds."""


class DsError(Exception):
    """Base exception for ds errors."""

    exit_code: int = 1
    """Exit code to use when this exception reaches main()."""


class ConfigError(DsError):
    """Error loading or parsing configuration."""

    pass


class TaskError(DsError):
    """Error executing a task."""

    def __init__(self, message: str, exit_code: int = 1):
        """Initialize with message and exit code."""
        super().__init__(message)
        self.exit_code = exit_code

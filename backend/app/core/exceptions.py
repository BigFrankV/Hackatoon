from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", *, code: str = "not_found") -> None:
        super().__init__(status_code=404, code=code, message=message)


class PermissionDeniedError(AppError):
    def __init__(
        self, message: str = "Not enough permissions", *, code: str = "forbidden"
    ) -> None:
        super().__init__(status_code=403, code=code, message=message)


class AuthenticationError(AppError):
    def __init__(
        self, message: str = "Not authenticated", *, code: str = "unauthorized"
    ) -> None:
        super().__init__(status_code=401, code=code, message=message)


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request", *, code: str = "bad_request") -> None:
        super().__init__(status_code=400, code=code, message=message)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", *, code: str = "conflict") -> None:
        super().__init__(status_code=409, code=code, message=message)


class RateLimitError(AppError):
    def __init__(
        self,
        message: str = "Too many requests",
        *,
        code: str = "rate_limited",
    ) -> None:
        super().__init__(status_code=429, code=code, message=message)

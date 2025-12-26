"""Custom exception classes."""

from fastapi import HTTPException, status


class VoiceNotesException(Exception):
    """Base exception for Scribe application."""

    pass


class AuthenticationError(VoiceNotesException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Could not validate credentials"):
        self.detail = detail
        super().__init__(detail)

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=self.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class NotFoundError(VoiceNotesException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str = "Resource", detail: str | None = None):
        self.detail = detail or f"{resource} not found"
        super().__init__(self.detail)

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=self.detail,
        )


class ServiceError(VoiceNotesException):
    """Raised when external service calls fail."""

    def __init__(self, detail: str = "External service error"):
        self.detail = detail
        super().__init__(detail)

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=self.detail,
        )

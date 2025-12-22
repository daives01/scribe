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


class PermissionDeniedError(VoiceNotesException):
    """Raised when user doesn't have permission for an action."""

    def __init__(self, detail: str = "Permission denied"):
        self.detail = detail
        super().__init__(detail)

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=self.detail,
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


class ProcessingError(VoiceNotesException):
    """Raised when processing (transcription, AI) fails."""

    def __init__(self, detail: str = "Processing failed"):
        self.detail = detail
        super().__init__(detail)

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

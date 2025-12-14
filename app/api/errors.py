"""
Обработка ошибок API.
"""

from fastapi import HTTPException, status
from typing import Any, Dict, Optional
import uuid
from .schemas import ErrorResponse


class APIError(HTTPException):
    """Базовый класс для ошибок API."""
    
    def __init__(
        self,
        status_code: int,
        error: str,
        detail: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status_code,
            detail=detail or error,
            headers=headers
        )
        self.error = error
        self.request_id = str(uuid.uuid4())[:8]
    
    def to_response(self) -> ErrorResponse:
        """Преобразует ошибку в Pydantic модель."""
        return ErrorResponse(
            error=self.error,
            detail=self.detail,
            request_id=self.request_id
        )


class FileTooLargeError(APIError):
    """Ошибка при превышении размера файла."""
    
    def __init__(self, max_size_mb: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error="File too large",
            detail=f"Maximum file size is {max_size_mb}MB"
        )


class UnsupportedFormatError(APIError):
    """Ошибка при неподдерживаемом формате файла."""
    
    def __init__(self, filename: str, allowed_extensions: list):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="Unsupported file format",
            detail=f"File '{filename}' has unsupported format. "
                   f"Allowed formats: {', '.join(allowed_extensions)}"
        )


class ProcessingError(APIError):
    """Ошибка при обработке аудио."""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="Audio processing failed",
            detail=detail
        )


class InvalidMethodError(APIError):
    """Ошибка при неверном методе обработки."""
    
    def __init__(self, method: str, allowed_methods: list):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="Invalid denoising method",
            detail=f"Method '{method}' is not supported. "
                   f"Allowed methods: {', '.join(allowed_methods)}"
        )


class FileNotFoundError(APIError):
    """Ошибка при отсутствии файла."""
    
    def __init__(self, filename: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error="File not found",
            detail=f"File '{filename}' not found"
        )


def handle_api_error(exc: APIError) -> ErrorResponse:
    """Обработчик для ошибок API."""
    return exc.to_response()


def handle_generic_error(exc: Exception) -> ErrorResponse:
    """Обработчик для общих ошибок."""
    request_id = str(uuid.uuid4())[:8]
    return ErrorResponse(
        error="Internal server error",
        detail=str(exc),
        request_id=request_id
    )
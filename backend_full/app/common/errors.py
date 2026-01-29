"""
Иерархия исключений с централизованными кодами ошибок.

Подход:
- Семантические базовые классы (лучше для обработки в хендлерах)
- Доменные подклассы при необходимости детализации
- Полная обратная совместимость со старым кодом
"""

from typing import NamedTuple, Dict, Any, Optional, Union, Type


# ===== 1. Коды ошибок (данные) =====
class ErrorCode(NamedTuple):
    """Структура кода ошибки."""
    code: str          # Уникальный идентификатор (например, "AUTH_001")
    message: str       # Человекочитаемое сообщение по умолчанию
    http_status: int = 400  # HTTP статус для API
    is_internal: bool = False  # True = ошибка не должна показываться клиенту


class ErrorCodes:
    """Централизованный реестр кодов ошибок."""

    # ===== Аутентификация =====
    AUTH_INVALID_CREDENTIALS = ErrorCode("AUTH_001", "Неверные учетные данные", 401)
    AUTH_TOKEN_EXPIRED = ErrorCode("AUTH_002", "Токен аутентификации истек", 401)
    AUTH_USER_BLOCKED = ErrorCode("AUTH_003", "Пользователь заблокирован", 403)
    AUTH_PERMISSION_DENIED = ErrorCode("AUTH_004", "Недостаточно прав для выполнения операции", 403)

    # ===== Валидация =====
    VALIDATION_REQUIRED_FIELD = ErrorCode("VALID_001", "Обязательное поле не заполнено", 422)
    VALIDATION_INVALID_EMAIL = ErrorCode("VALID_002", "Некорректный формат email", 422)
    VALIDATION_OUT_OF_RANGE = ErrorCode("VALID_003", "Значение вне допустимого диапазона", 422)

    # ===== Сущности не найдены =====
    NOT_FOUND_ENTITY = ErrorCode("NOT_FOUND_001", "Сущность не найдена", 404)
    NOT_FOUND_USER = ErrorCode("NOT_FOUND_002", "Пользователь не найден", 404)
    NOT_FOUND_PRODUCT = ErrorCode("NOT_FOUND_003", "Товар не найден", 404)
    NOT_FOUND_CATEGORY = ErrorCode("NOT_FOUND_004", "Категория не найдена", 404)

    # ===== Конфликты состояния =====
    CONCURRENCY_CONFLICT = ErrorCode("CONFLICT_001", "Конфликт версий при одновременном редактировании", 409)
    IDEMPOTENCY_VIOLATION = ErrorCode("CONFLICT_002", "Повторный запрос с тем же идемпотентным ключом", 409)
    STOCK_INSUFFICIENT = ErrorCode("CONFLICT_003", "Недостаточно товара на складе", 409)

    # ===== Внутренние ошибки =====
    SYSTEM_INTERNAL = ErrorCode("SYSTEM_001", "Внутренняя ошибка сервера", 500, is_internal=True)
    SYSTEM_UNAVAILABLE = ErrorCode("SYSTEM_002", "Сервис временно недоступен", 503, is_internal=True)


# ===== 2. Базовые классы исключений (поведение) =====
class DomainError(Exception):
    """
    Базовый класс для всех ошибок уровня домена.

    Поддерживает обратную совместимость:
    - Старый стиль: raise NotFoundError("msg")
    - Новый стиль: raise NotFoundError(error_code=ErrorCodes.NOT_FOUND_PRODUCT, details={...})
    """

    # Дефолтный код для обратной совместимости
    _DEFAULT_ERROR_CODE: ErrorCode = ErrorCodes.SYSTEM_INTERNAL

    def __init__(
        self,
        *args: Any,
        error_code: Optional[ErrorCode] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        # Поддержка старого стиля: raise NotFoundError("Product not found")
        if args and isinstance(args[0], str) and not error_code:
            message = args[0]
            args = args[1:]

        self.error_code = error_code or self._get_default_error_code()
        self.message = message or self.error_code.message
        self.details = details or {}

        super().__init__(self.message, *args, **kwargs)

    def _get_default_error_code(self) -> ErrorCode:
        """Определяет дефолтный код ошибки на основе типа исключения."""
        # Маппинг для обратной совместимости
        mapping: Dict[Type["DomainError"], ErrorCode] = {
            ValidationError: ErrorCodes.VALIDATION_REQUIRED_FIELD,
            PermissionDenied: ErrorCodes.AUTH_PERMISSION_DENIED,
            NotFoundError: ErrorCodes.NOT_FOUND_ENTITY,
            ConcurrencyError: ErrorCodes.CONCURRENCY_CONFLICT,
            IdempotencyError: ErrorCodes.IDEMPOTENCY_VIOLATION,
        }
        return mapping.get(type(self), self._DEFAULT_ERROR_CODE)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация ошибки для API."""
        return {
            "code": self.error_code.code,
            "message": self.message,
            "details": self.details,
            "http_status": self.error_code.http_status,
        }

    @property
    def is_internal(self) -> bool:
        """Является ли ошибка внутренней (не для клиентов)."""
        return self.error_code.is_internal


class ValidationError(DomainError):
    _DEFAULT_ERROR_CODE = ErrorCodes.VALIDATION_REQUIRED_FIELD


class PermissionDenied(DomainError):
    _DEFAULT_ERROR_CODE = ErrorCodes.AUTH_PERMISSION_DENIED


class NotFoundError(DomainError):
    _DEFAULT_ERROR_CODE = ErrorCodes.NOT_FOUND_ENTITY


class ConcurrencyError(DomainError):
    _DEFAULT_ERROR_CODE = ErrorCodes.CONCURRENCY_CONFLICT


class IdempotencyError(DomainError):
    _DEFAULT_ERROR_CODE = ErrorCodes.IDEMPOTENCY_VIOLATION


# ===== 3. Доменные подклассы (опционально, для детализации) =====
# Используются, когда нужна специфическая обработка в хендлерах

class ProductNotFoundError(NotFoundError):
    _DEFAULT_ERROR_CODE = ErrorCodes.NOT_FOUND_PRODUCT


class CategoryNotFoundError(NotFoundError):
    _DEFAULT_ERROR_CODE = ErrorCodes.NOT_FOUND_CATEGORY


class InsufficientStockError(ConcurrencyError):
    _DEFAULT_ERROR_CODE = ErrorCodes.STOCK_INSUFFICIENT


# ===== 4. Утилиты =====
_ERROR_CODE_REGISTRY = {
    code.code: code
    for name, code in vars(ErrorCodes).items()
    if isinstance(code, ErrorCode)
}


def get_error_code(code: str) -> ErrorCode:
    """Получить описание ошибки по её коду."""
    if code not in _ERROR_CODE_REGISTRY:
        raise ValueError(f"Неизвестный код ошибки: {code}")
    return _ERROR_CODE_REGISTRY[code]


def raise_error(
    error_code: ErrorCode,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None,
) -> None:
    """
    Универсальный способ выброса ошибки с автоматическим определением типа.

    Пример:
        raise_error(ErrorCodes.NOT_FOUND_PRODUCT, details={"product_id": 123})
    """
    exc_class = _get_exception_class_by_code(error_code)
    exc = exc_class(error_code=error_code, message=message, details=details)

    if cause:
        exc.__cause__ = cause

    raise exc


def _get_exception_class_by_code(error_code: ErrorCode) -> Type[DomainError]:
    """Определяет тип исключения по коду ошибки."""
    # Маппинг кодов → конкретных классов исключений
    code_to_class = {
        ErrorCodes.NOT_FOUND_PRODUCT: ProductNotFoundError,
        ErrorCodes.NOT_FOUND_CATEGORY: CategoryNotFoundError,
        ErrorCodes.STOCK_INSUFFICIENT: InsufficientStockError,
    }

    # По умолчанию используем семантический класс на основе статуса
    if error_code.http_status == 404:
        return NotFoundError
    elif error_code.http_status == 403:
        return PermissionDenied
    elif error_code.http_status == 422:
        return ValidationError
    elif error_code.http_status == 409:
        return ConcurrencyError

    return DomainError
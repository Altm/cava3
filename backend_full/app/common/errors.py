class DomainError(Exception):
    """Base class for domain-level errors."""


class ValidationError(DomainError):
    """Raised when domain invariants are violated."""


class PermissionDenied(DomainError):
    """Raised when user lacks permission."""


class NotFoundError(DomainError):
    """Raised when an entity is missing."""


class ConcurrencyError(DomainError):
    """Raised when optimistic locking or race conditions detected."""


class IdempotencyError(DomainError):
    """Raised on idempotency violations."""

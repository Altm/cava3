# app/common/decorators.py
import functools
import warnings
from typing import Callable, Type, Optional, TypeVar

T = TypeVar("T", bound=Type)


def deprecated(
        reason: Optional[str] = None,
        version: Optional[str] = None,
        alternative: Optional[str] = None,
        category: Type[Warning] = DeprecationWarning,
) -> Callable[[T], T]:
    """
    Декоратор для пометки класса как устаревшего (deprecated).

    Генерирует предупреждение при:
    - создании экземпляра класса
    - наследовании от класса (через __init_subclass__)

    Параметры:
        reason: Причина депрекации
        version: Версия, в которой класс объявлен устаревшим
        alternative: Рекомендуемая замена
        category: Тип предупреждения (по умолчанию DeprecationWarning)
    """

    def decorator(cls: T) -> T:
        cls_name = cls.__name__
        message_parts = [f"Класс {cls_name} объявлен устаревшим"]

        if version:
            message_parts.append(f"(с версии {version})")
        if reason:
            message_parts.append(f": {reason}")
        if alternative:
            message_parts.append(f". Используйте {alternative} вместо него.")

        message = " ".join(message_parts).strip()

        # Перехват создания экземпляра
        original_init = cls.__init__

        @functools.wraps(original_init)
        def new_init(self, *args, **kwargs):
            warnings.warn(message, category, stacklevel=2)
            return original_init(self, *args, **kwargs)

        cls.__init__ = new_init

        # Перехват наследования
        original_init_subclass = cls.__init_subclass__

        @classmethod
        @functools.wraps(original_init_subclass)
        def new_init_subclass(subclass, **kwargs):
            warnings.warn(message, category, stacklevel=3)
            if original_init_subclass is not object.__init_subclass__:
                original_init_subclass(**kwargs)

        cls.__init_subclass__ = new_init_subclass

        # Добавляем метаданные для интроспекции
        cls._deprecated = True
        cls._deprecated_message = message

        return cls

    return decorator
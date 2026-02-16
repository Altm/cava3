# Cavina Inventory Backend

## Старт через Docker (корень репозитория)
- Скопируйте `backend/.env.example` в `backend/.env` и при необходимости поправьте секреты.
- Запустите `docker-compose up --build` из корня. Поднимутся сервисы:
  - PostgreSQL: `localhost:5432`
  - Backend FastAPI: `http://localhost:8000`
  - Swagger FastAPI: `http://localhost:8001/docs`
  - Frontend Vue: `http://localhost:5173`
- Примените миграции внутри backend-контейнера: `alembic upgrade head`.
- Загрузите тестовые данные: `python scripts/seed.py`.

## Локальный запуск без Docker
- Перейдите в каталог `backend`.
- Установите зависимости: `pip install -r requirements.txt`.
- Поднимите PostgreSQL и выставьте `DATABASE_URL`.
- Запустите миграции: `alembic upgrade head`.
- Запустите приложение: `uvicorn app.main:app --reload`.

## Тесты
- Выполните `pytest`. Используется in-memory SQLite, поэтому внешние сервисы не требуются.
- Ключевые тесты покрывают идемпотентность, сверку, дробные списания, композитные рецепты, RBAC, аудит и промо-правила.

## Серийный учёт (QR)
Добавлен поштучный учёт для товаров с дискретной базовой единицей (`unit.is_discrete=true`).

- QR форматы:
  - `ITM:{UUID}` — единица (`product_item`)
  - `BOX:{UUID}` — коробка (`box`)
- `product_item.status`:
  - `receiving` (сгенерировано в приёмке, ещё не подтверждено)
  - `in_stock` (в наличии в локации)
  - `in_transit` (в доставке; локация меняется только при приёмке в баре)
  - `lost` (недостача в пути / по инвентаризации)
  - `voided` (погашено при отмене приёмки)
- Основные API:
  - `POST /api/v1/receipts` + `/lines` + `/generate` + `/post` + `/void`
  - `POST /api/v1/boxes` + `/{id}/open` + `/{id}/add-item` + `/{id}/seal`
  - `POST /api/v1/transfers` + `/{id}/plan` + `/{id}/scan` + `/{id}/ship` + `/{id}/close`
  - `POST /api/v1/inventories` + `/{id}/start` + `/{id}/scan` + `/{id}/close`
  - `POST /api/v1/scan/{qr_code}` — универсальный резолвер ITM/BOX


## Cron
Чистить логи!
Считать количество


## Ошибки
### В сервисах
```python
from app.common.errors import ErrorCodes, NotFoundError, ValidationError

def get_product(product_id: int):
    product = repo.get(product_id)
    if not product:
        raise NotFoundError(
            ErrorCodes.NOT_FOUND_PRODUCT,
            details={"product_id": product_id}
        )
    return product

def create_user(email: str, password: str):
    if "@" not in email:
        raise ValidationError(
            ErrorCodes.VALIDATION_INVALID_EMAIL,
            details={"field": "email", "value": email}
        )
```

### В FastAPI хендлерах
```python

from fastapi import Request
from fastapi.responses import JSONResponse
from app.common.errors import DomainError

async def domain_error_handler(request: Request, exc: DomainError):
    error_data = exc.to_dict()
    
    # Скрываем детали внутренних ошибок
    if exc.is_internal:
        error_data["message"] = "Внутренняя ошибка сервера"
        error_data["details"] = {}
        logger.exception(f"Internal error [{exc.error_code.code}]", exc_info=exc)
    
    return JSONResponse(
        status_code=error_data["http_status"],
        content={"error": error_data},
    )
```

### ИЛИ через фабрику
```python
raise_error(ErrorCodes.AUTH_PERMISSION_DENIED, details={"user_id": user.id})
```

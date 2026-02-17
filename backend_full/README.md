# Cavina Inventory Backend

## Быстрый старт

### Docker (из корня репозитория)
- Запуск: `docker-compose up --build`
- Backend API: `http://localhost:8001`
- Swagger: `http://localhost:8001/docs`
- Frontend dev: `http://localhost:8090` (проксирует `/api` на backend)
- Миграции: `docker compose exec backend_full alembic upgrade head`

### Локально (без Docker)
- `cd backend_full`
- `pip install -r requirements.txt`
- Настроить `DATABASE_URL`
- `alembic upgrade head`
- `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Тесты
- `pytest -q app/tests`

---

## Что изменено (рефакторинг Variant B)

Слой API переведён на «тонкие контроллеры»:
- роуты больше не содержат бизнес-логику;
- входные данные упаковываются в `Command/Query`;
- обработка выполняется через `dispatch_command` / `dispatch_query`;
- транзакции централизованы через `UnitOfWork`.

Добавлены/переведены модули application:
- `application/simple_catalog/*`
- `application/serial/{receipts,transfers,inventories,boxes,scan}.py`
- `application/{auth,users,me,products,sales,stock,catalog}/*`
- `application/common/{dispatcher.py,uow.py}`

Переиспользование текущих доменных сервисов сохранено:
- handlers вызывают `app/services/*` и/или ORM-модели напрямую;
- это позволяет развивать рефакторинг поэтапно без поломки API.

---

## Текущая структура и назначение

### API слой
- `app/api/v1/routes/*` — HTTP-эндпоинты, валидация FastAPI, авторизация, вызов dispatcher.
- `app/api/v1/deps/auth.py` — JWT, RBAC, получение текущего пользователя, доступ к DB-сессии.
- `app/api/v1/deps/uow.py` — фабрика UoW для роутов.

### Application слой
- `app/application/common/dispatcher.py` — единая точка выполнения command/query.
- `app/application/common/uow.py` — интерфейс `AbstractUnitOfWork`.
- `app/application/<module>/*` — use-case handlers и DTO (`Command`, `Query`).

### Infrastructure слой
- `app/infrastructure/db/session.py` — `SessionLocal`, движок SQLAlchemy.
- `app/infrastructure/db/uow.py`:
  - `SqlAlchemyUnitOfWork` — полноценная транзакция на запрос;
  - `BoundSessionUnitOfWork` — привязка к внешней сессии (используется в отдельных роут-методах и тестах для совместимости).

### Domain/Data слой
- `app/models/models.py` — SQLAlchemy модели.
- `app/schemas/{simple.py,serial.py}` — Pydantic-схемы API.
- `app/services/*` — доменные сервисы (receipt/transfer/inventory/stock/sales и др.).

### Cross-cutting
- `app/audit/*` — аудит и request-логирование.
- `app/security/*` — auth/hmac.
- `app/config.py` — настройки приложения.

---

## Схема вызова (request flow)

1. HTTP-запрос приходит в `app/api/v1/routes/<module>.py`.
2. В роуте применяются зависимости (`PermissionChecker`, `uow_factory`).
3. Роут создаёт `Command` или `Query`.
4. Вызывается:
   - `dispatch_command(...)` — открывает UoW, выполняет handler, делает `commit`;
   - `dispatch_query(...)` — открывает UoW, выполняет handler без `commit`.
5. Handler в `app/application/<module>/*` выполняет бизнес-операцию:
   - напрямую через ORM (`uow.session`) и/или
   - через `app/services/*`.
6. Результат возвращается в роут и сериализуется FastAPI/Pydantic.
7. При исключении UoW вызывает `rollback`.

---

## Серийный учёт (QR)

- Форматы:
  - `ITM:{UUID}` — единица (`product_item`)
  - `BOX:{UUID}` — коробка (`box`)
- Ключевые статусы `product_item.status`:
  - `receiving`, `in_stock`, `in_transit`, `lost`, `voided`
- Основные группы API:
  - `receipts` — приёмка
  - `boxes` — коробки
  - `transfers` — перемещения
  - `inventories` — инвентаризация
  - `scan` — универсальное чтение QR + история единицы

---

## Как создать новый модуль (чеклист)

Пример: новый модуль `suppliers`.

1) Создать application-слой:
- `app/application/suppliers/commands.py`
- `app/application/suppliers/queries.py`
- `app/application/suppliers/__init__.py`

2) Добавить DTO и handlers:
- `@dataclass(frozen=True)` для `CreateSupplierCommand`, `ListSuppliersQuery` и т.д.
- классы `CreateSupplierHandler`, `ListSuppliersHandler` с методом `handle(..., uow)`.

3) Реализовать бизнес-логику:
- использовать `uow.session` и/или существующие сервисы в `app/services/*`;
- для сложной логики добавить новый сервис в `app/services/suppliers_service.py`.

4) Добавить роуты:
- файл `app/api/v1/routes/suppliers.py`;
- в каждом endpoint только:
  - проверка прав (`PermissionChecker`);
  - сбор `Command/Query`;
  - вызов `dispatch_command` / `dispatch_query`.

5) Подключить роут:
- `app/main.py` → `app.include_router(suppliers.router, prefix="/api/v1")`.

6) Добавить схемы и права:
- Pydantic-схемы в `app/schemas/*` (если нужны публичные контракты);
- новые permission-коды и проверки в endpoint'ах.

7) Покрыть тестами:
- минимум: happy-path + 1-2 негативных кейса;
- запуск: `pytest -q app/tests`.

---

## Правила для новых endpoint'ов

- Не переносить бизнес-логику в роуты.
- Команды изменяют состояние, запросы только читают.
- Все write-операции — через `dispatch_command` + UoW commit.
- Ошибки поднимать через `HTTPException`/доменные ошибки, не через `print`.
- По возможности переиспользовать существующие сервисы, чтобы не дублировать SQL-логику.

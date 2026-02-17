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

Дополнительно по pricing:
- добавлено версионирование расчётов;
- ревизии прайса хранят снапшот `name/version/source_hash` использованного алгоритма;
- основной контракт создания ревизии для `mode=calculator` переведён на `calculator_version_id`.

Дополнительно по юнитам:
- добавлены дефолтные юниты типа товара (`product_type_unit`);
- добавлен флаг `product_type.strict_units_by_type`;
- при создании/обновлении товара юниты могут наследоваться из типа автоматически, при strict режиме запрещены юниты вне списка типа.

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
- `app/pricing_calculators/*` — файловые реализации расчётов с версиями.

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

## Прайсы: версия расчёта

### Таблицы
- `price_calculator` — логический реестр расчётов (`code`, `name`, `description`, `is_active`).
- `price_calculator_version` — версия реализации (`version`, `file_path`, `class_name`, `source_hash`, `changelog`, `is_active`).

### Расширение `price_list_revision`
- `calculator_version_id` — ссылка на выбранную версию расчёта.
- `calculator_name_snapshot` — имя расчёта на момент пересчёта.
- `calculator_version_snapshot` — версия на момент пересчёта.
- `calculator_source_hash_snapshot` — hash исходника на момент пересчёта.

### Runtime flow
1. `GET /api/v1/simple-catalog/prices/calculators` синхронизирует версии из `app/pricing_calculators/*` в БД.
2. `POST /api/v1/simple-catalog/prices/revisions` для `mode=calculator` использует `calculator_version_id`.
3. Для совместимости при устаревшем `calculator_version_id` выполняется fallback по `calculator_file + calculator_class`.
4. В `prices/current`, `prices/revisions`, `prices/revisions/{id}` возвращаются версия и hash расчёта.

### Примеры версий
- `app/pricing_calculators/example_multiplier.py` → `example_multiplier`, `Example Multiplier`, `1.0.0`.
- `app/pricing_calculators/example_multiplier_v2.py` → `example_multiplier`, `Example Multiplier`, `1.1.0` (добавлен параметр `floor`).

### Валидация JSON параметров
- На фронте добавлена явная проверка `calculator_params` с понятной ошибкой при невалидном JSON.

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

---

## Миграции для новых изменений

- `20260218_120000_add_stock_lot_purchase_price.py`
- `20260218_130000_add_price_calculator_versions.py`

Запуск:
- `docker compose exec backend_full alembic upgrade head`

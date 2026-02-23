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

Дополнительно по составным товарам и продаже:
- добавлен `CompositeDecompositionService` (`app/domain/composite.py`) для рекурсивной декомпозиции состава в листовые компоненты;
- в декомпозиции добавлено кэширование, проверка циклов и трассировка пути;
- добавлено версионирование рецептов: `product_recipe` и `product_recipe_component`;
- в компоненты добавлен `waste_factor` и учёт эффективного расхода;
- частичное списание сериализованных единиц обобщено через `product_item_usage` (`total_units/used_units/unit_id`);
- расчёт порций в checkout теперь опирается на конверсии юнитов и поля товара (`default_portion_size`, `portions_per_unit`), без `config.glasses_per_bottle`.

Дополнительно по архитектуре:
- в UoW и dispatcher добавлена поддержка доменных событий;
- после успешного checkout публикуется `ProductSoldEvent`;
- подписки регистрируются через `app/domain/subscribers.py`.

Дополнительно по тестам:
- добавлен performance-сценарий `app/tests/test_sales_performance.py` (запуск только при `RUN_PERFORMANCE_TESTS=1`);
- зарегистрирован pytest marker `performance` в `backend_full/pytest.ini`.

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
- `app/domain/composite.py` — сервис декомпозиции составных товаров (с учётом versioned recipe).
- `app/domain/{events.py,event_bus.py,subscribers.py}` — доменные события и подписчики.
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
   - `dispatch_command(...)` — открывает UoW, выполняет handler, делает `commit`, публикует накопленные доменные события;
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
- `20260218_150000_fix_unit_id_default.py`
- `20260219_090000_add_recipe_and_item_usage.py`

Запуск:
- `docker compose exec backend_full alembic upgrade head`



## Refactoring 3
Декомпозиция составных в отдельный сервис
Адекватность: высокая
Важность: высокая (поддерживаемость/повторное использование)
Риск/вред: в вашем примере cache_key = quantity.to_integral_value() вреден (ломает дроби 0.10/0.20). Кэш нужен по точному Decimal (с нормализацией), лучше в рамках одного запроса/UoW.

product_item_pour → универсальное частичное использование
Адекватность: высокая
Важность: средняя/высокая (если реально будут не только бокалы)
Риск/вред: unit_of_measure: str — плохая идея (потеря целостности). Нужен unit_id + FK на unit.

Версионирование рецептов
Адекватность: очень высокая
Важность: очень высокая (история себестоимости, корректная ретроспектива продаж)
Риск/вред: умеренная сложность миграции, но это правильное направление.

waste_factor в компонентах
Адекватность: высокая
Важность: средняя (зависит от операционки кухни/бара)
Риск/вред: если применять “в лоб”, можно искажать фактические списания. Нужны правила: нормативные потери vs фактический брак.

Единый источник истины для порций
Адекватность: высокая
Важность: высокая
Риск/вред: поля portions_per_unit/default_portion_size в product могут дублировать текущую модель product_unit/product_type_unit. Лучше SoT оставить в юнит-конверсиях, а config — только fallback по умолчанию.

Нагрузочные тесты
Адекватность: высокая
Важность: средняя
Риск/вред: пример с pytest + ThreadPool и допуском “15% фейлов” — слабый критерий. Лучше k6/Locust, отдельный стенд, четкие SLA (p95 latency, error rate <1%).

Domain Events
Адекватность: высокая
Важность: средняя сейчас, высокая в росте
Риск/вред: ранний полный event-driven может усложнить систему. Лучше постепенно: сначала внутренний dispatcher + outbox для внешних интеграций.
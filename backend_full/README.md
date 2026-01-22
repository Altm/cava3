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


## Cron
Чистить логи!
Считать количество


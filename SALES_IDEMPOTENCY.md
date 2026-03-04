# Идемпотентность Sales Transactions API

## Обзор

Endpoint `/api/v1/sales/register-sales-transactions` теперь поддерживает **идемпотентную регистрацию продаж** — одинаковые позиции не дублируются при повторной отправке.

## Уровни идемпотентности

### Level 1: Идемпотентность по событию (event_id)

Каждая продажа получает уникальный `event_id`:
- Если указан явно в payload — используется он
- Иначе генерируется как `register:{terminal_id}:{sale_id}`
- Если продажа с таким `event_id` уже существует — она пропускается

**Пример:**
```json
{
  "sales": [{
    "sale_id": 456,
    "event_id": "custom-event-123",  // Опционально
    "terminal_id": "T-1",
    "items": [...]
  }]
}
```

### Level 2: Идемпотентность по позиции (position hash)

Внутри одной продажи каждая позиция получает уникальный хеш:

```python
position_hash = SHA256(terminal_id:sale_id:product_id:quantity:timestamp)[:32]
```

**Что предотвращает:**
- Дублирование позиций при повторной отправке
- Ошибки сети (клиент отправил дважды)
- Ретраи на стороне терминала

## Пример использования

### Запрос
```bash
curl -X POST http://localhost:8001/api/v1/sales/register-sales-transactions \
  -H "X-Terminal-ID: T-1" \
  -H "X-Signature: abc123..." \
  -H "X-Timestamp: 1708500000" \
  -H "Content-Type: application/json" \
  -d '{
    "sales": [
      {
        "sale_id": 456,
        "terminal_id": "T-1",
        "user_id": 12,
        "timestamp": "2026-02-19T10:00:00Z",
        "items": [
          {"product_id": 1, "quantity": 2, "price": 100},
          {"product_id": 2, "quantity": 1, "price": 50},
          {"product_id": 1, "quantity": 2, "price": 100}  // Дубликат!
        ]
      }
    ],
    "timestamp": "2026-02-19T10:00:00Z"
  }'
```

### Ответ
```json
{
  "status": "success",
  "created_event_ids": ["register:T-1:456"],
  "skipped_event_ids": [],
  "duplicate_positions": ["a1b2c3d4e5f6..."],  // Хеш дубликата
  "received_sales_count": 1,
  "processed_positions_count": 2  // Только 2 уникальные позиции
}
```

## Сценарии использования

### 1. Повторная отправка за сутки

**Сценарий:** Терминал отправил продажи за вчера, но не получил ответ. Отправляет снова.

**Первый запрос:**
```json
{
  "sales": [{"sale_id": 456, "items": [...]}]
}
```
**Ответ:** `{"created_event_ids": ["register:T-1:456"], ...}`

**Второй запрос (тот же payload):**
```json
{
  "sales": [{"sale_id": 456, "items": [...]}]
}
```
**Ответ:** `{"skipped_event_ids": ["register:T-1:456"], ...}`

### 2. Частичное дублирование позиций

**Сценарий:** В продаже есть дублирующиеся позиции.

**Запрос:**
```json
{
  "sales": [{
    "sale_id": 457,
    "items": [
      {"product_id": 1, "quantity": 2, "price": 100},  // Позиция 1
      {"product_id": 2, "quantity": 1, "price": 50},   // Позиция 2
      {"product_id": 1, "quantity": 2, "price": 100}   // Дубликат Позиции 1
    ]
  }]
}
```

**Ответ:**
```json
{
  "status": "success",
  "created_event_ids": ["register:T-1:457"],
  "duplicate_positions": ["<hash>"],  // Хеш дубликата
  "processed_positions_count": 2  // Только 2 уникальные
}
```

### 3. Отправка с разными timestamp

**Сценарий:** Одинаковые позиции, но с разными timestamp (разные продажи).

**Запрос 1:**
```json
{
  "sales": [{
    "sale_id": 458,
    "timestamp": "2026-02-19T10:00:00Z",
    "items": [{"product_id": 1, "quantity": 2, "price": 100}]
  }]
}
```

**Запрос 2:**
```json
{
  "sales": [{
    "sale_id": 459,  // Другой sale_id
    "timestamp": "2026-02-19T11:00:00Z",  // Другой timestamp
    "items": [{"product_id": 1, "quantity": 2, "price": 100}]  // Те же товар и количество
  }]
}
```

**Результат:** Обе продажи будут зарегистрированы, так как position_hash разный (разные timestamp/sale_id).

## Алгоритм работы

```
1. Получить список продаж из payload
2. Для каждой продажи:
   a. Проверить event_id (Level 1)
      - Если уже существует → пропустить продажу
   b. Для каждой позиции:
      - Вычислить position_hash
      - Если hash уже был в этой продаже → пропустить позицию
   c. Если остались уникальные позиции:
      - Создать SaleEvent
      - Добавить уникальные SaleLine
3. Вернуть результат с метриками
```

## Метрики в ответе

| Поле | Описание |
|------|----------|
| `created_event_ids` | Список созданных событий |
| `skipped_event_ids` | Список пропущенных (уже существующих) событий |
| `duplicate_positions` | Хеш-идентификаторы дублирующихся позиций |
| `received_sales_count` | Получено продаж |
| `processed_positions_count` | Обработано уникальных позиций |

## Логирование

```
sales_transactions_registered
  terminal_id: "T-1"
  created: 5          # Создано продаж
  skipped: 2          # Пропущено (дубликаты event_id)
  duplicates: 3       # Дубликаты позиций
```

## Рекомендации

### Для клиентов API

1. **Всегда указывайте `sale_id`** — уникальный идентификатор продажи
2. **Используйте точный timestamp** — влияет на position_hash
3. **Обрабатывайте `skipped_event_ids`** — это нормально при ретраях
4. **Проверяйте `duplicate_positions`** — для отладки дубликатов

### Для сервера

1. **Индексы в БД** — убедитесь, что есть индекс на `SaleEvent.event_id`
2. **Мониторинг дубликатов** — логируйте `duplicate_positions` для анализа
3. **Очистка старых данных** — архивируйте старые SaleEvent для производительности

## Тестирование

### Проверка идемпотентности

```bash
# Отправьте один и тот же запрос дважды
curl -X POST ... -d '{"sales": [{"sale_id": 1, "items": [...]}]}'

# Первый ответ: created_event_ids: ["register:T-1:1"]
# Второй ответ: skipped_event_ids: ["register:T-1:1"]
```

### Проверка дублирования позиций

```bash
# Отправьте продажу с дубликатами
curl -X POST ... -d '{
  "sales": [{
    "sale_id": 2,
    "items": [
      {"product_id": 1, "quantity": 1, "price": 100},
      {"product_id": 1, "quantity": 1, "price": 100}
    ]
  }]
}'

# Ответ: processed_positions_count: 1 (не 2!)
```

## История изменений

- **2026-02-19**: Добавлена идемпотентность на уровне позиций
- **2026-02-19**: Добавлен `position_hash` для аудита
- **2026-02-19**: Расширен ответ API метриками дубликатов

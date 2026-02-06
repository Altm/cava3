# Пример запроса для curl

## Запрос для регистрации продаж и обновления остатков

### Команда curl
```bash
curl -X POST http://localhost:8000/api/v1/sales/register-sales-transactions \
  -H "Content-Type: application/json" \
  -H "X-Terminal-ID: YOUR_TERMINAL_ID" \
  -H "X-Signature: YOUR_HMAC_SIGNATURE" \
  -H "X-Timestamp: UNIX_TIMESTAMP" \
  -d '{
  "sales": [
    {"product_id": "ABC123", "quantity": 5},
    {"product_id": "DEF456", "quantity": 2}
  ],
  "timestamp": "2023-10-01T10:00:00Z"
}'
```

### Пояснения:
- `YOUR_TERMINAL_ID` - замените на реальный ID вашего терминала
- `YOUR_HMAC_SIGNATURE` - замените на действительную HMAC-подпись
- `UNIX_TIMESTAMP` - временная метка в формате Unix timestamp (например, 1696154400)

### Генерация HMAC подписи
Для генерации подписи используйте следующий скрипт на Python:

```python
import hmac
import hashlib
import time
import json

def generate_hmac_signature(method, path, body, terminal_id, secret, timestamp):
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    canonical_string = f"{method.upper()}|{path}|{timestamp}|{body_hash}"
    signature = hmac.new(
        secret.encode(),
        canonical_string.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

# Данные запроса
method = "POST"
path = "/api/v1/sales/register-sales-transactions"  # Обновленный путь
data = {
  "sales": [
    {"product_id": "ABC123", "quantity": 5},
    {"product_id": "DEF456", "quantity": 2}
  ],
  "timestamp": "2023-10-01T10:00:00Z"
}

body = json.dumps(data, separators=(',', ':'))  # Точная строка без лишних пробелов
terminal_id = "your_terminal_id"
secret = "your_terminal_secret"
timestamp = str(int(time.time()))  # Текущее время в Unix timestamp

signature = generate_hmac_signature(method, path, body, terminal_id, secret, timestamp)

print(f"Signature: {signature}")
print(f"Timestamp: {timestamp}")
```

### Пример готовой команды с подставленными значениями:
```bash
curl -X POST http://localhost:8000/api/v1/sales/register-sales-transactions \
  -H "Content-Type: application/json" \
  -H "X-Terminal-ID: TEST_TERMINAL_001" \
  -H "X-Signature: a3f8e7c2d5a1b9e4f6c8d7a9b2e5f3c6a8d1e9f4b7c3a6d9e2f5c8a1b7e4f6d3" \
  -H "X-Timestamp: 1696154400" \
  -d '{
  "sales": [
    {"product_id": "ABC123", "quantity": 5},
    {"product_id": "DEF456", "quantity": 2}
  ],
  "timestamp": "2023-10-01T10:00:00Z"
}'
```

> **ВАЖНО**: Пример выше содержит фиктивные значения для демонстрации. Перед использованием замените `X-Terminal-ID`, `X-Signature` и `X-Timestamp` на действительные значения, сгенерированные с использованием секретного ключа вашего терминала.

## Автоматическая генерация примера запроса

В режиме разработки (когда переменная окружения ENV != "PROD") доступен специальный эндпоинт для автоматической генерации примера запроса:

```
GET http://localhost:8000/api/v1/sales/generate-curl-example
```

Этот эндпоинт вернет актуальный пример команды curl с правильной сгенерированной подписью для тестирования.

## Генерация команды curl с правильной подписью

Для генерации команды curl с правильной подписью, используйте следующий эндпоинт:

```
GET http://localhost:8000/api/v1/sales/generate-curl-command
```

Этот эндпоинт генерирует готовую команду curl с правильной подписью, которая будет действительна в течение hmac_clock_skew_seconds (по умолчанию 3000 секунд).

### Пример использования с комментариями:

```bash
# Получаем готовую команду curl с правильной подписью
curl -X GET http://localhost:8000/api/v1/sales/generate-curl-command

# Ответ будет содержать команду в формате:
# curl --request POST --url http://localhost:8001/api/v1/sales/register-sales-transactions --header 'X-Signature: ...' --header 'X-Terminal-ID: T-1' --header 'X-Timestamp: ...' --header 'content-type: application/json' --data '{...}'

# Эта команда содержит:
# - X-Signature: HMAC-подпись, вычисленная для тела запроса и временной метки
# - X-Terminal-ID: Идентификатор терминала (в данном случае T-1)
# - X-Timestamp: Временная метка в формате Unix timestamp
# - Тело запроса: JSON с информацией о продажах
# Команда будет действительна в течение hmac_clock_skew_seconds с момента генерации
```

> **ВАЖНО**: Сгенерированная команда будет действительна в течение hmac_clock_skew_seconds (по умолчанию 3000 секунд или около 50 минут) с момента её генерации.
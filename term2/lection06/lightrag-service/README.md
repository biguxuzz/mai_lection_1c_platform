# LightRAG Service

Сервис для работы с LightRAG - легковесным фреймворком для Retrieval-Augmented Generation (RAG).

## Описание

LightRAG Service предоставляет REST API для индексации документов и выполнения поисковых запросов с использованием фреймворка LightRAG. Сервис интегрируется с LM Studio для получения эмбеддингов и генерации текста.

## Особенности

- **Легковесный и быстрый**: Использует оптимизированные алгоритмы для быстрой работы
- **Гибкие режимы поиска**: Поддержка local, global, hybrid и naive режимов
- **Интеграция с LM Studio**: Работает с локальными LLM моделями через LM Studio
- **REST API**: Простой и понятный API для интеграции
- **Пакетная индексация**: Возможность индексации множества документов за раз

## API Endpoints

### Health Check
```bash
GET /health
```
Проверка статуса сервиса.

### Индексация документа
```bash
POST /insert
Content-Type: application/json

{
  "text": "Текст документа для индексации",
  "metadata": {
    "source": "example.pdf",
    "page": 1
  }
}
```

### Поиск по документам
```bash
POST /query
Content-Type: application/json

{
  "query": "Поисковый запрос",
  "mode": "hybrid",
  "top_k": 5,
  "only_need_context": false
}
```

**Режимы поиска:**
- `local` - поиск по локальному контексту
- `global` - глобальный поиск по всем документам
- `hybrid` - комбинированный подход (рекомендуется)
- `naive` - простой поиск без дополнительной обработки

### Пакетная индексация
```bash
POST /insert_batch
Content-Type: application/json

[
  "Текст первого документа",
  "Текст второго документа",
  "Текст третьего документа"
]
```

### Очистка индекса
```bash
DELETE /clear
```
Полностью очищает индекс LightRAG.

## Переменные окружения

- `LMSTUDIO_BASE_URL` - URL для подключения к LM Studio (по умолчанию: `http://host.docker.internal:1234/v1`)
- `LMSTUDIO_API_KEY` - API ключ для LM Studio (по умолчанию: `lm-studio`)
- `LLM_MODEL` - Модель для генерации текста (по умолчанию: `Qwen2.5-1.5B-Instruct`)
- `EMBEDDING_MODEL` - Модель для эмбеддингов (по умолчанию: `text-embedding-nomic-embed-text-v1.5`)
- `WORKING_DIR` - Директория для хранения индекса (по умолчанию: `/app/data`)
- `MAX_TOKEN_SIZE` - Максимальный размер токена для чанков (по умолчанию: `512`)

## Примеры использования

### Python
```python
import httpx

# Индексация документа
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8002/insert",
        json={
            "text": "Ваш текст документа здесь"
        }
    )
    print(response.json())

# Поиск
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8002/query",
        json={
            "query": "Что такое LightRAG?",
            "mode": "hybrid",
            "top_k": 5
        }
    )
    print(response.json())
```

### cURL
```bash
# Индексация документа
curl -X POST http://localhost:8002/insert \
  -H "Content-Type: application/json" \
  -d '{"text": "Ваш текст документа здесь"}'

# Поиск
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Что такое LightRAG?", "mode": "hybrid", "top_k": 5}'
```

## Интеграция с другими сервисами

LightRAG Service может использоваться совместно с:

- **Docling Service** - для обработки и индексации документов
- **RAG Service** - для сравнительного анализа разных подходов к RAG
- **n8n** - для создания автоматизированных workflow

## Архитектура

LightRAG использует графовый подход к RAG:

1. **Индексация**: Документы разбиваются на чанки и индексируются с созданием графа знаний
2. **Поиск**: Запросы обрабатываются с учетом графовой структуры знаний
3. **Генерация**: Контекст из графа используется для генерации ответа через LLM

## Производительность

- Быстрая индексация благодаря оптимизированным алгоритмам
- Эффективное использование памяти
- Масштабируемость для больших коллекций документов

## Логирование

Сервис пишет логи в stdout с уровнями:
- `INFO` - информационные сообщения о работе
- `ERROR` - ошибки при выполнении операций

## Порты

- `8002` - HTTP API сервиса

## Зависимости

Основные зависимости:
- `lightrag-hku` - фреймворк LightRAG
- `fastapi` - веб-фреймворк
- `openai` - клиент для работы с OpenAI-совместимым API
- `numpy` - работа с массивами
- `networkx` - работа с графами

## Разработка

Для локальной разработки:

```bash
cd lightrag-service
pip install -r requirements.txt
python app.py
```

## Документация API

После запуска сервиса документация API доступна по адресу:
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc


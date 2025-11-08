# Размерности эмбеддингов популярных моделей

## Таблица размерностей

| Модель | Размерность | Описание |
|--------|-------------|----------|
| **text-embedding-qwen3-embedding-4b** | 768 | Qwen3 Embedding 4B |
| **text-embedding-nomic-embed-text-v1.5** | 768 | Nomic Embed Text v1.5 |
| **text-embedding-multilingual-e5-small** | 384 | Multilingual E5 Small |
| **multilingual-e5-base** | 768 | Multilingual E5 Base |
| **multilingual-e5-large** | 1024 | Multilingual E5 Large |
| **text-embedding-ada-002** | 1536 | OpenAI Ada-002 |
| **text-embedding-3-small** | 1536 | OpenAI Embedding 3 Small |
| **text-embedding-3-large** | 3072 | OpenAI Embedding 3 Large |

## Как проверить размерность модели

### Способ 1: Использование bash скрипта (рекомендуется)

```bash
# Простая проверка (без зависимостей, кроме curl)
chmod +x check_embedding_dim.sh
./check_embedding_dim.sh text-embedding-qwen3-embedding-4b

# С указанием URL (для Docker)
./check_embedding_dim.sh text-embedding-qwen3-embedding-4b http://host.docker.internal:1234/v1
```

### Способ 2: Использование Python утилиты

```bash
# Установка зависимости (если нужно)
pip install httpx

# Проверка конкретной модели
python check_embedding_dim.py text-embedding-qwen3-embedding-4b

# С указанием URL (для Docker)
python check_embedding_dim.py text-embedding-qwen3-embedding-4b \
  --api-url http://host.docker.internal:1234/v1
```

### Способ 3: Через curl (вручную)

```bash
# С jq (рекомендуется)
curl http://localhost:1234/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer lm-studio" \
  -d '{
    "model": "text-embedding-qwen3-embedding-4b",
    "input": "test"
  }' | jq '.data[0].embedding | length'

# С Python (если jq не установлен)
curl http://localhost:1234/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer lm-studio" \
  -d '{
    "model": "text-embedding-qwen3-embedding-4b",
    "input": "test"
  }' | python -c "import sys, json; print(len(json.load(sys.stdin)['data'][0]['embedding']))"
```

### Способ 4: Через Python скрипт

```python
import httpx

response = httpx.post(
    "http://localhost:1234/v1/embeddings",
    headers={
        "Authorization": "Bearer lm-studio",
        "Content-Type": "application/json"
    },
    json={
        "model": "text-embedding-qwen3-embedding-4b",
        "input": "test"
    }
)

data = response.json()
dim = len(data['data'][0]['embedding'])
print(f"Размерность: {dim}")
```

### Способ 5: Через Docker контейнер

```bash
# Выполнить команду внутри контейнера
docker exec lection6_lightrag_webui python /app/check_embedding_dim.py \
  text-embedding-qwen3-embedding-4b \
  --api-url http://host.docker.internal:1234/v1
```

## Определение размерности для вашей модели

Если модель не указана в таблице выше:

1. **Запустите утилиту проверки:**
   ```bash
   python check_embedding_dim.py ВАША_МОДЕЛЬ
   ```

2. **Или используйте curl:**
   ```bash
   curl http://localhost:1234/v1/embeddings \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer lm-studio" \
     -d "{\"model\": \"ВАША_МОДЕЛЬ\", \"input\": \"test\"}" \
     | python -c "import sys, json; print(len(json.load(sys.stdin)['data'][0]['embedding']))"
   ```

3. **Используйте полученное значение в docker-compose.yml:**
   ```yaml
   environment:
     - EMBEDDING_DIM=768  # Замените на ваше значение
   ```

## Проверка через LMStudio UI

1. Откройте LMStudio
2. Загрузите модель эмбеддингов
3. Перейдите в раздел "Local Server"
4. Откройте API документацию (обычно `http://localhost:1234/docs`)
5. Выполните тестовый запрос к `/embeddings`
6. Проверьте размерность в ответе

## Частые проблемы

### Проблема: Модель не найдена

**Решение:**
- Убедитесь, что модель загружена в LMStudio
- Проверьте точное имя модели (case-sensitive)
- Попробуйте получить список моделей: `python check_embedding_dim.py --list-models`

### Проблема: Неверная размерность в конфигурации

**Симптомы:**
- Ошибки при индексации документов
- IndexError в векторной базе данных
- Несоответствие размерности векторов

**Решение:**
1. Проверьте размерность модели через утилиту
2. Обновите `EMBEDDING_DIM` в `docker-compose.yml`
3. Перезапустите контейнеры

### Проблема: API недоступен

**Решение:**
- Убедитесь, что LMStudio запущен
- Проверьте URL в настройках
- Для Docker используйте `http://host.docker.internal:1234/v1`
- Для локального запуска используйте `http://localhost:1234/v1`

## Интеграция с docker-compose.yml

После определения размерности, обновите конфигурацию:

```yaml
lightrag-webui:
  environment:
    - EMBEDDING_MODEL=text-embedding-qwen3-embedding-4b
    - EMBEDDING_DIM=768  # ← Установите правильное значение
```

## Автоматическая проверка

Скрипт `start.py` в `lightrag-webui-service` теперь автоматически проверяет подключение и размерность эмбеддингов при запуске контейнера.

---

**Совет:** Сохраните размерность вашей модели в этом файле для будущих ссылок!


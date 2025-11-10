# 📄 Docling Service - Сервис обработки документов

Микросервис для обработки документов различных форматов с использованием [Docling](https://github.com/DS4SD/docling) и автоматической отправкой в RAG систему.

## 🎯 Возможности

### Поддерживаемые форматы:
- **PDF** - с поддержкой OCR и распознавания структуры
- **Microsoft Office**: DOCX, PPTX
- **Изображения**: PNG, JPG, JPEG, GIF, BMP
- **Веб-форматы**: HTML, HTM
- **Документация**: Markdown (MD), AsciiDoc
- **Данные**: CSV, TXT

### Основные функции:
✅ Конвертация документов в Markdown  
✅ Извлечение структуры документа (заголовки, таблицы, списки)  
✅ Описание изображений с помощью Vision LLM (SmolVLM через LM Studio)  
✅ Автоматическая разбивка на чанки с учетом токенов  
✅ Автоматическая отправка чанков в RAG систему  
✅ Сохранение метаданных (страницы, формат, изображения)

## 🚀 Быстрый старт

### 1. Запуск через Docker Compose

```bash
# Из корня проекта lection06
docker-compose up -d docling-service
```

Сервис будет доступен по адресу: `http://localhost:8001`

### 2. Проверка здоровья сервиса

```bash
curl http://localhost:8001/health
```

Ответ:
```json
{
  "status": "healthy",
  "service": "docling-service",
  "lm_studio_url": "http://host.docker.internal:1234/v1/chat/completions",
  "rag_service_url": "http://rag-service:8000/ingest"
}
```

### 3. Получение поддерживаемых форматов

```bash
curl http://localhost:8001/formats
```

## 📝 API Endpoints

### POST /process - Обработка документа

Загрузка и обработка документа с автоматическим чанкингом и отправкой в RAG.

#### Параметры (multipart/form-data):

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `file` | file | Да | Файл документа |
| `enable_image_description` | boolean | Нет (default: true) | Включить описание изображений через LLM |
| `send_to_rag` | boolean | Нет (default: true) | Автоматически отправить чанки в RAG |
| `metadata` | JSON string | Нет | Дополнительные метаданные |

#### Пример использования (PowerShell):

```powershell
# Простая загрузка PDF
curl.exe -X POST "http://localhost:8001/process" `
  -F "file=@document.pdf"

# С дополнительными параметрами
$metadata = @{
    author = "Иван Иванов"
    category = "Документация"
    tags = @("AI", "ML", "RAG")
} | ConvertTo-Json

curl.exe -X POST "http://localhost:8001/process" `
  -F "file=@presentation.pptx" `
  -F "enable_image_description=true" `
  -F "send_to_rag=true" `
  -F "metadata=$metadata"
```

#### Пример ответа:

```json
{
  "success": true,
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "metadata": {
    "filename": "document.pdf",
    "format": "pdf",
    "pages": 10
  },
  "pictures": [
    {
      "self_ref": "picture_1",
      "caption": "Diagram showing neural network architecture",
      "annotations": ["Figure 1.1"]
    }
  ],
  "chunks_count": 25,
  "chunks_preview_only": true,
  "chunks": [
    {
      "content": "# Introduction\n\nThis document describes...",
      "metadata": {
        "source_filename": "document.pdf",
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "chunk_index": 0,
        "chunk_tokens": 120,
        "total_chunks": 25,
        "format": "pdf",
        "pages": 10
      }
    }
  ],
  "rag_ingestion": {
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "total_chunks": 25,
    "successful": 25,
    "failed": 0,
    "errors": []
  }
}
```

### GET /health - Проверка здоровья

Проверка работоспособности сервиса.

### GET /formats - Поддерживаемые форматы

Получение списка поддерживаемых форматов и настроек чанкинга.

## ⚙️ Конфигурация

Настройки задаются через переменные окружения:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `PORT` | Порт сервиса | 8001 |
| `LM_STUDIO_URL` | URL LM Studio API для описания изображений | http://host.docker.internal:1234/v1/chat/completions |
| `LM_STUDIO_MODEL` | Модель для описания изображений | smolvlm-256m-instruct |
| `LM_STUDIO_TIMEOUT` | Timeout для запросов к LM Studio (сек) | 90 |
| `RAG_SERVICE_URL` | URL RAG сервиса для отправки чанков | http://rag-service:8000/ingest |
| `CHUNK_SIZE_TOKENS` | Размер чанка в токенах | 128 |
| `CHUNK_OVERLAP_TOKENS` | Перекрытие между чанками в токенах | 30 |

## 🔧 Интеграция с LM Studio

Для описания изображений в документах используется локальная модель SmolVLM через LM Studio.

### Настройка LM Studio:

1. Скачайте и установите [LM Studio](https://lmstudio.ai/)
2. Загрузите модель: `HuggingFaceTB/SmolVLM-256M-Instruct-GGUF`
3. Запустите локальный сервер:
   - Выберите модель
   - Нажмите "Start Server"
   - Убедитесь что сервер запущен на `http://localhost:1234`

### Без LM Studio:

Если LM Studio недоступен, сервис продолжит работу, но описание изображений будет отключено:

```bash
# Отключить описание изображений
curl.exe -X POST "http://localhost:8001/process" `
  -F "file=@document.pdf" `
  -F "enable_image_description=false"
```

## 🔗 Интеграция с n8n

Создан специальный workflow для удобной работы с docling-service через n8n.

### Импорт workflow:

1. Откройте n8n: http://localhost:5678
2. Импортируйте файл: `n8n-workflows/workflow-docling-process.json`
3. Активируйте workflow

### Использование webhook:

```powershell
# Отправка документа через n8n webhook
curl.exe -X POST "http://localhost:5678/webhook-test/docling-process" `
  -F "file=@document.pdf" `
  -F "metadata={\"category\":\"documentation\"}"
```

## 📊 Процесс обработки

```
1. Загрузка документа
   ↓
2. Docling конвертация → Markdown + структура
   ↓
3. Описание изображений (если включено)
   ↓ (через LM Studio SmolVLM)
4. Разбивка на чанки
   ↓ (с учетом токенов и overlap)
5. Обогащение метаданными
   ↓
6. Отправка в RAG
   ↓ (автоматически если send_to_rag=true)
7. Возврат результата
```

## 🧩 Примеры использования

### Пример 1: Обработка PDF с отправкой в RAG

```python
import requests

# Загрузка и обработка PDF
with open('report.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8001/process',
        files={'file': f},
        data={
            'enable_image_description': 'true',
            'send_to_rag': 'true',
            'metadata': json.dumps({
                'author': 'Data Team',
                'category': 'Analytics',
                'year': 2024
            })
        }
    )

result = response.json()
print(f"Processed: {result['filename']}")
print(f"Chunks created: {result['chunks_count']}")
print(f"Sent to RAG: {result['rag_ingestion']['successful']}/{result['rag_ingestion']['total_chunks']}")
```

### Пример 2: Обработка презентации PowerPoint

```python
import requests

with open('presentation.pptx', 'rb') as f:
    response = requests.post(
        'http://localhost:8001/process',
        files={'file': f},
        data={
            'enable_image_description': 'true',  # Описать диаграммы и картинки
            'send_to_rag': 'true'
        }
    )

result = response.json()
print(f"Images found: {result['pictures']}")
for pic in result['pictures']:
    print(f"  - {pic['caption']}")
```

### Пример 3: Batch обработка через Python

```python
import requests
from pathlib import Path

docs_folder = Path('./documents')

for doc_path in docs_folder.glob('**/*.pdf'):
    with open(doc_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8001/process',
            files={'file': f},
            data={
                'metadata': json.dumps({
                    'source_folder': str(doc_path.parent),
                    'batch': 'daily_import'
                })
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ {doc_path.name}: {result['chunks_count']} chunks")
        else:
            print(f"✗ {doc_path.name}: Error")
```

## 🐛 Troubleshooting

### Ошибка: "Failed to enable image description"

**Причина**: LM Studio недоступен

**Решение**:
1. Проверьте, что LM Studio запущен и сервер активен
2. Проверьте URL в переменной `LM_STUDIO_URL`
3. Или отключите описание изображений: `enable_image_description=false`

### Ошибка: "Connection refused" к RAG Service

**Причина**: RAG Service не запущен или недоступен

**Решение**:
```bash
# Проверьте статус RAG Service
docker-compose ps rag-service

# Перезапустите если нужно
docker-compose restart rag-service
```

### Большие файлы обрабатываются долго

**Решение**: Увеличьте timeout в настройках:
```yaml
# docker-compose.yml
environment:
  - LM_STUDIO_TIMEOUT=180  # Увеличить с 90 до 180 секунд
```

### Ошибка памяти при обработке больших PDF

**Решение**: Увеличьте лимиты памяти для контейнера:
```yaml
# docker-compose.yml
docling-service:
  deploy:
    resources:
      limits:
        memory: 4G
```

## 📚 Дополнительные ресурсы

- [Docling Documentation](https://github.com/DS4SD/docling)
- [SmolVLM Model](https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct)
- [LM Studio](https://lmstudio.ai/)
- [tiktoken для подсчета токенов](https://github.com/openai/tiktoken)

---

**Создано для курса "Искусственный интеллект" МАИ, Лекция 6** 🎓



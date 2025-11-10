# 🔄 Примеры n8n Workflows для Graph RAG

Эта папка содержит примеры workflow для автоматизации работы с Graph RAG системой.

## 📋 Доступные Workflows

### 1. RAG Document Ingestion (workflow-rag-ingest.json)
Workflow для добавления текстовых документов в RAG систему.

**Узлы:**
1. **Webhook Ingest** - принимает POST запрос с текстом
2. **Validate & Prepare** - валидация и подготовка данных
3. **Ingest to RAG** - отправка в RAG Service
4. **Respond Success** - возврат результата

**Использование:**
```bash
curl -X POST "http://localhost:5678/webhook-test/rag-ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Машинное обучение - это...",
    "metadata": {"source": "manual", "category": "AI"}
  }'
```

### 2. RAG Query (workflow-rag-query.json)
Workflow для запросов к RAG системе.

**Узлы:**
1. **Webhook Query** - принимает POST запрос с вопросом
2. **Query RAG** - отправляет запрос в RAG Service
3. **Respond** - возвращает ответ

**Использование:**
```bash
curl -X POST "http://localhost:5678/webhook-test/rag-query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Что такое машинное обучение?"}'
```

### 3. 🆕 Docling Document Processing (workflow-docling-process.json)
Workflow для обработки документов любых форматов через Docling Service.

**Особенности:**
- ✅ Поддержка PDF, DOCX, PPTX, изображений и других форматов
- ✅ Автоматическое извлечение текста и структуры
- ✅ Описание изображений через Vision LLM (SmolVLM)
- ✅ Автоматическая разбивка на чанки
- ✅ Автоматическая отправка в RAG систему

**Узлы:**
1. **Webhook Document Upload** - принимает файл
2. **Validate Input** - валидация параметров
3. **Process with Docling** - обработка через Docling Service
4. **Format Response** - форматирование результата
5. **Respond Success/Error** - возврат результата

**Использование (PowerShell):**
```powershell
# Простая загрузка документа
curl.exe -X POST "http://localhost:5678/webhook-test/docling-process" `
  -F "file=@document.pdf"

# С дополнительными параметрами
$metadata = @{
    author = "Иван Иванов"
    category = "Документация"
    tags = @("AI", "ML")
} | ConvertTo-Json

curl.exe -X POST "http://localhost:5678/webhook-test/docling-process" `
  -F "file=@presentation.pptx" `
  -F "enable_image_description=true" `
  -F "send_to_rag=true" `
  -F "metadata=$metadata"
```

**Поддерживаемые форматы:**
- PDF (с OCR)
- Microsoft Office: DOCX, PPTX
- Изображения: PNG, JPG, GIF
- HTML, Markdown, AsciiDoc
- CSV, TXT

### 4. Document Ingestion (добавление документов)
Workflow для массового добавления документов.

**Узлы:**
1. **Manual Trigger** - ручной запуск
2. **Read File** - чтение файлов
3. **Loop** - обход документов
4. **HTTP Request** - добавление в RAG
5. **Slack/Email** - уведомление о завершении

### 3. Scheduled Knowledge Update (плановое обновление)
Автоматическое обновление базы знаний по расписанию.

**Узлы:**
1. **Schedule Trigger** - запуск по расписанию (например, ежедневно)
2. **HTTP Request** - получение данных из внешнего источника
3. **Data Transformation** - обработка данных
4. **HTTP Request** - добавление в RAG
5. **Database** - логирование операций

### 4. Email to Knowledge Base (письма в базу знаний)
Автоматическое добавление важных писем в базу знаний.

**Узлы:**
1. **Email Trigger (IMAP)** - мониторинг почты
2. **Filter** - фильтрация по критериям (тема, отправитель)
3. **Extract Attachments** - извлечение вложений
4. **HTTP Request** - добавление в RAG
5. **Gmail** - пометка письма как обработанного

### 5. RAG with Fallback (RAG с запасным вариантом)
Workflow с fallback на внешний LLM, если локальный не дал ответ.

**Узлы:**
1. **Webhook** - прием запроса
2. **HTTP Request** - запрос к локальному RAG
3. **IF** - проверка качества ответа
4. **HTTP Request** - fallback на ChatGPT/Claude (опционально)
5. **Respond to Webhook** - возврат результата

## 🚀 Импорт Workflows в n8n

### Способ 1: Через UI
1. Откройте n8n: http://localhost:5678
2. Нажмите "+" → "Import from file"
3. Выберите JSON файл из этой папки

### Способ 2: Через API
```bash
curl -X POST http://localhost:5678/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d @workflow-simple-query.json
```

## 📝 Создание собственного Workflow

### Базовая структура для работы с RAG:

1. **Triигger Node** (выберите один):
   - Webhook (для API)
   - Schedule (по расписанию)
   - Email Trigger (из почты)
   - Manual Trigger (ручной)

2. **RAG Query Node** (HTTP Request):
   ```
   Method: POST
   URL: http://rag-service:8000/query
   Body (JSON):
   {
     "question": "{{ $json.question }}",
     "top_k": 5,
     "use_graph": true
   }
   ```

3. **RAG Ingest Node** (HTTP Request):
   ```
   Method: POST
   URL: http://rag-service:8000/ingest
   Body (JSON):
   {
     "content": "{{ $json.content }}",
     "metadata": {{ $json.metadata }}
   }
   ```

4. **Response/Action Node** (выберите):
   - Respond to Webhook
   - Send Email
   - Slack Message
   - Database Insert

## 🔗 Полезные узлы для интеграции

### Источники данных:
- **RSS Feed** - новости и блоги
- **Google Sheets** - таблицы
- **Notion** - документация
- **GitHub** - репозитории
- **Confluence** - wiki
- **MySQL/PostgreSQL** - базы данных

### Уведомления:
- **Email** - отправка писем
- **Slack** - сообщения в каналы
- **Telegram** - боты
- **Discord** - уведомления

### Обработка:
- **Code** - JavaScript/Python код
- **IF** - условная логика
- **Switch** - множественный выбор
- **Merge** - объединение данных
- **Split In Batches** - пакетная обработка

## 💡 Примеры реальных сценариев

### Сценарий 1: Документация в RAG
```
Notion Trigger → Read Pages → Format Content → RAG Ingest → Slack Notification
```

### Сценарий 2: Поддержка клиентов
```
Email Trigger → Extract Question → RAG Query → Generate Response → Send Email
```

### Сценарий 3: Анализ конкурентов
```
Schedule → Web Scraping → Clean Data → RAG Ingest → Generate Report → Save to DB
```

### Сценарий 4: Telegram Bot с RAG
```
Telegram Trigger → Extract Message → RAG Query → Format Response → Send to Telegram
```

### Сценарий 5: Еженедельный отчет
```
Schedule (Weekly) → RAG Query (multiple) → Aggregate Results → Generate PDF → Email
```

## 🔐 Безопасность

При создании публичных webhook:
1. Используйте authentication в n8n
2. Добавьте проверку токенов
3. Ограничьте rate limiting
4. Валидируйте входные данные

## 📊 Мониторинг

n8n предоставляет:
- Историю выполнения workflow
- Логи ошибок
- Статистику по времени выполнения
- Уведомления об ошибках

## 🆘 Troubleshooting

### Workflow не запускается
- Проверьте, что workflow активирован (переключатель Active)
- Проверьте логи: n8n → Executions → выберите execution

### Ошибка подключения к RAG Service
- Используйте `http://rag-service:8000` (не localhost!)
- Проверьте, что RAG Service запущен: `docker-compose ps`

### Webhook не отвечает
- Проверьте URL webhook в настройках узла
- Убедитесь, что workflow активирован
- Проверьте, что n8n доступен извне

## 📚 Дополнительные ресурсы

- [n8n Documentation](https://docs.n8n.io)
- [n8n Community](https://community.n8n.io)
- [n8n Workflow Templates](https://n8n.io/workflows)
- [RAG Service API Docs](http://localhost:8000/docs)

---

**Создавайте свои workflow и автоматизируйте работу с базой знаний! 🚀**


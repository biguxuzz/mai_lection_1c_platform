# Dockerfile для Docling Service
# Сервис обработки документов с использованием Docling

FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY app.py .

# Создание директорий для временных файлов
RUN mkdir -p /tmp/docling_uploads /tmp/docling_output

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PORT=8001
ENV LM_STUDIO_URL=http://host.docker.internal:1234/v1/chat/completions
ENV LM_STUDIO_MODEL=smolvlm-256m-instruct
ENV RAG_SERVICE_URL=http://rag-service:8000/ingest
ENV CHUNK_SIZE_TOKENS=128
ENV CHUNK_OVERLAP_TOKENS=30

# Открытие порта
EXPOSE 8001

#Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health').raise_for_status()"

# Запуск приложения
# Увеличен timeout до 2 часов (7200 сек) для обработки больших PDF с VLM
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "--workers", "2", "--timeout", "7200", "--graceful-timeout", "7200", "--access-logfile", "-", "--error-logfile", "-", "app:app"]



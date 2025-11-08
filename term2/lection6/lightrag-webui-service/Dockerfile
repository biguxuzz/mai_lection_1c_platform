# Multi-stage build для LightRAG WebUI
FROM python:3.12-slim as builder

WORKDIR /build

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    git \
    curl \
    unzip \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Установка Bun для сборки фронтенда
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

# Клонирование репозитория LightRAG
RUN git clone https://github.com/HKUDS/LightRAG.git /build/lightrag

WORKDIR /build/lightrag

# Установка Python зависимостей с API поддержкой
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[api]"

# Сборка фронтенда
WORKDIR /build/lightrag/lightrag_webui
RUN bun install --frozen-lockfile && \
    bun run build

# Финальный образ
FROM python:3.12-slim

WORKDIR /app

# Установка только необходимых runtime зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование установленных Python пакетов
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копирование собранного приложения
COPY --from=builder /build/lightrag /app/lightrag

# Копирование стартового скрипта
COPY start.py /app/start.py

WORKDIR /app/lightrag

# Создание директорий для данных
RUN mkdir -p /app/data

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Порт для WebUI API
EXPOSE 9621

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9621/ || exit 1

# Запуск через стартовый скрипт
CMD ["python", "/app/start.py"]


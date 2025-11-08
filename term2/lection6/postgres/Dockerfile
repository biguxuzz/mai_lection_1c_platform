FROM postgres:16

# Установка зависимостей для сборки расширений (добавлены flex и bison)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    postgresql-server-dev-16 \
    curl \
    ca-certificates \
    flex \
    bison \
    && rm -rf /var/lib/apt/lists/*

# Установка pgvector v0.7.4
RUN cd /tmp && \
    git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git && \
    cd pgvector && \
    make clean && \
    make OPTFLAGS="" && \
    make install && \
    cd / && rm -rf /tmp/pgvector

# Установка Apache AGE (master - последняя стабильная версия)
RUN cd /tmp && \
    git clone https://github.com/apache/age.git && \
    cd age && \
    make clean && \
    make PG_CONFIG=/usr/bin/pg_config install && \
    cd / && rm -rf /tmp/age

# Копирование init скрипта
COPY init.sql /docker-entrypoint-initdb.d/

# Настройка PostgreSQL для поддержки AGE
RUN echo "shared_preload_libraries = 'age'" >> /usr/share/postgresql/postgresql.conf.sample

EXPOSE 5432
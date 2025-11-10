-- ==========================================
-- Инициализация БД для Лекции 7 (RAG Demo)
-- ==========================================

-- Создание базы данных lection7
SELECT 'CREATE DATABASE lection7'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'lection7')\gexec

-- Подключаемся к базе lection7
\c lection7

-- Создание расширения pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- Таблицы для хранения чанков лекции с разными размерностями векторов
-- ==========================================

-- Таблица для 384-мерных векторов (text-embedding-multilingual-e5-small)
CREATE TABLE IF NOT EXISTS lecture_chunks_384 (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    chunk_index INTEGER,
    content_length INTEGER,
    source_file VARCHAR(255),
    document_type VARCHAR(50) DEFAULT 'lecture',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для 768-мерных векторов (multilingual-e5-base, nomic-embed-text)
CREATE TABLE IF NOT EXISTS lecture_chunks_768 (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB DEFAULT '{}',
    chunk_index INTEGER,
    content_length INTEGER,
    source_file VARCHAR(255),
    document_type VARCHAR(50) DEFAULT 'lecture',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для 1024-мерных векторов (multilingual-e5-large)
CREATE TABLE IF NOT EXISTS lecture_chunks_1024 (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    chunk_index INTEGER,
    content_length INTEGER,
    source_file VARCHAR(255),
    document_type VARCHAR(50) DEFAULT 'lecture',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для 1536-мерных векторов (OpenAI text-embedding-ada-002, text-embedding-3-small)
CREATE TABLE IF NOT EXISTS lecture_chunks_1536 (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    chunk_index INTEGER,
    content_length INTEGER,
    source_file VARCHAR(255),
    document_type VARCHAR(50) DEFAULT 'lecture',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для 3072-мерных векторов (OpenAI text-embedding-3-large)
CREATE TABLE IF NOT EXISTS lecture_chunks_3072 (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    embedding vector(3072),
    metadata JSONB DEFAULT '{}',
    chunk_index INTEGER,
    content_length INTEGER,
    source_file VARCHAR(255),
    document_type VARCHAR(50) DEFAULT 'lecture',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Алиас для обратной совместимости (по умолчанию 384)
CREATE OR REPLACE VIEW lecture_chunks AS SELECT * FROM lecture_chunks_384;

-- ==========================================
-- Индексы для оптимизации
-- ==========================================

-- Индексы для lecture_chunks_384
CREATE INDEX IF NOT EXISTS lecture_chunks_384_embedding_hnsw_idx 
ON lecture_chunks_384 USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS lecture_chunks_384_metadata_idx ON lecture_chunks_384 USING gin (metadata);
CREATE INDEX IF NOT EXISTS lecture_chunks_384_source_idx ON lecture_chunks_384(source_file);
CREATE INDEX IF NOT EXISTS lecture_chunks_384_created_at_idx ON lecture_chunks_384(created_at DESC);

-- Индексы для lecture_chunks_768
CREATE INDEX IF NOT EXISTS lecture_chunks_768_embedding_hnsw_idx 
ON lecture_chunks_768 USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS lecture_chunks_768_metadata_idx ON lecture_chunks_768 USING gin (metadata);
CREATE INDEX IF NOT EXISTS lecture_chunks_768_source_idx ON lecture_chunks_768(source_file);
CREATE INDEX IF NOT EXISTS lecture_chunks_768_created_at_idx ON lecture_chunks_768(created_at DESC);

-- Индексы для lecture_chunks_1024
CREATE INDEX IF NOT EXISTS lecture_chunks_1024_embedding_hnsw_idx 
ON lecture_chunks_1024 USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS lecture_chunks_1024_metadata_idx ON lecture_chunks_1024 USING gin (metadata);
CREATE INDEX IF NOT EXISTS lecture_chunks_1024_source_idx ON lecture_chunks_1024(source_file);
CREATE INDEX IF NOT EXISTS lecture_chunks_1024_created_at_idx ON lecture_chunks_1024(created_at DESC);

-- Индексы для lecture_chunks_1536
CREATE INDEX IF NOT EXISTS lecture_chunks_1536_embedding_hnsw_idx 
ON lecture_chunks_1536 USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS lecture_chunks_1536_metadata_idx ON lecture_chunks_1536 USING gin (metadata);
CREATE INDEX IF NOT EXISTS lecture_chunks_1536_source_idx ON lecture_chunks_1536(source_file);
CREATE INDEX IF NOT EXISTS lecture_chunks_1536_created_at_idx ON lecture_chunks_1536(created_at DESC);

-- Индексы для lecture_chunks_3072 
-- ВНИМАНИЕ: pgvector не поддерживает индексы для >2000 dimensions
-- Векторный поиск будет использовать sequential scan (медленнее, но работает)
CREATE INDEX IF NOT EXISTS lecture_chunks_3072_metadata_idx ON lecture_chunks_3072 USING gin (metadata);
CREATE INDEX IF NOT EXISTS lecture_chunks_3072_source_idx ON lecture_chunks_3072(source_file);
CREATE INDEX IF NOT EXISTS lecture_chunks_3072_created_at_idx ON lecture_chunks_3072(created_at DESC);

-- ==========================================
-- Функции для работы с векторным поиском
-- ==========================================

-- Функции для косинусного поиска похожих чанков (для каждой размерности)

CREATE OR REPLACE FUNCTION search_similar_chunks_384(
    query_embedding vector(384),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.0
)
RETURNS TABLE (id INTEGER, text TEXT, similarity FLOAT, metadata JSONB, source_file VARCHAR, chunk_index INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT lc.id, lc.text, 1 - (lc.embedding <=> query_embedding) AS similarity,
           lc.metadata, lc.source_file, lc.chunk_index
    FROM lecture_chunks_384 lc
    WHERE lc.embedding IS NOT NULL AND (1 - (lc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY lc.embedding <=> query_embedding LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_similar_chunks_768(
    query_embedding vector(768),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.0
)
RETURNS TABLE (id INTEGER, text TEXT, similarity FLOAT, metadata JSONB, source_file VARCHAR, chunk_index INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT lc.id, lc.text, 1 - (lc.embedding <=> query_embedding) AS similarity,
           lc.metadata, lc.source_file, lc.chunk_index
    FROM lecture_chunks_768 lc
    WHERE lc.embedding IS NOT NULL AND (1 - (lc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY lc.embedding <=> query_embedding LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_similar_chunks_1024(
    query_embedding vector(1024),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.0
)
RETURNS TABLE (id INTEGER, text TEXT, similarity FLOAT, metadata JSONB, source_file VARCHAR, chunk_index INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT lc.id, lc.text, 1 - (lc.embedding <=> query_embedding) AS similarity,
           lc.metadata, lc.source_file, lc.chunk_index
    FROM lecture_chunks_1024 lc
    WHERE lc.embedding IS NOT NULL AND (1 - (lc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY lc.embedding <=> query_embedding LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_similar_chunks_1536(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.0
)
RETURNS TABLE (id INTEGER, text TEXT, similarity FLOAT, metadata JSONB, source_file VARCHAR, chunk_index INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT lc.id, lc.text, 1 - (lc.embedding <=> query_embedding) AS similarity,
           lc.metadata, lc.source_file, lc.chunk_index
    FROM lecture_chunks_1536 lc
    WHERE lc.embedding IS NOT NULL AND (1 - (lc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY lc.embedding <=> query_embedding LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_similar_chunks_3072(
    query_embedding vector(3072),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.0
)
RETURNS TABLE (id INTEGER, text TEXT, similarity FLOAT, metadata JSONB, source_file VARCHAR, chunk_index INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT lc.id, lc.text, 1 - (lc.embedding <=> query_embedding) AS similarity,
           lc.metadata, lc.source_file, lc.chunk_index
    FROM lecture_chunks_3072 lc
    WHERE lc.embedding IS NOT NULL AND (1 - (lc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY lc.embedding <=> query_embedding LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Алиас для обратной совместимости (использует 384)
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(384),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.0
)
RETURNS TABLE (id INTEGER, text TEXT, similarity FLOAT, metadata JSONB, source_file VARCHAR, chunk_index INTEGER) AS $$
BEGIN
    RETURN QUERY SELECT * FROM search_similar_chunks_384(query_embedding, match_count, similarity_threshold);
END;
$$ LANGUAGE plpgsql;

-- Функция для обновления временной метки
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_lecture_chunks_384_updated_at ON lecture_chunks_384;
CREATE TRIGGER update_lecture_chunks_384_updated_at BEFORE UPDATE ON lecture_chunks_384
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_lecture_chunks_768_updated_at ON lecture_chunks_768;
CREATE TRIGGER update_lecture_chunks_768_updated_at BEFORE UPDATE ON lecture_chunks_768
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_lecture_chunks_1024_updated_at ON lecture_chunks_1024;
CREATE TRIGGER update_lecture_chunks_1024_updated_at BEFORE UPDATE ON lecture_chunks_1024
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_lecture_chunks_1536_updated_at ON lecture_chunks_1536;
CREATE TRIGGER update_lecture_chunks_1536_updated_at BEFORE UPDATE ON lecture_chunks_1536
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_lecture_chunks_3072_updated_at ON lecture_chunks_3072;
CREATE TRIGGER update_lecture_chunks_3072_updated_at BEFORE UPDATE ON lecture_chunks_3072
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Представления для аналитики
-- ==========================================

-- Статистика по чанкам (объединенная для всех таблиц)
CREATE OR REPLACE VIEW lecture_chunks_stats AS
SELECT 
    '384' as dimension,
    COUNT(*) as total_chunks,
    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as chunks_with_embeddings,
    COUNT(DISTINCT source_file) as unique_files,
    AVG(content_length) as avg_chunk_length,
    MIN(created_at) as first_chunk_date,
    MAX(created_at) as last_chunk_date
FROM lecture_chunks_384
UNION ALL
SELECT 
    '768', COUNT(*), COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END),
    COUNT(DISTINCT source_file), AVG(content_length), MIN(created_at), MAX(created_at)
FROM lecture_chunks_768
UNION ALL
SELECT 
    '1024', COUNT(*), COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END),
    COUNT(DISTINCT source_file), AVG(content_length), MIN(created_at), MAX(created_at)
FROM lecture_chunks_1024
UNION ALL
SELECT 
    '1536', COUNT(*), COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END),
    COUNT(DISTINCT source_file), AVG(content_length), MIN(created_at), MAX(created_at)
FROM lecture_chunks_1536
UNION ALL
SELECT 
    '3072', COUNT(*), COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END),
    COUNT(DISTINCT source_file), AVG(content_length), MIN(created_at), MAX(created_at)
FROM lecture_chunks_3072;

-- ==========================================
-- Функции для очистки данных (для тестов)
-- ==========================================

CREATE OR REPLACE FUNCTION clear_all_chunks()
RETURNS void AS $$
BEGIN
    TRUNCATE TABLE lecture_chunks_384 RESTART IDENTITY CASCADE;
    TRUNCATE TABLE lecture_chunks_768 RESTART IDENTITY CASCADE;
    TRUNCATE TABLE lecture_chunks_1024 RESTART IDENTITY CASCADE;
    TRUNCATE TABLE lecture_chunks_1536 RESTART IDENTITY CASCADE;
    TRUNCATE TABLE lecture_chunks_3072 RESTART IDENTITY CASCADE;
    RAISE NOTICE 'All chunks have been deleted from all tables';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION clear_chunks_384() RETURNS void AS $$
BEGIN TRUNCATE TABLE lecture_chunks_384 RESTART IDENTITY CASCADE; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION clear_chunks_768() RETURNS void AS $$
BEGIN TRUNCATE TABLE lecture_chunks_768 RESTART IDENTITY CASCADE; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION clear_chunks_1024() RETURNS void AS $$
BEGIN TRUNCATE TABLE lecture_chunks_1024 RESTART IDENTITY CASCADE; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION clear_chunks_1536() RETURNS void AS $$
BEGIN TRUNCATE TABLE lecture_chunks_1536 RESTART IDENTITY CASCADE; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION clear_chunks_3072() RETURNS void AS $$
BEGIN TRUNCATE TABLE lecture_chunks_3072 RESTART IDENTITY CASCADE; END; $$ LANGUAGE plpgsql;

-- ==========================================
-- Примеры использования
-- ==========================================

/*
-- Просмотр статистики:
SELECT * FROM lecture_chunks_stats;

-- Поиск похожих чанков (выберите функцию по размерности):
SELECT * FROM search_similar_chunks_384('[0.1, 0.2, ...]'::vector(384), 5, 0.7);
SELECT * FROM search_similar_chunks_768('[0.1, 0.2, ...]'::vector(768), 5, 0.7);
SELECT * FROM search_similar_chunks_1024('[0.1, 0.2, ...]'::vector(1024), 5, 0.7);
SELECT * FROM search_similar_chunks_1536('[0.1, 0.2, ...]'::vector(1536), 5, 0.7);
SELECT * FROM search_similar_chunks_3072('[0.1, 0.2, ...]'::vector(3072), 5, 0.7);

-- Очистка:
SELECT clear_all_chunks();       -- Все таблицы
SELECT clear_chunks_384();       -- Только 384
SELECT clear_chunks_3072();      -- Только 3072

-- Поиск по метаданным (пример для 384):
SELECT * FROM lecture_chunks_384 WHERE metadata->>'chapter' = 'Введение в RAG';

-- Полнотекстовый поиск (пример для 3072):
SELECT id, source_file, chunk_index, LEFT(text, 100) as preview
FROM lecture_chunks_3072 WHERE text ILIKE '%векторный поиск%' ORDER BY chunk_index;
*/

-- Вывод информации о настройке
DO $$
BEGIN
    RAISE NOTICE '✅ База данных lection7 успешно инициализирована';
    RAISE NOTICE '📊 Создано расширений: vector';
    RAISE NOTICE '📋 Создано таблиц: lecture_chunks_384, lecture_chunks_768, lecture_chunks_1024, lecture_chunks_1536, lecture_chunks_3072';
    RAISE NOTICE '🔍 Создано функций поиска для каждой размерности';
    RAISE NOTICE '📈 Создано представлений: lecture_chunks_stats';
    RAISE NOTICE '🎯 Поддерживаемые размерности: 384, 768, 1024, 1536, 3072';
END $$;


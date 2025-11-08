-- ==========================================
-- Инициализация БД для Graph RAG и n8n
-- ==========================================

-- Создание базы данных для n8n (если не существует)
SELECT 'CREATE DATABASE n8n_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n_db')\gexec

-- Подключаемся к основной БД graphrag для настройки RAG
\c graphrag

-- Создание расширений
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS age;

-- Загрузка AGE в путь поиска
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Создание графа для хранения знаний
SELECT create_graph('knowledge_graph');

-- ==========================================
-- Таблицы для RAG системы
-- ==========================================

-- Таблица для хранения документов с эмбеддингами
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(768), -- размер зависит от модели (по умолчанию 768 для nomic-embed)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индекс для векторного поиска (HNSW - быстрый приближенный поиск)
CREATE INDEX IF NOT EXISTS documents_embedding_idx 
ON documents USING hnsw (embedding vector_cosine_ops);

-- Индекс для поиска по метаданным
CREATE INDEX IF NOT EXISTS documents_metadata_idx 
ON documents USING gin (metadata);

-- Индекс для временных меток
CREATE INDEX IF NOT EXISTS documents_created_at_idx 
ON documents(created_at DESC);

-- ==========================================
-- Таблица для связи документов с графовыми узлами
-- ==========================================

CREATE TABLE IF NOT EXISTS document_nodes (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    node_id BIGINT NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, node_id)
);

CREATE INDEX IF NOT EXISTS document_nodes_doc_id_idx ON document_nodes(document_id);
CREATE INDEX IF NOT EXISTS document_nodes_node_id_idx ON document_nodes(node_id);
CREATE INDEX IF NOT EXISTS document_nodes_type_idx ON document_nodes(node_type);

-- ==========================================
-- Функции для работы с векторным поиском
-- ==========================================

-- Функция для косинусного поиска похожих документов
CREATE OR REPLACE FUNCTION search_similar_documents(
    query_embedding vector(768),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.0
)
RETURNS TABLE (
    id INTEGER,
    content TEXT,
    similarity FLOAT,
    metadata JSONB,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.content,
        1 - (d.embedding <=> query_embedding) AS similarity,
        d.metadata,
        d.created_at
    FROM documents d
    WHERE d.embedding IS NOT NULL
      AND (1 - (d.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
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

-- Триггер для автоматического обновления updated_at
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Вспомогательные представления
-- ==========================================

-- Представление для быстрого просмотра статистики
CREATE OR REPLACE VIEW documents_stats AS
SELECT 
    COUNT(*) as total_documents,
    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as documents_with_embeddings,
    COUNT(DISTINCT metadata->>'source') as unique_sources,
    MIN(created_at) as first_document_date,
    MAX(created_at) as last_document_date
FROM documents;

-- ==========================================
-- Примеры использования (закомментированы)
-- ==========================================

/*
-- Добавление документа с эмбеддингом:
INSERT INTO documents (content, embedding, metadata)
VALUES (
    'Это тестовый документ',
    '[0.1, 0.2, 0.3, ...]'::vector(768),
    '{"source": "test", "author": "system"}'::jsonb
);

-- Поиск похожих документов:
SELECT * FROM search_similar_documents(
    '[0.1, 0.2, 0.3, ...]'::vector(768),
    5,
    0.7
);

-- Создание узла в графе через AGE:
SELECT * FROM cypher('knowledge_graph', $$
    CREATE (d:Document {id: 1, title: 'Test Document'})
    RETURN d
$$) as (node agtype);

-- Поиск узлов в графе:
SELECT * FROM cypher('knowledge_graph', $$
    MATCH (d:Document)
    RETURN d
    LIMIT 10
$$) as (node agtype);
*/

-- Вывод информации о настройке
DO $$
BEGIN
    RAISE NOTICE '✅ База данных graphrag успешно инициализирована';
    RAISE NOTICE '📊 Создано расширений: vector, age';
    RAISE NOTICE '🕸️ Создан граф: knowledge_graph';
    RAISE NOTICE '📋 Создано таблиц: documents, document_nodes';
    RAISE NOTICE '🔍 Создано функций: search_similar_documents';
    RAISE NOTICE '📈 Создано представлений: documents_stats';
END $$;


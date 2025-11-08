import os
import asyncio
import json
from typing import List, Dict, Optional, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)


class GraphRAG:
    """
    Класс для работы с графовой системой RAG
    Использует PostgreSQL + pgvector для векторного поиска
    и Apache AGE для графовых связей
    """
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.lmstudio_url = os.getenv("LMSTUDIO_BASE_URL", "http://host.docker.internal:1234/v1")
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
        self.llm_model_name = os.getenv("LLM_MODEL", "llama-3.2-3b-instruct")
        self.embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
        
        self.engine = None
        self.Session = None
        
        # Инициализация OpenAI клиента для работы с LMStudio
        self.client = AsyncOpenAI(
            base_url=self.lmstudio_url,
            api_key="lm-studio"  # LMStudio не требует реальный API ключ
        )
        
        logger.info(f"GraphRAG инициализирован:")
        logger.info(f"  - LMStudio URL: {self.lmstudio_url}")
        logger.info(f"  - Embedding модель: {self.embedding_model_name}")
        logger.info(f"  - LLM модель: {self.llm_model_name}")
        logger.info(f"  - Размерность эмбеддингов: {self.embedding_dimensions}")
    
    async def initialize(self):
        """Инициализация подключений и проверка доступности сервисов"""
        try:
            # Подключение к БД
            logger.info("🔄 Подключение к PostgreSQL...")
            self.engine = create_engine(
                self.db_url,
                poolclass=NullPool,
                echo=False
            )
            self.Session = sessionmaker(bind=self.engine)
            
            # Проверка подключения к БД
            if await self.check_db_connection():
                logger.info("✅ Подключение к PostgreSQL установлено")
            else:
                raise Exception("Не удалось подключиться к PostgreSQL")
            
            # Проверка подключения к LMStudio
            logger.info("🔄 Проверка подключения к LMStudio...")
            await self._check_lmstudio_connection()
            
            logger.info("✅ Инициализация GraphRAG завершена успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации: {e}")
            raise
    
    async def _check_lmstudio_connection(self):
        """Проверка подключения к LMStudio и доступности моделей"""
        try:
            models = await self.client.models.list()
            available_models = [m.id for m in models.data]
            logger.info(f"✅ LMStudio подключен. Доступные модели: {available_models}")
            
            if not available_models:
                logger.warning("⚠️ В LMStudio не загружено ни одной модели!")
                logger.warning("   Пожалуйста, загрузите модели в LMStudio перед использованием")
            
        except Exception as e:
            logger.error(f"⚠️ Ошибка подключения к LMStudio: {e}")
            logger.warning("   Убедитесь, что:")
            logger.warning("   1. LMStudio запущен на http://127.0.0.1:1234")
            logger.warning("   2. В настройках LMStudio включены CORS и Network Access")
            logger.warning("   3. Загружена хотя бы одна модель")
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Получение эмбеддинга через LMStudio"""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model_name,
                input=text
            )
            embedding = response.data[0].embedding
            
            # Проверка размерности
            if len(embedding) != self.embedding_dimensions:
                logger.warning(
                    f"⚠️ Размер эмбеддинга ({len(embedding)}) не совпадает с ожидаемым ({self.embedding_dimensions})"
                )
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения эмбеддинга: {e}")
            raise Exception(f"Не удалось получить эмбеддинг: {str(e)}")
    
    async def ingest_document(self, content: str, metadata: Optional[Dict] = None) -> int:
        """
        Добавление документа в базу знаний
        
        Args:
            content: Текстовое содержимое документа
            metadata: Дополнительные метаданные
            
        Returns:
            ID добавленного документа
        """
        session = self.Session()
        try:
            # Получение эмбеддинга через LMStudio
            logger.info("🔄 Генерация эмбеддинга...")
            embedding = await self._get_embedding(content)
            
            # Подготовка метаданных
            if metadata is None:
                metadata = {}
            
            # Сохранение документа
            logger.info("🔄 Сохранение документа в БД...")
            result = session.execute(
                text(f"""
                    INSERT INTO documents (content, embedding, metadata)
                    VALUES (:content, :embedding::vector({self.embedding_dimensions}), :metadata::jsonb)
                    RETURNING id
                """),
                {
                    "content": content,
                    "embedding": str(embedding),
                    "metadata": json.dumps(metadata)
                }
            )
            doc_id = result.fetchone()[0]
            
            # Создание узлов в графе
            logger.info("🔄 Создание узлов в графе...")
            await self._create_graph_nodes(session, doc_id, content, metadata)
            
            session.commit()
            logger.info(f"✅ Документ успешно добавлен с ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка при добавлении документа: {e}")
            raise
        finally:
            session.close()
    
    async def _create_graph_nodes(self, session, doc_id: int, content: str, metadata: Dict):
        """Создание узлов и связей в графе Apache AGE"""
        try:
            # Создание базового узла документа
            preview = content[:200].replace("'", "''")  # Экранирование кавычек
            source = metadata.get('source', 'unknown').replace("'", "''")
            
            session.execute(
                text("""
                    SELECT * FROM cypher('knowledge_graph', $$
                        CREATE (d:Document {
                            doc_id: $doc_id,
                            preview: $preview,
                            source: $source,
                            length: $length
                        })
                        RETURN d
                    $$) as (node agtype);
                """),
                {
                    "doc_id": doc_id,
                    "preview": preview,
                    "source": source,
                    "length": len(content)
                }
            )
            
            # Сохранение связи документа с узлом
            session.execute(
                text("""
                    INSERT INTO document_nodes (document_id, node_id, node_type, properties)
                    VALUES (:doc_id, :node_id, 'Document', :props)
                """),
                {
                    "doc_id": doc_id,
                    "node_id": doc_id,  # Используем doc_id как node_id
                    "props": json.dumps({"source": metadata.get('source', 'unknown')})
                }
            )
            
            logger.info(f"✅ Графовый узел создан для документа {doc_id}")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при создании графового узла: {e}")
            # Не прерываем процесс, если граф не создался
    
    async def query(
        self,
        question: str,
        top_k: int = 5,
        use_graph: bool = True,
        similarity_threshold: float = 0.0
    ) -> Dict[str, Any]:
        """
        Выполнение запроса к базе знаний
        
        Args:
            question: Вопрос пользователя
            top_k: Количество документов для поиска
            use_graph: Использовать ли графовый контекст
            similarity_threshold: Минимальный порог схожести
            
        Returns:
            Словарь с ответом, источниками и графовым контекстом
        """
        session = self.Session()
        try:
            # Получение эмбеддинга вопроса
            logger.info("🔄 Генерация эмбеддинга запроса...")
            question_embedding = await self._get_embedding(question)
            
            # Векторный поиск похожих документов
            logger.info("🔍 Поиск похожих документов...")
            result = session.execute(
                text(f"""
                    SELECT 
                        id,
                        content,
                        metadata,
                        1 - (embedding <=> :embedding::vector({self.embedding_dimensions})) as similarity
                    FROM documents
                    WHERE embedding IS NOT NULL
                      AND (1 - (embedding <=> :embedding::vector({self.embedding_dimensions}))) >= :threshold
                    ORDER BY embedding <=> :embedding::vector({self.embedding_dimensions})
                    LIMIT :limit
                """),
                {
                    "embedding": str(question_embedding),
                    "limit": top_k,
                    "threshold": similarity_threshold
                }
            )
            
            documents = result.fetchall()
            logger.info(f"📊 Найдено {len(documents)} документов")
            
            if not documents:
                logger.warning("⚠️ Не найдено документов, удовлетворяющих критериям поиска")
                return {
                    "answer": "К сожалению, я не нашел релевантной информации в базе знаний для ответа на ваш вопрос.",
                    "sources": [],
                    "graph_context": None
                }
            
            # Получение графового контекста
            graph_context = None
            if use_graph and documents:
                logger.info("🕸️ Получение графового контекста...")
                graph_context = await self._get_graph_context(session, documents)
            
            # Формирование контекста для LLM
            context = self._build_context(documents, graph_context)
            
            # Генерация ответа
            logger.info("🤖 Генерация ответа через LLM...")
            answer = await self._generate_answer(question, context)
            
            return {
                "answer": answer,
                "sources": [
                    {
                        "id": doc[0],
                        "content": doc[1][:300],  # Первые 300 символов
                        "similarity": round(float(doc[3]), 4),
                        "metadata": doc[2]
                    }
                    for doc in documents
                ],
                "graph_context": graph_context
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке запроса: {e}")
            raise
        finally:
            session.close()
    
    async def _get_graph_context(self, session, documents) -> Optional[Dict]:
        """Получение графового контекста для найденных документов"""
        try:
            doc_ids = [doc[0] for doc in documents]
            
            # Cypher запрос для получения связанных узлов
            result = session.execute(
                text("""
                    SELECT * FROM cypher('knowledge_graph', $$
                        MATCH (d:Document)
                        WHERE d.doc_id IN $doc_ids
                        OPTIONAL MATCH (d)-[r]-(related)
                        RETURN d, type(r) as rel_type, related
                        LIMIT 20
                    $$) as (doc agtype, rel_type agtype, related agtype);
                """),
                {"doc_ids": doc_ids}
            )
            
            graph_data = result.fetchall()
            
            if not graph_data:
                return None
            
            return {
                "nodes_found": len(graph_data),
                "has_relationships": any(row[1] is not None for row in graph_data),
                "sample_nodes": len(graph_data)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при получении графового контекста: {e}")
            return None
    
    def _build_context(self, documents, graph_context: Optional[Dict]) -> str:
        """Формирование контекста для LLM из найденных документов"""
        context_parts = ["Контекст из базы знаний:\n"]
        
        for idx, doc in enumerate(documents, 1):
            similarity = float(doc[3])
            content = doc[1]
            metadata = doc[2] if doc[2] else {}
            
            source_info = f" (Источник: {metadata.get('source', 'неизвестно')})" if metadata else ""
            context_parts.append(
                f"\n[Документ {idx} | Релевантность: {similarity:.2%}]{source_info}:\n{content}\n"
            )
        
        if graph_context and graph_context.get('nodes_found', 0) > 0:
            context_parts.append(
                f"\n[Графовый контекст]: Найдено {graph_context['nodes_found']} связанных узлов в графе знаний."
            )
        
        return "\n".join(context_parts)
    
    async def _generate_answer(self, question: str, context: str) -> str:
        """Генерация ответа с помощью LLM через LMStudio"""
        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": """Ты - полезный ассистент для ответов на вопросы по базе знаний.
Отвечай ТОЛЬКО на основе предоставленного контекста.
Если в контексте нет информации для ответа, честно скажи об этом.
Отвечай на русском языке, четко и по существу."""
                    },
                    {
                        "role": "user",
                        "content": f"{context}\n\nВопрос: {question}\n\nОтвет:"
                    }
                ],
                temperature=0.7,
                max_tokens=800,
                top_p=0.9
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info("✅ Ответ успешно сгенерирован")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации ответа: {e}")
            return f"К сожалению, произошла ошибка при генерации ответа: {str(e)}"
    
    async def delete_document(self, doc_id: int):
        """Удаление документа из базы знаний"""
        session = self.Session()
        try:
            result = session.execute(
                text("DELETE FROM documents WHERE id = :id"),
                {"id": doc_id}
            )
            
            if result.rowcount == 0:
                raise Exception(f"Документ с ID {doc_id} не найден")
            
            session.commit()
            logger.info(f"✅ Документ {doc_id} удален")
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка при удалении документа: {e}")
            raise
        finally:
            session.close()
    
    async def get_documents_stats(self) -> Dict[str, Any]:
        """Получение статистики по документам"""
        session = self.Session()
        try:
            result = session.execute(text("SELECT * FROM documents_stats"))
            row = result.fetchone()
            
            if row:
                return {
                    "total_documents": row[0],
                    "documents_with_embeddings": row[1],
                    "unique_sources": row[2],
                    "first_document_date": str(row[3]) if row[3] else None,
                    "last_document_date": str(row[4]) if row[4] else None
                }
            else:
                return {
                    "total_documents": 0,
                    "documents_with_embeddings": 0,
                    "unique_sources": 0,
                    "first_document_date": None,
                    "last_document_date": None
                }
        finally:
            session.close()
    
    async def check_db_connection(self) -> bool:
        """Проверка подключения к базе данных"""
        try:
            session = self.Session()
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            return False
    
    async def check_llm_connection(self) -> bool:
        """Проверка подключения к LMStudio"""
        try:
            await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к LMStudio: {e}")
            return False


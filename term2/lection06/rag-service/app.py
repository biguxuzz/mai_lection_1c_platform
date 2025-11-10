from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from graph_rag import GraphRAG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация FastAPI приложения
app = FastAPI(
    title="Graph RAG API",
    description="API для работы с графовой системой RAG на базе PostgreSQL + pgvector + Apache AGE",
    version="1.0.0"
)

# Глобальный экземпляр GraphRAG
rag: Optional[GraphRAG] = None


# ==========================================
# Модели данных (Pydantic)
# ==========================================

class Document(BaseModel):
    """Модель для входящего документа"""
    content: str = Field(..., description="Текстовое содержимое документа", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные метаданные")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Машинное обучение - это раздел искусственного интеллекта...",
                "metadata": {"source": "учебник", "chapter": 1, "author": "Иванов И.И."}
            }
        }


class Query(BaseModel):
    """Модель для поискового запроса"""
    question: str = Field(..., description="Вопрос для поиска в базе знаний", min_length=1)
    top_k: int = Field(default=5, ge=1, le=20, description="Количество документов для возврата")
    use_graph: bool = Field(default=True, description="Использовать ли графовый контекст")
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Минимальный порог схожести")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Что такое машинное обучение?",
                "top_k": 5,
                "use_graph": True,
                "similarity_threshold": 0.7
            }
        }


class IngestResponse(BaseModel):
    """Ответ при добавлении документа"""
    document_id: int
    message: str
    embedding_dimension: int


class QueryResponse(BaseModel):
    """Ответ на поисковый запрос"""
    answer: str
    sources: List[Dict[str, Any]]
    graph_context: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Ответ проверки здоровья сервиса"""
    status: str
    database: bool
    llm: bool
    embedding_model: str
    llm_model: str


class ErrorResponse(BaseModel):
    """Модель ошибки"""
    detail: str


# ==========================================
# События жизненного цикла приложения
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    global rag
    try:
        logger.info("🚀 Запуск RAG Service...")
        rag = GraphRAG()
        await rag.initialize()
        logger.info("✅ RAG Service успешно инициализирован и готов к работе")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации RAG Service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка ресурсов при остановке"""
    logger.info("🛑 Остановка RAG Service...")


# ==========================================
# Эндпоинты API
# ==========================================

@app.get("/", tags=["Root"])
async def root():
    """Корневой эндпоинт с информацией о сервисе"""
    return {
        "service": "Graph RAG API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Проверка здоровья сервиса"
)
async def health_check():
    """
    Проверяет доступность всех компонентов системы:
    - База данных PostgreSQL
    - LMStudio (LLM и embeddings)
    """
    try:
        db_status = await rag.check_db_connection()
        llm_status = await rag.check_llm_connection()
        
        status = "healthy" if (db_status and llm_status) else "degraded"
        
        return HealthResponse(
            status=status,
            database=db_status,
            llm=llm_status,
            embedding_model=rag.embedding_model_name,
            llm_model=rag.llm_model_name
        )
    except Exception as e:
        logger.error(f"Ошибка при проверке здоровья: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
    summary="Добавление документа в базу знаний"
)
async def ingest_document(doc: Document):
    """
    Добавляет новый документ в базу знаний:
    1. Генерирует эмбеддинг через LMStudio
    2. Сохраняет в PostgreSQL с pgvector
    3. Создает узлы в графе Apache AGE
    """
    try:
        logger.info(f"📥 Получен запрос на добавление документа (длина: {len(doc.content)} символов)")
        doc_id = await rag.ingest_document(doc.content, doc.metadata)
        logger.info(f"✅ Документ успешно добавлен с ID: {doc_id}")
        
        return IngestResponse(
            document_id=doc_id,
            message="Документ успешно добавлен в базу знаний",
            embedding_dimension=rag.embedding_dimensions
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении документа: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при добавлении документа: {str(e)}"
        )


@app.post(
    "/query",
    response_model=QueryResponse,
    tags=["Search"],
    summary="Поиск в базе знаний"
)
async def query_knowledge(query: Query):
    """
    Выполняет поиск в базе знаний:
    1. Векторный поиск похожих документов
    2. Опционально: получение графового контекста
    3. Генерация ответа через LLM
    """
    try:
        logger.info(f"🔍 Получен запрос: '{query.question[:50]}...'")
        result = await rag.query(
            query.question,
            top_k=query.top_k,
            use_graph=query.use_graph,
            similarity_threshold=query.similarity_threshold
        )
        logger.info(f"✅ Запрос обработан, найдено {len(result['sources'])} документов")
        
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке запроса: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке запроса: {str(e)}"
        )


@app.delete(
    "/documents/{doc_id}",
    tags=["Documents"],
    summary="Удаление документа"
)
async def delete_document(doc_id: int):
    """
    Удаляет документ из базы знаний по ID
    """
    try:
        logger.info(f"🗑️ Запрос на удаление документа ID: {doc_id}")
        await rag.delete_document(doc_id)
        logger.info(f"✅ Документ {doc_id} успешно удален")
        
        return {"message": f"Документ {doc_id} успешно удален"}
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении документа: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении документа: {str(e)}"
        )


@app.get(
    "/documents/stats",
    tags=["Documents"],
    summary="Статистика по документам"
)
async def get_documents_stats():
    """
    Возвращает статистику по документам в базе знаний
    """
    try:
        stats = await rag.get_documents_stats()
        return stats
    except Exception as e:
        logger.error(f"❌ Ошибка при получении статистики: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении статистики: {str(e)}"
        )


# ==========================================
# Обработка ошибок
# ==========================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений"""
    logger.error(f"Необработанное исключение: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера"}
    )


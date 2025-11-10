"""
LightRAG Service - сервис для работы с LightRAG фреймворком
Предоставляет API для индексации и поиска документов с использованием LightRAG
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import httpx
from lightrag import LightRAG, QueryParam


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # LM Studio настройки
    lmstudio_base_url: str = Field(
        default="http://host.docker.internal:1234/v1",
        description="Base URL для LM Studio API"
    )
    lmstudio_api_key: str = Field(
        default="lm-studio",
        description="API ключ для LM Studio"
    )
    
    # Модели
    llm_model: str = Field(
        default="llama-3.2-3b-instruct",
        description="Модель для генерации текста"
    )
    embedding_model: str = Field(
        default="text-embedding-nomic-embed-text-v1.5",
        description="Модель для эмбеддингов"
    )
    
    # Директории
    working_dir: str = Field(
        default="./data",
        description="Рабочая директория для хранения индекса"
    )
    
    # Параметры LightRAG
    max_token_size: int = Field(
        default=512,
        description="Максимальный размер токена для чанков"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


# Инициализация FastAPI приложения
app = FastAPI(
    title="LightRAG Service",
    description="Сервис для работы с LightRAG - легковесным фреймворком для RAG",
    version="1.0.0"
)


# Глобальная переменная для LightRAG экземпляра
lightrag_instance: Optional[LightRAG] = None


# Pydantic модели для API
class DocumentInput(BaseModel):
    """Модель для входных данных документа"""
    text: str = Field(..., description="Текст документа для индексации")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Метаданные документа"
    )


class QueryInput(BaseModel):
    """Модель для поискового запроса"""
    query: str = Field(..., description="Поисковый запрос")
    mode: str = Field(
        default="hybrid",
        description="Режим поиска: local, global, hybrid, naive"
    )
    top_k: int = Field(
        default=5,
        description="Количество возвращаемых результатов"
    )
    only_need_context: bool = Field(
        default=False,
        description="Возвращать только контекст без генерации ответа"
    )


class HealthResponse(BaseModel):
    """Модель ответа для health check"""
    status: str
    timestamp: str
    lightrag_initialized: bool


class InsertResponse(BaseModel):
    """Модель ответа при добавлении документа"""
    status: str
    message: str
    document_length: int


class QueryResponse(BaseModel):
    """Модель ответа на поисковый запрос"""
    query: str
    mode: str
    response: str
    context: Optional[str] = None


async def get_openai_async_client():
    """Получение асинхронного клиента OpenAI для работы с LM Studio"""
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(
        api_key=settings.lmstudio_api_key,
        base_url=settings.lmstudio_base_url
    )
    return client


class EmbeddingFunc:
    """Обертка для функции эмбеддинга с атрибутом embedding_dim"""
    
    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim
    
    async def __call__(self, texts: List[str]) -> List[List[float]]:
        """
        Функция для получения эмбеддингов через LM Studio
        
        Args:
            texts: Список текстов для эмбеддинга
            
        Returns:
            Список векторов эмбеддингов
        """
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=settings.lmstudio_api_key,
            base_url=settings.lmstudio_base_url
        )
        
        try:
            response = await client.embeddings.create(
                model=settings.embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Ошибка при получении эмбеддингов: {e}")
            raise


async def lmstudio_completion_func(
    prompt: str,
    system_prompt: Optional[str] = None,
    **kwargs
) -> str:
    """
    Функция для генерации текста через LM Studio
    
    Args:
        prompt: Текст промпта
        system_prompt: Системный промпт
        **kwargs: Дополнительные параметры
        
    Returns:
        Сгенерированный текст
    """
    client = await get_openai_async_client()
    
    messages = []
    if system_prompt:
        # Добавляем строгое требование извлекать только из предоставленного текста
        # Это критично для предотвращения галлюцинаций при извлечении сущностей и отношений
        strict_system_prompt = system_prompt
        # Проверяем, является ли это промптом для извлечения информации
        prompt_lower = system_prompt.lower()
        if any(keyword in prompt_lower for keyword in ["extract", "entity", "relation", "entity", "relationship", "knowledge"]):
            strict_system_prompt = (
                system_prompt + 
                "\n\nКРИТИЧЕСКИ ВАЖНО: " +
                "Извлекайте ТОЛЬКО информацию, которая ЯВНО и ДОСЛОВНО присутствует в предоставленном тексте. " +
                "НЕ используйте ваши знания из обучающих данных. " +
                "НЕ добавляйте информацию, которой нет в тексте. " +
                "НЕ придумывайте факты, события или отношения. " +
                "Если информация отсутствует в тексте, НЕ извлекайте её."
            )
        messages.append({"role": "system", "content": strict_system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Настройки для уменьшения галлюцинаций при извлечении сущностей и отношений
    # Температура 0.0 обеспечивает максимальную детерминированность и уменьшает галлюцинации
    # Top-p также ограничивает разнообразие ответов
    generation_params = {
        "temperature": kwargs.get("temperature", 0.0),  # Температура 0.0 для максимально строгого извлечения
        "top_p": kwargs.get("top_p", 0.95),  # Ограничение разнообразия
        "max_tokens": kwargs.get("max_tokens", 2048),
    }
    # Объединяем параметры, kwargs имеет приоритет
    generation_params.update({k: v for k, v in kwargs.items() if k not in generation_params})
    
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            **generation_params
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка при генерации текста: {e}")
        raise


def initialize_lightrag():
    """Инициализация LightRAG экземпляра"""
    global lightrag_instance
    
    try:
        # Создание рабочей директории если её нет
        working_dir = Path(settings.working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Инициализация LightRAG с рабочей директорией: {working_dir}")
        logger.info(f"LM Studio URL: {settings.lmstudio_base_url}")
        logger.info(f"LLM модель: {settings.llm_model}")
        logger.info(f"Embedding модель: {settings.embedding_model}")
        
        # Создаем экземпляр функции эмбеддинга с размерностью
        embedding_func = EmbeddingFunc(embedding_dim=768)
        
        lightrag_instance = LightRAG(
            working_dir=str(working_dir),
            llm_model_func=lmstudio_completion_func,
            embedding_func=embedding_func
        )
        
        logger.info("LightRAG успешно инициализирован")
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации LightRAG: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Событие при запуске приложения"""
    logger.info("Запуск LightRAG Service...")
    initialize_lightrag()
    logger.info("LightRAG Service успешно запущен")


@app.on_event("shutdown")
async def shutdown_event():
    """Событие при остановке приложения"""
    logger.info("Остановка LightRAG Service...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Статус сервиса
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        lightrag_initialized=lightrag_instance is not None
    )


@app.post("/insert", response_model=InsertResponse)
async def insert_document(document: DocumentInput):
    """
    Индексация документа в LightRAG
    
    Args:
        document: Документ для индексации
        
    Returns:
        Статус операции
    """
    if lightrag_instance is None:
        raise HTTPException(
            status_code=503,
            detail="LightRAG не инициализирован"
        )
    
    try:
        # Очистка и валидация текста документа
        text_to_index = document.text.strip()
        
        if not text_to_index:
            raise HTTPException(
                status_code=400,
                detail="Текст документа не может быть пустым"
            )
        
        logger.info(f"Индексация документа, длина: {len(text_to_index)} символов")
        logger.debug(f"Первые 500 символов документа: {text_to_index[:500]}")
        
        # Добавление документа в LightRAG
        # Передаем только очищенный текст документа без дополнительных данных
        # LightRAG сам обработает текст и извлечет сущности и отношения
        await lightrag_instance.ainsert(text_to_index)
        
        logger.info("Документ успешно проиндексирован")
        
        return InsertResponse(
            status="success",
            message="Документ успешно проиндексирован",
            document_length=len(document.text)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при индексации документа: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при индексации документа: {str(e)}"
        )


@app.post("/query", response_model=QueryResponse)
async def query_documents(query_input: QueryInput):
    """
    Поиск по проиндексированным документам
    
    Args:
        query_input: Параметры поискового запроса
        
    Returns:
        Результаты поиска
    """
    if lightrag_instance is None:
        raise HTTPException(
            status_code=503,
            detail="LightRAG не инициализирован"
        )
    
    try:
        logger.info(f"Выполнение запроса: '{query_input.query}' в режиме {query_input.mode}")
        
        # Создание параметров запроса
        query_param = QueryParam(
            mode=query_input.mode,
            top_k=query_input.top_k,
            only_need_context=query_input.only_need_context
        )
        
        # Выполнение запроса
        response = await lightrag_instance.aquery(
            query_input.query,
            param=query_param
        )
        
        logger.info(f"Запрос успешно выполнен, длина ответа: {len(response)} символов")
        
        return QueryResponse(
            query=query_input.query,
            mode=query_input.mode,
            response=response,
            context=None  # LightRAG возвращает уже обработанный ответ
        )
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при выполнении запроса: {str(e)}"
        )


@app.post("/insert_batch")
async def insert_batch_documents(texts: List[str]):
    """
    Пакетная индексация документов
    
    Args:
        texts: Список текстов для индексации
        
    Returns:
        Статус операции
    """
    if lightrag_instance is None:
        raise HTTPException(
            status_code=503,
            detail="LightRAG не инициализирован"
        )
    
    try:
        logger.info(f"Пакетная индексация {len(texts)} документов")
        
        for i, text in enumerate(texts, 1):
            await lightrag_instance.ainsert(text)
            logger.info(f"Проиндексирован документ {i}/{len(texts)}")
        
        return {
            "status": "success",
            "message": f"Успешно проиндексировано {len(texts)} документов",
            "count": len(texts)
        }
        
    except Exception as e:
        logger.error(f"Ошибка при пакетной индексации: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при пакетной индексации: {str(e)}"
        )


@app.delete("/clear")
async def clear_index():
    """
    Очистка индекса LightRAG
    
    Returns:
        Статус операции
    """
    try:
        logger.info("Очистка индекса LightRAG")
        
        # Переинициализация LightRAG (это очистит индекс)
        initialize_lightrag()
        
        logger.info("Индекс успешно очищен")
        
        return {
            "status": "success",
            "message": "Индекс успешно очищен"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при очистке индекса: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при очистке индекса: {str(e)}"
        )


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "LightRAG Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "insert": "/insert",
            "query": "/query",
            "insert_batch": "/insert_batch",
            "clear": "/clear",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)


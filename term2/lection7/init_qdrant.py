"""
Скрипт инициализации Qdrant для Lection 7 - RAG Demo
Создает коллекции для хранения векторов документов (аналог init_lection7_db.sql)
"""
import os
import time
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)

def wait_for_qdrant(client, max_retries=30, delay=2):
    """Ожидание готовности Qdrant"""
    print("⏳ Ожидание готовности Qdrant...")
    for i in range(max_retries):
        try:
            collections = client.get_collections()
            print(f"✅ Qdrant готов! Найдено коллекций: {len(collections.collections)}")
            return True
        except Exception as e:
            print(f"   Попытка {i+1}/{max_retries}: {str(e)}")
            time.sleep(delay)
    return False

def init_qdrant():
    """Инициализация Qdrant коллекций"""
    
    # Подключение к Qdrant
    qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
    
    print("=" * 70)
    print("🚀 Инициализация Qdrant для Лекции 7 - RAG Demo")
    print("=" * 70)
    print(f"📡 Подключение к Qdrant: {qdrant_host}:{qdrant_port}")
    print()
    
    client = QdrantClient(host=qdrant_host, port=qdrant_port)
    
    # Ожидание готовности Qdrant
    if not wait_for_qdrant(client):
        print("❌ Не удалось подключиться к Qdrant")
        return False
    
    print()
    
    # Конфигурация коллекций (аналог таблиц в PostgreSQL)
    collections_config = {
        "lecture_chunks_384": {
            "description": "Чанки лекций с 384-мерными embeddings (text-embedding-multilingual-e5-small)",
            "vector_size": 384,
            "distance": Distance.COSINE
        },
        "lecture_chunks_768": {
            "description": "Чанки лекций с 768-мерными embeddings (multilingual-e5-large)",
            "vector_size": 768,
            "distance": Distance.COSINE
        },
        "lecture_chunks_1536": {
            "description": "Чанки лекций с 1536-мерными embeddings (OpenAI text-embedding-ada-002)",
            "vector_size": 1536,
            "distance": Distance.COSINE
        }
    }
    
    # Создание коллекций
    print("📊 Создание коллекций:")
    print()
    
    for collection_name, config in collections_config.items():
        try:
            # Проверка существования коллекции
            collections = client.get_collections()
            exists = any(c.name == collection_name for c in collections.collections)
            
            if exists:
                collection_info = client.get_collection(collection_name)
                print(f"ℹ️  Коллекция '{collection_name}' уже существует")
                print(f"   • Векторов: {collection_info.vectors_count}")
                print(f"   • Точек: {collection_info.points_count}")
                print()
            else:
                # Создание новой коллекции
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=config["vector_size"],
                        distance=config["distance"]
                    )
                )
                print(f"✅ Создана коллекция '{collection_name}'")
                print(f"   • Описание: {config['description']}")
                print(f"   • Размерность вектора: {config['vector_size']}")
                print(f"   • Метрика расстояния: {config['distance']}")
                print()
                
        except Exception as e:
            print(f"❌ Ошибка создания коллекции '{collection_name}': {str(e)}")
            return False
    
    print("=" * 70)
    print("✅ Инициализация Qdrant успешно завершена!")
    print("=" * 70)
    print()
    print("📚 Доступные коллекции:")
    collections = client.get_collections()
    for collection in collections.collections:
        try:
            info = client.get_collection(collection.name)
            print(f"   • {collection.name}")
            print(f"     - Векторов: {info.vectors_count}")
            print(f"     - Точек: {info.points_count}")
            print(f"     - Статус: {info.status}")
        except:
            print(f"   • {collection.name} (недоступна)")
    
    print()
    print("🔗 Qdrant endpoints:")
    print(f"   • REST API: http://{qdrant_host}:{qdrant_port}")
    print(f"   • Web UI: http://{qdrant_host}:{qdrant_port}/dashboard")
    print(f"   • gRPC: {qdrant_host}:6334")
    print()
    print("💡 Примеры использования:")
    print()
    print("   # Python:")
    print("   from qdrant_client import QdrantClient")
    print(f"   client = QdrantClient('{qdrant_host}', port={qdrant_port})")
    print("   collections = client.get_collections()")
    print()
    print("   # n8n - Qdrant Vector Store node:")
    print(f"   Host: qdrant")
    print(f"   Port: 6333")
    print(f"   Collection: lecture_chunks_384")
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = init_qdrant()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


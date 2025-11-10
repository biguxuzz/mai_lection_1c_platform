"""
Скрипт очистки Qdrant коллекций для Lection 7 - RAG Demo
Очищает все точки из указанных коллекций или удаляет коллекции полностью
"""
import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

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
            import time
            time.sleep(delay)
    return False

def clear_collection(client, collection_name, delete_collection=False):
    """Очистка коллекции: удаление всех точек или удаление коллекции"""
    try:
        # Проверка существования коллекции
        collections = client.get_collections()
        exists = any(c.name == collection_name for c in collections.collections)
        
        if not exists:
            print(f"⚠️  Коллекция '{collection_name}' не существует")
            return False
        
        collection_info = client.get_collection(collection_name)
        points_count = collection_info.points_count
        
        if points_count == 0:
            print(f"ℹ️  Коллекция '{collection_name}' уже пуста")
            if delete_collection:
                client.delete_collection(collection_name)
                print(f"✅ Коллекция '{collection_name}' удалена")
            return True
        
        if delete_collection:
            # Удаление коллекции полностью
            client.delete_collection(collection_name)
            print(f"✅ Коллекция '{collection_name}' удалена (было точек: {points_count})")
        else:
            # Очистка всех точек из коллекции
            # Способ 1: Удаление всех точек через scroll и delete
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=10000,
                with_payload=False,
                with_vectors=False
            )
            
            if scroll_result[0]:
                point_ids = [point.id for point in scroll_result[0]]
                # Удаление порциями по 1000 точек
                batch_size = 1000
                deleted = 0
                for i in range(0, len(point_ids), batch_size):
                    batch = point_ids[i:i + batch_size]
                    client.delete(
                        collection_name=collection_name,
                        points_selector=batch
                    )
                    deleted += len(batch)
                    print(f"   Удалено точек: {deleted}/{points_count}", end='\r')
                
                print(f"\n✅ Очищена коллекция '{collection_name}' (удалено точек: {points_count})")
            else:
                print(f"⚠️  Не удалось получить точки из коллекции '{collection_name}'")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при очистке коллекции '{collection_name}': {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def clear_qdrant(collection_names=None, delete_collections=False):
    """Очистка Qdrant коллекций"""
    
    # Подключение к Qdrant
    qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
    
    print("=" * 70)
    print("🧹 Очистка Qdrant коллекций для Лекции 7 - RAG Demo")
    print("=" * 70)
    print(f"📡 Подключение к Qdrant: {qdrant_host}:{qdrant_port}")
    print()
    
    client = QdrantClient(host=qdrant_host, port=qdrant_port)
    
    # Ожидание готовности Qdrant
    if not wait_for_qdrant(client):
        print("❌ Не удалось подключиться к Qdrant")
        return False
    
    print()
    
    # Если коллекции не указаны, используем стандартные
    if collection_names is None:
        collection_names = [
            "lecture_chunks_384",
            "lecture_chunks_768",
            "lecture_chunks_1536"
        ]
    
    print(f"📋 Коллекции для очистки: {', '.join(collection_names)}")
    print(f"🔧 Режим: {'Удаление коллекций' if delete_collections else 'Очистка точек'}")
    print()
    
    # Показать текущее состояние коллекций
    print("📊 Текущее состояние коллекций:")
    collections = client.get_collections()
    for collection in collections.collections:
        if collection.name in collection_names:
            try:
                info = client.get_collection(collection.name)
                print(f"   • {collection.name}: {info.points_count} точек")
            except:
                print(f"   • {collection.name}: недоступна")
    print()
    
    # Подтверждение
    action = "удаления" if delete_collections else "очистки"
    print(f"⚠️  ВНИМАНИЕ: Будет выполнена {action} указанных коллекций!")
    response = input("Продолжить? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y', 'да', 'д']:
        print("❌ Операция отменена")
        return False
    
    print()
    
    # Очистка коллекций
    success_count = 0
    for collection_name in collection_names:
        if clear_collection(client, collection_name, delete_collections):
            success_count += 1
        print()
    
    print("=" * 70)
    if success_count == len(collection_names):
        print("✅ Очистка успешно завершена!")
    else:
        print(f"⚠️  Очищено коллекций: {success_count}/{len(collection_names)}")
    print("=" * 70)
    print()
    
    # Показать итоговое состояние
    print("📚 Итоговое состояние коллекций:")
    collections = client.get_collections()
    for collection in collections.collections:
        if collection.name in collection_names:
            try:
                info = client.get_collection(collection.name)
                print(f"   • {collection.name}: {info.points_count} точек")
            except:
                print(f"   • {collection.name}: удалена")
    print()
    
    return success_count == len(collection_names)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Очистка Qdrant коллекций')
    parser.add_argument(
        '--collections',
        nargs='+',
        help='Имена коллекций для очистки (по умолчанию: все коллекции лекции 7)'
    )
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Удалить коллекции полностью (по умолчанию: только очистить точки)'
    )
    
    args = parser.parse_args()
    
    try:
        success = clear_qdrant(
            collection_names=args.collections,
            delete_collections=args.delete
        )
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Операция прервана пользователем")
        exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)










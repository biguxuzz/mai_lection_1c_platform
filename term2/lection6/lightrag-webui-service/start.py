#!/usr/bin/env python3
"""
Стартовый скрипт для LightRAG WebUI API
Запускает официальный LightRAG API сервер с WebUI
Включает проверку подключения к LMStudio и инициализацию базы данных
"""
import sys
import os
import time
from pathlib import Path

# Добавляем путь к LightRAG
sys.path.insert(0, "/app/lightrag")

def check_lmstudio_connection(max_retries=10, delay=2):
    """Проверка подключения к LMStudio"""
    import httpx
    
    lmstudio_host = os.getenv('LLM_BINDING_HOST', 'http://host.docker.internal:1234/v1')
    api_key = os.getenv('OPENAI_API_KEY', 'lm-studio')
    embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-qwen3-embedding-4b')
    
    print("=" * 60)
    print("🔍 Проверка подключения к LMStudio...")
    print(f"   URL: {lmstudio_host}")
    print(f"   Embedding модель: {embedding_model}")
    print("=" * 60)
    
    for attempt in range(1, max_retries + 1):
        try:
            # Тестируем генерацию эмбеддинга
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{lmstudio_host}/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": embedding_model,
                        "input": "test"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and len(data['data']) > 0:
                        embedding = data['data'][0].get('embedding', [])
                        if len(embedding) > 0:
                            print(f"✅ Подключение успешно! Размерность эмбеддинга: {len(embedding)}")
                            return True
                        else:
                            print(f"⚠️  Получен пустой эмбеддинг (попытка {attempt}/{max_retries})")
                    else:
                        print(f"⚠️  Неверный формат ответа (попытка {attempt}/{max_retries})")
                else:
                    print(f"⚠️  HTTP {response.status_code}: {response.text[:100]} (попытка {attempt}/{max_retries})")
                    
        except httpx.ConnectError as e:
            print(f"⚠️  Ошибка подключения: {e} (попытка {attempt}/{max_retries})")
        except Exception as e:
            print(f"⚠️  Ошибка: {e} (попытка {attempt}/{max_retries})")
        
        if attempt < max_retries:
            print(f"   Повтор через {delay} секунд...")
            time.sleep(delay)
    
    print("❌ Не удалось подключиться к LMStudio после всех попыток")
    print("   Убедитесь, что LMStudio запущен и модель доступна")
    return False


def cleanup_corrupted_db(working_dir):
    """Очистка поврежденной базы данных"""
    working_path = Path(working_dir)
    if not working_path.exists():
        return
    
    print("=" * 60)
    print("🔧 Проверка рабочей директории...")
    print(f"   Путь: {working_dir}")
    print("=" * 60)
    
    # Ищем файлы nano_vectordb
    db_files = list(working_path.glob("**/*.npy"))
    db_files.extend(working_path.glob("**/*.npz"))
    db_files.extend(working_path.glob("**/storage*"))
    
    if db_files:
        print(f"   Найдено файлов БД: {len(db_files)}")
        # Не удаляем автоматически, но предупреждаем
        print("   ⚠️  Если возникают ошибки, попробуйте очистить volume:")
        print(f"      docker volume rm lection6_lightrag_webui_data")
    else:
        print("   ✅ Рабочая директория чиста")


if __name__ == "__main__":
    import uvicorn
    from lightrag.api.lightrag_server import create_app
    from lightrag.api.config import global_args
    
    print("=" * 60)
    print("🚀 Starting official LightRAG API Server with WebUI")
    print("=" * 60)
    
    # Проверка подключения к LMStudio
    if not check_lmstudio_connection():
        print("\n❌ Не удалось подключиться к LMStudio")
        print("   Сервер не будет запущен. Проверьте настройки подключения.")
        sys.exit(1)
    
    # Проверка рабочей директории
    working_dir = os.getenv('WORKING_DIR', '/app/data')
    cleanup_corrupted_db(working_dir)
    
    print("\n" + "=" * 60)
    print("📋 Конфигурация сервера:")
    print(f"   📁 Working directory: {global_args.working_dir}")
    print(f"   🌐 Server URL: http://0.0.0.0:9621")
    print(f"   🔐 Auth Accounts: {os.getenv('AUTH_ACCOUNTS', 'N/A')}")
    print(f"   🔒 Auth Enabled: {os.getenv('DISABLE_AUTH', 'false') == 'false'}")
    print("=" * 60)
    print()
    
    # Создаем официальное приложение LightRAG API с WebUI используя global_args
    app = create_app(global_args)
    
    # Запуск сервера
    print("🚀 Запуск сервера...")
    uvicorn.run(app, host="0.0.0.0", port=9621)

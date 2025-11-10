#!/usr/bin/env python3
"""
Утилита для проверки размерности эмбеддингов модели
Определяет EMBEDDING_DIM для конкретной модели эмбеддингов
"""
import sys
import os
import argparse
import httpx
from typing import Optional


def check_embedding_dim(
    model_name: str,
    api_url: str = "http://localhost:1234/v1",
    api_key: str = "lm-studio",
    timeout: float = 30.0
) -> Optional[int]:
    """
    Проверяет размерность эмбеддингов для указанной модели
    
    Args:
        model_name: Имя модели эмбеддингов
        api_url: URL API (LMStudio или OpenAI совместимый)
        api_key: API ключ
        timeout: Таймаут запроса в секундах
        
    Returns:
        Размерность эмбеддинга или None в случае ошибки
    """
    print("=" * 70)
    print("🔍 Проверка размерности эмбеддингов")
    print("=" * 70)
    print(f"📡 API URL: {api_url}")
    print(f"🤖 Модель: {model_name}")
    print("=" * 70)
    print()
    
    try:
        with httpx.Client(timeout=timeout) as client:
            print("📤 Отправка запроса на генерацию эмбеддинга...")
            
            response = client.post(
                f"{api_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "input": "test"  # Тестовый текст
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Ошибка HTTP {response.status_code}")
                print(f"   Ответ: {response.text[:200]}")
                return None
            
            data = response.json()
            
            # Проверка структуры ответа
            if 'data' not in data:
                print("❌ Неверный формат ответа: отсутствует поле 'data'")
                print(f"   Ответ: {data}")
                return None
            
            if len(data['data']) == 0:
                print("❌ Пустой ответ: нет данных эмбеддинга")
                return None
            
            embedding = data['data'][0].get('embedding', [])
            
            if not embedding:
                print("❌ Пустой эмбеддинг в ответе")
                return None
            
            dim = len(embedding)
            
            print("✅ Успешно получен эмбеддинг!")
            print()
            print("=" * 70)
            print(f"📊 Размерность эмбеддинга: {dim}")
            print("=" * 70)
            print()
            print("💡 Используйте это значение для:")
            print(f"   EMBEDDING_DIM={dim}")
            print(f"   EMBEDDING_DIMENSIONS={dim}")
            print()
            
            # Дополнительная информация
            if 'usage' in data:
                usage = data['usage']
                print("📈 Статистика использования:")
                if 'prompt_tokens' in usage:
                    print(f"   Prompt tokens: {usage['prompt_tokens']}")
                if 'total_tokens' in usage:
                    print(f"   Total tokens: {usage['total_tokens']}")
                print()
            
            return dim
            
    except httpx.ConnectError as e:
        print(f"❌ Ошибка подключения: {e}")
        print()
        print("💡 Убедитесь, что:")
        print("   - LMStudio запущен")
        print("   - Модель эмбеддингов загружена")
        print("   - API доступен по указанному URL")
        return None
        
    except httpx.TimeoutException:
        print(f"❌ Таймаут запроса (>{timeout} сек)")
        print("   Модель может быть слишком медленной или недоступной")
        return None
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_available_models(api_url: str = "http://localhost:1234/v1") -> None:
    """
    Пытается получить список доступных моделей
    """
    print("=" * 70)
    print("📋 Попытка получить список доступных моделей")
    print("=" * 70)
    print()
    
    try:
        with httpx.Client(timeout=10.0) as client:
            # Пробуем разные эндпоинты
            endpoints = [
                "/models",
                "/v1/models",
            ]
            
            for endpoint in endpoints:
                try:
                    response = client.get(f"{api_url}{endpoint}")
                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data:
                            models = data['data']
                            print(f"✅ Найдено моделей: {len(models)}")
                            print()
                            for model in models[:10]:  # Показываем первые 10
                                model_id = model.get('id', 'unknown')
                                print(f"   • {model_id}")
                            if len(models) > 10:
                                print(f"   ... и еще {len(models) - 10} моделей")
                            print()
                            return
                except:
                    continue
            
            print("⚠️  Не удалось получить список моделей")
            print("   Проверьте документацию вашего API")
            
    except Exception as e:
        print(f"⚠️  Ошибка при получении списка моделей: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Проверка размерности эмбеддингов для модели",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Проверка конкретной модели
  python check_embedding_dim.py text-embedding-qwen3-embedding-4b

  # С указанием URL API
  python check_embedding_dim.py text-embedding-qwen3-embedding-4b \\
    --api-url http://host.docker.internal:1234/v1

  # С таймаутом
  python check_embedding_dim.py text-embedding-qwen3-embedding-4b \\
    --timeout 60

  # Получить список доступных моделей
  python check_embedding_dim.py --list-models
        """
    )
    
    parser.add_argument(
        'model',
        nargs='?',
        help='Имя модели эмбеддингов (например: text-embedding-qwen3-embedding-4b)'
    )
    
    parser.add_argument(
        '--api-url',
        default=os.getenv('EMBEDDING_BINDING_HOST', 'http://localhost:1234/v1'),
        help='URL API (по умолчанию: http://localhost:1234/v1)'
    )
    
    parser.add_argument(
        '--api-key',
        default=os.getenv('OPENAI_API_KEY', 'lm-studio'),
        help='API ключ (по умолчанию: lm-studio)'
    )
    
    parser.add_argument(
        '--timeout',
        type=float,
        default=30.0,
        help='Таймаут запроса в секундах (по умолчанию: 30)'
    )
    
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='Показать список доступных моделей'
    )
    
    args = parser.parse_args()
    
    if args.list_models:
        list_available_models(args.api_url)
        return
    
    if not args.model:
        parser.print_help()
        print()
        print("❌ Ошибка: необходимо указать имя модели")
        print()
        print("Пример:")
        print("  python check_embedding_dim.py text-embedding-qwen3-embedding-4b")
        sys.exit(1)
    
    dim = check_embedding_dim(
        model_name=args.model,
        api_url=args.api_url,
        api_key=args.api_key,
        timeout=args.timeout
    )
    
    if dim is None:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()


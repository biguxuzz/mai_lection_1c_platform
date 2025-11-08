#!/bin/bash
# Простая утилита для проверки размерности эмбеддингов через curl

MODEL="${1:-text-embedding-qwen3-embedding-4b}"
API_URL="${2:-http://localhost:1234/v1}"
API_KEY="${3:-lm-studio}"

echo "============================================================"
echo "🔍 Проверка размерности эмбеддингов"
echo "============================================================"
echo "📡 API URL: $API_URL"
echo "🤖 Модель: $MODEL"
echo "============================================================"
echo ""

# Проверка наличия curl
if ! command -v curl &> /dev/null; then
    echo "❌ Ошибка: curl не установлен"
    echo "   Установите curl или используйте Python версию: python check_embedding_dim.py"
    exit 1
fi

# Проверка наличия jq (опционально)
HAS_JQ=false
if command -v jq &> /dev/null; then
    HAS_JQ=true
fi

echo "📤 Отправка запроса на генерацию эмбеддинга..."
echo ""

# Выполнение запроса
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_URL/embeddings" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d "{
        \"model\": \"$MODEL\",
        \"input\": \"test\"
    }")

# Разделение ответа и кода статуса
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo "❌ Ошибка HTTP $HTTP_CODE"
    echo ""
    echo "Ответ сервера:"
    echo "$BODY" | head -c 200
    echo ""
    echo ""
    echo "💡 Убедитесь, что:"
    echo "   - LMStudio запущен"
    echo "   - Модель эмбеддингов загружена"
    echo "   - API доступен по указанному URL"
    exit 1
fi

# Извлечение размерности
if [ "$HAS_JQ" = true ]; then
    DIM=$(echo "$BODY" | jq -r '.data[0].embedding | length' 2>/dev/null)
    
    if [ -z "$DIM" ] || [ "$DIM" = "null" ]; then
        echo "❌ Не удалось извлечь размерность из ответа"
        echo ""
        echo "Ответ сервера:"
        echo "$BODY" | head -c 500
        echo ""
        exit 1
    fi
else
    # Без jq - используем Python для парсинга
    if command -v python3 &> /dev/null; then
        DIM=$(echo "$BODY" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data['data'][0]['embedding']))" 2>/dev/null)
    elif command -v python &> /dev/null; then
        DIM=$(echo "$BODY" | python -c "import sys, json; data = json.load(sys.stdin); print(len(data['data'][0]['embedding']))" 2>/dev/null)
    else
        echo "❌ Для парсинга ответа требуется jq или Python"
        echo ""
        echo "Установите jq:"
        echo "   Windows: choco install jq"
        echo "   Linux: sudo apt-get install jq"
        echo "   Mac: brew install jq"
        echo ""
        echo "Или используйте Python версию:"
        echo "   pip install httpx"
        echo "   python check_embedding_dim.py $MODEL"
        echo ""
        echo "Ответ сервера (первые 500 символов):"
        echo "$BODY" | head -c 500
        exit 1
    fi
    
    if [ -z "$DIM" ]; then
        echo "❌ Не удалось извлечь размерность из ответа"
        echo ""
        echo "Ответ сервера:"
        echo "$BODY" | head -c 500
        echo ""
        exit 1
    fi
fi

echo "✅ Успешно получен эмбеддинг!"
echo ""
echo "============================================================"
echo "📊 Размерность эмбеддинга: $DIM"
echo "============================================================"
echo ""
echo "💡 Используйте это значение для:"
echo "   EMBEDDING_DIM=$DIM"
echo "   EMBEDDING_DIMENSIONS=$DIM"
echo ""
echo "📝 Пример для docker-compose.yml:"
echo "   environment:"
echo "     - EMBEDDING_DIM=$DIM"
echo ""

exit 0


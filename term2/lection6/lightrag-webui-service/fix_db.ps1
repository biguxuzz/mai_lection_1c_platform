# Скрипт для очистки поврежденной базы данных LightRAG WebUI (PowerShell)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🔧 Исправление базы данных LightRAG WebUI" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Остановка контейнера
Write-Host "🛑 Остановка контейнера..." -ForegroundColor Yellow
docker stop lection6_lightrag_webui 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Контейнер уже остановлен" -ForegroundColor Gray
}

# Удаление volume с данными
Write-Host ""
Write-Host "🗑️  Удаление поврежденных данных..." -ForegroundColor Yellow
$confirmation = Read-Host "   Вы уверены, что хотите удалить все данные LightRAG WebUI? (y/N)"
if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
    docker volume rm lection6_lightrag_webui_data 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Данные удалены" -ForegroundColor Green
    } else {
        Write-Host "   Volume не найден или уже удален" -ForegroundColor Gray
    }
} else {
    Write-Host "   ❌ Операция отменена" -ForegroundColor Red
    exit 1
}

# Перезапуск контейнера
Write-Host ""
Write-Host "🚀 Перезапуск контейнера..." -ForegroundColor Yellow
docker-compose up -d lightrag-webui

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Готово! Контейнер перезапущен с чистой БД" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan


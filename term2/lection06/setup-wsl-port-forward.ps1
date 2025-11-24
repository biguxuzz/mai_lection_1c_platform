# Скрипт для настройки порт-форвардинга с хоста Windows на WSL
# Пробрасывает порт 18080 на хосте -> порт 80 на BXZ-NOTE.WSL (172.17.238.77)
# Требует запуска с правами администратора

Write-Host "Настройка порт-форвардинга для доступа к WSL..." -ForegroundColor Yellow

# Параметры
$WSLHost = "172.17.238.77"
$WSLPort = 80
$HostPort = 18080

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ОШИБКА: Скрипт должен быть запущен с правами администратора!" -ForegroundColor Red
    Write-Host "Запустите PowerShell от имени администратора и выполните:" -ForegroundColor Yellow
    Write-Host "  .\setup-wsl-port-forward.ps1" -ForegroundColor Cyan
    exit 1
}

# Проверка существующего правила
$existingRule = Get-NetNatStaticMapping -StaticMappingID 1 -ErrorAction SilentlyContinue | Where-Object {
    $_.ExternalPort -eq $HostPort -and $_.InternalAddress -eq $WSLHost -and $_.InternalPort -eq $WSLPort
}

if ($existingRule) {
    Write-Host "Порт-форвардинг уже настроен:" -ForegroundColor Green
    $existingRule | Format-Table -AutoSize
    Write-Host "`nДля удаления выполните:" -ForegroundColor Yellow
    Write-Host "  Remove-NetNatStaticMapping -StaticMappingID $($existingRule.StaticMappingID)" -ForegroundColor Cyan
} else {
    # Используем netsh для порт-форвардинга (более надежно на Windows)
    try {
        # Удаляем существующее правило если есть
        netsh interface portproxy delete v4tov4 listenport=$HostPort listenaddress=0.0.0.0 2>$null | Out-Null
        
        # Добавляем новое правило
        netsh interface portproxy add v4tov4 listenport=$HostPort listenaddress=0.0.0.0 connectport=$WSLPort connectaddress=$WSLHost | Out-Null
        
        Write-Host "Порт-форвардинг успешно настроен!" -ForegroundColor Green
        Write-Host "  Внешний порт (на хосте): $HostPort" -ForegroundColor Cyan
        Write-Host "  Внутренний адрес (WSL): $WSLHost`:$WSLPort" -ForegroundColor Cyan
        Write-Host "`nТеперь контейнеры могут обращаться к WSL через:" -ForegroundColor Yellow
        Write-Host "  http://host.docker.internal:$HostPort" -ForegroundColor Cyan
        Write-Host "  или" -ForegroundColor Yellow
        Write-Host "  http://lection6_wsl_proxy:8080 (через прокси-контейнер)" -ForegroundColor Cyan
    } catch {
        Write-Host "ОШИБКА при настройке порт-форвардинга: $_" -ForegroundColor Red
        Write-Host "`nПопробуйте выполнить команду вручную:" -ForegroundColor Yellow
        Write-Host "  netsh interface portproxy add v4tov4 listenport=$HostPort listenaddress=0.0.0.0 connectport=$WSLPort connectaddress=$WSLHost" -ForegroundColor Cyan
        exit 1
    }
}

Write-Host "`nПроверка настроек:" -ForegroundColor Yellow
netsh interface portproxy show all | Select-String "$HostPort"

Write-Host "`nПерезапустите контейнеры:" -ForegroundColor Yellow
Write-Host "  docker-compose restart wsl-proxy" -ForegroundColor Cyan


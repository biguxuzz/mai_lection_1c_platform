# Скрипт для добавления маршрута к WSL сети из Docker контейнеров
# Требует запуска с правами администратора

Write-Host "Добавление маршрута к WSL сети..." -ForegroundColor Yellow

# IP адрес WSL gateway (обнаружен автоматически)
$WSLGateway = "172.17.224.1"
# Подсеть WSL
$WSLSubnet = "172.17.224.0/20"

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ОШИБКА: Скрипт должен быть запущен с правами администратора!" -ForegroundColor Red
    Write-Host "Запустите PowerShell от имени администратора и выполните:" -ForegroundColor Yellow
    Write-Host "  .\add-wsl-route.ps1" -ForegroundColor Cyan
    exit 1
}

# Проверка существования маршрута
$existingRoute = Get-NetRoute -DestinationPrefix "172.17.224.0/20" -ErrorAction SilentlyContinue

if ($existingRoute) {
    Write-Host "Маршрут уже существует:" -ForegroundColor Green
    $existingRoute | Format-Table -AutoSize
    
    # Проверяем, правильный ли gateway
    $currentNextHop = ($existingRoute | Select-Object -First 1).NextHop
    if ($currentNextHop -eq "0.0.0.0" -or $currentNextHop -ne $WSLGateway) {
        Write-Host "`nВНИМАНИЕ: Маршрут существует, но NextHop = $currentNextHop" -ForegroundColor Yellow
        Write-Host "Нужно обновить маршрут с правильным gateway ($WSLGateway)" -ForegroundColor Yellow
        Write-Host "`nУдаляем старый маршрут..." -ForegroundColor Cyan
        $interfaceIndex = ($existingRoute | Select-Object -First 1).InterfaceIndex
        Remove-NetRoute -DestinationPrefix $WSLSubnet -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Добавляем новый маршрут..." -ForegroundColor Cyan
        New-NetRoute -DestinationPrefix $WSLSubnet -NextHop $WSLGateway -InterfaceIndex $interfaceIndex -ErrorAction Stop
        Write-Host "Маршрут успешно обновлен!" -ForegroundColor Green
    } else {
        Write-Host "Маршрут настроен правильно с gateway $WSLGateway" -ForegroundColor Green
    }
} else {
    # Добавление маршрута
    try {
        # Находим интерфейс WSL
        $wslInterface = Get-NetAdapter | Where-Object {$_.InterfaceDescription -like "*WSL*"} | Select-Object -First 1
        if ($wslInterface) {
            New-NetRoute -DestinationPrefix $WSLSubnet -NextHop $WSLGateway -InterfaceIndex $wslInterface.ifIndex -ErrorAction Stop
            Write-Host "Маршрут успешно добавлен!" -ForegroundColor Green
            Write-Host "  Подсеть: $WSLSubnet" -ForegroundColor Cyan
            Write-Host "  Gateway: $WSLGateway" -ForegroundColor Cyan
            Write-Host "  Интерфейс: $($wslInterface.Name)" -ForegroundColor Cyan
        } else {
            # Используем InterfaceIndex из существующего маршрута или находим по IP
            $wslAdapter = Get-NetIPAddress -IPAddress "172.17.224.1" -ErrorAction SilentlyContinue
            if ($wslAdapter) {
                New-NetRoute -DestinationPrefix $WSLSubnet -NextHop $WSLGateway -InterfaceIndex $wslAdapter.InterfaceIndex -ErrorAction Stop
                Write-Host "Маршрут успешно добавлен!" -ForegroundColor Green
            } else {
                throw "Не удалось найти интерфейс WSL"
            }
        }
    } catch {
        Write-Host "ОШИБКА при добавлении маршрута: $_" -ForegroundColor Red
        Write-Host "`nПопробуйте добавить маршрут вручную:" -ForegroundColor Yellow
        Write-Host "  route add 172.17.224.0 mask 255.255.240.0 $WSLGateway" -ForegroundColor Cyan
        exit 1
    }
}

Write-Host "`nПроверка маршрута:" -ForegroundColor Yellow
Get-NetRoute -DestinationPrefix "172.17.224.0/20" | Format-Table -AutoSize

Write-Host "`nВАЖНО: Для работы доступа к WSL из Docker контейнеров:" -ForegroundColor Yellow
Write-Host "1. Убедитесь, что маршрут настроен правильно (NextHop = $WSLGateway)" -ForegroundColor Cyan
Write-Host "2. Docker на Windows использует NAT, поэтому может потребоваться дополнительная настройка" -ForegroundColor Cyan
Write-Host "3. Если ping не работает, попробуйте использовать host.docker.internal для доступа к хосту" -ForegroundColor Cyan
Write-Host "   и затем с хоста обращаться к WSL" -ForegroundColor Cyan
Write-Host "`nПерезапустите контейнеры:" -ForegroundColor Yellow
Write-Host "  docker-compose restart" -ForegroundColor Cyan


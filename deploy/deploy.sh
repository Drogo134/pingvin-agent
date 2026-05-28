#!/bin/bash
# ================================================================
# РПК ПинГвин — Deploy на Linux сервер (Ubuntu/Debian)
# Запускать на сервере: bash deploy/deploy.sh
# ================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo ""
echo "========================================"
echo "  OpenClaw AI Agent — Deploy"
echo "  РПК ПинГвин, Домодедово"
echo "========================================"
echo ""

# --- Проверка .env ---
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "⚠️  ВАЖНО: Заполните $PROJECT_DIR/.env"
    echo "Обязательные переменные:"
    echo "  ANTHROPIC_API_KEY"
    echo "  TELEGRAM_BOT_TOKEN"
    echo "  MANAGER_TELEGRAM_CHAT_ID"
    echo "  SBIS_LOGIN / SBIS_PASSWORD"
    echo ""
    echo "После заполнения запустите скрипт снова."
    exit 1
fi

# --- Проверка Docker ---
if ! command -v docker &> /dev/null; then
    echo "Установка Docker..."
    curl -fsSL https://get.docker.com | bash
    sudo usermod -aG docker $USER
    echo "Docker установлен. Перезайдите в систему или выполните: newgrp docker"
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Установка Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

echo "[OK] Docker: $(docker --version)"
echo "[OK] Docker Compose: $(docker-compose --version)"

# --- Создать директорию uploads ---
mkdir -p "$PROJECT_DIR/uploads"
chmod 755 "$PROJECT_DIR/uploads"

# --- Сборка и запуск ---
cd "$PROJECT_DIR"

echo ""
echo "Сборка Docker образа..."
docker-compose build --no-cache

echo ""
echo "Запуск агента..."
docker-compose up -d

# --- Ждать готовности ---
echo ""
echo "Ожидание запуска (30 сек)..."
sleep 30

# --- Проверка статуса ---
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ Агент запущен успешно!"
    docker-compose ps
else
    echo ""
    echo "❌ Ошибка запуска. Логи:"
    docker-compose logs --tail=50
    exit 1
fi

echo ""
echo "========================================"
echo "  Деплой завершён!"
echo "========================================"
echo ""
echo "Команды управления:"
echo "  Логи:       docker-compose logs -f"
echo "  Статус:     docker-compose ps"
echo "  Остановить: docker-compose down"
echo "  Рестарт:    docker-compose restart"
echo "  Обновить:   git pull && docker-compose up -d --build"
echo ""

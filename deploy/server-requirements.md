# Требования к серверу для деплоя

## Минимальные требования

| Параметр | Минимум | Рекомендовано |
|----------|---------|---------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Диск | 20 GB SSD | 40 GB SSD |
| ОС | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Docker | 24+ | 26+ |

## Провайдеры (рекомендованные)

| Провайдер | Конфигурация | Цена (ориентировочно) |
|-----------|-------------|----------------------|
| Selectel | 2 vCPU, 4 GB RAM | ~1 200 руб/мес |
| Timeweb Cloud | 2 vCPU, 4 GB RAM | ~1 000 руб/мес |
| Yandex Cloud | e2-standard-2 | ~2 000 руб/мес |
| Hetzner | CX22 | ~500 руб/мес |

## Сетевые требования

- Публичный IP адрес (не обязателен для Telegram polling)
- Порт 18789 открыт (если нужен внешний доступ)
- Порт 80/443 если используется Nginx + Telegram webhook

## Подготовка сервера

```bash
# 1. Обновить систему
sudo apt update && sudo apt upgrade -y

# 2. Установить Git
sudo apt install -y git

# 3. Клонировать репозиторий
git clone <repo_url> /opt/pingvin-agent
cd /opt/pingvin-agent

# 4. Запустить деплой
bash deploy/deploy.sh
```

## Обновление агента

```bash
cd /opt/pingvin-agent
git pull
docker-compose up -d --build
```

## Резервное копирование

```bash
# Данные OpenClaw (сессии, память)
docker run --rm -v pingvin_openclaw_data:/data -v $(pwd)/backup:/backup \
  alpine tar czf /backup/openclaw_data_$(date +%Y%m%d).tar.gz /data

# Загруженные макеты
tar czf backup/uploads_$(date +%Y%m%d).tar.gz uploads/
```

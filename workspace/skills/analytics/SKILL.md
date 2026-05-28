# AnalyticsSkill — Базовая аналитика MVP

## Назначение

Отслеживание и отчётность по ключевым KPI агента для оценки MVP.

## KPI для MVP

| Метрика | Цель | Как считать |
|---------|------|-------------|
| Полный цикл диалога | ≥70% | от первого сообщения до создания лида в СБИС |
| Время первого ответа | ≤60 сек (рабочее время) | timestamp входящего vs timestamp ответа |
| Handoff rate | ≤30% от диалогов | кол-во handoff / кол-во диалогов |
| Конверсия в лид | ≥50% | лиды создано / диалоги начаты |
| Follow-up ответы | ≥20% | ответы после follow-up / отправлено follow-up |

## Структура лога аналитики

Каждый диалог логируй в формате JSON:
```json
{
  "session_id": "...",
  "channel": "telegram|email",
  "started_at": "ISO-8601",
  "first_response_ms": 1200,
  "lead_created": true,
  "lead_id": "...",
  "handoff": false,
  "handoff_reason": null,
  "full_cycle_complete": true,
  "service_type": "banner|sign|poly|...",
  "estimate_given": true,
  "follow_up_sent": 0,
  "follow_up_responses": 0,
  "ended_at": "ISO-8601"
}
```

Записывать в: `logs/analytics_[YYYY-MM].jsonl`

## Ежедневный отчёт (через HEARTBEAT.md)

Запускается каждый день в 9:00 МСК.

**Команда:**
```bash
cat logs/analytics_$(date +%Y-%m).jsonl | python3 -c "
import sys, json
from datetime import date, timedelta
today = date.today().isoformat()
yesterday = (date.today() - timedelta(1)).isoformat()

lines = [json.loads(l) for l in sys.stdin if l.strip()]
yesterday_logs = [l for l in lines if l.get('started_at','').startswith(yesterday)]

total = len(yesterday_logs)
if total == 0:
    print('Вчера диалогов не было.')
    sys.exit()

leads = sum(1 for l in yesterday_logs if l.get('lead_created'))
handoffs = sum(1 for l in yesterday_logs if l.get('handoff'))
full_cycle = sum(1 for l in yesterday_logs if l.get('full_cycle_complete'))
avg_resp = sum(l.get('first_response_ms', 0) for l in yesterday_logs) / total

print(f'''📊 Отчёт за {yesterday}:
  Диалогов: {total}
  Создано лидов: {leads} ({leads*100//total}%)
  Handoff: {handoffs} ({handoffs*100//total}%)
  Полный цикл: {full_cycle} ({full_cycle*100//total}%) [цель ≥70%]
  Avg первый ответ: {avg_resp/1000:.1f} сек
''')
"
```

## Как логировать события в диалоге

### В начале диалога
```bash
echo '{"session_id":"SESSION","channel":"telegram","started_at":"TIMESTAMP","first_response_ms":0}' >> logs/analytics_$(date +%Y-%m).jsonl
```

### При создании лида
Обновить запись: `lead_created: true, lead_id: "..."`

### При handoff
Обновить запись: `handoff: true, handoff_reason: "no_tariff|user_request|complex"`

### При завершении полного цикла
Полный цикл = **лид создан + предварительный расчёт дан + менеджеру передано или follow-up запущен**  
Обновить: `full_cycle_complete: true`

## Отчёт по запросу менеджера

**Только если запрос пришёл НЕ с менеджерского Telegram-ID** (менеджерские ID не общаются с ботом). Для отчётов менеджерам — cron + `notify_managers.sh`.


Если менеджер в Telegram пишет `/stats` или `покажи статистику`:

1. Прочитать `logs/analytics_[текущий месяц].jsonl`
2. Посчитать метрики за текущий месяц
3. Отправить ответ всем менеджерам: `bash workspace/scripts/notify_managers.sh` с текстом отчёта (или ответить в чат, если запрос из `MANAGER_TELEGRAM_CHAT_IDS`):

Шаблон для notify_managers:

```
📊 Статистика за [месяц]:

Диалогов всего: N
Лидов создано: N (X%)
Передано менеджерам: N (X%)
Полный цикл: N (X%) [цель ≥70%]
Ср. время ответа: X сек

По каналам:
• Telegram: N диалогов
• Email/сайт: N диалогов

По услугам:
• Баннеры/вывески: N
• Полиграфия: N
• Печати: N
• Другое: N
```

## Правило

- НИКОГДА не удалять файлы аналитики
- При ошибке чтения лога — не блокировать диалог, пропустить событие
- Логировать только агрегированные данные, без личных данных клиента в сводном отчёте

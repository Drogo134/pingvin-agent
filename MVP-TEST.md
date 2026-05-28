# MVP — пошаговая проверка РПК «ПинГвин»

Модель: **OpenAI gpt-4o** (как в `openclaw.json`).

Перед началом:

```powershell
cd C:\Users\dan\OneDrive\Desktop\OpenclawAgent
.\scripts\start-local.ps1 -Sync
.\scripts\mvp-check.ps1          # автопроверка инфраструктуры
```

Кабинет: http://127.0.0.1:18789/?token=pingvin-mvp-dashboard-2026

---

## Часть A — Автоматика (5 мин)

| # | Проверка | Команда | Ожидание |
|---|----------|---------|----------|
| A1 | OpenAI | `mvp-check.ps1` | `[PASS] OpenAI API (gpt-4o)` |
| A2 | Telegram bot | то же | `@rpkpingvin_bot` |
| A3 | Saby auth | то же | `session ...` |
| A4 | Gateway | то же | `HTTP 200` на :18789 |
| A5 | Обращение в Saby | см. A5 ниже | `ok: true`, номер обращения |

**A5 — тест Saby (без Telegram):**

```powershell
python -c "
import json, os, importlib.util
from pathlib import Path
root = Path('.').resolve()
for line in (root/'.env').read_text().splitlines():
    if '=' in line and not line.strip().startswith('#'):
        k,v=line.split('=',1); os.environ[k.strip()]=v.strip()
spec=importlib.util.spec_from_file_location('s', root/'workspace/scripts/sbis_api.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(json.dumps(m.create_appeal({
  'name':'MVP Тест','phone':'+79001112233','source':'mvp-test',
  'service_type':'Визитки','description':'Автотест MVP',
  'channel_id':'mvp:test-001'
}), ensure_ascii=False, indent=2))
"
```

Проверить список (включая черновики):

```powershell
python scripts\sbis_list_appeals.py
```

В браузере: https://online.sbis.ru/page/support-service — обращение видно **только после отправки**.

Если в ответе `draft: true` — в `.env` задайте `SBIS_MANAGER_ID` (см. `scripts/sbis-manager-id.md`) и выполните:

```powershell
python workspace\scripts\sbis_api.py submit_appeal '{"appeal_id":"<uuid>","description":"MVP тест"}'
```

---

## Часть B — Диалог в Telegram (15–20 мин)

Бот: **@rpkpingvin_bot**. Можно писать и с менеджерского аккаунта — обычные фразы («нужны визитки») обрабатываются как у клиента. Внутренние команды (`/stats`, «очередь обращений») — только по явному запросу.

### Сценарий 1: Полный цикл «визитки»

| Шаг | Вы пишете боту | Ожидание от агента |
|-----|----------------|-------------------|
| B1 | `Здравствуйте, нужны визитки` | Приветствие, уточняющие вопросы (тираж, бумага, срок) |
| B2 | `1000 шт, мелованный картон, обычный срок` | Уточнения или ориентир по цене из прайса |
| B3 | `Иван Тестов, +79001112233` | Резюме + «передаю менеджеру» / подтверждение заявки |
| B4 | — | В Saby появилось обращение с текстом про визитки и `channel_id` |
| B5 | — | Менеджерам (1280280963, 8096376287) пришло уведомление в Telegram |

**Критерий PASS:** обращение в support-service + осмысленный диалог + handoff.

### Сценарий 2: Handoff «сложный заказ»

| Шаг | Сообщение | Ожидание |
|-----|-----------|----------|
| B6 | Новый чат: `Нужна вывеска 5 метров с монтажом на высоте` | Агент не даёт финальную цену «с потолка», задаёт вопросы |
| B7 | `Бюджет около 200000, нужен монтаж` | Передача менеджеру (сложный/крупный заказ) |

**Критерий PASS:** handoff без выдуманной точной суммы.

### Сценарий 3: Повторное обращение

| Шаг | Действие | Ожидание |
|-----|----------|----------|
| B8 | В том же чате что B1: `А когда будет готово?` | Помнит контекст, не создаёт дубликат обращения (или обновляет) |

---

## Часть C — Control UI (5 мин)

| # | Действие | Ожидание |
|---|----------|----------|
| C1 | Открыть кабинет с token | Dashboard загружается |
| C2 | Sessions → ваш Telegram-диалог | История сообщений видна |
| C3 | Model → `GPT-4o` | Модель переключается, ответы продолжаются |
| C4 | Логи gateway (pm2 logs) | Нет постоянных crash/restart |

---

## Часть D — Email (опционально, 10 мин)

| # | Действие | Ожидание |
|---|----------|----------|
| D1 | Отправить на info@ra-pingvin.ru письмо «Заявка: листовки 5000 шт» | — |
| D2 | Подождать cron / heartbeat | Агент обрабатывает или логирует intake |
| D3 | — | Обращение в Saby или ответ клиенту (если email-intake настроен на авто) |

*Email может быть менее стабилен на MVP — зафиксируйте результат как PASS/FAIL.*

---

## Часть E — Чеклист MVP (итог)

Отметьте ✅ / ❌:

- [ ] Gateway online, OpenAI отвечает
- [ ] Telegram-бот отвечает в течение ~30 сек
- [ ] Расчёт/ориентир по цене (визитки) из прайса
- [ ] Обращение создаётся в https://online.sbis.ru/page/support-service
- [ ] Handoff менеджерам в Telegram
- [ ] Нет дублей обращений при повторном сообщении
- [ ] Control UI показывает сессию

**MVP считается пройденным:** минимум **5 из 7** пунктов E, обязательно пункты 2, 4, 5.

---

## Если что-то падает

| Симптом | Решение |
|---------|---------|
| Gateway не открывается | `pm2 delete pingvin-agent`; `.\scripts\start-local.ps1 -Sync` |
| PM2 «waiting restart» | Исправлено: используется `node openclaw.mjs` |
| Бот молчит | Проверить `TELEGRAM_BOT_TOKEN`, логи: `.\scripts\start-local.ps1 -Logs` |
| Saby не создаёт | `python scripts\sbis_test_auth.py` |
| OpenAI 401 | Проверить `OPENAI_API_KEY` в `.env` |

---

## Тестовые фразы (копировать)

```
Здравствуйте, нужны визитки 1000 шт, мелованный картон
```

```
Меня зовут Иван, телефон +79001112233, Домодедово
```

```
Нужна световая вывеска 3 метра с установкой, срок срочно
```

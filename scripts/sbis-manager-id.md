# Как узнать SBIS_MANAGER_ID

Обращения через API создаются как **черновик** («Ожидается отправка»). Чтобы они появились в [Контакт-центре](https://online.sbis.ru/page/support-service), после создания нужен `submit_appeal` с **получателем** — UUID сотрудника в Saby.

## Шаг 1 — выберите менеджера

Обычно это сотрудник, который обрабатывает обращения в Контакт-центре (не учётка `ai_agent`).

## Шаг 2 — скопируйте UUID из Saby

1. Войдите в https://online.sbis.ru под администратором или менеджером.
2. Откройте карточку сотрудника (Персонал / Сотрудники → нужный человек).
3. В адресной строке браузера найдите GUID вида `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` — это и есть `SBIS_MANAGER_ID`.

Альтернатива: создайте **одно** обращение вручную в UI, назначьте ответственного, затем:

```powershell
cd C:\Users\dan\OneDrive\Desktop\OpenclawAgent
python workspace\scripts\sbis_api.py find_appeal '{"appeal_id":"<guid из URL документа>"}'
```

В ответе смотрите поле `document.Ответственный.Идентификатор`.

## Шаг 3 — пропишите в `.env`

```env
SBIS_MANAGER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
SBIS_AUTO_SUBMIT=true
```

Перезапустите агента: `scripts\start-local.cmd`

## Проверка

```powershell
python workspace\scripts\sbis_api.py list_appeals '{}'
python workspace\scripts\sbis_api.py submit_appeal '{"appeal_id":"<uuid черновика>","description":"Тест отправки"}'
```

После успешного `submit_appeal` поле `draft` должно стать `false`, обращение видно в Контакт-центре.

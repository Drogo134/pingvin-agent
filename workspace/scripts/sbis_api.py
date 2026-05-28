#!/usr/bin/env python3
"""Saby (SBIS) — обращения в Контакт-центр / support-service (не CRM-сделки)."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]  # OpenclawAgent/
TOKEN_CACHE = Path(os.environ.get("SBIS_TOKEN_CACHE", SCRIPT_DIR.parent / ".cache" / "sbis_session"))
TOKEN_TTL = 1700
USER_AGENT = os.environ.get("SBIS_APP_NAME", "OpenClawAgent.PingvinRPK/1.0")
LOG_FILE = Path(os.environ.get("SBIS_LOG_FILE", SCRIPT_DIR.parent / "logs" / "sbis_api.log"))


def load_env_file() -> None:
    """Подгрузить .env из корня проекта (если переменные ещё не заданы в окружении)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip()
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


load_env_file()

# Перечитать после load_env_file
SBIS_AUTH_URL = os.environ.get("SBIS_AUTH_URL", "https://online.sbis.ru/auth/service/")
SBIS_API_URL = os.environ.get("SBIS_API_URL", "https://online.sbis.ru/service/?srv=1")
SBIS_LOGIN = os.environ.get("SBIS_LOGIN", "")
SBIS_PASSWORD = os.environ.get("SBIS_PASSWORD", "")
SBIS_ACCOUNT_NUMBER = os.environ.get("SBIS_ACCOUNT_NUMBER", "")
SBIS_MANAGER_ID = os.environ.get("SBIS_MANAGER_ID", "")
SBIS_DEPARTMENT_ID = os.environ.get("SBIS_DEPARTMENT_ID", "")
SBIS_DEPARTMENT_NAME = os.environ.get("SBIS_DEPARTMENT_NAME", "")
# auto = подразделение (общая очередь), если задано; иначе сотрудник
SBIS_RECIPIENT_MODE = os.environ.get("SBIS_RECIPIENT_MODE", "auto").strip().lower()
SBIS_APPEAL_REGULATION_NAME = os.environ.get("SBIS_APPEAL_REGULATION_NAME", "Обращение")
SBIS_APPEAL_REGULATION_ID = os.environ.get("SBIS_APPEAL_REGULATION_ID", "")
SBIS_APPEAL_DOC_TYPE = os.environ.get("SBIS_APPEAL_DOC_TYPE", "РекламацияВх")
SBIS_AUTO_SUBMIT = os.environ.get("SBIS_AUTO_SUBMIT", "true").lower() in ("1", "true", "yes")
SBIS_NOTIFY_MANAGERS = os.environ.get("SBIS_NOTIFY_MANAGERS", "true").lower() in ("1", "true", "yes")
SBIS_ORG_INN = os.environ.get("SBIS_ORG_INN", "")
SBIS_ORG_KPP = os.environ.get("SBIS_ORG_KPP", "")
SBIS_SUPPORT_URL = os.environ.get(
    "SBIS_SUPPORT_URL", "https://online.sbis.ru/page/support-service"
)


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(f"[sbis_api] {msg}", file=sys.stderr)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def http_post(url: str, payload: dict[str, Any], session_id: str | None = None) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json-rpc;charset=utf-8",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if session_id:
        headers["X-SBISSessionID"] = session_id

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        if exc.code >= 400:
            log(f"HTTP {exc.code}: {raw[:300]}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": {"message": raw, "code": exc.code}}
    except urllib.error.URLError as exc:
        log(f"Network error: {exc}")
        return {"error": {"message": str(exc), "code": "network"}}

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log(f"Invalid JSON response: {raw[:300]}")
        return {"error": {"message": "invalid_json", "details": raw[:500]}}


def extract_session_id(response: dict[str, Any]) -> str:
    if "error" in response:
        return ""
    result = response.get("result")
    if isinstance(result, str) and result:
        return result
    if isinstance(result, dict):
        for key in ("session", "SessionId", "Сид", "ИдентификаторСессии"):
            val = result.get(key)
            if isinstance(val, str) and val:
                return val
    return ""


def build_auth_payloads() -> list[dict[str, Any]]:
    base: dict[str, str] = {"Логин": SBIS_LOGIN, "Пароль": SBIS_PASSWORD}
    if SBIS_ACCOUNT_NUMBER:
        base["НомерАккаунта"] = SBIS_ACCOUNT_NUMBER
    return [
        {"jsonrpc": "2.0", "method": "СБИС.Аутентифицировать", "params": dict(base), "id": 1},
        {"jsonrpc": "2.0", "method": "СБИС.Аутентифицировать", "params": {"Параметр": dict(base)}, "id": 1},
    ]


def read_cached_session() -> str:
    try:
        if not TOKEN_CACHE.exists():
            return ""
        if time.time() - TOKEN_CACHE.stat().st_mtime > TOKEN_TTL:
            return ""
        return TOKEN_CACHE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def write_cached_session(session_id: str) -> None:
    try:
        TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE.write_text(session_id, encoding="utf-8")
    except OSError:
        pass


def authenticate(force: bool = False) -> str:
    if not force:
        cached = read_cached_session()
        if cached:
            return cached

    if not SBIS_LOGIN or not SBIS_PASSWORD:
        log("ERROR: SBIS_LOGIN или SBIS_PASSWORD не заданы")
        return "ERROR_NO_CREDENTIALS"

    for payload in build_auth_payloads():
        resp = http_post(SBIS_AUTH_URL, payload)
        session_id = extract_session_id(resp)
        if session_id:
            write_cached_session(session_id)
            log("Auth OK")
            return session_id
        if "error" in resp:
            log(f"Auth failed: {json.dumps(resp.get('error'), ensure_ascii=False)[:300]}")

    log("ERROR: не удалось аутентифицироваться")
    return "ERROR_AUTH"


def rpc(method: str, params: dict[str, Any], session_id: str | None = None) -> dict[str, Any]:
    sid = session_id or authenticate()
    if sid.startswith("ERROR"):
        return {"error": {"message": "auth_failed", "detail": sid}}

    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    resp = http_post(SBIS_API_URL, payload, session_id=sid)

    if "error" in resp and not session_id:
        err = resp.get("error") or {}
        code = err.get("code")
        msg = str(err.get("message", "")).lower()
        if code in (-32000, 401, 403) or "сесс" in msg or "auth" in msg:
            sid = authenticate(force=True)
            if sid.startswith("ERROR"):
                return {"error": {"message": "auth_failed", "detail": sid}}
            resp = http_post(SBIS_API_URL, payload, session_id=sid)

    return resp


def build_appeal_note(data: dict[str, Any]) -> str:
    name = data.get("name") or data.get("client_name") or ""
    source = data.get("source") or "unknown"
    description = data.get("description") or ""
    phone = data.get("phone") or data.get("contact") or ""
    email = data.get("email") or ""
    service_type = data.get("service_type") or ""
    channel_id = data.get("channel_id") or ""
    session_id = data.get("session_id") or ""
    estimated_price = data.get("estimated_price") or ""
    missing_data = data.get("missing_data") or ""
    handoff_reason = data.get("handoff_reason") or ""

    lines = ["OpenClaw Agent — обращение", ""]
    if description:
        lines.extend(["Описание:", description, ""])
    if name:
        lines.append(f"Клиент: {name}")
    if phone:
        lines.append(f"Контакт для связи: {phone}")
    if email:
        lines.append(f"Email: {email}")
    if service_type:
        lines.append(f"Услуга: {service_type}")
    if estimated_price:
        lines.append(f"Ориентировочная стоимость: {estimated_price}")
    if missing_data:
        lines.append(f"Недостающие данные: {missing_data}")
    if handoff_reason:
        lines.append(f"Причина передачи менеджеру: {handoff_reason}")
    lines.extend(
        [
            f"Источник: {source}",
            f"Канал: {channel_id}" if channel_id else "",
            f"SessionID: {session_id}" if session_id else "",
            f"UI: {SBIS_SUPPORT_URL}",
        ]
    )
    return "\n".join(line for line in lines if line).strip()


def _build_kontragent(data: dict[str, Any]) -> dict[str, Any] | None:
    """Контакт обращения: описание, телефон, email. ЮЛ — только при link_client_company."""
    description = (data.get("description") or "").strip()
    phone = (data.get("phone") or data.get("contact") or "").strip()
    email = (data.get("email") or "").strip()
    name = (data.get("name") or data.get("client_name") or "").strip()

    kont: dict[str, Any] = {}
    if description:
        kont["Описание"] = description
    elif name:
        kont["Описание"] = f"Обращение от {name}"
    if phone:
        kont["Телефон"] = phone
    if email:
        kont["Email"] = email

    if data.get("link_client_company"):
        client_inn = (data.get("client_inn") or data.get("inn") or "").strip()
        client_name = (data.get("client_company") or data.get("company_name") or "").strip()
        if client_inn and len(client_inn) == 10:
            sv: dict[str, Any] = {
                "Название": client_name or "Клиент OpenClaw",
                "ИНН": client_inn,
                "КодСтраны": "643",
            }
            kpp = (data.get("client_kpp") or "").strip()
            if kpp:
                sv["КПП"] = kpp
            kont["СвЮЛ"] = sv

    return kont or None


def _department_ref(data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data or {}
    dept_id = (data.get("department_id") or SBIS_DEPARTMENT_ID or "").strip()
    dept_name = (data.get("department_name") or SBIS_DEPARTMENT_NAME or "").strip()
    ref: dict[str, Any] = {}
    if dept_id:
        ref["Идентификатор"] = dept_id
    if dept_name:
        ref["Название"] = dept_name
    return ref


def resolve_submit_recipient(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str, str]:
    """
    Кому отправить обращение при submit.
    Возвращает (recipient_obj, mode, hint_if_missing).
    mode: department | manager
    """
    mode = (data.get("recipient_mode") or SBIS_RECIPIENT_MODE or "auto").strip().lower()
    manager_id = (data.get("manager_id") or SBIS_MANAGER_ID or "").strip()
    dept = _department_ref(data)

    if mode == "department":
        if not dept:
            return None, "department", "Задайте SBIS_DEPARTMENT_ID или SBIS_DEPARTMENT_NAME (общая очередь)"
        return dept, "department", ""

    if mode == "manager":
        if not manager_id:
            return None, "manager", "Задайте SBIS_MANAGER_ID (конкретный сотрудник)"
        return {"Идентификатор": manager_id}, "manager", ""

    # auto: первый вариант для логов; полный перебор — в submit_recipient_attempts()
    attempts = submit_recipient_attempts(data)
    if attempts:
        return attempts[0][0], attempts[0][1], ""
    return (
        None,
        "",
        "Задайте SBIS_DEPARTMENT_NAME и/или SBIS_MANAGER_ID (см. scripts/sbis-recipients.md)",
    )


def submit_recipient_attempts(data: dict[str, Any] | None = None) -> list[tuple[dict[str, Any], str]]:
    """
    Цепочка fallback при submit (режим auto):
    1) SBIS_DEPARTMENT_NAME — общая очередь «РПК ПИНГВИН, ООО»
    2) Живые менеджеры с доступом в Saby (223, 3374 по умолчанию)
    3) SBIS_MANAGER_ID (часто ИИ Агент — только если разрешён регламентом)
    """
    data = data or {}
    mode = (data.get("recipient_mode") or SBIS_RECIPIENT_MODE or "auto").strip().lower()
    manager_id = (data.get("manager_id") or SBIS_MANAGER_ID or "").strip()
    dept = _department_ref(data)
    attempts: list[tuple[dict[str, Any], str]] = []
    tried_mgr: set[str] = set()

    if mode in ("department", "auto") and dept:
        dept_ref = dict(dept)
        if mode == "auto":
            dept_ref.pop("Идентификатор", None)
        if dept_ref.get("Название") and not dept_ref.get("Структура"):
            dept_ref["Структура"] = "Управленческая"
        if dept_ref.get("Название") or dept_ref.get("Идентификатор"):
            attempts.append((dept_ref, "department"))

    if mode == "auto":
        fallback_raw = os.environ.get("SBIS_FALLBACK_MANAGER_IDS", "223,3374")
        for mid in fallback_raw.replace(";", ",").split(","):
            mid = mid.strip()
            if mid and mid not in tried_mgr:
                attempts.append((read_employee_ref(mid), "manager"))
                tried_mgr.add(mid)

    if mode in ("manager", "auto") and manager_id and manager_id not in tried_mgr:
        attempts.append((read_employee_ref(manager_id), "manager"))
        tried_mgr.add(manager_id)

    if mode == "manager" and manager_id and not attempts:
        attempts.append(({"Идентификатор": manager_id}, "manager"))
    if mode == "department" and dept and not attempts:
        attempts.append((dept, "department"))

    return attempts


def _build_submit_stage(
    appeal_id: str,
    doc: dict[str, Any],
    description: str,
    recipient: dict[str, Any],
    recipient_mode: str,
) -> dict[str, Any]:
    stage_id, stage_name, action_name = workflow_stage_from_doc(doc)
    stage: dict[str, Any] = {
        "Идентификатор": stage_id,
        "Действие": [{"Название": action_name, "Комментарий": str(description)[:2000]}],
    }
    if stage_name:
        stage["Название"] = stage_name

    if recipient_mode == "department":
        dept = dict(recipient)
        if dept.get("Название") and not dept.get("Структура"):
            dept["Структура"] = "Управленческая"
        exec_ref = {"Подразделение": dept}
    else:
        emp = dict(recipient)
        if emp.get("Идентификатор") and not emp.get("Фамилия"):
            emp = read_employee_ref(str(emp["Идентификатор"]))
        exec_ref = {"Сотрудник": emp}

    stage["Исполнитель"] = exec_ref
    stage["СледующийЭтап"] = [{"Исполнитель": [exec_ref]}]
    return stage


def _execute_submit_action(appeal_id: str, stage: dict[str, Any]) -> dict[str, Any]:
    """ПодготовитьДействие + ВыполнитьДействие (рекомендуемый путь Saby API)."""
    prep = rpc(
        "СБИС.ПодготовитьДействие",
        {"Документ": {"Идентификатор": appeal_id, "Этап": stage}},
    )
    if "error" in prep:
        return prep

    result = prep.get("result") or {}
    stages = result.get("Этап") or []
    if isinstance(stages, dict):
        stages = [stages]
    exec_stage = stages[0] if stages else stage
    if not isinstance(exec_stage, dict):
        exec_stage = stage
    else:
        exec_stage = dict(exec_stage)
        if stage.get("Исполнитель"):
            exec_stage["Исполнитель"] = stage["Исполнитель"]
        if stage.get("СледующийЭтап"):
            exec_stage["СледующийЭтап"] = stage["СледующийЭтап"]
        acts = exec_stage.get("Действие") or stage.get("Действие")
        if acts:
            exec_stage["Действие"] = acts

    return rpc(
        "СБИС.ВыполнитьДействие",
        {"Документ": {"Идентификатор": appeal_id, "Этап": exec_stage}},
    )


def read_employee_ref(employee_id: str) -> dict[str, Any]:
    """ФИО + идентификатор для этапа документооборота (из кадрового справочника)."""
    employee_id = (employee_id or "").strip()
    if not employee_id:
        return {}
    resp = rpc(
        "СБИС.ПрочитатьСотрудника",
        {"Параметр": {"Сотрудник": {"Идентификатор": employee_id}}},
    )
    if "error" in resp:
        return {"Идентификатор": employee_id}
    emp = (resp.get("result") or {}).get("Сотрудник") or resp.get("result") or {}
    ref: dict[str, Any] = {"Идентификатор": emp.get("Идентификатор") or employee_id}
    for key in ("Фамилия", "Имя", "Отчество"):
        if emp.get(key):
            ref[key] = emp[key]
    return ref


def build_appeal_document(data: dict[str, Any], *, appeal_id: str | None = None) -> dict[str, Any]:
    """Документ регламента «Обращение» → раздел Контакт-центр / support-service."""
    doc: dict[str, Any] = {
        "Регламент": {"Название": SBIS_APPEAL_REGULATION_NAME},
        "Примечание": build_appeal_note(data),
    }
    if appeal_id:
        doc["Идентификатор"] = appeal_id

    mode = (data.get("recipient_mode") or SBIS_RECIPIENT_MODE or "auto").strip().lower()
    dept = _department_ref(data)
    manager_id = (data.get("manager_id") or SBIS_MANAGER_ID or "").strip()

    # Подразделение при create только в режиме department (в auto — только при submit fallback).
    if dept and mode == "department":
        doc["Подразделение"] = dept
    # Ответственный при create ломает ЗаписатьДокумент («работающий сотрудник»).
    # Получателя назначаем только на этапе «Отправка» → submit_appeal / execute_appeal_action.
    if data.get("set_responsible_on_create") and manager_id:
        doc["Ответственный"] = read_employee_ref(manager_id)

    kont = _build_kontragent(data)
    if kont:
        doc["Контрагент"] = kont
    return doc


def normalize_appeal_response(resp: dict[str, Any]) -> dict[str, Any]:
    if "error" in resp:
        return resp
    doc = resp.get("result")
    if not isinstance(doc, dict):
        return resp
    state = doc.get("Состояние") if isinstance(doc.get("Состояние"), dict) else {}
    return {
        "ok": True,
        "appeal_id": doc.get("Идентификатор"),
        "title": doc.get("Название"),
        "number": doc.get("Номер"),
        "state": state,
        "draft": is_appeal_draft(state),
        "open_url": doc.get("СсылкаДляНашаОрганизация") or "",
        "support_url": SBIS_SUPPORT_URL,
        "document": doc,
    }


def is_appeal_draft(state: dict[str, Any] | None) -> bool:
    if not state:
        return True
    desc = str(state.get("Описание") or "")
    name = str(state.get("Название") or "")
    code = str(state.get("Код") or "")
    return code in ("0", "") or "ожидается отправка" in desc.lower() or "редактируется" in name.lower()


def _org_filter() -> dict[str, Any]:
    org: dict[str, Any] = {"СвЮЛ": {"ИНН": SBIS_ORG_INN, "КодСтраны": "643"}}
    if SBIS_ORG_KPP:
        org["СвЮЛ"]["КПП"] = SBIS_ORG_KPP
    return org


def _regulation_filter() -> dict[str, Any]:
    reg: dict[str, Any] = {"Название": SBIS_APPEAL_REGULATION_NAME}
    if SBIS_APPEAL_REGULATION_ID:
        reg["Идентификатор"] = SBIS_APPEAL_REGULATION_ID
    return reg


def list_stage_actions(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Доступные кнопки на этапе «Отправка»: Выполнить (→ в работу), Решено (закрыть)."""
    out: list[dict[str, Any]] = []
    stages = doc.get("Этап") or []
    if isinstance(stages, dict):
        stages = [stages]
    for st in stages:
        for act in st.get("Действие") or []:
            out.append(
                {
                    "stage_id": str(st.get("Идентификатор") or ""),
                    "stage_name": str(st.get("Название") or ""),
                    "action": str(act.get("Название") or ""),
                    "requires_executor": act.get("ТребуетИсполнителя") == "Да",
                }
            )
    return out


def workflow_stage_from_doc(
    doc: dict[str, Any], *, prefer_action: str | None = None
) -> tuple[str, str, str]:
    stages = doc.get("Этап") or []
    if isinstance(stages, dict):
        stages = [stages]
    prefer = (prefer_action or "Выполнить").strip()
    for st in stages:
        actions = st.get("Действие") or []
        for act in actions:
            if act.get("Название") == prefer:
                return (
                    str(st.get("Идентификатор") or ""),
                    str(st.get("Название") or "Отправка"),
                    prefer,
                )
    for st in stages:
        for act in st.get("Действие") or []:
            if act.get("Название") == "Выполнить":
                return (
                    str(st.get("Идентификатор") or ""),
                    str(st.get("Название") or "Отправка"),
                    "Выполнить",
                )
    if stages:
        st = stages[0]
        acts = st.get("Действие") or [{"Название": "Выполнить"}]
        return (
            str(st.get("Идентификатор") or ""),
            str(st.get("Название") or ""),
            str(acts[0].get("Название") or "Выполнить"),
        )
    return "", "Отправка", "Выполнить"


def execute_appeal_action(data: dict[str, Any]) -> dict[str, Any]:
    """
    Выполнить действие на этапе «Отправка».
    action: «Выполнить» (передать в работу, нужен получатель) | «Решено» (закрыть).
    manager_id: для «Выполнить» — ID сотрудника (попробуйте 27850 = ИИ Агент).
    """
    appeal_id = data.get("appeal_id") or data.get("id") or ""
    action_name = (data.get("action") or data.get("workflow_action") or "Выполнить").strip()
    description = data.get("description") or data.get("comment") or "OpenClaw Agent"

    if not appeal_id:
        return {"ok": False, "error": {"message": "missing_appeal_id"}}

    read = find_appeal({"appeal_id": appeal_id})
    if not read.get("found"):
        return {"ok": False, "error": read.get("error") or {"message": "appeal_not_found"}}

    doc = read.get("document") or {}
    stage_id, stage_name, resolved_action = workflow_stage_from_doc(doc, prefer_action=action_name)

    stage: dict[str, Any] = {
        "Идентификатор": stage_id,
        "Действие": [{"Название": resolved_action, "Комментарий": str(description)[:2000]}],
    }
    if stage_name:
        stage["Название"] = stage_name

    recipient_mode = ""
    if resolved_action == "Выполнить":
        manager_id = (data.get("manager_id") or SBIS_MANAGER_ID or "").strip()
        if manager_id:
            recipient_mode = "manager"
            emp = read_employee_ref(manager_id)
            ref = {"Сотрудник": emp}
        else:
            recipient, recipient_mode, hint = resolve_submit_recipient(data)
            if not recipient:
                return {"ok": False, "error": "missing_recipient", "hint": hint, "appeal_id": appeal_id}
            if recipient_mode == "department":
                dept = dict(recipient)
                if dept.get("Название") and not dept.get("Структура"):
                    dept["Структура"] = "Управленческая"
                ref = {"Подразделение": dept}
            else:
                ref = {"Сотрудник": dict(recipient)}
        stage["Исполнитель"] = ref
        stage["СледующийЭтап"] = [{"Исполнитель": [ref]}]

    log(f"EXECUTE_ACTION id={appeal_id} action={resolved_action} mode={recipient_mode}")
    resp = _execute_submit_action(appeal_id, stage)
    if "error" in resp:
        err = resp.get("error") or {}
        return {
            "ok": False,
            "appeal_id": appeal_id,
            "action": resolved_action,
            "error": err,
            "hint": _submit_error_hint(str(err.get("message") or "")),
            "available_actions": list_stage_actions(doc),
        }

    result_doc = resp.get("result") if isinstance(resp.get("result"), dict) else doc
    new_state = result_doc.get("Состояние") if isinstance(result_doc.get("Состояние"), dict) else {}
    return {
        "ok": True,
        "appeal_id": appeal_id,
        "action": resolved_action,
        "state": new_state,
        "draft": is_appeal_draft(new_state),
        "in_contact_center": not is_appeal_draft(new_state),
        "open_url": result_doc.get("СсылкаДляНашаОрганизация") or doc.get("СсылкаДляНашаОрганизация") or "",
        "support_url": SBIS_SUPPORT_URL,
    }


def submit_appeal(data: dict[str, Any]) -> dict[str, Any]:
    """Отправить черновик обращения в документооборот (иначе в UI Контакт-центра пусто)."""
    appeal_id = data.get("appeal_id") or data.get("id") or ""
    description = (
        data.get("description")
        or data.get("note")
        or (data.get("service_type") and f"Услуга: {data['service_type']}")
        or "Обращение от OpenClaw Agent"
    )

    if not appeal_id:
        return {"ok": False, "error": {"message": "missing_appeal_id"}}

    attempts = submit_recipient_attempts(data)
    if not attempts:
        _, _, missing_hint = resolve_submit_recipient(data)
        return {
            "ok": False,
            "error": "missing_recipient",
            "hint": missing_hint,
            "appeal_id": appeal_id,
            "support_url": SBIS_SUPPORT_URL,
        }

    read = find_appeal({"appeal_id": appeal_id})
    if not read.get("found"):
        return {"ok": False, "error": read.get("error") or {"message": "appeal_not_found"}, "appeal_id": appeal_id}

    doc = read.get("document") or {}
    state = doc.get("Состояние") if isinstance(doc.get("Состояние"), dict) else {}
    if not is_appeal_draft(state):
        return {
            "ok": True,
            "already_submitted": True,
            "appeal_id": appeal_id,
            "state": state,
            "open_url": doc.get("СсылкаДляНашаОрганизация") or "",
            "support_url": SBIS_SUPPORT_URL,
        }

    try_errors: list[dict[str, Any]] = []
    for recipient, recipient_mode in attempts:
        stage = _build_submit_stage(appeal_id, doc, description, recipient, recipient_mode)
        if not stage.get("Идентификатор"):
            return {
                "ok": False,
                "error": {"message": "workflow_stage_not_found"},
                "appeal_id": appeal_id,
            }

        log(
            f"SUBMIT_APPEAL id={appeal_id} try={recipient_mode} "
            f"recipient={json.dumps(recipient, ensure_ascii=False)[:80]}"
        )
        resp = _execute_submit_action(appeal_id, stage)
        if "error" not in resp:
            result_doc = resp.get("result") if isinstance(resp.get("result"), dict) else doc
            new_state = result_doc.get("Состояние") if isinstance(result_doc.get("Состояние"), dict) else {}
            return {
                "ok": True,
                "submitted": True,
                "appeal_id": appeal_id,
                "recipient_mode": recipient_mode,
                "recipient": recipient,
                "submit_attempts": len(try_errors) + 1,
                "state": new_state,
                "draft": is_appeal_draft(new_state),
                "open_url": result_doc.get("СсылкаДляНашаОрганизация")
                or doc.get("СсылкаДляНашаОрганизация")
                or "",
                "support_url": SBIS_SUPPORT_URL,
                "document": result_doc,
            }

        err = resp.get("error") or {}
        try_errors.append(
            {
                "mode": recipient_mode,
                "recipient": recipient,
                "message": err.get("message"),
            }
        )
        log(f"SUBMIT_FAIL mode={recipient_mode}: {str(err.get('message', ''))[:100]}")

    last = try_errors[-1] if try_errors else {}
    return {
        "ok": False,
        "appeal_id": appeal_id,
        "error": {"message": last.get("message"), "attempts": try_errors},
        "hint": _submit_error_hint(str(last.get("message") or "")),
        "open_url": doc.get("СсылкаДляНашаОрганизация") or "",
        "support_url": SBIS_SUPPORT_URL,
    }


def _submit_error_hint(message: str) -> str:
    msg = message.lower()
    if "получател" in msg:
        return (
            "Получатель не принят регламентом «Обращение». Попросите админа Saby: права ai_agent на этап "
            "«Отправка», список получателей в Контакт-центре. SBIS_DEPARTMENT_ID из discover часто "
            "не подходит для документооборота — укажите SBIS_MANAGER_ID сотрудника с доступом в Saby "
            "или настройте очередь получателей в регламенте «Обращение» (права «Администратор» недостаточно)."
        )
    if "работающего сотрудника" in msg:
        return (
            "ID из СписокСотрудников не подходит для этапа «Отправка». Нужен сотрудник из очереди "
            "Контакт-центра (ДоступВСистему=Да). См. scripts/SBIS-SETUP.md — шаг для администратора."
        )
    if "подразделение" in msg and "не найдено" in msg:
        return "Уберите SBIS_DEPARTMENT_ID из .env или задайте SBIS_RECIPIENT_MODE=manager — ID подразделения из API кадров ≠ ID в документообороте."
    if "описан" in msg:
        return "Передайте description в create_appeal / submit_appeal."
    return "Проверьте получателя и права учётки ai_agent на этап «Отправка» (scripts/SBIS-SETUP.md)."


def list_appeals(data: dict[str, Any]) -> dict[str, Any]:
    """Список обращений (в т.ч. черновиков) — для проверки после скрипта."""
    if not SBIS_ORG_INN:
        return {"ok": False, "error": {"message": "SBIS_ORG_INN not set"}}

    limit = int(data.get("limit") or 30)
    filt: dict[str, Any] = {
        "НашаОрганизация": _org_filter(),
        "Тип": SBIS_APPEAL_DOC_TYPE,
        "Регламент": _regulation_filter(),
        "Навигация": {"РазмерСтраницы": str(limit), "Страница": "0"},
    }
    resp = rpc("СБИС.СписокДокументов", {"Фильтр": filt})
    if "error" in resp:
        return {"ok": False, "error": resp.get("error"), "support_url": SBIS_SUPPORT_URL}

    result = resp.get("result", {})
    items = result.get("Документ") or result.get("Документы") or []
    if isinstance(items, dict):
        items = [items]

    appeals = []
    drafts = 0
    for item in items:
        state = item.get("Состояние") if isinstance(item.get("Состояние"), dict) else {}
        draft = is_appeal_draft(state)
        if draft:
            drafts += 1
        appeals.append(
            {
                "number": item.get("Номер"),
                "title": item.get("Название"),
                "appeal_id": item.get("Идентификатор"),
                "draft": draft,
                "state": state.get("Название"),
                "state_detail": state.get("Описание"),
                "open_url": item.get("СсылкаДляНашаОрганизация") or "",
            }
        )

    return {
        "ok": True,
        "count": len(appeals),
        "drafts": drafts,
        "appeals": appeals,
        "support_url": SBIS_SUPPORT_URL,
        "hint": (
            "Черновики (draft=true) не видны в Контакт-центре до submit_appeal. "
            "Нужен SBIS_MANAGER_ID."
            if drafts
            else None
        ),
    }


def format_appeal_telegram_message(data: dict[str, Any], result: dict[str, Any]) -> str:
    """Текст уведомления менеджерам: полное ТЗ + ссылка (форма Saby часто пустая)."""
    lines = ["📋 Новое обращение — РПК ПинГвин"]
    number = result.get("number")
    title = result.get("title")
    if number:
        lines.append(f"№ {number}" + (f" ({title})" if title and str(title) not in str(number) else ""))
    elif title:
        lines.append(str(title))

    open_url = (result.get("open_url") or "").strip()
    if open_url:
        lines.append(f"🔗 {open_url}")

    submit_info = result.get("submit") or {}
    if result.get("draft") and not submit_info.get("submitted"):
        lines.append("⚠️ Черновик — в карточке Saby верхняя форма может быть пустой.")
    elif result.get("visible_in_crm"):
        lines.append("✅ В Контакт-центре.")

    # Полный текст заявки (то же, что в Примечание документа — менеджеру не искать в пустой форме)
    note = build_appeal_note(data)
    if note:
        lines.extend(["", "——— Текст заявки ———", note])

    return "\n".join(lines)


def notify_managers_on_appeal(data: dict[str, Any], result: dict[str, Any]) -> dict[str, Any] | None:
    """Telegram всем MANAGER_TELEGRAM_CHAT_IDS после create_appeal."""
    if data.get("notify_managers") is False:
        return {"skipped": True, "reason": "notify_managers=false in request"}
    if not SBIS_NOTIFY_MANAGERS:
        return {"skipped": True, "reason": "SBIS_NOTIFY_MANAGERS disabled"}

    try:
        from notify_managers import notify_managers as send_telegram
    except ImportError:
        log("NOTIFY_MANAGERS: module notify_managers not found")
        return {"skipped": True, "reason": "notify_managers module not found"}

    message = format_appeal_telegram_message(data, result)
    out = send_telegram(message)
    log(f"NOTIFY_MANAGERS sent={out.get('sent')} failed={out.get('failed')}")
    return out


def create_appeal(data: dict[str, Any]) -> dict[str, Any]:
    doc = build_appeal_document(data)
    log(f"CREATE_APPEAL regulation={SBIS_APPEAL_REGULATION_NAME}")
    resp = rpc("СБИС.ЗаписатьДокумент", {"Документ": doc})
    result = normalize_appeal_response(resp)
    if not result.get("ok"):
        return result

    auto_submit = data.get("auto_submit")
    if auto_submit is None:
        auto_submit = SBIS_AUTO_SUBMIT
    recipient, _, _ = resolve_submit_recipient(data)
    if auto_submit and recipient:
        submit_data = dict(data)
        submit_data["appeal_id"] = result.get("appeal_id")
        submitted = submit_appeal(submit_data)
        result["submit"] = submitted
        if submitted.get("submitted"):
            result["state"] = submitted.get("state") or result.get("state")
            result["draft"] = submitted.get("draft", True)
    elif auto_submit and not recipient:
        result["submit"] = {
            "ok": False,
            "skipped": True,
            "hint": "Нет получателя: задайте SBIS_DEPARTMENT_ID/NAME или SBIS_MANAGER_ID (scripts/sbis-recipients.md)",
        }

    submit_info = result.get("submit") or {}
    submitted = bool(submit_info.get("submitted"))
    result["visible_in_crm"] = submitted or not result.get("draft", True)
    if result.get("draft") and not submitted:
        result["warning"] = (
            submit_info.get("hint")
            or "Черновик создан, но не виден в Контакт-центре до submit_appeal с получателем"
        )

    notify_out = notify_managers_on_appeal(data, result)
    if notify_out is not None:
        result["telegram_notify"] = notify_out

    return result


def update_appeal(data: dict[str, Any]) -> dict[str, Any]:
    appeal_id = data.get("id") or data.get("appeal_id") or ""
    if not appeal_id:
        return {"error": {"message": "missing_appeal_id"}}

    note = data.get("note") or data.get("description") or ""
    status = data.get("status") or ""
    if status:
        status_labels = {
            "new": "Новое",
            "in_progress": "В работе",
            "waiting_manager": "Ожидает менеджера",
            "resolved": "Решено",
            "closed": "Закрыто",
        }
        note = f"Статус: {status_labels.get(status, status)}\n{note}".strip()

    patch = {"Идентификатор": appeal_id}
    if note:
        patch["Примечание"] = note

    log(f"UPDATE_APPEAL id={appeal_id}")
    resp = rpc("СБИС.ЗаписатьДокумент", {"Документ": patch})
    return normalize_appeal_response(resp)


def find_appeal(data: dict[str, Any]) -> dict[str, Any]:
    appeal_id = data.get("id") or data.get("appeal_id") or ""
    if appeal_id:
        resp = rpc("СБИС.ПрочитатьДокумент", {"Документ": {"Идентификатор": appeal_id}})
        if "result" in resp:
            doc = resp["result"]
            return {
                "ok": True,
                "found": True,
                "appeal_id": doc.get("Идентификатор"),
                "title": doc.get("Название"),
                "note": doc.get("Примечание"),
                "support_url": SBIS_SUPPORT_URL,
                "document": doc,
            }
        return resp

    # Поиск по channel_id — только если есть права на список и задана организация
    channel_id = data.get("channel_id") or data.get("session_id") or ""
    if not channel_id or not SBIS_ORG_INN:
        return {
            "ok": False,
            "found": False,
            "hint": "Передайте appeal_id из предыдущего create_appeal или сохраните его в сессии агента",
            "support_url": SBIS_SUPPORT_URL,
        }

    filt: dict[str, Any] = {
        "НашаОрганизация": _org_filter(),
        "Тип": SBIS_APPEAL_DOC_TYPE,
        "Регламент": _regulation_filter(),
        "Навигация": {"РазмерСтраницы": "50", "Страница": "0"},
    }
    resp = rpc("СБИС.СписокДокументов", {"Фильтр": filt})
    if "error" in resp:
        return {
            "ok": False,
            "found": False,
            "channel_id": channel_id,
            "list_error": resp.get("error"),
            "hint": "Сохраняйте appeal_id после create_appeal — у ai_agent может не быть прав на список",
            "support_url": SBIS_SUPPORT_URL,
        }

    documents = resp.get("result", {})
    if isinstance(documents, dict):
        items = documents.get("Документ") or documents.get("Документы") or []
    elif isinstance(documents, list):
        items = documents
    else:
        items = []

    for item in items:
        note = str(item.get("Примечание") or "")
        if channel_id in note:
            return {
                "ok": True,
                "found": True,
                "appeal_id": item.get("Идентификатор"),
                "title": item.get("Название"),
                "note": note,
                "support_url": SBIS_SUPPORT_URL,
                "document": item,
            }

    return {"ok": True, "found": False, "channel_id": channel_id, "support_url": SBIS_SUPPORT_URL}


def test_auth() -> dict[str, Any]:
    session = authenticate(force=True)
    if session.startswith("ERROR"):
        return {"ok": False, "error": session}
    return {"ok": True, "session_prefix": session[:8], "support_url": SBIS_SUPPORT_URL}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: sbis_api.py <command> [json]", file=sys.stderr)
        print(
            "Commands: create_appeal | submit_appeal | execute_appeal_action | "
            "list_appeals | update_appeal | find_appeal | test_auth",
            file=sys.stderr,
        )
        return 1

    command = sys.argv[1]
    raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": {"message": "invalid_json", "detail": str(exc)}}, ensure_ascii=False))
        return 1

    aliases = {
        "create_lead": "create_appeal",
        "update_lead": "update_appeal",
        "find_lead": "find_appeal",
    }
    command = aliases.get(command, command)

    handlers = {
        "create_appeal": create_appeal,
        "submit_appeal": submit_appeal,
        "execute_appeal_action": execute_appeal_action,
        "list_appeals": list_appeals,
        "update_appeal": update_appeal,
        "find_appeal": find_appeal,
        "test_auth": lambda _: test_auth(),
    }
    handler = handlers.get(command)
    if not handler:
        print(json.dumps({"error": {"message": f"unknown_command: {command}"}}, ensure_ascii=False))
        return 1

    result = handler(data)
    print(json.dumps(result, ensure_ascii=False))
    if command == "test_auth":
        return 0
    return 0 if result.get("ok") or "document" in result else 1


if __name__ == "__main__":
    sys.exit(main())

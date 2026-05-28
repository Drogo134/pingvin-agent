#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

aid = sys.argv[1] if len(sys.argv) > 1 else "d0ed9465-510e-4918-b87b-14eb1215d621"

def try_submit(mid: str, fio: tuple[str, str, str]):
    r = m.submit_appeal({
        "appeal_id": aid,
        "description": f"test {mid}",
        "manager_id": mid,
        "recipient_mode": "manager",
    })
    err = (r.get("error") or {}).get("message", "OK" if r.get("ok") else r)
    print(f"id={mid} {fio[0]}: {err}")

for mid, fio in [
    ("27850", ("ИИ", "Агент", "")),
    ("223", ("Ткачук", "Андрей", "Васильевич")),
    ("3374", ("Федоров", "Иван", "Александрович")),
]:
    try_submit(mid, fio)

# try Исполнитель = ai agent on stage directly
read = m.find_appeal({"appeal_id": aid})
doc = read.get("document") or {}
sid, sname, act = m.workflow_stage_from_doc(doc)
agent = {"Идентификатор": "27850", "Фамилия": "ИИ", "Имя": "Агент"}
stage = {
    "Идентификатор": sid,
    "Действие": [{"Название": act, "Комментарий": "agent exec"}],
    "Исполнитель": {"Сотрудник": agent},
    "СледующийЭтап": [{"Исполнитель": [{"Сотрудник": agent}]}],
}
ex = m.rpc("СБИС.ВыполнитьДействие", {"Документ": {"Идентификатор": aid, "Этап": stage}})
print("agent stage:", json.dumps(ex.get("error") or {"ok": True}, ensure_ascii=False)[:300])

#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "workspace" / "scripts"))
import sbis_api as m

# Read #78 with extra fields
aid = "cdce3234-2730-439b-aaff-7cf373eaf22e"
r = m.rpc("СБИС.ПрочитатьДокумент", {
    "Документ": {"Идентификатор": aid, "ДопПоля": "ДополнительныеПоля,Расширение"},
})
doc = r.get("result") or {}
print("ДополнительныеПоля:", json.dumps(doc.get("ДополнительныеПоля"), ensure_ascii=False, indent=2))
print("Расширение full:", json.dumps(doc.get("Расширение"), ensure_ascii=False, indent=2)[:3000])

# Try patch with Описание on Контрагент + СвФЛ
parts = "Мария Тестова".split()
patch = {
    "Идентификатор": aid,
    "Примечание": m.build_appeal_note({
        "name": "Мария Тестова",
        "phone": "+79265551234",
        "email": "maria@test.ru",
        "description": "Визитки 500 шт — тест полей UI",
        "service_type": "Визитки",
    }),
    "Контрагент": {
        "СвФЛ": {
            "Фамилия": parts[0] if parts else "Тестова",
            "Имя": parts[1] if len(parts) > 1 else "Мария",
            "ЧастноеЛицо": "Да",
        },
        "Телефон": "+79265551234",
        "Email": "maria@test.ru",
        "Описание": "Визитки 500 шт — с чем обратился клиент (API тест)",
    },
}
w = m.rpc("СБИС.ЗаписатьДокумент", {"Документ": patch})
print("\nPATCH:", "OK" if w.get("result") else json.dumps(w.get("error"), ensure_ascii=False)[:400])

@router.get("/ai/engine/catalog/insurances")
def get_insurances():

    data = load_raw_insurance_catalog()

    raw_items = data.get("value", [])

    import re

    cleaned = set()

    for item in raw_items:

        name = item.get("label") or item.get("name") or ""

        if not name:
            continue

        name = name.strip()

        # حذف درصد
        name = re.sub(r"\d+\s*%", "", name)

        # حذف عدد آخر
        name = re.sub(r"\s+\d+$", "", name)

        name = name.strip()

        if not name:
            continue

        if name.lower() == "sos":
            continue

        cleaned.add(name)

    result = []

    for name in sorted(cleaned):
        result.append({
            "id": name,
            "value": name,
            "label": name,
            "name": name
        })

    return result
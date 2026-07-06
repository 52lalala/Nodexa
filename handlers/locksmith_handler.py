import math
from typing import Any
from sqlalchemy.orm import Session
from models.node import Node
from models.relation import Relation


def handle(plugin: dict, params: dict[str, Any], db: Session) -> dict[str, Any]:
    action = params["action"]

    if action == "find_locksmith":
        return _find_locksmith(params, db)
    elif action == "get_quote":
        return _get_quote(params, db)
    else:
        raise ValueError(f"未知操作: {action}")


def _find_locksmith(params: dict, db: Session) -> dict:
    location = _parse_location(params["location"])
    lock_type = params["lock_type"]

    locksmiths = db.query(Node).filter(Node.type == "Locksmith").all()

    matched = []
    for ls in locksmiths:
        skills = ls.attributes.get("skills", [])
        if lock_type in skills:
            ls_loc = ls.attributes.get("location")
            if ls_loc:
                dist = _haversine(location["lat"], location["lng"], ls_loc["lat"], ls_loc["lng"])
                matched.append((dist, ls))

    matched.sort(key=lambda x: x[0])
    top = matched[:5]

    ls_ids = [ls.id for _, ls in top]
    relations = (
        db.query(Relation)
        .filter(Relation.from_node.in_(ls_ids))
        .all()
    )

    district_ids = {r.to_node for r in relations if r.type == "COVERS"}
    districts = db.query(Node).filter(Node.id.in_(district_ids)).all()

    all_nodes = {d.id: d for d in districts}
    for _, ls in top:
        all_nodes[ls.id] = ls

    ls_names = [ls.name for _, ls in top]
    answer = f"为您找到 {len(top)} 位可处理{lock_type}的锁匠: {', '.join(ls_names)}"

    return {
        "answer": answer,
        "nodes": [{"id": n.id, "type": n.type, "name": n.name, "attributes": n.attributes or {}} for n in all_nodes.values()],
        "relations": [{"from": r.from_node, "to": r.to_node, "type": r.type} for r in relations],
    }


def _get_quote(params: dict, db: Session) -> dict:
    location = _parse_location(params["location"])
    lock_type = params["lock_type"]
    time_period = params.get("time_period", "白天")

    locksmiths = db.query(Node).filter(Node.type == "Locksmith").all()

    quotes = []
    for ls in locksmiths:
        skills = ls.attributes.get("skills", [])
        if lock_type not in skills:
            continue
        ls_loc = ls.attributes.get("location")
        base_price = ls.attributes.get("base_price", 80)

        dist = 5.0
        if ls_loc:
            dist = _haversine(location["lat"], location["lng"], ls_loc["lat"], ls_loc["lng"])

        time_mult = {"白天": 1.0, "夜间": 1.5, "凌晨": 2.0}.get(time_period, 1.0)
        total = base_price * time_mult

        quotes.append((total, dist, ls))

    quotes.sort(key=lambda x: x[0])
    top = quotes[:3]

    lines = []
    for total, dist, ls in top:
        lines.append(f"{ls.name}: ¥{total:.0f}（约{dist:.1f}km{'，含时段附加费' if total > ls.attributes.get('base_price', 80) else ''}）")

    answer = f"预估报价（{lock_type}，{time_period}）:\n" + "\n".join(lines)

    return {
        "answer": answer,
        "nodes": [{"id": ls.id, "type": ls.type, "name": ls.name, "attributes": ls.attributes or {}} for _, _, ls in top],
        "relations": [],
    }


def _parse_location(raw: str | dict | list) -> dict:
    if isinstance(raw, dict) and "lat" in raw and "lng" in raw:
        return {"lat": raw["lat"], "lng": raw["lng"]}
    if isinstance(raw, list) and len(raw) == 2:
        return {"lat": raw[0], "lng": raw[1]}
    if isinstance(raw, str):
        parts = raw.replace(" ", "").split(",")
        if len(parts) == 2:
            return {"lat": float(parts[0]), "lng": float(parts[1])}
    return {"lat": 39.9, "lng": 116.4}


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

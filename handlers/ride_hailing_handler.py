import math
from typing import Any
from sqlalchemy.orm import Session
from models.node import Node
from models.relation import Relation


def handle(plugin: dict, params: dict[str, Any], db: Session) -> dict[str, Any]:
    action = params["action"]

    if action == "find_car":
        return _find_car(params, db)
    elif action == "estimate_fare":
        return _estimate_fare(params, db)
    else:
        raise ValueError(f"未知操作: {action}")


def _find_car(params: dict, db: Session) -> dict:
    pickup = _parse_location(params["pickup"])
    car_type = params.get("car_type")

    vehicles = db.query(Node).filter(Node.type == "Vehicle").all()

    matched = []
    for v in vehicles:
        if v.attributes.get("status") != "idle":
            continue
        if car_type and v.attributes.get("type") != car_type:
            continue
        v_loc = v.attributes.get("location")
        if v_loc:
            dist = _haversine(pickup["lat"], pickup["lng"], v_loc["lat"], v_loc["lng"])
            matched.append((dist, v))

    matched.sort(key=lambda x: x[0])
    top = matched[:5]

    v_ids = [v.id for _, v in top]
    relations = (
        db.query(Relation)
        .filter(Relation.from_node.in_(v_ids) | Relation.to_node.in_(v_ids))
        .all()
    )

    driver_ids = set()
    for r in relations:
        if r.type == "DRIVEN_BY" and r.from_node in v_ids:
            driver_ids.add(r.to_node)

    drivers = db.query(Node).filter(Node.id.in_(driver_ids)).all()

    all_nodes = {d.id: d for d in drivers}
    for _, v in top:
        all_nodes[v.id] = v

    car_desc = []
    for dist, v in top:
        driver_rel = [r for r in relations if r.type == "DRIVEN_BY" and r.from_node == v.id]
        driver_name = ""
        if driver_rel:
            d = next((d for d in drivers if d.id == driver_rel[0].to_node), None)
            if d:
                driver_name = f"，司机: {d.attributes.get('name', '')}"
        car_desc.append(f"{v.attributes.get('plate', '')} ({v.attributes.get('type', '')}) 约{dist:.1f}km{driver_name}")

    type_desc = f"「{car_type}」" if car_type else ""
    answer = f"为您找到 {len(top)} 辆附近空闲{type_desc}车辆:\n" + "\n".join(car_desc)

    return {
        "answer": answer,
        "nodes": [{"id": n.id, "type": n.type, "name": n.name, "attributes": n.attributes or {}} for n in all_nodes.values()],
        "relations": [{"from": r.from_node, "to": r.to_node, "type": r.type} for r in relations],
    }


def _estimate_fare(params: dict, db: Session) -> dict:
    pickup = _parse_location(params["pickup"])
    dropoff = _parse_location(params.get("dropoff", "39.93, 116.45"))
    car_type = params.get("car_type", "快车")

    distance = _haversine(pickup["lat"], pickup["lng"], dropoff["lat"], dropoff["lng"])

    rate_map = {"快车": 2.5, "专车": 4.0, "拼车": 1.8, "豪华车": 8.0}
    rate = rate_map.get(car_type, 2.5)
    fare = max(10.0, distance * rate)

    vehicles = (
        db.query(Node)
        .filter(Node.type == "Vehicle", Node.attributes["status"].as_string() == "idle")
        .all()
    )
    vehicles = [v for v in vehicles if v.attributes.get("type") == car_type]

    vehicle_ids = [v.id for v in vehicles[:3]]
    if not vehicle_ids:
        return {
            "answer": f"当前无可用的{car_type}车辆，预估费用 ¥{fare:.1f}（约{distance:.1f}km）",
            "nodes": [],
            "relations": [],
        }

    relations = (
        db.query(Relation)
        .filter(Relation.from_node.in_(vehicle_ids) | Relation.to_node.in_(vehicle_ids))
        .all()
    )

    driver_ids = {r.to_node for r in relations if r.type == "DRIVEN_BY" and r.from_node in vehicle_ids}
    drivers = db.query(Node).filter(Node.id.in_(driver_ids)).all()

    all_nodes = {d.id: d for d in drivers}
    for v in vehicles[:3]:
        all_nodes[v.id] = v

    answer = f"预估费用 ¥{fare:.1f}（{car_type}，约{distance:.1f}km），附近有 {len([v for v in vehicles if v.attributes.get('status')=='idle'])} 辆可用车"

    return {
        "answer": answer,
        "nodes": [{"id": n.id, "type": n.type, "name": n.name, "attributes": n.attributes or {}} for n in all_nodes.values()],
        "relations": [{"from": r.from_node, "to": r.to_node, "type": r.type} for r in relations],
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

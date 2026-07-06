import math
from typing import Any
from sqlalchemy.orm import Session
from models.node import Node
from models.relation import Relation


def handle(plugin: dict, params: dict[str, Any], db: Session) -> dict[str, Any]:
    action = params["action"]

    if action == "find_store":
        return _find_store(params, db)
    elif action == "find_product":
        return _find_product(params, db)
    else:
        raise ValueError(f"未知操作: {action}")


def _find_store(params: dict, db: Session) -> dict:
    location = _parse_location(params["location"])
    min_rating = params.get("min_rating", 0)

    stores = db.query(Node).filter(Node.type == "Store").all()

    nearby = []
    for s in stores:
        store_loc = s.attributes.get("location")
        if store_loc:
            dist = _haversine(location["lat"], location["lng"], store_loc["lat"], store_loc["lng"])
            rating = s.attributes.get("rating", 0)
            if rating >= min_rating:
                nearby.append((dist, s))

    nearby.sort(key=lambda x: x[0])

    top = nearby[:5]
    node_ids = [n.id for _, n in top]

    relations = (
        db.query(Relation)
        .filter(Relation.from_node.in_(node_ids) | Relation.to_node.in_(node_ids))
        .all()
    )

    related_node_ids = set()
    for r in relations:
        if r.from_node in node_ids:
            related_node_ids.add(r.to_node)
        if r.to_node in node_ids:
            related_node_ids.add(r.from_node)

    all_nodes = {n.id: n for _, n in top}
    if related_node_ids:
        extra = db.query(Node).filter(Node.id.in_(related_node_ids)).all()
        for n in extra:
            all_nodes[n.id] = n

    store_names = [n.name for _, n in top]
    answer = f"为您找到 {len(top)} 家附近宠物用品门店: {', '.join(store_names)}"

    return {
        "answer": answer,
        "nodes": [{"id": n.id, "type": n.type, "name": n.name, "attributes": n.attributes or {}} for n in all_nodes.values()],
        "relations": [{"from": r.from_node, "to": r.to_node, "type": r.type} for r in relations],
    }


def _find_product(params: dict, db: Session) -> dict:
    pet_type = params.get("pet_type")
    category = params.get("category")

    q = db.query(Node).filter(Node.type == "Product")
    if pet_type:
        q = q.filter(Node.attributes["pet_type"].as_string() == pet_type)
    if category:
        q = q.filter(Node.attributes["category"].as_string() == category)

    products = q.all()
    product_ids = [p.id for p in products]

    relations = (
        db.query(Relation)
        .filter(Relation.to_node.in_(product_ids))
        .all()
    )

    store_ids = {r.from_node for r in relations if r.type == "SELLS"}
    stores = db.query(Node).filter(Node.id.in_(store_ids)).all()

    all_nodes = {s.id: s for s in stores}
    for p in products:
        all_nodes[p.id] = p

    filters_desc = []
    if pet_type:
        filters_desc.append(f"宠物类型「{pet_type}」")
    if category:
        filters_desc.append(f"分类「{category}」")
    filter_str = "、".join(filters_desc) if filters_desc else "全部"

    answer = f"为您找到 {len(products)} 件商品（筛选条件: {filter_str}），分布在 {len(stores)} 家门店"

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

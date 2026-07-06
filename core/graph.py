from typing import Any
from sqlalchemy.orm import Session
from models.node import Node
from models.relation import Relation
from models.event import Event


def query_nodes(db: Session, node_type: str | None = None) -> list[dict[str, Any]]:
    q = db.query(Node)
    if node_type:
        q = q.filter(Node.type == node_type)
    rows = q.all()
    return [_node_to_dict(r) for r in rows]


def query_relations(db: Session, relation_type: str | None = None) -> list[dict[str, Any]]:
    q = db.query(Relation)
    if relation_type:
        q = q.filter(Relation.type == relation_type)
    rows = q.all()
    return [_relation_to_dict(r) for r in rows]


def query_nodes_by_ids(db: Session, node_ids: list[str]) -> list[dict[str, Any]]:
    rows = db.query(Node).filter(Node.id.in_(node_ids)).all()
    return [_node_to_dict(r) for r in rows]


def query_relations_by_nodes(db: Session, node_ids: list[str]) -> list[dict[str, Any]]:
    rows = (
        db.query(Relation)
        .filter(
            (Relation.from_node.in_(node_ids)) | (Relation.to_node.in_(node_ids))
        )
        .all()
    )
    return [_relation_to_dict(r) for r in rows]


def insert_event(db: Session, actor: str, action: str, target: str, context: dict[str, Any] | None = None) -> None:
    import uuid, time
    event = Event(
        id=str(uuid.uuid4()),
        actor=actor,
        action=action,
        target=target,
        context=context or {},
        timestamp=int(time.time() * 1000),
    )
    db.add(event)
    db.commit()


def _node_to_dict(node: Node) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type,
        "name": node.name,
        "attributes": node.attributes or {},
    }


def _relation_to_dict(rel: Relation) -> dict[str, Any]:
    return {
        "from": rel.from_node,
        "to": rel.to_node,
        "type": rel.type,
    }

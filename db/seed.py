import json
from pathlib import Path
from sqlalchemy.exc import IntegrityError

from db.connection import SessionLocal, engine as db_engine, Base
from models.node import Node
from models.relation import Relation

PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


def run_seed():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    try:
        existing_nodes = db.query(Node).count()
        if existing_nodes > 0:
            return

        for filepath in PLUGINS_DIR.glob("*.json"):
            with open(filepath, "r", encoding="utf-8") as f:
                plugin = json.load(f)

            seed = plugin.get("seed_data", {})
            nodes_data = seed.get("nodes", [])
            relations_data = seed.get("relations", [])

            for nd in nodes_data:
                node = Node(
                    id=nd["id"],
                    type=nd["type"],
                    name=nd["name"],
                    attributes=nd.get("attributes", {}),
                )
                db.add(node)

            for rd in relations_data:
                rel = Relation(
                    id=rd["id"],
                    from_node=rd["from_node"],
                    to_node=rd["to_node"],
                    type=rd["type"],
                    weight=rd.get("weight", 0.0),
                    timestamp=rd.get("timestamp", 0),
                )
                db.add(rel)

        db.commit()
    except IntegrityError:
        db.rollback()
    finally:
        db.close()

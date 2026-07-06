from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.schemas import (
    IntentsResponse,
    IntentItem,
    ExecuteRequest,
    ExecuteSuccess,
    ExecuteError,
    NodeItem,
    RelationItem,
)
from db.connection import get_db
from core import engine

router = APIRouter()


@router.get("/intents", response_model=IntentsResponse)
def get_intents():
    intents = engine.list_intents()
    return IntentsResponse(
        intents=[IntentItem(**i) for i in intents]
    )


@router.get("/plugins/{intent}")
def get_plugin(intent: str):
    plugin = engine.get_plugin(intent)
    if plugin is None:
        return ExecuteError(
            success=False,
            error={
                "code": "PLUGIN_NOT_FOUND",
                "message": f"未找到行业 '{intent}'",
                "details": {},
            },
        ).model_dump()
    return plugin


@router.post("/execute")
def execute(req: ExecuteRequest, db: Session = Depends(get_db)):
    result = engine.execute(req.intent, req.params, db)
    if not result["success"]:
        return ExecuteError(success=False, error=result["error"]).model_dump()

    nodes = [NodeItem(**n) for n in result.get("nodes", [])]
    relations = _build_relations(result.get("relations", []))
    return ExecuteSuccess(
        success=True,
        answer=result["answer"],
        nodes=nodes,
        relations=relations,
    ).model_dump(by_alias=True)


def _build_relations(raw: list[dict]) -> list[RelationItem]:
    items = []
    for r in raw:
        items.append(RelationItem(
            from_=r["from"],
            to=r["to"],
            type=r["type"],
        ))
    return items

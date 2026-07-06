from pydantic import BaseModel, Field
from typing import Any


class IntentItem(BaseModel):
    intent: str
    name: str
    description: str


class IntentsResponse(BaseModel):
    intents: list[IntentItem]


class ExecuteRequest(BaseModel):
    intent: str
    params: dict[str, Any] = Field(default_factory=dict)


class NodeItem(BaseModel):
    id: str
    type: str
    name: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class RelationItem(BaseModel):
    from_: str = Field(serialization_alias="from")
    to: str
    type: str

    model_config = {"populate_by_name": True}


class ExecuteSuccess(BaseModel):
    success: bool = True
    answer: str
    nodes: list[NodeItem] = Field(default_factory=list)
    relations: list[RelationItem] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ExecuteError(BaseModel):
    success: bool = False
    error: ErrorDetail

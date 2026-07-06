import json
import os
import importlib
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from core.validator import validate_params

PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


def list_intents() -> list[dict[str, str]]:
    result = []
    for filepath in PLUGINS_DIR.glob("*.json"):
        plugin = _load_plugin_file(filepath)
        result.append({
            "intent": plugin["intent"],
            "name": plugin["name"],
            "description": plugin.get("description", ""),
        })
    return result


def get_plugin(intent: str) -> dict[str, Any] | None:
    filepath = PLUGINS_DIR / f"{intent}.json"
    if not filepath.exists():
        return None
    return _load_plugin_file(filepath)


def execute(intent: str, params: dict[str, Any], db: Session) -> dict[str, Any]:
    plugin = get_plugin(intent)
    if plugin is None:
        return {
            "success": False,
            "error": {
                "code": "PLUGIN_NOT_FOUND",
                "message": f"未找到行业 '{intent}'",
                "details": {},
            },
        }

    errors = validate_params(plugin, params)
    if errors:
        return {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "参数校验失败",
                "details": {"fields": errors},
            },
        }

    try:
        handler_module = importlib.import_module(f"handlers.{intent}_handler")
        result = handler_module.handle(plugin, params, db)
        result["success"] = True
        return result
    except ModuleNotFoundError:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"行业 '{intent}' 的 Handler 未实现",
                "details": {},
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "EXECUTION_ERROR",
                "message": str(e),
                "details": {},
            },
        }


def _load_plugin_file(filepath: Path) -> dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

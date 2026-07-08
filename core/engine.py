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


import re


def build_tools() -> list[dict[str, Any]]:
    tools = []
    for filepath in PLUGINS_DIR.glob("*.json"):
        plugin = _load_plugin_file(filepath)
        action_field = plugin.get("params", {}).get("action")
        if not action_field or action_field.get("type") != "single_select":
            continue

        intent = plugin["intent"]
        for action_key in action_field.get("options", []):
            tool_name = f"{intent}_{action_key}"
            tool_params = _filter_params_for_action(plugin["params"], action_key)
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": _tool_description(plugin, action_key),
                    "parameters": _params_to_json_schema(tool_params),
                },
            })
    return tools


def execute(tool: str, params: dict[str, Any], db: Session) -> dict[str, Any]:
    intent, action = _parse_tool(tool)
    if not intent:
        return {
            "success": False,
            "error": {
                "code": "TOOL_NOT_FOUND",
                "message": f"未找到 tool '{tool}'",
                "details": {},
            },
        }

    params = {**params, "action": action}

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


def _parse_tool(tool: str) -> tuple[str, str]:
    intents = [p.stem for p in PLUGINS_DIR.glob("*.json")]
    for intent in sorted(intents, key=len, reverse=True):
        prefix = intent + "_"
        if tool.startswith(prefix):
            return intent, tool[len(prefix):]
    return "", ""


def _filter_params_for_action(
    params: dict[str, Any], action_key: str
) -> dict[str, Any]:
    result = {}
    for name, field in params.items():
        if name == "action":
            continue
        condition = field.get("condition", "")
        if not condition:
            result[name] = field
        elif _condition_matches(condition, action_key):
            result[name] = field
    return result


def _condition_matches(condition: str, action_key: str) -> bool:
    condition = condition.strip()
    if condition == "action":
        return True
    m = re.search(r"action\s*==\s*['\"]([^'\"]+)['\"]", condition)
    if m:
        return m.group(1) == action_key
    return True


def _params_to_json_schema(params: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, field in params.items():
        ft = field.get("type", "text")
        schema: dict[str, Any] = {}

        if ft == "single_select" and field.get("options"):
            schema = {"type": "string", "enum": field["options"]}
        elif ft == "number":
            schema = {"type": "number"}
        elif ft == "location":
            schema = {"type": "string", "description": "坐标，格式 lat,lng"}
        else:
            schema = {"type": "string"}

        if field.get("prompt"):
            schema["description"] = field["prompt"]
        if "default" in field:
            schema["default"] = field["default"]

        properties[name] = schema
        if field.get("required"):
            required.append(name)

    return {"type": "object", "properties": properties, "required": required}


def _tool_description(plugin: dict[str, Any], action_key: str) -> str:
    actions = plugin.get("actions", {})
    if isinstance(actions, dict) and action_key in actions:
        desc = actions[action_key]
        if isinstance(desc, dict):
            return desc.get("description", action_key)
        return str(desc)
    return f"{plugin.get('description', '')} - {action_key}"


def _load_plugin_file(filepath: Path) -> dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

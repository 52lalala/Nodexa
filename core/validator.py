from typing import Any


def validate_params(plugin: dict, params: dict[str, Any]) -> list[str]:
    errors = []
    plugin_params = plugin.get("params", {})

    for field_name, field_def in plugin_params.items():
        required = field_def.get("required", False)
        value = params.get(field_name)

        if required and (value is None or value == ""):
            errors.append(f"缺少必填参数: {field_name} ({field_def.get('prompt', '')})")
            continue

        if value is not None and value != "":
            field_type = field_def.get("type", "text")
            type_error = _check_type(field_name, value, field_type)
            if type_error:
                errors.append(type_error)
                continue

            validation = field_def.get("validation")
            if validation:
                val_error = _check_validation(field_name, value, validation)
                if val_error:
                    errors.append(val_error)

            if field_type == "single_select":
                options = field_def.get("options", [])
                if options and value not in options:
                    errors.append(f"参数 {field_name} 的值 '{value}' 不在允许选项中: {options}")

    return errors


def _check_type(field_name: str, value: Any, field_type: str) -> str | None:
    if field_type in ("text", "location", "single_select"):
        if not isinstance(value, str):
            return f"参数 {field_name} 应为字符串类型"
    elif field_type == "number":
        if not isinstance(value, (int, float)):
            return f"参数 {field_name} 应为数字类型"
    return None


def _check_validation(field_name: str, value: Any, rule: str) -> str | None:
    return None

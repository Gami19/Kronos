"""Parse Flask request bodies / query strings into Pydantic models."""

from __future__ import annotations

from typing import Any, Literal, TypeVar

from flask import jsonify, request
from pydantic import BaseModel, ValidationError

from backend.schemas.data_requests import ValidateDataBody

T = TypeVar("T", bound=BaseModel)


def _first_user_message(exc: ValidationError, *, default: str) -> str:
    errs = exc.errors()
    if not errs:
        return default
    loc = errs[0].get("loc", ())
    msg = errs[0].get("msg", "")
    if "file_path" in loc:
        return "ファイルパスが指定されていません"
    if "ticker_id" in loc:
        return "ticker_id を指定してください"
    return default if not msg else str(msg)


def parse_json_body(
    model: type[T],
    *,
    force: bool = False,
    silent: bool = True,
    error_format: Literal["load_data", "import_market"] = "load_data",
) -> tuple[T | None, tuple[Any, int] | None]:
    """
    Parse JSON object body into ``model``.

    Returns ``(instance, None)`` or ``(None, (jsonify(...), status))``.
    """
    raw = request.get_json(force=force, silent=silent)
    if raw is None and silent:
        raw = {}
    if not isinstance(raw, dict):
        if error_format == "import_market":
            return None, (jsonify({"success": False, "error": "JSON ボディはオブジェクトである必要があります"}), 400)
        return None, (jsonify({"error": "JSON ボディはオブジェクトである必要があります"}), 400)
    try:
        return model.model_validate(raw), None
    except ValidationError as e:
        msg = _first_user_message(e, default="リクエストの形式が正しくありません")
        if error_format == "import_market":
            return None, (jsonify({"success": False, "error": msg}), 400)
        return None, (jsonify({"error": msg}), 400)


def parse_validate_data_body() -> ValidateDataBody:
    """
    Parse POST /api/data/validate body.

    On validation failure (e.g. wrong types for ``file_path``), returns a model with ``file_path``
    cleared so the view responds with HTTP 200 and ``valid: False`` (API contract).
    """
    raw = request.get_json(force=True, silent=True) or {}
    if not isinstance(raw, dict):
        return ValidateDataBody()
    try:
        return ValidateDataBody.model_validate(raw)
    except ValidationError:
        return ValidateDataBody()


def parse_query_params(model: type[T]) -> tuple[T | None, tuple[Any, int] | None]:
    """Parse ``request.args`` (flat) into a model."""
    flat = request.args.to_dict(flat=False)
    # take first value for each key when list
    data = {k: (v[0] if isinstance(v, list) and v else v) for k, v in flat.items()}
    try:
        return model.model_validate(data), None
    except ValidationError as e:
        msg = _first_user_message(e, default="クエリパラメータが正しくありません")
        return None, (jsonify({"success": False, "error": msg}), 400)

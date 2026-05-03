"""In-process Kronos tokenizer / model / predictor (Flask 非依存のモジュール状態)."""

from __future__ import annotations

from typing import Any, Optional

MODEL_AVAILABLE = False

tokenizer: Any = None
model: Any = None
predictor: Any = None

AVAILABLE_MODELS: dict[str, dict[str, Any]] = {
    "kronos-mini": {
        "name": "Kronos-mini",
        "model_id": "NeoQuasar/Kronos-mini",
        "tokenizer_id": "NeoQuasar/Kronos-Tokenizer-2k",
        "context_length": 2048,
        "params": "4.1M",
        "description": "軽量モデル。高速な予測向き",
    },
    "kronos-small": {
        "name": "Kronos-small",
        "model_id": "NeoQuasar/Kronos-small",
        "tokenizer_id": "NeoQuasar/Kronos-Tokenizer-base",
        "context_length": 512,
        "params": "24.7M",
        "description": "小型モデル。性能と速度のバランス型",
    },
    "kronos-base": {
        "name": "Kronos-base",
        "model_id": "NeoQuasar/Kronos-base",
        "tokenizer_id": "NeoQuasar/Kronos-Tokenizer-base",
        "context_length": 512,
        "params": "102.3M",
        "description": "ベースモデル。より高品質な予測",
    },
}


def set_model_available(available: bool) -> None:
    global MODEL_AVAILABLE
    MODEL_AVAILABLE = bool(available)


def set_inference_stack(tok: Any, mod: Any, pred: Any) -> None:
    global tokenizer, model, predictor
    tokenizer = tok
    model = mod
    predictor = pred


def get_tokenizer() -> Any:
    return tokenizer


def get_model() -> Any:
    return model


def get_predictor() -> Any:
    return predictor


def is_predictor_loaded() -> bool:
    return predictor is not None


def inference_ready() -> bool:
    return MODEL_AVAILABLE and predictor is not None

"""学習ジョブ YAML 生成・メタ更新・サブプロセスワーカー。"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys

import yaml

from backend import paths as app_paths
from backend.constants_api import PREDICTION_RESULT_ID_PATTERN, TRAIN_JOB_EXP_NAME


def train_jobs_runs_dir() -> str:
    return app_paths.train_jobs_runs_dir()


def finetune_csv_dir() -> str:
    return app_paths.finetune_csv_dir()


def _atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _utc_now_iso_z():
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _tail_text_file(path, max_lines):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as bf:
            bf.seek(0, os.SEEK_END)
            size = bf.tell()
            chunk = min(size, 131072)
            bf.seek(max(0, size - chunk))
            raw = bf.read()
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        return "\n".join(lines)
    except OSError:
        return None


def _read_train_job_max_context(job_id, default=512):
    cfg_path = os.path.join(train_jobs_runs_dir(), job_id, "config.yaml")
    try:
        with open(cfg_path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        if not doc or "data" not in doc:
            return default
        v = doc["data"].get("max_context", default)
        return int(v)
    except (OSError, TypeError, ValueError, KeyError):
        return default


def _resolve_train_job_checkpoint_paths(job_id):
    jid = (job_id or "").strip()
    if not jid or not PREDICTION_RESULT_ID_PATTERN.fullmatch(jid):
        return None, None, "無効な train_job_id です"
    meta_path = os.path.join(train_jobs_runs_dir(), jid, "meta.json")
    if not os.path.isfile(meta_path):
        return None, None, "ジョブが見つかりません"
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return None, None, f"meta.json の読み込みに失敗しました: {e}"
    if (meta.get("status") or "").strip() != "succeeded":
        return None, None, "ジョブが succeeded ではありません。学習完了後に再度お試しください"
    tok = meta.get("tokenizer_best_model_path")
    bas = meta.get("basemodel_best_model_path")
    if not tok or not bas:
        return None, None, "meta に checkpoint パスがありません"
    if not isinstance(tok, str) or not isinstance(bas, str):
        return None, None, "checkpoint パスが無効です"
    if not os.path.isdir(tok) or not os.path.isdir(bas):
        return None, None, "checkpoint ディレクトリが存在しません"
    try:
        rt = os.path.realpath(tok)
        rb = os.path.realpath(bas)
        root = os.path.realpath(app_paths.project_root())
    except OSError:
        return None, None, "パスの解決に失敗しました"
    for p, label in ((rt, "tokenizer"), (rb, "basemodel")):
        if p != root and not p.startswith(root + os.sep):
            return None, None, f"{label} checkpoint がプロジェクト外です"
    return rt, rb, None


def safe_import_filename_token(s):
    t = re.sub(r"[^a-zA-Z0-9._-]+", "_", (s or "").strip())
    return t or "x"


def build_train_job_yaml_dict(
    data_path,
    pretrained_tokenizer,
    pretrained_predictor,
    job_parent_abs,
    tokenizer_lr,
    predictor_lr,
    tokenizer_epochs,
    basemodel_epochs,
    batch_size,
    log_interval,
    num_workers,
    seed,
    lookback_window,
    predict_window,
    max_context,
    clip,
    train_ratio,
    val_ratio,
    test_ratio,
    accumulation_steps,
    experiment_name,
    experiment_description,
    train_tokenizer,
    train_basemodel,
    skip_existing,
    device_use_cuda,
    device_use_mps,
    device_id,
):
    return {
        "data": {
            "data_path": data_path,
            "lookback_window": lookback_window,
            "predict_window": predict_window,
            "max_context": max_context,
            "clip": clip,
            "train_ratio": train_ratio,
            "val_ratio": val_ratio,
            "test_ratio": test_ratio,
        },
        "training": {
            "tokenizer_epochs": tokenizer_epochs,
            "basemodel_epochs": basemodel_epochs,
            "batch_size": batch_size,
            "log_interval": log_interval,
            "num_workers": num_workers,
            "seed": seed,
            "tokenizer_learning_rate": tokenizer_lr,
            "predictor_learning_rate": predictor_lr,
            "adam_beta1": 0.9,
            "adam_beta2": 0.95,
            "adam_weight_decay": 0.1,
            "accumulation_steps": accumulation_steps,
        },
        "model_paths": {
            "pretrained_tokenizer": pretrained_tokenizer,
            "pretrained_predictor": pretrained_predictor,
            "exp_name": TRAIN_JOB_EXP_NAME,
            "base_path": job_parent_abs,
            "base_save_path": "",
            "finetuned_tokenizer": "",
            "tokenizer_save_name": "tokenizer",
            "basemodel_save_name": "basemodel",
        },
        "experiment": {
            "name": experiment_name,
            "description": experiment_description,
            "use_comet": False,
            "train_tokenizer": train_tokenizer,
            "train_basemodel": train_basemodel,
            "skip_existing": skip_existing,
        },
        "device": {
            "use_cuda": bool(device_use_cuda),
            "use_mps": bool(device_use_mps),
            "device_id": int(device_id),
        },
        "distributed": {
            "use_ddp": False,
            "backend": "nccl",
        },
    }


def run_train_job_worker(job_id, config_abs, finetune_csv_d, cli_extra):
    job_dir = os.path.join(train_jobs_runs_dir(), job_id)
    meta_path = os.path.join(job_dir, "meta.json")
    log_path = os.path.join(job_dir, "train.log")

    def patch_meta(updates):
        try:
            with open(meta_path, encoding="utf-8") as f:
                m = json.load(f)
        except (OSError, json.JSONDecodeError):
            m = {"job_id": job_id}
        m.update(updates)
        m["updated_at"] = _utc_now_iso_z()
        _atomic_write_json(meta_path, m)

    patch_meta({"status": "running"})
    train_script = os.path.join(finetune_csv_d, "train_sequential.py")
    cmd = [sys.executable, train_script, "--config", config_abs] + cli_extra
    exit_code = 1
    try:
        with open(log_path, "ab") as logf:
            p = subprocess.Popen(
                cmd,
                cwd=finetune_csv_d,
                stdout=logf,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
            patch_meta({"pid": p.pid})
            exit_code = p.wait()
    except Exception as e:
        patch_meta(
            {
                "status": "failed",
                "exit_code": 1,
                "error_message": str(e)[:800],
            }
        )
        return

    base_save = os.path.normpath(os.path.join(job_dir, TRAIN_JOB_EXP_NAME))
    tok_best = os.path.join(base_save, "tokenizer", "best_model")
    bas_best = os.path.join(base_save, "basemodel", "best_model")
    tok_ok = os.path.isdir(tok_best)
    bas_ok = os.path.isdir(bas_best)

    status = "succeeded" if exit_code == 0 else "failed"
    err_tail = _tail_text_file(log_path, 40) if status == "failed" else None
    patch_meta(
        {
            "status": status,
            "exit_code": exit_code,
            "tokenizer_best_model_path": tok_best if tok_ok else None,
            "basemodel_best_model_path": bas_best if bas_ok else None,
            "error_message": err_tail,
        }
    )

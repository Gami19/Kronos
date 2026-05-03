"""Blueprint: finetune train jobs under /api/train."""

from __future__ import annotations

import json
import os
import threading
import uuid

import yaml
from flask import Blueprint, jsonify, request

from backend.constants_api import PREDICTION_RESULT_ID_PATTERN
from backend.services import checkpoints
from backend.services import data_io
from backend.services import data_layout as dl
from backend.services import train_jobs_ops as tjo

def train_jobs_create():
    """finetune_csv 学習ジョブを投入する（YAML 生成 → train_sequential サブプロセス）"""
    body = request.get_json(force=True, silent=True) or {}
    data_path = (body.get('data_path') or '').strip()
    if not data_path:
        return jsonify({'success': False, 'error': 'data_path は必須です'}), 400

    ok_dp, err_dp = dl.validate_data_file_path(data_path)
    if not ok_dp:
        return jsonify({'success': False, 'error': err_dp}), 400

    pt_raw = (body.get('pretrained_tokenizer') or os.environ.get('KRONOS_PRETRAINED_TOKENIZER') or '').strip()
    pp_raw = (body.get('pretrained_predictor') or os.environ.get('KRONOS_PRETRAINED_PREDICTOR') or '').strip()
    ok_pt, pt, err_pt = checkpoints.validate_pretrained_dir(pt_raw, 'pretrained_tokenizer')
    if not ok_pt:
        return jsonify({'success': False, 'error': err_pt}), 400
    ok_pp, pp, err_pp = checkpoints.validate_pretrained_dir(pp_raw, 'pretrained_predictor')
    if not ok_pp:
        return jsonify({'success': False, 'error': err_pp}), 400

    train_last_ts, ts_err = data_io.compute_train_last_timestamp_iso(data_path)
    if ts_err:
        return jsonify({'success': False, 'error': f'train_last_timestamp 算出に失敗: {ts_err}'}), 400

    device_req = (body.get('device') or 'cpu').strip().lower()
    if device_req not in ('cuda', 'cpu', 'mps'):
        return jsonify({'success': False, 'error': 'device は cuda / cpu / mps のいずれかです'}), 400
    if device_req == 'mps':
        try:
            import torch as _torch
            if not (hasattr(_torch.backends, 'mps') and _torch.backends.mps.is_available()):
                return jsonify({'success': False, 'error': 'MPS が利用できません（Apple Silicon + 対応 PyTorch が必要です）'}), 400
        except Exception as ex:
            return jsonify({'success': False, 'error': f'MPS 確認に失敗しました: {ex}'}), 400

    use_cuda = device_req == 'cuda'
    use_mps = device_req == 'mps'
    if use_cuda:
        try:
            import torch as _torch
            if not _torch.cuda.is_available():
                return jsonify({'success': False, 'error': 'CUDA が利用できません'}), 400
        except Exception as ex:
            return jsonify({'success': False, 'error': f'CUDA 確認に失敗しました: {ex}'}), 400

    skip_existing = bool(body.get('skip_existing', False))
    skip_tokenizer = bool(body.get('skip_tokenizer', False))
    skip_basemodel = bool(body.get('skip_basemodel', False))
    train_tokenizer = not skip_tokenizer
    train_basemodel = not skip_basemodel
    if not train_tokenizer and not train_basemodel:
        return jsonify({'success': False, 'error': 'tokenizer と basemodel の両方をスキップすることはできません'}), 400

    tokenizer_lr = float(body.get('tokenizer_learning_rate', 2e-4))
    predictor_lr = float(body.get('predictor_learning_rate', 1e-6))
    tokenizer_epochs = int(body.get('tokenizer_epochs', 30))
    basemodel_epochs = int(body.get('basemodel_epochs', 20))
    batch_size = int(body.get('batch_size', 32))
    log_interval = int(body.get('log_interval', 50))
    num_workers = int(body.get('num_workers', 2))
    seed = int(body.get('seed', 42))
    lookback_window = int(body.get('lookback_window', 512))
    predict_window = int(body.get('predict_window', 48))
    max_context = int(body.get('max_context', lookback_window))
    clip = float(body.get('clip', 5.0))
    train_ratio = float(body.get('train_ratio', 0.9))
    val_ratio = float(body.get('val_ratio', 0.1))
    test_ratio = float(body.get('test_ratio', 0.0))
    accumulation_steps = int(body.get('accumulation_steps', 1))
    experiment_name = (body.get('experiment_name') or 'webui_train_job').strip() or 'webui_train_job'
    experiment_description = (body.get('experiment_description') or '').strip()
    device_id = int(body.get('device_id', 0))

    job_id = uuid.uuid4().hex
    if not PREDICTION_RESULT_ID_PATTERN.fullmatch(job_id):
        return jsonify({'success': False, 'error': '内部エラー: job_id が不正です'}), 500

    runs_root = tjo.train_jobs_runs_dir()
    os.makedirs(runs_root, exist_ok=True)
    job_dir = os.path.join(runs_root, job_id)
    os.makedirs(job_dir, exist_ok=True)

    job_parent_abs = os.path.normpath(os.path.realpath(job_dir))
    cfg_dict = tjo.build_train_job_yaml_dict(
        data_path,
        pt,
        pp,
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
        use_cuda,
        use_mps,
        device_id,
    )
    config_path = os.path.join(job_dir, 'config.yaml')
    with open(config_path, 'w', encoding='utf-8') as yf:
        yaml.safe_dump(cfg_dict, yf, default_flow_style=False, allow_unicode=True, sort_keys=False)

    now = tjo._utc_now_iso_z()
    meta = {
        'job_id': job_id,
        'status': 'queued',
        'created_at': now,
        'updated_at': now,
        'data_path': data_path,
        'train_last_timestamp': train_last_ts,
        'config_path': config_path,
        'exit_code': None,
        'tokenizer_best_model_path': None,
        'basemodel_best_model_path': None,
        'error_message': None,
        'device': device_req,
    }
    tjo._atomic_write_json(os.path.join(job_dir, 'meta.json'), meta)

    cli_extra = []
    if skip_existing:
        cli_extra.append('--skip-existing')
    if skip_tokenizer:
        cli_extra.append('--skip-tokenizer')
    if skip_basemodel:
        cli_extra.append('--skip-basemodel')

    finetune_csv_d = tjo.finetune_csv_dir()
    if not os.path.isfile(os.path.join(finetune_csv_d, 'train_sequential.py')):
        return jsonify({'success': False, 'error': 'finetune_csv/train_sequential.py が見つかりません'}), 500

    t = threading.Thread(
        target=tjo.run_train_job_worker,
        args=(job_id, os.path.abspath(config_path), finetune_csv_d, cli_extra),
        daemon=True,
    )
    t.start()

    return jsonify({
        'success': True,
        'job_id': job_id,
        'meta': {
            'job_id': job_id,
            'status': 'queued',
            'train_last_timestamp': train_last_ts,
            'data_path': data_path,
            'config_path': config_path,
        },
    }), 201


def train_jobs_list():
    """学習ジョブ一覧（meta.json 要約）"""
    rd = tjo.train_jobs_runs_dir()
    os.makedirs(rd, exist_ok=True)
    jobs = []
    try:
        names = sorted(os.listdir(rd), reverse=True)
    except OSError:
        names = []
    for name in names:
        if not PREDICTION_RESULT_ID_PATTERN.fullmatch(name):
            continue
        jd = os.path.join(rd, name)
        if not os.path.isdir(jd):
            continue
        mp = os.path.join(jd, 'meta.json')
        if not os.path.isfile(mp):
            continue
        try:
            with open(mp, encoding='utf-8') as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        jobs.append({
            'job_id': meta.get('job_id', name),
            'status': meta.get('status', 'unknown'),
            'created_at': meta.get('created_at'),
            'exit_code': meta.get('exit_code'),
        })
    return jsonify({'success': True, 'jobs': jobs})


def train_jobs_get(job_id):
    """ジョブの meta.json 全文"""
    if not PREDICTION_RESULT_ID_PATTERN.fullmatch(job_id):
        return jsonify({'success': False, 'error': '無効な job_id です'}), 400
    mp = os.path.join(tjo.train_jobs_runs_dir(), job_id, 'meta.json')
    if not os.path.isfile(mp):
        return jsonify({'success': False, 'error': 'ジョブが見つかりません'}), 404
    try:
        with open(mp, encoding='utf-8') as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': True, 'meta': meta})


def train_jobs_log(job_id):
    """train.log の末尾"""
    if not PREDICTION_RESULT_ID_PATTERN.fullmatch(job_id):
        return jsonify({'success': False, 'error': '無効な job_id です'}), 400
    try:
        tail_lines = int(request.args.get('tail_lines', 200))
    except ValueError:
        tail_lines = 200
    tail_lines = max(1, min(tail_lines, 5000))
    lp = os.path.join(tjo.train_jobs_runs_dir(), job_id, 'train.log')
    text = tjo._tail_text_file(lp, tail_lines)
    if text is None:
        return jsonify({'success': False, 'error': 'ログファイルがありません'}), 404
    return jsonify({'success': True, 'job_id': job_id, 'log': text})



train_bp = Blueprint("train", __name__, url_prefix="/api/train")

train_bp.add_url_rule("/jobs", view_func=train_jobs_create, methods=["POST"])
train_bp.add_url_rule("/jobs", view_func=train_jobs_list, methods=["GET"])
train_bp.add_url_rule("/jobs/<job_id>", view_func=train_jobs_get, methods=["GET"])
train_bp.add_url_rule("/jobs/<job_id>/log", view_func=train_jobs_log, methods=["GET"])

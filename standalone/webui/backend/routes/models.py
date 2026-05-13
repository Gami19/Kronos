"""Blueprint: load-model."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend import model_runtime as mr
from backend.kronos_loader import Kronos, KronosPredictor, KronosTokenizer
from backend.services import checkpoints
from backend.services import train_jobs_ops as tjo

def load_model():
    """
    Kronos モデルを読み込む。次のいずれか一つのみ指定すること（排他）:
    - model_key: Hugging Face 事前学習（従来）
    - train_job_id: Phase 2 の meta.json から checkpoint 解決
    - local_tokenizer_path + local_predictor_path: リポジトリ内ローカル checkpoint
    """
    try:
        if not mr.MODEL_AVAILABLE:
            return jsonify({'error': 'Kronos モデルライブラリが利用できません'}), 400

        data = request.get_json(force=True, silent=True) or {}
        device = data.get('device', 'cpu')

        mk = (data.get('model_key') or '').strip() or None
        tj = (data.get('train_job_id') or '').strip() or None
        lt = (data.get('local_tokenizer_path') or '').strip() or None
        lp = (data.get('local_predictor_path') or '').strip() or None

        if tj and (mk or lt or lp):
            return jsonify({'error': 'train_job_id を指定するときは model_key および local_* を指定できません'}), 400
        if (lt or lp) and not (lt and lp):
            return jsonify({'error': 'local_tokenizer_path と local_predictor_path は両方指定してください'}), 400
        if lt and lp and (mk or tj):
            return jsonify({'error': 'local_* を指定するときは model_key および train_job_id を指定できません'}), 400
        if mk and (tj or lt or lp):
            return jsonify({'error': 'model_key を指定するときは train_job_id および local_* を指定できません'}), 400

        raw_mc = data.get('max_context')
        max_context_body = None
        if raw_mc is not None and raw_mc != '':
            try:
                max_context_body = int(raw_mc)
            except (TypeError, ValueError):
                return jsonify({'error': 'max_context は整数で指定してください'}), 400
            if max_context_body < 32 or max_context_body > 32768:
                return jsonify({'error': 'max_context は 32〜32768 の範囲で指定してください'}), 400

        if tj:
            tok_path, bas_path, err = tjo._resolve_train_job_checkpoint_paths(tj)
            if err:
                return jsonify({'error': err}), 400
            max_ctx = max_context_body if max_context_body is not None else tjo._read_train_job_max_context(tj)
            tok = KronosTokenizer.from_pretrained(tok_path)
            mod = Kronos.from_pretrained(bas_path)
            pred = KronosPredictor(mod, tok, device=device, max_context=max_ctx)
            mr.set_inference_stack(tok, mod, pred)
            return jsonify({
                'success': True,
                'load_source': 'train_job',
                'train_job_id': tj,
                'tokenizer_path': tok_path,
                'predictor_path': bas_path,
                'message': f'学習ジョブのモデルを読み込みました（job={tj}）デバイス: {device}, max_context={max_ctx}',
                'model_info': {
                    'name': f'Fine-tuned (job {tj[:8]}…)',
                    'params': 'custom',
                    'context_length': max_ctx,
                    'description': f'tokenizer: {tok_path} / predictor: {bas_path}',
                },
            })

        if lt and lp:
            ok_t, tok_path, e1 = checkpoints.validate_checkpoint_dir(lt, 'local_tokenizer_path')
            if not ok_t:
                return jsonify({'error': e1}), 400
            ok_p, bas_path, e2 = checkpoints.validate_checkpoint_dir(lp, 'local_predictor_path')
            if not ok_p:
                return jsonify({'error': e2}), 400
            max_ctx = max_context_body if max_context_body is not None else 512
            tok = KronosTokenizer.from_pretrained(tok_path)
            mod = Kronos.from_pretrained(bas_path)
            pred = KronosPredictor(mod, tok, device=device, max_context=max_ctx)
            mr.set_inference_stack(tok, mod, pred)
            return jsonify({
                'success': True,
                'load_source': 'local',
                'tokenizer_path': tok_path,
                'predictor_path': bas_path,
                'message': f'ローカル checkpoint を読み込みました。デバイス: {device}, max_context={max_ctx}',
                'model_info': {
                    'name': 'Local checkpoints',
                    'params': 'custom',
                    'context_length': max_ctx,
                    'description': f'tokenizer: {tok_path} / predictor: {bas_path}',
                },
            })

        model_key = mk or 'kronos-small'
        if max_context_body is not None:
            return jsonify({'error': 'model_key モードでは max_context を指定できません（モデル定義に従います）'}), 400
        if model_key not in mr.AVAILABLE_MODELS:
            return jsonify({'error': f'未対応のモデルです: {model_key}'}), 400

        model_config = mr.AVAILABLE_MODELS[model_key]
        tok = KronosTokenizer.from_pretrained(model_config['tokenizer_id'])
        mod = Kronos.from_pretrained(model_config['model_id'])
        pred = KronosPredictor(
            mod, tok, device=device, max_context=model_config['context_length']
        )
        mr.set_inference_stack(tok, mod, pred)

        return jsonify({
            'success': True,
            'load_source': 'hf',
            'message': f'モデルを読み込みました: {model_config["name"]}（{model_config["params"]}）デバイス: {device}',
            'model_info': {
                'name': model_config['name'],
                'params': model_config['params'],
                'context_length': model_config['context_length'],
                'description': model_config['description'],
            },
        })

    except Exception as e:
        return jsonify({'error': f'モデルの読み込みに失敗しました: {str(e)}'}), 500



models_bp = Blueprint("models", __name__, url_prefix="/api")

models_bp.add_url_rule("/load-model", view_func=load_model, methods=["POST"])

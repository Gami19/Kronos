"""Blueprint: synchronous backtest v1."""

from __future__ import annotations

import numpy as np
import pandas as pd
from flask import Blueprint, jsonify, request

from backend import model_runtime as mr
from backend.kronos_loader import Kronos, KronosPredictor, KronosTokenizer
from backend.lib.backtest_v1 import simulate_v1_ooh_strategy_bh
from backend.services import checkpoints
from backend.services import data_io
from backend.services import data_layout as dl
from backend.services import train_jobs_ops as tjo

def backtest_run():
    """
    docs/バックテスト.md v1.0 同期バックテスト。
    checkpoint は train_job_id または local_tokenizer_path + local_predictor_path（排他）。
    """
    if not mr.MODEL_AVAILABLE:
        return jsonify({'error': 'Kronos モデルライブラリが利用できません'}), 400

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({'error': 'JSON ボディが無効です'}), 400

    spec = (data.get('backtest_spec_version') or '').strip()
    if spec != '1.0':
        return jsonify({'error': 'backtest_spec_version は "1.0" を指定してください'}), 400

    file_path = (data.get('data_path') or data.get('file_path') or '').strip()
    if not file_path:
        return jsonify({'error': 'data_path（または file_path）を指定してください'}), 400

    ok_path, err_path = dl.validate_data_file_path(file_path)
    if not ok_path:
        return jsonify({'error': err_path}), 400

    tls_raw = data.get('train_last_timestamp')
    if not tls_raw or not isinstance(tls_raw, str) or not str(tls_raw).strip():
        return jsonify({'error': 'train_last_timestamp は必須です（ISO 日時文字列）'}), 400
    try:
        train_cutoff = pd.Timestamp(str(tls_raw).strip())
        if pd.isna(train_cutoff):
            raise ValueError('na')
    except Exception:
        return jsonify({'error': 'train_last_timestamp を解釈できませんでした'}), 400

    eval_start = data.get('eval_start')
    eval_end = data.get('eval_end')

    try:
        lookback = int(data.get('lookback', 400))
    except (TypeError, ValueError):
        return jsonify({'error': 'lookback は整数で指定してください'}), 400
    if lookback < 2:
        return jsonify({'error': 'lookback は 2 以上を指定してください'}), 400

    try:
        pred_len_body = int(data.get('pred_len', 1))
    except (TypeError, ValueError):
        return jsonify({'error': 'pred_len は整数で指定してください'}), 400
    if pred_len_body < 1:
        return jsonify({'error': 'pred_len は 1 以上を指定してください'}), 400

    try:
        T = float(data.get('T', data.get('temperature', 1.0)))
    except (TypeError, ValueError):
        return jsonify({'error': 'T（temperature）は数値で指定してください'}), 400

    try:
        top_p = float(data.get('top_p', 0.9))
    except (TypeError, ValueError):
        return jsonify({'error': 'top_p は数値で指定してください'}), 400

    try:
        sample_count = int(data.get('sample_count', 1))
    except (TypeError, ValueError):
        return jsonify({'error': 'sample_count は整数で指定してください'}), 400
    if sample_count < 1:
        return jsonify({'error': 'sample_count は 1 以上を指定してください'}), 400

    device = (data.get('device') or 'cpu').strip() or 'cpu'

    tj = (data.get('train_job_id') or '').strip() or None
    lt = (data.get('local_tokenizer_path') or '').strip() or None
    lp = (data.get('local_predictor_path') or '').strip() or None

    if tj and (lt or lp):
        return jsonify({'error': 'train_job_id と local_* は同時に指定できません'}), 400
    if (lt or lp) and not (lt and lp):
        return jsonify({'error': 'local_tokenizer_path と local_predictor_path は両方指定してください'}), 400
    if not tj and not (lt and lp):
        return jsonify({'error': 'train_job_id または local_tokenizer_path + local_predictor_path を指定してください'}), 400

    raw_mc = data.get('max_context')
    max_context_body = None
    if raw_mc is not None and raw_mc != '':
        try:
            max_context_body = int(raw_mc)
        except (TypeError, ValueError):
            return jsonify({'error': 'max_context は整数で指定してください'}), 400
        if max_context_body < 32 or max_context_body > 32768:
            return jsonify({'error': 'max_context は 32〜32768 の範囲で指定してください'}), 400

    tok_path = None
    bas_path = None
    if tj:
        tok_path, bas_path, err = tjo._resolve_train_job_checkpoint_paths(tj)
        if err:
            return jsonify({'error': err}), 400
        max_ctx = max_context_body if max_context_body is not None else tjo._read_train_job_max_context(tj)
    else:
        ok_t, tok_path, e1 = checkpoints.validate_checkpoint_dir(lt, 'local_tokenizer_path')
        if not ok_t:
            return jsonify({'error': e1}), 400
        ok_p, bas_path, e2 = checkpoints.validate_checkpoint_dir(lp, 'local_predictor_path')
        if not ok_p:
            return jsonify({'error': e2}), 400
        max_ctx = max_context_body if max_context_body is not None else 512

    if lookback > max_ctx:
        return jsonify({'error': f'lookback（{lookback}）が max_context（{max_ctx}）を超えています'}), 400

    df, err = data_io.load_data_file(file_path)
    if err:
        return jsonify({'error': err}), 400
    n = len(df)
    if n < lookback + 1:
        return jsonify({'error': f'データが不足しています（最低 {lookback + 1} 行必要、現在 {n} 行）'}), 400

    mask = np.ones(n, dtype=bool)
    try:
        if eval_start not in (None, ''):
            mask &= (df['timestamps'] >= pd.to_datetime(eval_start)).values
        if eval_end not in (None, ''):
            mask &= (df['timestamps'] <= pd.to_datetime(eval_end)).values
    except Exception as e:
        return jsonify({'error': f'eval_start / eval_end を解釈できませんでした: {e}'}), 400

    positions = np.flatnonzero(mask)
    if positions.size == 0:
        return jsonify({'error': '評価窓に該当する行がありません'}), 400
    i0 = int(positions[0])
    i1 = int(positions[-1])
    if not np.all(np.diff(positions) == 1):
        return jsonify({'error': 'eval_start / eval_end の結果が時系列で連続していません'}), 400

    if i1 - i0 < 1:
        return jsonify({'error': '評価窓には少なくとも 2 本のバーが必要です（open-to-open 用）'}), 400

    eval_ts = df['timestamps'].iloc[i0 : i1 + 1]
    if not (eval_ts > train_cutoff).all():
        return jsonify({'error': '評価窓の全タイムスタンプが train_last_timestamp より後である必要があります'}), 400

    t_lo = i0
    t_hi = i1 - 1
    if t_hi < t_lo:
        return jsonify({'error': '内部エラー: OOH 範囲が無効です'}), 400

    # シグナル want_long[t] が必要な t は最大で t_hi-1（open t_hi のポジション用）
    t_pred_lo = max(lookback - 1, (i0 - 1) if i0 > 0 else lookback - 1)
    t_pred_hi = min(t_hi - 1, n - 2)
    if t_pred_lo > t_pred_hi:
        return jsonify({'error': '評価窓と lookback の組合せではシグナルを計算できません'}), 400

    required_cols = ['open', 'high', 'low', 'close']
    if 'volume' in df.columns:
        required_cols.append('volume')

    try:
        local_tok = KronosTokenizer.from_pretrained(tok_path)
        local_model = Kronos.from_pretrained(bas_path)
        local_predictor = KronosPredictor(
            local_model, local_tok, device=device, max_context=max_ctx
        )
    except Exception as e:
        return jsonify({'error': f'checkpoint の読み込みに失敗しました: {e}'}), 500

    want_long: list = [None] * n
    pred_len_use = 1

    try:
        for t in range(t_pred_lo, t_pred_hi + 1):
            if t + 1 >= n:
                break
            sl = t - lookback + 1
            x_df = df.iloc[sl : t + 1][required_cols].copy()
            x_timestamp = df.iloc[sl : t + 1]['timestamps']
            y_timestamp = df.iloc[t + 1 : t + 1 + pred_len_use]['timestamps']
            if len(y_timestamp) < pred_len_use:
                break
            if isinstance(x_timestamp, pd.DatetimeIndex):
                x_timestamp = pd.Series(x_timestamp, name='timestamps')
            if isinstance(y_timestamp, pd.DatetimeIndex):
                y_timestamp = pd.Series(y_timestamp, name='timestamps')
            pred_df = local_predictor.predict(
                df=x_df,
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=pred_len_use,
                T=T,
                top_p=top_p,
                sample_count=sample_count,
                verbose=False,
            )
            hat_c = float(pred_df['close'].iloc[0])
            c_t = float(df['close'].iloc[t])
            if c_t == 0:
                return jsonify({'error': f'バー {t} の終値が 0 です'}), 400
            r_hat = (hat_c - c_t) / c_t
            want_long[t] = r_hat > 0.0
    except Exception as e:
        return jsonify({'error': f'バックテスト推論に失敗しました: {e}'}), 500

    opens = df['open'].astype(float).tolist()
    step_ts = []
    for t in range(t_lo, t_hi + 1):
        ts = df['timestamps'].iloc[t]
        step_ts.append(ts.isoformat() if hasattr(ts, 'isoformat') and not pd.isna(ts) else str(t))

    try:
        strat_curve, bh_curve, _, metrics = simulate_v1_ooh_strategy_bh(
            opens, t_lo, t_hi, want_long, step_timestamp_iso=step_ts
        )
    except Exception as e:
        return jsonify({'error': f'シミュレーションに失敗しました: {e}'}), 500

    series_timestamps = []
    for k in range(len(strat_curve)):
        ix = min(t_lo + k, n - 1)
        ts = df['timestamps'].iloc[ix]
        series_timestamps.append(ts.isoformat() if hasattr(ts, 'isoformat') and not pd.isna(ts) else str(ix))

    return jsonify({
        'success': True,
        'backtest_spec_version': '1.0',
        'metrics': metrics,
        'series': {
            'timestamps': series_timestamps,
            'strategy_equity': strat_curve,
            'bh_equity': bh_curve,
        },
        'message': (
            f'バックテスト完了（バー {t_lo}〜{t_hi} の open-to-open、pred_len={pred_len_body} は v1.0 で先頭 1 ステップのみ使用）'
        ),
    })



backtest_bp = Blueprint("backtest", __name__, url_prefix="/api/backtest")

backtest_bp.add_url_rule("/run", view_func=backtest_run, methods=["POST"])

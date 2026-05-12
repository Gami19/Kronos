"""Blueprint: load-data, import-market, upload, validate."""

from __future__ import annotations

import os

import pandas as pd
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from backend.lib.data_path_rules import TICKER_FOLDER_PATTERN
from backend.services import data_io
from backend.services import data_layout as dl
from backend.services import train_jobs_ops as tjo

def load_data():
    """データファイルを読み込み、メタ情報を返す"""
    from backend.schemas.data_requests import LoadDataBody
    from backend.schemas.flask_parse import parse_json_body

    body, parse_err = parse_json_body(LoadDataBody, silent=True)
    if parse_err:
        return parse_err
    file_path = body.file_path

    try:
        ok, err_msg = dl.validate_data_file_path(file_path)
        if not ok:
            return jsonify({'error': err_msg}), 400
        
        df, error = data_io.load_data_file(file_path)
        if error:
            return jsonify({'error': error}), 400
        
        # データの時間粒度を推定
        def detect_timeframe(df):
            if len(df) < 2:
                return "不明"
            
            time_diffs = []
            for i in range(1, min(10, len(df))):  # 先頭付近の差分を最大10本
                diff = df['timestamps'].iloc[i] - df['timestamps'].iloc[i-1]
                time_diffs.append(diff)
            
            if not time_diffs:
                return "不明"
            
            # 平均間隔
            avg_diff = sum(time_diffs, pd.Timedelta(0)) / len(time_diffs)
            
            # 表示用の文言
            if avg_diff < pd.Timedelta(minutes=1):
                return f"約 {avg_diff.total_seconds():.0f} 秒"
            elif avg_diff < pd.Timedelta(hours=1):
                return f"約 {avg_diff.total_seconds() / 60:.0f} 分"
            elif avg_diff < pd.Timedelta(days=1):
                return f"約 {avg_diff.total_seconds() / 3600:.0f} 時間"
            else:
                return f"約 {avg_diff.days} 日"
        
        # データ情報を返す
        data_info = {
            'rows': len(df),
            'columns': list(df.columns),
            'start_date': df['timestamps'].min().isoformat() if 'timestamps' in df.columns else 'N/A',
            'end_date': df['timestamps'].max().isoformat() if 'timestamps' in df.columns else 'N/A',
            'price_range': {
                'min': float(df[['open', 'high', 'low', 'close']].min().min()),
                'max': float(df[['open', 'high', 'low', 'close']].max().max())
            },
            'prediction_columns': ['open', 'high', 'low', 'close'] + (['volume'] if 'volume' in df.columns else []),
            'timeframe': detect_timeframe(df)
        }
        
        ohlc_rows = data_io.dataframe_to_ohlc_rows(df)

        return jsonify({
            'success': True,
            'data_info': data_info,
            'ohlc_rows': ohlc_rows,
            'message': f'データを読み込みました。全 {len(df)} 行です'
        })
        
    except Exception as e:
        return jsonify({'error': f'データの読み込みに失敗しました: {str(e)}'}), 500


def data_import_market():
    """yfinance で取得した OHLCV を data/<ticker_id>/ に CSV 保存する（同一パスは上書き）"""
    from backend.schemas.data_requests import ImportMarketBody
    from backend.schemas.flask_parse import parse_json_body
    from backend.services import yfinance_market as yfinance_market_svc

    body, parse_err = parse_json_body(
        ImportMarketBody, force=True, silent=True, error_format="import_market"
    )
    if parse_err:
        return parse_err
    ticker_id = body.ticker_id
    interval = body.interval or "5m"
    period = body.period or "5d"
    use_range = body.start is not None and body.end is not None

    if not ticker_id:
        return jsonify({'success': False, 'error': 'ticker_id を指定してください'}), 400
    if ticker_id == dl.FLAT_TICKER_ID:
        return jsonify({'success': False, 'error': '__flat__ には取り込みできません。実銘柄フォルダ名を指定してください'}), 400
    if not TICKER_FOLDER_PATTERN.fullmatch(ticker_id):
        return jsonify({'success': False, 'error': '無効な ticker_id です（英数字・._- で始まる識別子）'}), 400

    if use_range:
        start_s = body.start
        end_s = body.end
        hist, err = yfinance_market_svc.fetch_yfinance_hist_df_range(ticker_id, interval, start_s, end_s)
    else:
        hist, err = yfinance_market_svc.fetch_yfinance_hist_df(ticker_id, interval, period)
    if err:
        return jsonify(err['body']), err['status']

    out_df = yfinance_market_svc.hist_to_import_ohlcv_dataframe(hist)

    if out_df.empty:
        return jsonify({
            'success': False,
            'error': '有効な行が得られませんでした（取得データを確認してください）',
        }), 422

    base = dl.project_data_dir()
    os.makedirs(base, exist_ok=True)
    ticker_dir = os.path.join(base, ticker_id)
    os.makedirs(ticker_dir, exist_ok=True)

    if use_range:
        start_norm = pd.to_datetime(start_s)
        end_norm = pd.to_datetime(end_s)
        start_token = tjo.safe_import_filename_token(pd.Timestamp(start_norm).strftime("%Y%m%d"))
        end_token = tjo.safe_import_filename_token(pd.Timestamp(end_norm).strftime("%Y%m%d"))
        fname = f"import_{tjo.safe_import_filename_token(interval)}_{start_token}_{end_token}.csv"
    else:
        fname = f"import_{tjo.safe_import_filename_token(interval)}_{tjo.safe_import_filename_token(period)}.csv"
    file_path = os.path.join(ticker_dir, fname)
    out_df.to_csv(file_path, index=False)

    ok, err_msg = dl.validate_data_file_path(file_path)
    if not ok:
        try:
            os.remove(file_path)
        except OSError:
            pass
        return jsonify({'success': False, 'error': err_msg or '保存後のパス検証に失敗しました'}), 500

    return jsonify({
        'success': True,
        'ticker_id': ticker_id,
        'file_path': file_path,
        'message': f'保存しました: {fname}',
    })


def data_upload():
    """multipart: ticker_id, file → data/<ticker_id>/ に保存（同一ファイル名は上書き）"""
    ticker_id = (request.form.get('ticker_id') or '').strip()
    if not ticker_id:
        return jsonify({'success': False, 'error': 'ticker_id を指定してください'}), 400
    if ticker_id == dl.FLAT_TICKER_ID:
        return jsonify({'success': False, 'error': '__flat__ へのアップロードはできません'}), 400
    if not TICKER_FOLDER_PATTERN.fullmatch(ticker_id):
        return jsonify({'success': False, 'error': '無効な ticker_id です'}), 400

    up = request.files.get('file')
    if up is None or not up.filename:
        return jsonify({'success': False, 'error': 'file が必要です'}), 400

    safe_name = secure_filename(up.filename)
    if not safe_name:
        return jsonify({'success': False, 'error': '無効なファイル名です'}), 400
    if not (safe_name.endswith('.csv') or safe_name.endswith('.feather')):
        return jsonify({'success': False, 'error': '.csv または .feather のみアップロードできます'}), 400

    base = dl.project_data_dir()
    os.makedirs(base, exist_ok=True)
    ticker_dir = os.path.join(base, ticker_id)
    os.makedirs(ticker_dir, exist_ok=True)
    dest_path = os.path.normpath(os.path.join(ticker_dir, safe_name))
    if not dest_path.startswith(os.path.normpath(ticker_dir) + os.sep):
        return jsonify({'success': False, 'error': '不正なパスです'}), 400

    up.save(dest_path)

    ok, err_msg = dl.validate_data_file_path(dest_path)
    if not ok:
        try:
            os.remove(dest_path)
        except OSError:
            pass
        return jsonify({'success': False, 'error': err_msg or '保存後のパス検証に失敗しました'}), 500

    return jsonify({
        'success': True,
        'ticker_id': ticker_id,
        'file_path': dest_path,
        'filename': safe_name,
    })


def data_validate():
    """data 配下 file_path の形式と必須列を検証する（常に 200、valid で成否を表す）"""
    from backend.schemas.flask_parse import parse_validate_data_body

    body = parse_validate_data_body()
    file_path = body.file_path

    if not file_path or not isinstance(file_path, str):
        return jsonify({'valid': False, 'error': 'file_path を指定してください', 'file_path': None}), 200

    ok, err_msg = dl.validate_data_file_path(file_path)
    if not ok:
        return jsonify({'valid': False, 'error': err_msg, 'file_path': file_path}), 200

    df, load_err = data_io.load_data_file(file_path)
    if load_err:
        return jsonify({'valid': False, 'error': load_err, 'file_path': file_path}), 200

    data_info = {
        'rows': len(df),
        'columns': list(df.columns),
        'start_date': df['timestamps'].min().isoformat() if 'timestamps' in df.columns else None,
        'end_date': df['timestamps'].max().isoformat() if 'timestamps' in df.columns else None,
    }
    return jsonify({
        'valid': True,
        'file_path': file_path,
        'message': '検証に成功しました',
        'data_info': data_info,
    }), 200



data_bp = Blueprint("data", __name__, url_prefix="/api")

data_bp.add_url_rule("/load-data", view_func=load_data, methods=["POST"])
data_bp.add_url_rule("/data/import-market", view_func=data_import_market, methods=["POST"])
data_bp.add_url_rule("/data/upload", view_func=data_upload, methods=["POST"])
data_bp.add_url_rule("/data/validate", view_func=data_validate, methods=["POST"])

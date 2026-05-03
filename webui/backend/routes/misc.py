"""Blueprint: tickers, data-files listing, market-history, model catalog/status."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend import model_runtime as mr
from backend.services import data_layout as dl

def api_tickers():
    """銘柄一覧（data/<ticker>/ またはレガシー __flat__）"""
    items = dl.get_tickers_payload()
    return jsonify({
        'success': True,
        'tickers': items,
        'default_ticker': dl.default_ticker_id() if items else None,
    })


def get_data_files():
    """利用可能なデータファイル一覧（クエリ ticker で銘柄切替。省略時は既定）"""
    items = dl.get_tickers_payload()
    if not items:
        return jsonify([])

    requested = (request.args.get('ticker') or '').strip()
    valid_ids = {t['id'] for t in items}
    ticker_id = requested if requested in valid_ids else dl.default_ticker_id()
    if ticker_id not in valid_ids:
        ticker_id = items[0]['id']

    data_files = dl.load_data_files_for_ticker(ticker_id)
    return jsonify(data_files)

def market_history():
    """yfinance による市場履歴（OHLC）"""
    from backend.schemas.data_requests import MarketHistoryQuery
    from backend.schemas.flask_parse import parse_query_params
    from backend.services import yfinance_market as yfinance_market_svc

    q, parse_err = parse_query_params(MarketHistoryQuery)
    if parse_err:
        return parse_err

    raw_q = q.ticker
    if raw_q is None or str(raw_q).strip() == '':
        ticker = dl.DEFAULT_YFIN_TICKER
    else:
        ticker = dl.yfinance_ticker_from_client_param(str(raw_q).strip())
    interval = q.interval
    period = q.period
    warnings_list = []

    hist, err = yfinance_market_svc.fetch_yfinance_hist_df(ticker, interval, period)
    if err:
        return jsonify(err['body']), err['status']

    rows = yfinance_market_svc.historical_to_api_rows(hist)
    return jsonify({
        'success': True,
        'ticker': ticker,
        'interval': interval,
        'period': period,
        'rows': rows,
        'warnings': warnings_list,
    })


def get_available_models():
    """利用可能なモデル一覧を返す"""
    return jsonify({
        'models': mr.AVAILABLE_MODELS,
        'model_available': mr.MODEL_AVAILABLE
    })

def get_model_status():
    """モデルの読み込み状態を返す"""
    if mr.MODEL_AVAILABLE:
        pred = mr.get_predictor()
        if pred is not None:
            return jsonify({
                'available': True,
                'loaded': True,
                'message': 'Kronos モデルは読み込み済みで利用できます',
                'current_model': {
                    'name': pred.model.__class__.__name__,
                    'device': str(next(pred.model.parameters()).device)
                }
            })
        else:
            return jsonify({
                'available': True,
                'loaded': False,
                'message': 'Kronos モデルは利用可能ですが未読み込みです'
            })
    else:
        return jsonify({
            'available': False,
            'loaded': False,
            'message': 'Kronos モデルライブラリが利用できません。依存関係をインストールしてください'
        })

misc_bp = Blueprint("misc", __name__, url_prefix="/api")

misc_bp.add_url_rule("/tickers", view_func=api_tickers, methods=["GET"])
misc_bp.add_url_rule("/data-files", view_func=get_data_files, methods=["GET"])
misc_bp.add_url_rule("/market-history", view_func=market_history, methods=["GET"])
misc_bp.add_url_rule("/available-models", view_func=get_available_models, methods=["GET"])
misc_bp.add_url_rule("/model-status", view_func=get_model_status, methods=["GET"])

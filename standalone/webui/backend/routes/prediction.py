"""Blueprint: prediction results list/detail, predict."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

import pandas as pd

from backend import model_runtime as mr
from backend import paths as app_paths
from backend.constants_api import PREDICTION_RESULT_ID_PATTERN
from backend.schemas.data_requests import PredictBody
from backend.schemas.flask_parse import parse_json_body
from backend.services import charts_plotly as charts
from backend.services import data_io
from backend.services import data_layout as dl
from backend.services import predict_window as pw
from backend.services import prediction_storage


def list_prediction_results():
    """保存済み予測結果の一覧（メタのみ）"""
    from backend.services import prediction_results as prediction_results_svc

    items = prediction_results_svc.list_result_metas(app_paths.prediction_results_dir())
    return jsonify({'success': True, 'results': items})


def get_prediction_result_detail(result_id):
    """保存済み予測結果 1 件の全文"""
    from backend.services import prediction_results as prediction_results_svc

    payload, err, code = prediction_results_svc.read_result_payload(
        app_paths.prediction_results_dir(), result_id, PREDICTION_RESULT_ID_PATTERN
    )
    if err is not None:
        return jsonify({'error': err}), code
    return jsonify(payload)


def predict():
    """予測を実行する（評価モード: 範囲末尾の lookback 本で予測し、同じ窓の末尾 pred_len 本を実測と比較）。"""
    try:
        body, parse_err = parse_json_body(PredictBody, force=True, silent=True, error_format="predict")
        if parse_err:
            return parse_err

        file_path = body.file_path
        lookback = body.lookback
        pred_len = body.pred_len
        temperature = body.temperature
        top_p = body.top_p
        sample_count = body.sample_count
        start_date = body.start_date
        end_date = body.end_date

        ok_path, err_path = dl.validate_data_file_path(file_path)
        if not ok_path:
            return jsonify({'error': err_path}), 400

        df, error = data_io.load_data_file(file_path)
        if error:
            return jsonify({'error': error}), 400

        sel, win_err = pw.select_predict_window(
            df,
            start_date=start_date,
            end_date=end_date,
            lookback=lookback,
            pred_len=pred_len,
        )
        if sel is None:
            return jsonify({'error': win_err or '窓の選択に失敗しました'}), 400

        window_df = sel.window_df

        required_cols = ['open', 'high', 'low', 'close']
        if 'volume' in df.columns:
            required_cols.append('volume')

        x_df = window_df.iloc[:lookback][required_cols]
        x_timestamp = window_df.iloc[:lookback]['timestamps']
        actual_df = window_df.iloc[-pred_len:]
        y_timestamp = actual_df['timestamps']

        if isinstance(x_timestamp, pd.DatetimeIndex):
            x_timestamp = pd.Series(x_timestamp, name='timestamps')
        if isinstance(y_timestamp, pd.DatetimeIndex):
            y_timestamp = pd.Series(y_timestamp, name='timestamps')

        range_desc_parts = []
        if start_date:
            range_desc_parts.append(f"start={start_date}")
        if end_date:
            range_desc_parts.append(f"end={end_date}")
        range_desc = "、".join(range_desc_parts) if range_desc_parts else "全期間"
        prediction_type = (
            f"Kronos モデル予測（評価モード: {range_desc}、末尾 {lookback} 本で予測、"
            f"末尾 {pred_len} 本を実測と比較）"
        )

        if not mr.inference_ready():
            return jsonify({'error': 'Kronos モデルが読み込まれていません。先にモデルを読み込んでください'}), 400

        try:
            pred_df = mr.get_predictor().predict(
                df=x_df,
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=pred_len,
                T=temperature,
                top_p=top_p,
                sample_count=sample_count,
            )
        except Exception as e:
            return jsonify({'error': f'Kronos モデルの予測に失敗しました: {str(e)}'}), 500

        actual_data = []
        for _, row in actual_df.iterrows():
            ts = row['timestamps']
            actual_data.append({
                'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') and not pd.isna(ts) else str(ts),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']) if 'volume' in row else 0,
                'amount': float(row['amount']) if 'amount' in row else 0,
            })

        historical_start_idx = sel.historical_start_idx
        chart_dict = charts.create_prediction_chart(df, pred_df, lookback, pred_len, actual_df, historical_start_idx)

        prediction_results = []
        for i, (_, row) in enumerate(pred_df.iterrows()):
            ts = actual_df['timestamps'].iloc[i]
            prediction_results.append({
                'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') and not pd.isna(ts) else str(ts),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']) if 'volume' in row else 0,
                'amount': float(row['amount']) if 'amount' in row else 0,
            })

        try:
            prediction_storage.save_prediction_results(
                file_path=file_path,
                prediction_type=prediction_type,
                prediction_results=prediction_results,
                actual_data=actual_data,
                input_data=x_df,
                prediction_params={
                    'lookback': lookback,
                    'pred_len': pred_len,
                    'temperature': temperature,
                    'top_p': top_p,
                    'sample_count': sample_count,
                    'start_date': start_date,
                    'end_date': end_date,
                    'mode': 'eval_end_window',
                },
                chart=chart_dict,
            )
        except Exception as e:
            print(f"予測結果の保存に失敗しました: {e}")

        return jsonify({
            'success': True,
            'prediction_type': prediction_type,
            'chart': chart_dict,
            'prediction_results': prediction_results,
            'actual_data': actual_data,
            'has_comparison': len(actual_data) > 0,
            'message': (
                f'予測が完了しました。{pred_len} 件の予測ポイントを生成しました'
                + (f'（比較用の実データ {len(actual_data)} 本を含みます）' if len(actual_data) > 0 else '')
            ),
        })

    except Exception as e:
        return jsonify({'error': f'予測に失敗しました: {str(e)}'}), 500


prediction_bp = Blueprint("prediction", __name__, url_prefix="/api")

prediction_bp.add_url_rule(
    "/prediction-results",
    view_func=list_prediction_results,
    methods=["GET"],
)
prediction_bp.add_url_rule(
    "/prediction-results/<result_id>",
    view_func=get_prediction_result_detail,
    methods=["GET"],
)
prediction_bp.add_url_rule("/predict", view_func=predict, methods=["POST"])

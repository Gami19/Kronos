"""Blueprint: prediction results list/detail, predict."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

import pandas as pd

from backend import model_runtime as mr
from backend import paths as app_paths
from backend.constants_api import PREDICTION_RESULT_ID_PATTERN
from backend.services import charts_plotly as charts
from backend.services import data_io
from backend.services import data_layout as dl
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
    """予測を実行する"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        lookback = int(data.get('lookback', 400))
        pred_len = int(data.get('pred_len', 120))
        
        # 予測品質パラメータ
        temperature = float(data.get('temperature', 1.0))
        top_p = float(data.get('top_p', 0.9))
        sample_count = int(data.get('sample_count', 1))
        
        if not file_path:
            return jsonify({'error': 'ファイルパスが指定されていません'}), 400

        ok_path, err_path = dl.validate_data_file_path(file_path)
        if not ok_path:
            return jsonify({'error': err_path}), 400
        
        # データ読み込み
        df, error = data_io.load_data_file(file_path)
        if error:
            return jsonify({'error': error}), 400
        
        if len(df) < lookback:
            return jsonify({'error': f'データ長が不足しています。最低 {lookback} 行必要です'}), 400
        
        # 予測実行
        if mr.inference_ready():
            try:
                # 実 Kronos モデルを使用
                # 必要列のみ（OHLCV）。amount は含めない
                required_cols = ['open', 'high', 'low', 'close']
                if 'volume' in df.columns:
                    required_cols.append('volume')
                
                # 期間指定の処理
                start_date = data.get('start_date')
                
                if start_date:
                    # 選択ウィンドウ内のデータを使用
                    start_dt = pd.to_datetime(start_date)
                    
                    # 開始時刻以降の行
                    mask = df['timestamps'] >= start_dt
                    time_range_df = df[mask]
                    
                    # lookback + pred_len 分そろっているか
                    if len(time_range_df) < lookback + pred_len:
                        return jsonify({'error': f'開始時刻 {start_dt.strftime("%Y-%m-%d %H:%M")} 以降のデータが不足しています。最低 {lookback + pred_len} 本必要ですが、現在は {len(time_range_df)} 本しかありません'}), 400
                    
                    # ウィンドウ先頭 lookback 本で予測
                    x_df = time_range_df.iloc[:lookback][required_cols]
                    x_timestamp = time_range_df.iloc[:lookback]['timestamps']
                    
                    # 末尾 pred_len 本を実値として比較
                    y_timestamp = time_range_df.iloc[lookback:lookback+pred_len]['timestamps']
                    
                    # ウィンドウ内の実時間幅
                    start_timestamp = time_range_df['timestamps'].iloc[0]
                    end_timestamp = time_range_df['timestamps'].iloc[lookback+pred_len-1]
                    time_span = end_timestamp - start_timestamp
                    
                    prediction_type = f"Kronos モデル予測（選択ウィンドウ内: 先頭 {lookback} 本で予測、末尾 {pred_len} 本で比較、時間幅: {time_span}）"
                else:
                    # 最新データを使用
                    x_df = df.iloc[:lookback][required_cols]
                    x_timestamp = df.iloc[:lookback]['timestamps']
                    y_timestamp = df.iloc[lookback:lookback+pred_len]['timestamps']
                    prediction_type = "Kronos モデル予測（最新データ）"
                
                # DatetimeIndex のままだと .dt で落ちるため Series にそろえる
                if isinstance(x_timestamp, pd.DatetimeIndex):
                    x_timestamp = pd.Series(x_timestamp, name='timestamps')
                if isinstance(y_timestamp, pd.DatetimeIndex):
                    y_timestamp = pd.Series(y_timestamp, name='timestamps')
                
                pred_df = mr.get_predictor().predict(
                    df=x_df,
                    x_timestamp=x_timestamp,
                    y_timestamp=y_timestamp,
                    pred_len=pred_len,
                    T=temperature,
                    top_p=top_p,
                    sample_count=sample_count
                )
                
            except Exception as e:
                return jsonify({'error': f'Kronos モデルの予測に失敗しました: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Kronos モデルが読み込まれていません。先にモデルを読み込んでください'}), 400
        
        # 比較用の実データ（あれば）
        actual_data = []
        actual_df = None
        
        if start_date:  # 期間指定
            # 選択ウィンドウ内のデータを使用
            # 予測はウィンドウ先頭 lookback 本
            # 実データはウィンドウ末尾 pred_len 本
            start_dt = pd.to_datetime(start_date)
            
            mask = df['timestamps'] >= start_dt
            time_range_df = df[mask]
            
            if len(time_range_df) >= lookback + pred_len:
                # ウィンドウ内の末尾 pred_len 本を実値として抽出
                actual_df = time_range_df.iloc[lookback:lookback+pred_len]
                
                for i, (_, row) in enumerate(actual_df.iterrows()):
                    actual_data.append({
                        'timestamp': row['timestamps'].isoformat(),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['volume']) if 'volume' in row else 0,
                        'amount': float(row['amount']) if 'amount' in row else 0
                    })
        else:  # 最新データ
            # 先頭 lookback 本で予測、その直後の pred_len 本を実値
            if len(df) >= lookback + pred_len:
                actual_df = df.iloc[lookback:lookback+pred_len]
                for i, (_, row) in enumerate(actual_df.iterrows()):
                    actual_data.append({
                        'timestamp': row['timestamps'].isoformat(),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['volume']) if 'volume' in row else 0,
                        'amount': float(row['amount']) if 'amount' in row else 0
                    })
        
        # チャート用に履歴開始インデックスを渡す
        if start_date:
            # 期間指定: 元 df 上での履歴開始位置
            start_dt = pd.to_datetime(start_date)
            mask = df['timestamps'] >= start_dt
            historical_start_idx = df[mask].index[0] if len(df[mask]) > 0 else 0
        else:
            # 最新データ: 先頭から
            historical_start_idx = 0
        
        chart_dict = charts.create_prediction_chart(df, pred_df, lookback, pred_len, actual_df, historical_start_idx)
        
        # 予測結果のタイムスタンプ列を組み立て
        if 'timestamps' in df.columns:
            if start_date:
                # 選択ウィンドウ内で未来時刻を算出
                start_dt = pd.to_datetime(start_date)
                mask = df['timestamps'] >= start_dt
                time_range_df = df[mask]
                
                if len(time_range_df) >= lookback:
                    # ウィンドウ内 lookback 本目の次の刻みから pred_len 本
                    last_timestamp = time_range_df['timestamps'].iloc[lookback-1]
                    time_diff = df['timestamps'].iloc[1] - df['timestamps'].iloc[0]
                    future_timestamps = pd.date_range(
                        start=last_timestamp + time_diff,
                        periods=pred_len,
                        freq=time_diff
                    )
                else:
                    future_timestamps = []
            else:
                # 全データの最終刻みの次から pred_len 本
                last_timestamp = df['timestamps'].iloc[-1]
                time_diff = df['timestamps'].iloc[1] - df['timestamps'].iloc[0]
                future_timestamps = pd.date_range(
                    start=last_timestamp + time_diff,
                    periods=pred_len,
                    freq=time_diff
                )
        else:
            future_timestamps = range(len(df), len(df) + pred_len)
        
        prediction_results = []
        for i, (_, row) in enumerate(pred_df.iterrows()):
            prediction_results.append({
                'timestamp': future_timestamps[i].isoformat() if i < len(future_timestamps) else f"T{i}",
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']) if 'volume' in row else 0,
                'amount': float(row['amount']) if 'amount' in row else 0
            })
        
        # 予測結果をファイル保存
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
                    'start_date': start_date if start_date else 'latest'
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
            'message': f'予測が完了しました。{pred_len} 件の予測ポイントを生成しました' + (f'（比較用の実データ {len(actual_data)} 本を含みます）' if len(actual_data) > 0 else '')
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

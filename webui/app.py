import os
import re
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import plotly.utils
from plotly.subplots import make_subplots
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import warnings
import datetime
import yfinance as yf
warnings.filterwarnings('ignore')

PREDICTION_RESULT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
# データレイアウト: data/<ticker>/ に CSV/Feather（銘柄フォルダ名は yfinance シンボルと同一推奨）
# ルート直下のみファイルがある場合は合成銘柄 __flat__（レガシー）
FLAT_TICKER_ID = '__flat__'
DEFAULT_YFIN_TICKER = '8058.T'
TICKER_FOLDER_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')


def project_data_dir():
    """リポジトリの data ディレクトリ（絶対パス）"""
    return os.path.normpath(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    )


def _directory_has_data_files(dir_path):
    if not os.path.isdir(dir_path):
        return False
    for name in os.listdir(dir_path):
        if name.endswith(('.csv', '.feather')):
            child = os.path.join(dir_path, name)
            if os.path.isfile(child):
                return True
    return False


def list_ticker_subdirs_with_data():
    """銘柄サブフォルダのうちデータファイルを1つ以上含むものの ID 一覧"""
    base = project_data_dir()
    found = []
    if not os.path.isdir(base):
        return found
    for name in sorted(os.listdir(base)):
        sub = os.path.join(base, name)
        if not os.path.isdir(sub) or name.startswith('.'):
            continue
        if not TICKER_FOLDER_PATTERN.fullmatch(name):
            continue
        if _directory_has_data_files(sub):
            found.append(name)
    return found


def legacy_flat_layout_active():
    """銘柄サブフォルダにデータがなく、ルート直下にのみ CSV/Feather がある"""
    if list_ticker_subdirs_with_data():
        return False
    base = project_data_dir()
    if not os.path.isdir(base):
        return False
    for name in os.listdir(base):
        if name.endswith(('.csv', '.feather')):
            fp = os.path.join(base, name)
            if os.path.isfile(fp):
                return True
    return False


def get_tickers_payload():
    """GET /api/tickers 用のエントリ一覧"""
    items = []
    for tid in list_ticker_subdirs_with_data():
        items.append({'id': tid, 'label': tid, 'legacy_root': False})
    if legacy_flat_layout_active():
        items.append({
            'id': FLAT_TICKER_ID,
            'label': 'ルート直下（レガシー）',
            'legacy_root': True,
        })
    return items


def default_ticker_id():
    """既定銘柄（8058.T があれば優先、なければ先頭、レガシーのみなら __flat__）"""
    subs = list_ticker_subdirs_with_data()
    if '8058.T' in subs:
        return '8058.T'
    if subs:
        return subs[0]
    if legacy_flat_layout_active():
        return FLAT_TICKER_ID
    return FLAT_TICKER_ID


def load_data_files_for_ticker(ticker_id):
    """指定銘柄ディレクトリまたはレガシールートのファイル一覧"""
    base = project_data_dir()
    data_files = []

    if ticker_id == FLAT_TICKER_ID:
        if not os.path.isdir(base):
            return data_files
        for file in sorted(os.listdir(base)):
            if not file.endswith(('.csv', '.feather')):
                continue
            file_path = os.path.join(base, file)
            if not os.path.isfile(file_path):
                continue
            file_size = os.path.getsize(file_path)
            data_files.append({
                'name': file,
                'path': file_path,
                'size': f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB",
            })
        return data_files

    sub = os.path.join(base, ticker_id)
    if not os.path.isdir(sub):
        return data_files

    for file in sorted(os.listdir(sub)):
        if not file.endswith(('.csv', '.feather')):
            continue
        file_path = os.path.join(sub, file)
        if not os.path.isfile(file_path):
            continue
        file_size = os.path.getsize(file_path)
        data_files.append({
            'name': file,
            'path': file_path,
            'size': f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB",
        })
    return data_files


def validate_data_file_path(file_path):
    """
    load-data / predict で許可するパスか検証する。
    - data/<ticker>/<file> は銘柄フォルダが存在すれば可
    - data/<file> は legacy_flat_layout_active() のときのみ可
    """
    if not file_path or not isinstance(file_path, str):
        return False, 'ファイルパスが無効です'
    try:
        norm = os.path.normpath(os.path.realpath(file_path))
    except OSError:
        return False, 'ファイルパスが無効です'

    base = os.path.realpath(project_data_dir())
    if not os.path.isdir(base):
        return False, 'データディレクトリがありません'

    if norm != base and not norm.startswith(base + os.sep):
        return False, '許可されていないパスです（プロジェクトの data 配下のみ利用できます）'

    rel = os.path.relpath(norm, base)
    parts = rel.split(os.sep)

    if len(parts) == 1:
        fname = parts[0]
        if fname in ('.', '..'):
            return False, '無効なデータパスです'
        if not fname.endswith(('.csv', '.feather')):
            return False, 'データファイルではありません'
        if not legacy_flat_layout_active():
            return False, '直下ファイルは利用できません。data/<銘柄>/ にファイルを置くか、銘柄フォルダのみの構成にしてください'
        return True, None

    if len(parts) == 2:
        tdir, fname = parts
        if not TICKER_FOLDER_PATTERN.fullmatch(tdir):
            return False, '無効な銘柄パスです'
        if not fname.endswith(('.csv', '.feather')):
            return False, 'データファイルではありません'
        sub = os.path.join(base, tdir)
        if not os.path.isdir(sub):
            return False, '銘柄フォルダがありません'
        return True, None

    return False, '無効なデータパスです'


def yfinance_ticker_from_client_param(raw_ticker):
    """UI の銘柄 ID を yfinance シンボルに変換（__flat__ は三菱商事デフォルト）"""
    if raw_ticker is None:
        return DEFAULT_YFIN_TICKER
    s = raw_ticker.strip()
    if not s or s == FLAT_TICKER_ID:
        return DEFAULT_YFIN_TICKER
    return s


# GET /api/market-history: クエリ検証用（フロントの 5m・5d/30d/60d/1mo と整合）
MARKET_HISTORY_ALLOWED_INTERVALS = frozenset({
    '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo',
})
MARKET_HISTORY_ALLOWED_PERIODS = frozenset({
    '1d', '5d', '30d', '60d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max',
})


def _yfinance_exception_user_message(exc):
    """yfinance 例外をユーザー向け日本語メッセージに変換"""
    if isinstance(exc, TimeoutError):
        return '市場データの取得がタイムアウトしました。時間をおいて再度お試しください。'
    if isinstance(exc, ConnectionError):
        return 'ネットワーク接続エラーです。インターネット接続を確認してください。'
    detail = str(exc).strip()
    if len(detail) > 180:
        detail = detail[:177] + '...'
    if not detail:
        detail = type(exc).__name__
    return f'市場データの取得に失敗しました。（{detail}）'


# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from model import Kronos, KronosTokenizer, KronosPredictor
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False
    print("警告: Kronos モデルをインポートできません。デモ用のシミュレーションデータを使用します")

app = Flask(__name__)
CORS(app)

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'dist')

# モデル保持用グローバル変数
tokenizer = None
model = None
predictor = None

# 利用可能なモデル設定
AVAILABLE_MODELS = {
    'kronos-mini': {
        'name': 'Kronos-mini',
        'model_id': 'NeoQuasar/Kronos-mini',
        'tokenizer_id': 'NeoQuasar/Kronos-Tokenizer-2k',
        'context_length': 2048,
        'params': '4.1M',
        'description': '軽量モデル。高速な予測向き'
    },
    'kronos-small': {
        'name': 'Kronos-small',
        'model_id': 'NeoQuasar/Kronos-small',
        'tokenizer_id': 'NeoQuasar/Kronos-Tokenizer-base',
        'context_length': 512,
        'params': '24.7M',
        'description': '小型モデル。性能と速度のバランス型'
    },
    'kronos-base': {
        'name': 'Kronos-base',
        'model_id': 'NeoQuasar/Kronos-base',
        'tokenizer_id': 'NeoQuasar/Kronos-Tokenizer-base',
        'context_length': 512,
        'params': '102.3M',
        'description': 'ベースモデル。より高品質な予測'
    }
}

def load_data_file(file_path):
    """データファイルを読み込む"""
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.feather'):
            df = pd.read_feather(file_path)
        else:
            return None, "未対応のファイル形式です"
        
        # 必須列の確認
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return None, f"必須列が不足しています: {required_cols}"
        
        # タイムスタンプ列の処理
        if 'timestamps' in df.columns:
            df['timestamps'] = pd.to_datetime(df['timestamps'])
        elif 'timestamp' in df.columns:
            df['timestamps'] = pd.to_datetime(df['timestamp'])
        elif 'date' in df.columns:
            # 列名が date の場合は timestamps 相当として扱う
            df['timestamps'] = pd.to_datetime(df['date'])
        else:
            # タイムスタンプ列がない場合は生成
            df['timestamps'] = pd.date_range(start='2024-01-01', periods=len(df), freq='1H')
        
        # 数値列を数値型にそろえる
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 出来高（任意）
        if 'volume' in df.columns:
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        
        # 金額（任意。予測には使用しない）
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # NaN を含む行を削除
        df = df.dropna()
        
        return df, None
        
    except Exception as e:
        return None, f"ファイルの読み込みに失敗しました: {str(e)}"


def figure_to_plotly_dict(fig):
    """Plotly Figure を JSON 互換の dict に変換する（クライアントで二重 JSON.parse 不要）"""
    return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))


def prediction_results_dir():
    """予測結果 JSON の保存ディレクトリ"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prediction_results')


def dataframe_to_ohlc_rows(df):
    """プレビュー・チャート用に DataFrame を行 dict のリストへ変換する"""
    rows = []
    has_volume = 'volume' in df.columns
    has_amount = 'amount' in df.columns
    for _, row in df.iterrows():
        ts = row['timestamps']
        item = {
            'timestamp': ts.isoformat() if pd.notna(ts) else None,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
        }
        if has_volume:
            v = row['volume']
            item['volume'] = float(v) if pd.notna(v) else None
        if has_amount:
            a = row['amount']
            item['amount'] = float(a) if pd.notna(a) else None
        rows.append(item)
    return rows


def save_prediction_results(file_path, prediction_type, prediction_results, actual_data, input_data, prediction_params, chart=None):
    """予測結果をファイルに保存する"""
    try:
        # 保存先ディレクトリ
        results_dir = prediction_results_dir()
        os.makedirs(results_dir, exist_ok=True)
        
        # ファイル名生成
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'prediction_{timestamp}.json'
        filepath = os.path.join(results_dir, filename)
        
        # 保存用データの組み立て
        save_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'file_path': file_path,
            'prediction_type': prediction_type,
            'prediction_params': prediction_params,
            'input_data_summary': {
                'rows': len(input_data),
                'columns': list(input_data.columns),
                'price_range': {
                    'open': {'min': float(input_data['open'].min()), 'max': float(input_data['open'].max())},
                    'high': {'min': float(input_data['high'].min()), 'max': float(input_data['high'].max())},
                    'low': {'min': float(input_data['low'].min()), 'max': float(input_data['low'].max())},
                    'close': {'min': float(input_data['close'].min()), 'max': float(input_data['close'].max())}
                },
                'last_values': {
                    'open': float(input_data['open'].iloc[-1]),
                    'high': float(input_data['high'].iloc[-1]),
                    'low': float(input_data['low'].iloc[-1]),
                    'close': float(input_data['close'].iloc[-1])
                }
            },
            'prediction_results': prediction_results,
            'actual_data': actual_data,
            'chart': chart,
            'analysis': {}
        }
        
        # 実データがあり予測がある場合のみ連続性（ギャップ）分析
        if actual_data and len(actual_data) > 0 and len(prediction_results) > 0:
            last_pred = prediction_results[-1]
            first_actual = actual_data[0]
            save_data['analysis']['continuity'] = {
                'last_prediction': {
                    'open': last_pred['open'],
                    'high': last_pred['high'],
                    'low': last_pred['low'],
                    'close': last_pred['close']
                },
                'first_actual': {
                    'open': first_actual['open'],
                    'high': first_actual['high'],
                    'low': first_actual['low'],
                    'close': first_actual['close']
                },
                'gaps': {
                    'open_gap': abs(last_pred['open'] - first_actual['open']),
                    'high_gap': abs(last_pred['high'] - first_actual['high']),
                    'low_gap': abs(last_pred['low'] - first_actual['low']),
                    'close_gap': abs(last_pred['close'] - first_actual['close'])
                },
                'gap_percentages': {
                    'open_gap_pct': (abs(last_pred['open'] - first_actual['open']) / first_actual['open']) * 100,
                    'high_gap_pct': (abs(last_pred['high'] - first_actual['high']) / first_actual['high']) * 100,
                    'low_gap_pct': (abs(last_pred['low'] - first_actual['low']) / first_actual['low']) * 100,
                    'close_gap_pct': (abs(last_pred['close'] - first_actual['close']) / first_actual['close']) * 100
                }
            }
        
        # ファイルへ書き出し
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        print(f"予測結果を保存しました: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"予測結果の保存に失敗しました: {e}")
        return None

def _candlestick_trace(x, open_, high, low, close, name, inc_color, dec_color):
    """ローソク足トレース（線幅・ヒゲ幅をそろえて視認性を上げる）"""
    return go.Candlestick(
        x=x,
        open=open_,
        high=high,
        low=low,
        close=close,
        name=name,
        increasing_line_color=inc_color,
        decreasing_line_color=dec_color,
        increasing_line_width=1.5,
        decreasing_line_width=1.5,
        whiskerwidth=0.72,
    )


def create_prediction_chart(df, pred_df, lookback, pred_len, actual_df=None, historical_start_idx=0):
    """予測結果のチャート用 Figure を生成する（縦分割サブプロットで重なりを避ける）"""
    # 履歴の開始位置は引数で指定（常に df 先頭とは限らない）
    if historical_start_idx + lookback + pred_len <= len(df):
        historical_df = df.iloc[historical_start_idx:historical_start_idx+lookback]
    else:
        available_lookback = min(lookback, len(df) - historical_start_idx)
        historical_df = df.iloc[historical_start_idx:historical_start_idx+available_lookback]

    has_pred = pred_df is not None and len(pred_df) > 0
    has_actual = actual_df is not None and len(actual_df) > 0

    pred_timestamps = None
    if has_pred:
        if 'timestamps' in df.columns and len(historical_df) > 0:
            last_timestamp = historical_df['timestamps'].iloc[-1]
            time_diff = df['timestamps'].iloc[1] - df['timestamps'].iloc[0] if len(df) > 1 else pd.Timedelta(hours=1)
            pred_timestamps = pd.date_range(
                start=last_timestamp + time_diff,
                periods=len(pred_df),
                freq=time_diff
            )
        else:
            pred_timestamps = range(len(historical_df), len(historical_df) + len(pred_df))

    actual_timestamps = None
    if has_actual:
        if 'timestamps' in df.columns:
            if pred_timestamps is not None:
                actual_timestamps = pred_timestamps
            elif len(historical_df) > 0:
                last_timestamp = historical_df['timestamps'].iloc[-1]
                time_diff = df['timestamps'].iloc[1] - df['timestamps'].iloc[0] if len(df) > 1 else pd.Timedelta(hours=1)
                actual_timestamps = pd.date_range(
                    start=last_timestamp + time_diff,
                    periods=len(actual_df),
                    freq=time_diff
                )
            else:
                actual_timestamps = range(len(historical_df), len(historical_df) + len(actual_df))
        else:
            actual_timestamps = range(len(historical_df), len(historical_df) + len(actual_df))

    # 行数: 履歴 +（予測があれば）+（検証実データがあれば）
    nrows = 1 + (1 if has_pred else 0) + (1 if has_actual else 0)
    if nrows == 1:
        row_heights = [1.0]
        layout_height = 600
    elif nrows == 2:
        row_heights = [0.55, 0.45]
        layout_height = 750
    else:
        row_heights = [0.48, 0.28, 0.24]
        layout_height = 920

    fig = make_subplots(
        rows=nrows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=row_heights,
    )

    row_hist = 1
    x_hist = historical_df['timestamps'] if 'timestamps' in historical_df.columns else historical_df.index
    fig.add_trace(
        _candlestick_trace(
            x_hist,
            historical_df['open'],
            historical_df['high'],
            historical_df['low'],
            historical_df['close'],
            '実データ（履歴 400 本）',
            '#26A69A',
            '#EF5350',
        ),
        row=row_hist,
        col=1,
    )
    fig.update_yaxes(title_text='履歴（価格）', row=row_hist, col=1)

    current_row = row_hist
    if has_pred:
        current_row += 1
        fig.add_trace(
            _candlestick_trace(
                pred_timestamps,
                pred_df['open'],
                pred_df['high'],
                pred_df['low'],
                pred_df['close'],
                '予測データ（120 本）',
                '#66BB6A',
                '#FF7043',
            ),
            row=current_row,
            col=1,
        )
        fig.update_yaxes(title_text='予測（価格）', row=current_row, col=1)

    if has_actual:
        current_row += 1
        fig.add_trace(
            _candlestick_trace(
                actual_timestamps,
                actual_df['open'],
                actual_df['high'],
                actual_df['low'],
                actual_df['close'],
                '検証用 実データ（120 本）',
                '#FF9800',
                '#F44336',
            ),
            row=current_row,
            col=1,
        )
        fig.update_yaxes(title_text='検証・実データ（価格）', row=current_row, col=1)

    fig.update_layout(
        title='Kronos 予測結果（履歴 400 本 + 予測 120 本 vs 実データ 120 本）',
        template='plotly_white',
        height=layout_height,
        showlegend=True,
        hovermode='x unified',
    )
    fig.update_xaxes(title_text='時刻', row=nrows, col=1)

    if 'timestamps' in historical_df.columns:
        all_timestamps = []
        if len(historical_df) > 0:
            all_timestamps.extend(historical_df['timestamps'])
        if pred_timestamps is not None:
            all_timestamps.extend(pred_timestamps)
        if actual_timestamps is not None:
            all_timestamps.extend(actual_timestamps)
        if all_timestamps:
            all_timestamps = sorted(all_timestamps)
            fig.update_xaxes(
                range=[all_timestamps[0], all_timestamps[-1]],
                rangeslider_visible=False,
                type='date',
            )

    return figure_to_plotly_dict(fig)

@app.route('/api/tickers')
def api_tickers():
    """銘柄一覧（data/<ticker>/ またはレガシー __flat__）"""
    items = get_tickers_payload()
    return jsonify({
        'success': True,
        'tickers': items,
        'default_ticker': default_ticker_id() if items else None,
    })


@app.route('/api/data-files')
def get_data_files():
    """利用可能なデータファイル一覧（クエリ ticker で銘柄切替。省略時は既定）"""
    items = get_tickers_payload()
    if not items:
        return jsonify([])

    requested = (request.args.get('ticker') or '').strip()
    valid_ids = {t['id'] for t in items}
    ticker_id = requested if requested in valid_ids else default_ticker_id()
    if ticker_id not in valid_ids:
        ticker_id = items[0]['id']

    data_files = load_data_files_for_ticker(ticker_id)
    return jsonify(data_files)

@app.route('/api/load-data', methods=['POST'])
def load_data():
    """データファイルを読み込み、メタ情報を返す"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({'error': 'ファイルパスが指定されていません'}), 400

        ok, err_msg = validate_data_file_path(file_path)
        if not ok:
            return jsonify({'error': err_msg}), 400
        
        df, error = load_data_file(file_path)
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
        
        ohlc_rows = dataframe_to_ohlc_rows(df)

        return jsonify({
            'success': True,
            'data_info': data_info,
            'ohlc_rows': ohlc_rows,
            'message': f'データを読み込みました。全 {len(df)} 行です'
        })
        
    except Exception as e:
        return jsonify({'error': f'データの読み込みに失敗しました: {str(e)}'}), 500


@app.route('/api/prediction-results')
def list_prediction_results():
    """保存済み予測結果の一覧（メタのみ）"""
    results_dir = prediction_results_dir()
    if not os.path.isdir(results_dir):
        return jsonify({'success': True, 'results': []})

    items = []
    for name in sorted(os.listdir(results_dir), reverse=True):
        if not name.endswith('.json'):
            continue
        path = os.path.join(results_dir, name)
        try:
            with open(path, encoding='utf-8') as f:
                doc = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        stem = os.path.splitext(name)[0]
        pr = doc.get('prediction_results')
        ad = doc.get('actual_data')
        fp = doc.get('file_path') or ''
        items.append({
            'id': stem,
            'filename': name,
            'timestamp': doc.get('timestamp'),
            'prediction_type': doc.get('prediction_type'),
            'file_path': os.path.basename(fp) if fp else '',
            'prediction_params': doc.get('prediction_params'),
            'counts': {
                'prediction_results': len(pr) if isinstance(pr, list) else 0,
                'actual_data': len(ad) if isinstance(ad, list) else 0,
            },
        })

    return jsonify({'success': True, 'results': items})


@app.route('/api/prediction-results/<result_id>')
def get_prediction_result_detail(result_id):
    """保存済み予測結果 1 件の全文"""
    if not PREDICTION_RESULT_ID_PATTERN.fullmatch(result_id):
        return jsonify({'error': '無効な id です'}), 400

    path = os.path.join(prediction_results_dir(), f'{result_id}.json')
    if not os.path.isfile(path):
        return jsonify({'error': '見つかりません'}), 404

    try:
        with open(path, encoding='utf-8') as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return jsonify({'error': f'読み込みに失敗しました: {str(e)}'}), 500

    return jsonify(payload)


@app.route('/api/market-history')
def market_history():
    """yfinance による市場履歴（OHLC）"""
    raw_q = request.args.get('ticker')
    if raw_q is None or str(raw_q).strip() == '':
        ticker = DEFAULT_YFIN_TICKER
    else:
        ticker = yfinance_ticker_from_client_param(str(raw_q).strip())
    interval = (request.args.get('interval') or '5m').strip()
    period = (request.args.get('period') or '5d').strip()
    warnings_list = []

    if interval not in MARKET_HISTORY_ALLOWED_INTERVALS:
        allowed = ', '.join(sorted(MARKET_HISTORY_ALLOWED_INTERVALS))
        return jsonify({
            'success': False,
            'error': f'無効な interval です。次のいずれかを指定してください: {allowed}',
            'ticker': ticker,
            'interval': interval,
            'period': period,
            'warnings': warnings_list,
        }), 400

    if period not in MARKET_HISTORY_ALLOWED_PERIODS:
        allowed = ', '.join(sorted(MARKET_HISTORY_ALLOWED_PERIODS))
        return jsonify({
            'success': False,
            'error': f'無効な period です。次のいずれかを指定してください: {allowed}',
            'ticker': ticker,
            'interval': interval,
            'period': period,
            'warnings': warnings_list,
        }), 400

    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval=interval, auto_adjust=False)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': _yfinance_exception_user_message(e),
            'ticker': ticker,
            'interval': interval,
            'period': period,
            'warnings': warnings_list,
        }), 502

    if hist is None or hist.empty:
        hint_intraday = ''
        if interval.endswith('m') or interval.endswith('h'):
            hint_intraday = (
                ' 分足・時間足は取得できる期間に上限があることが多く、長い period では空になりやすいです。'
                '期間を短くするか、日足（interval=1d）を試してください。'
            )
        return jsonify({
            'success': False,
            'error': (
                'データが取得できませんでした（ティッカー・期間・間隔の組み合わせを確認してください）。'
                + hint_intraday
            ),
            'ticker': ticker,
            'interval': interval,
            'period': period,
            'warnings': warnings_list,
        }), 422

    rows = []
    for idx, row in hist.iterrows():
        ts = idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx
        rows.append({
            'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': float(row['Volume']) if 'Volume' in row and pd.notna(row['Volume']) else None,
        })

    return jsonify({
        'success': True,
        'ticker': ticker,
        'interval': interval,
        'period': period,
        'rows': rows,
        'warnings': warnings_list,
    })

@app.route('/api/predict', methods=['POST'])
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

        ok_path, err_path = validate_data_file_path(file_path)
        if not ok_path:
            return jsonify({'error': err_path}), 400
        
        # データ読み込み
        df, error = load_data_file(file_path)
        if error:
            return jsonify({'error': error}), 400
        
        if len(df) < lookback:
            return jsonify({'error': f'データ長が不足しています。最低 {lookback} 行必要です'}), 400
        
        # 予測実行
        if MODEL_AVAILABLE and predictor is not None:
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
                
                pred_df = predictor.predict(
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
        
        chart_dict = create_prediction_chart(df, pred_df, lookback, pred_len, actual_df, historical_start_idx)
        
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
            save_prediction_results(
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

@app.route('/api/load-model', methods=['POST'])
def load_model():
    """Kronos モデルを読み込む"""
    global tokenizer, model, predictor
    
    try:
        if not MODEL_AVAILABLE:
            return jsonify({'error': 'Kronos モデルライブラリが利用できません'}), 400
        
        data = request.get_json()
        model_key = data.get('model_key', 'kronos-small')
        device = data.get('device', 'cpu')
        
        if model_key not in AVAILABLE_MODELS:
            return jsonify({'error': f'未対応のモデルです: {model_key}'}), 400
        
        model_config = AVAILABLE_MODELS[model_key]
        
        # トークナイザとモデルを読み込み
        tokenizer = KronosTokenizer.from_pretrained(model_config['tokenizer_id'])
        model = Kronos.from_pretrained(model_config['model_id'])
        
        # Predictor を生成
        predictor = KronosPredictor(model, tokenizer, device=device, max_context=model_config['context_length'])
        
        return jsonify({
            'success': True,
            'message': f'モデルを読み込みました: {model_config["name"]}（{model_config["params"]}）デバイス: {device}',
            'model_info': {
                'name': model_config['name'],
                'params': model_config['params'],
                'context_length': model_config['context_length'],
                'description': model_config['description']
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'モデルの読み込みに失敗しました: {str(e)}'}), 500

@app.route('/api/available-models')
def get_available_models():
    """利用可能なモデル一覧を返す"""
    return jsonify({
        'models': AVAILABLE_MODELS,
        'model_available': MODEL_AVAILABLE
    })

@app.route('/api/model-status')
def get_model_status():
    """モデルの読み込み状態を返す"""
    if MODEL_AVAILABLE:
        if predictor is not None:
            return jsonify({
                'available': True,
                'loaded': True,
                'message': 'Kronos モデルは読み込み済みで利用できます',
                'current_model': {
                    'name': predictor.model.__class__.__name__,
                    'device': str(next(predictor.model.parameters()).device)
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


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    """React ビルド成果物を配信する（開発時は Vite を別途利用）"""
    if path == 'api' or path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404

    dist = FRONTEND_DIST
    dist_norm = os.path.normpath(dist)
    if not os.path.isdir(dist):
        return jsonify({
            'error': 'フロントエンドがビルドされていません。webui/frontend で npm run build を実行してください',
        }), 503

    if path:
        candidate = os.path.normpath(os.path.join(dist, path))
        if candidate.startswith(dist_norm) and os.path.isfile(candidate):
            rel = os.path.relpath(candidate, dist_norm)
            return send_from_directory(dist, rel)

    return send_from_directory(dist, 'index.html')


if __name__ == '__main__':
    print("Kronos Web UI を起動しています…")
    print(f"モデル利用可否: {MODEL_AVAILABLE}")
    if MODEL_AVAILABLE:
        print("ヒント: /api/load-model エンドポイントから Kronos モデルを読み込めます")
    else:
        print("ヒント: デモ用にシミュレーションデータが使われます")
    index_html = os.path.join(FRONTEND_DIST, 'index.html')
    if not os.path.isfile(index_html):
        print("警告: frontend/dist/index.html がありません。UI は 503 になります。cd frontend && npm run build を実行してください。")

    app.run(debug=True, host='0.0.0.0', port=7070)

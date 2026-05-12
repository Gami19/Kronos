import type { OhlcRow } from '../api/types'
import { getPredictionQuality } from '../utils/predictionMetrics'

interface ComparisonPanelProps {
  predictionType?: string
  predictions: OhlcRow[]
  actuals: OhlcRow[]
}

export default function ComparisonPanel({ predictionType, predictions, actuals }: ComparisonPanelProps) {
  const stats = getPredictionQuality(predictions, actuals)
  const minLen = Math.min(predictions.length, actuals.length)

  return (
    <div className="comparison-panel">
      <h3>予測と実データの比較</h3>
      {predictionType && (
        <p>
          <strong>予測タイプ:</strong> {predictionType}
        </p>
      )}
      <p>
        <strong>比較データ:</strong> 実データ {actuals.length} 本（表示 {minLen} 行）
      </p>
      <div className="error-stats">
        <div className="error-stat">
          <h4>MAE</h4>
          <div className="value">{stats.mae.toFixed(4)}</div>
        </div>
        <div className="error-stat">
          <h4>RMSE</h4>
          <div className="value">{stats.rmse.toFixed(4)}</div>
        </div>
        <div className="error-stat">
          <h4>MAPE</h4>
          <div className="value">{stats.mape.toFixed(2)}%</div>
        </div>
      </div>
      <div className="table-wrap">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>時刻</th>
              <th>実 O</th>
              <th>予 O</th>
              <th>実 H</th>
              <th>予 H</th>
              <th>実 L</th>
              <th>予 L</th>
              <th>実 C</th>
              <th>予 C</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: minLen }, (_, i) => {
              const pred = predictions[i]
              const act = actuals[i]
              return (
                <tr key={i}>
                  <td>{pred.timestamp ? new Date(pred.timestamp).toLocaleString() : '—'}</td>
                  <td>{act.open.toFixed(4)}</td>
                  <td>{pred.open.toFixed(4)}</td>
                  <td>{act.high.toFixed(4)}</td>
                  <td>{pred.high.toFixed(4)}</td>
                  <td>{act.low.toFixed(4)}</td>
                  <td>{pred.low.toFixed(4)}</td>
                  <td>{act.close.toFixed(4)}</td>
                  <td>{pred.close.toFixed(4)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

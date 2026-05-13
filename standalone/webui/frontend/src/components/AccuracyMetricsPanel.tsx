import { useMemo } from 'react'
import type { OhlcRow } from '../api/types'
import {
  computeAccuracyMetrics,
  dirSignToArrow,
  type PerBarErr,
} from '../utils/accuracyMetrics'

export interface AccuracyMetricsPanelProps {
  predictionType?: string
  predictions: OhlcRow[]
  actuals: OhlcRow[]
  /** ホバーに載せるワースト行数 */
  topN?: number
}

function buildAbsErrorTooltip(perBar: PerBarErr[], topN: number, heading: string): string {
  const sorted = [...perBar].sort((a, b) => b.absError - a.absError).slice(0, topN)
  const lines = [heading]
  for (const b of sorted) {
    lines.push(
      `#${b.index}: |Δ| ${b.absError.toFixed(4)} (act ${b.actClose.toFixed(4)} → pred ${b.predClose.toFixed(4)})`,
    )
  }
  return lines.join('\n')
}

function buildDirectionMissTooltip(perBar: PerBarErr[], topN: number): string {
  const misses = perBar
    .filter((b) => b.dirMatch === false)
    .sort((a, b) => b.absError - a.absError)
    .slice(0, topN)
  if (!misses.length) {
    return '方向ハズレはありません（または比較対象の騰落がすべてフラットでした）。'
  }
  const lines = [`方向ハズレ ${Math.min(topN, misses.length)} 本（|Δclose| 大きい順）`]
  for (const b of misses) {
    const pa = b.predDir !== undefined ? dirSignToArrow(b.predDir) : '?'
    const aa = b.actDir !== undefined ? dirSignToArrow(b.actDir) : '?'
    lines.push(`#${b.index}: act ${aa} vs pred ${pa} (|Δc| ${b.absError.toFixed(4)})`)
  }
  return lines.join('\n')
}

export default function AccuracyMetricsPanel({
  predictionType,
  predictions,
  actuals,
  topN = 5,
}: AccuracyMetricsPanelProps) {
  const metrics = useMemo(
    () => computeAccuracyMetrics(predictions, actuals),
    [predictions, actuals],
  )

  const { count, directionAccuracy, closeMae, maxError, perBar } = metrics

  const maeCardTitle = useMemo(
    () => buildAbsErrorTooltip(perBar, topN, `ワースト ${topN} 本（絶対誤差 |Δclose|）`),
    [perBar, topN],
  )

  const maxCardTitle = useMemo(
    () => buildAbsErrorTooltip(perBar, topN, `絶対誤差上位 ${topN} 本（最大誤差カード）`),
    [perBar, topN],
  )

  const dirCardTitle = useMemo(() => buildDirectionMissTooltip(perBar, topN), [perBar, topN])

  if (count === 0) {
    return (
      <div className="accuracy-metrics-panel">
        <h3>精度サマリ（デモ）</h3>
        <p className="msg-muted small">比較できる予測・実測データがありません。</p>
      </div>
    )
  }

  const dirPct = (100 * directionAccuracy).toFixed(1)
  const dirDenominator = perBar.filter((b) => b.dirMatch !== undefined).length

  return (
    <div className="accuracy-metrics-panel">
      <h3>精度サマリ（デモ）</h3>
      {predictionType && (
        <p className="msg-muted small">
          予測タイプ: <strong>{predictionType}</strong> — バー数 {count}（方向判定の母数 {dirDenominator}）
        </p>
      )}
      {!predictionType && (
        <p className="msg-muted small">
          バー数 {count}（方向判定の母数 {dirDenominator}）
        </p>
      )}
      <div className="accuracy-cards" role="list">
        <div
          className="accuracy-card"
          role="listitem"
          title={dirCardTitle}
        >
          <h4 className="accuracy-card__label">方向精度</h4>
          <div className="accuracy-card__value">{dirPct}%</div>
          <p className="accuracy-card__hint">隣接 close 騰落の一致（フラット除外）</p>
        </div>
        <div
          className="accuracy-card"
          role="listitem"
          title={maeCardTitle}
        >
          <h4 className="accuracy-card__label">close MAE</h4>
          <div className="accuracy-card__value">{closeMae.toFixed(4)}</div>
          <p className="accuracy-card__hint">全バー平均 |Δclose|</p>
        </div>
        <div
          className="accuracy-card"
          role="listitem"
          title={maxCardTitle}
        >
          <h4 className="accuracy-card__label">最大誤差</h4>
          <div className="accuracy-card__value">{maxError.toFixed(4)}</div>
          <p className="accuracy-card__hint">max |Δclose|</p>
        </div>
      </div>
    </div>
  )
}

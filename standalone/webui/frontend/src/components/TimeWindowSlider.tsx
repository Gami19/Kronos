import type { DataInfo } from '../api/types'

const LOOKBACK = 400
const PRED_LEN = 120
const WINDOW = LOOKBACK + PRED_LEN

export interface TimeWindowSliderProps {
  dataInfo: DataInfo
  startPct: number
  onStartPctChange: (pct: number) => void
}

export function windowFitsRows(rows: number): boolean {
  return rows >= WINDOW
}

/** スライダー左端 0〜1 に対応する予測開始時刻（API 用 YYYY-MM-DDTHH:MM） */
export function computePredictStartDateIso(dataInfo: DataInfo, startPct: number): string {
  const start = new Date(dataInfo.start_date ?? '')
  const end = new Date(dataInfo.end_date ?? '')
  const total = end.getTime() - start.getTime()
  const t = start.getTime() + total * startPct
  return new Date(t).toISOString().slice(0, 16)
}

export default function TimeWindowSlider({ dataInfo, startPct, onStartPctChange }: TimeWindowSliderProps) {
  const rows = dataInfo.rows
  const windowRatio = Math.min(WINDOW / rows, 1)
  const maxStart = Math.max(0, 1 - windowRatio)

  const fits = windowFitsRows(rows)

  const displayStart = () => {
    if (!dataInfo.start_date || !dataInfo.end_date) return '—'
    const s = new Date(dataInfo.start_date).getTime()
    const e = new Date(dataInfo.end_date).getTime()
    const t = s + (e - s) * startPct
    return new Date(t).toLocaleString()
  }

  const displayEnd = () => {
    if (!dataInfo.start_date || !dataInfo.end_date) return '—'
    const s = new Date(dataInfo.start_date).getTime()
    const e = new Date(dataInfo.end_date).getTime()
    const t = s + (e - s) * (startPct + windowRatio)
    return new Date(t).toLocaleString()
  }

  if (!fits) {
    return (
      <div className="form-group">
        <p className="msg-error">
          データが不足しています。最低 {WINDOW} 本必要ですが、現在は {rows} 本です。
        </p>
      </div>
    )
  }

  const sliderMax = Math.round(maxStart * 10000)
  const sliderVal = Math.round(Math.min(startPct, maxStart) * 10000)

  return (
    <div className="time-window-block">
      <h3>時間窓の選択</h3>
      <p className="msg-muted small">
        参照 {LOOKBACK} 本 + 予測 {PRED_LEN} 本 = {WINDOW} 本（固定）。スライダーで窓の開始位置を選びます。
      </p>
      <div className="window-range-readout">
        <span>開始付近: {displayStart()}</span>
        <span>終了付近: {displayEnd()}</span>
      </div>
      <input
        type="range"
        className="window-slider"
        min={0}
        max={sliderMax}
        step={1}
        value={sliderVal}
        onChange={(e) => onStartPctChange(Number(e.target.value) / 10000)}
      />
      <div className="window-range-readout msg-muted small">
        <span>{dataInfo.start_date?.split('T')[0]}（最古）</span>
        <span>{dataInfo.end_date?.split('T')[0]}（最新）</span>
      </div>
    </div>
  )
}

export { LOOKBACK, PRED_LEN, WINDOW }

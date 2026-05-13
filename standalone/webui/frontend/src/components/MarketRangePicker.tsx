import { useCallback, useMemo, useState } from 'react'
import { importMarket } from '../api/endpoints'
import { FLAT_TICKER_ID } from '../context/TickerContext'
import { formatUserFacingError } from '../utils/formatError'
import { rangeRuleHint, validateYfinanceRange } from '../utils/yfinanceLimits'

const RANGE_INTERVALS = ['1d', '1h', '5m'] as const

function todayUtcDateString(): string {
  const d = new Date()
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, '0')
  const day = String(d.getUTCDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function addUtcDays(iso: string, deltaDays: number): string {
  const [y, mo, da] = iso.split('-').map(Number)
  const t = Date.UTC(y, mo - 1, da) + deltaDays * 86_400_000
  const d = new Date(t)
  const yy = d.getUTCFullYear()
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(d.getUTCDate()).padStart(2, '0')
  return `${yy}-${mm}-${dd}`
}

export type MarketRangePickerProps = {
  tickerId: string
  disabled?: boolean
  flatTickerId?: string
  onImported?: () => void | Promise<void>
}

export default function MarketRangePicker({
  tickerId,
  disabled = false,
  flatTickerId = FLAT_TICKER_ID,
  onImported,
}: MarketRangePickerProps) {
  const today = useMemo(() => todayUtcDateString(), [])
  const [interval, setInterval] = useState<(typeof RANGE_INTERVALS)[number]>('5m')
  const [start, setStart] = useState(() => addUtcDays(today, -7))
  const [end, setEnd] = useState(today)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const validation = useMemo(() => validateYfinanceRange(interval, start, end), [interval, start, end])
  const hint = useMemo(() => rangeRuleHint(interval), [interval])

  const minStartByRule = useMemo(() => {
    if (interval === '1d') return '1970-01-01'
    const rules: Record<string, number> = { '5m': 60, '1h': 730 }
    const lb = rules[interval] ?? 60
    return addUtcDays(today, -lb)
  }, [interval, today])

  const handleFetch = useCallback(async () => {
    setMsg(null)
    if (!tickerId || tickerId === flatTickerId) {
      setMsg('銘柄を実ティッカーに切り替えてから取り込んでください。')
      return
    }
    const v = validateYfinanceRange(interval, start, end)
    if (!v.ok) {
      setMsg(v.error)
      return
    }
    setBusy(true)
    try {
      const res = await importMarket({
        ticker_id: tickerId,
        interval,
        start,
        end,
      })
      if (res.success) {
        setMsg(res.message ?? '保存しました')
        await onImported?.()
      } else {
        setMsg(res.error ?? '取り込みに失敗しました')
      }
    } catch (e) {
      setMsg(formatUserFacingError(e))
    } finally {
      setBusy(false)
    }
  }, [tickerId, flatTickerId, interval, start, end, onImported])

  const blocked = disabled || busy || !validation.ok

  return (
    <div className="market-range-picker">
      <h3>日付レンジで yfinance 取り込み</h3>
      <p className="msg-muted small">{hint}</p>
      <div className="form-group">
        <label htmlFor="mrp-interval">間隔</label>
        <select
          id="mrp-interval"
          value={interval}
          onChange={(e) => setInterval(e.target.value as (typeof RANGE_INTERVALS)[number])}
          disabled={disabled || busy}
        >
          {RANGE_INTERVALS.map((iv) => (
            <option key={iv} value={iv}>
              {iv}
            </option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <label htmlFor="mrp-start">開始日</label>
        <input
          id="mrp-start"
          type="date"
          value={start}
          max={end}
          min={minStartByRule}
          onChange={(e) => setStart(e.target.value)}
          disabled={disabled || busy}
        />
      </div>
      <div className="form-group">
        <label htmlFor="mrp-end">終了日</label>
        <input
          id="mrp-end"
          type="date"
          value={end}
          max={today}
          min={start}
          onChange={(e) => setEnd(e.target.value)}
          disabled={disabled || busy}
        />
      </div>
      {!validation.ok && <p className="msg-warning small">{validation.error}</p>}
      {msg && <p className={msg.includes('失敗') || msg.includes('できません') ? 'msg-error small' : 'msg-muted small'}>{msg}</p>}
      <button type="button" className="btn btn-secondary" disabled={blocked} onClick={handleFetch}>
        {busy ? '取得中…' : 'レンジで取得して CSV 保存'}
      </button>
    </div>
  )
}

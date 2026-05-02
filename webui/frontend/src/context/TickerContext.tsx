import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { getTickers } from '../api/endpoints'
import { formatUserFacingError } from '../utils/formatError'
import type { TickerEntry } from '../api/types'

/** バックエンドの FLAT_TICKER_ID と一致させる */
export const FLAT_TICKER_ID = '__flat__' as const
export const DEFAULT_YFIN_TICKER = '8058.T' as const

export function yfinanceDisplaySymbol(tickerId: string): string {
  if (!tickerId || tickerId === FLAT_TICKER_ID) return DEFAULT_YFIN_TICKER
  return tickerId
}

export type TickerContextValue = {
  tickers: TickerEntry[]
  selectedTickerId: string
  setSelectedTickerId: (id: string) => void
  /** GET /api/market-history の ticker（空ならクエリ省略しサーバ既定） */
  marketHistoryTickerQuery: string
  /** チャート・説明文用の yfinance シンボル表示 */
  yfinanceDisplaySymbol: string
  loading: boolean
  error: string | null
}

const TickerContext = createContext<TickerContextValue | null>(null)

export function TickerProvider({ children }: { children: ReactNode }) {
  const [tickers, setTickers] = useState<TickerEntry[]>([])
  const [selectedTickerId, setSelectedTickerIdState] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await getTickers()
        if (cancelled) return
        const list = res.tickers ?? []
        setTickers(list)
        const def = res.default_ticker ?? list[0]?.id ?? ''
        setSelectedTickerIdState(def)
      } catch (e) {
        if (!cancelled) setError(formatUserFacingError(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const setSelectedTickerId = useCallback((id: string) => {
    setSelectedTickerIdState(id)
  }, [])

  const displaySym = useMemo(
    () => yfinanceDisplaySymbol(selectedTickerId),
    [selectedTickerId],
  )

  const value = useMemo<TickerContextValue>(
    () => ({
      tickers,
      selectedTickerId,
      setSelectedTickerId,
      marketHistoryTickerQuery: selectedTickerId,
      yfinanceDisplaySymbol: displaySym,
      loading,
      error,
    }),
    [tickers, selectedTickerId, setSelectedTickerId, displaySym, loading, error],
  )

  return <TickerContext.Provider value={value}>{children}</TickerContext.Provider>
}

export function useTicker(): TickerContextValue {
  const ctx = useContext(TickerContext)
  if (!ctx) throw new Error('useTicker must be used within TickerProvider')
  return ctx
}

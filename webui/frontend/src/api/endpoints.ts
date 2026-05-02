import { apiGet, apiPost } from './client'
import type {
  AvailableModelsResponse,
  LoadDataResponse,
  LoadModelResponse,
  MarketHistoryResponse,
  ModelStatusResponse,
  PredictionDetailRecord,
  PredictionResultsListResponse,
  PredictRequest,
  PredictResponse,
  DataFileMeta,
  TickersResponse,
} from './types'

export function getModelStatus(): Promise<ModelStatusResponse> {
  return apiGet<ModelStatusResponse>('/api/model-status')
}

export function getAvailableModels(): Promise<AvailableModelsResponse> {
  return apiGet<AvailableModelsResponse>('/api/available-models')
}

export function getTickers(): Promise<TickersResponse> {
  return apiGet<TickersResponse>('/api/tickers')
}

export function getDataFiles(ticker?: string): Promise<DataFileMeta[]> {
  const qs = ticker ? `?ticker=${encodeURIComponent(ticker)}` : ''
  return apiGet<DataFileMeta[]>(`/api/data-files${qs}`)
}

export function listPredictionResults(): Promise<PredictionResultsListResponse> {
  return apiGet<PredictionResultsListResponse>('/api/prediction-results')
}

export function getPredictionResultDetail(id: string): Promise<PredictionDetailRecord> {
  return apiGet<PredictionDetailRecord>(`/api/prediction-results/${encodeURIComponent(id)}`)
}

export function loadData(filePath: string): Promise<LoadDataResponse> {
  return apiPost<LoadDataResponse>('/api/load-data', { file_path: filePath })
}

export function loadModel(body: { model_key: string; device: string }): Promise<LoadModelResponse> {
  return apiPost<LoadModelResponse>('/api/load-model', body)
}

export function predict(body: PredictRequest): Promise<PredictResponse> {
  return apiPost<PredictResponse>('/api/predict', body)
}

export function marketHistory(params: {
  ticker?: string
  interval?: string
  period?: string
}): Promise<MarketHistoryResponse> {
  const q = new URLSearchParams()
  if (params.ticker) q.set('ticker', params.ticker)
  if (params.interval) q.set('interval', params.interval)
  if (params.period) q.set('period', params.period)
  const qs = q.toString()
  return apiGet<MarketHistoryResponse>(`/api/market-history${qs ? `?${qs}` : ''}`)
}

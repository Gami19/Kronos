import { apiGet, apiPost, apiPostFormData } from './client'
import type {
  AvailableModelsResponse,
  ImportMarketResponse,
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
  UploadDataResponse,
  ValidateDataResponse,
  CreateTrainJobRequest,
  CreateTrainJobResponse,
  ListTrainJobsResponse,
  GetTrainJobResponse,
  TrainJobLogResponse,
  LoadModelRequest,
  BacktestRunRequest,
  BacktestRunResponse,
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

export function importMarket(body: {
  ticker_id: string
  interval?: string
  period?: string
}): Promise<ImportMarketResponse> {
  return apiPost<ImportMarketResponse>('/api/data/import-market', body)
}

export function uploadDataFile(tickerId: string, file: File): Promise<UploadDataResponse> {
  const fd = new FormData()
  fd.set('ticker_id', tickerId)
  fd.set('file', file)
  return apiPostFormData<UploadDataResponse>('/api/data/upload', fd)
}

export function validateDataFile(filePath: string): Promise<ValidateDataResponse> {
  return apiPost<ValidateDataResponse>('/api/data/validate', { file_path: filePath })
}

export function createTrainJob(body: CreateTrainJobRequest): Promise<CreateTrainJobResponse> {
  return apiPost<CreateTrainJobResponse>('/api/train/jobs', body)
}

export function listTrainJobs(): Promise<ListTrainJobsResponse> {
  return apiGet<ListTrainJobsResponse>('/api/train/jobs')
}

export function getTrainJob(jobId: string): Promise<GetTrainJobResponse> {
  return apiGet<GetTrainJobResponse>(`/api/train/jobs/${encodeURIComponent(jobId)}`)
}

export function getTrainJobLog(jobId: string, tailLines = 200): Promise<TrainJobLogResponse> {
  return apiGet<TrainJobLogResponse>(
    `/api/train/jobs/${encodeURIComponent(jobId)}/log?tail_lines=${encodeURIComponent(String(tailLines))}`,
  )
}

export function loadModel(body: LoadModelRequest): Promise<LoadModelResponse> {
  return apiPost<LoadModelResponse>('/api/load-model', body)
}

export function predict(body: PredictRequest): Promise<PredictResponse> {
  return apiPost<PredictResponse>('/api/predict', body)
}

export function runBacktest(body: BacktestRunRequest): Promise<BacktestRunResponse> {
  return apiPost<BacktestRunResponse>('/api/backtest/run', body)
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

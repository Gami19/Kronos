import type { ApiErrorBody } from './types'

async function parseJsonResponse<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!text) {
    return {} as T
  }
  try {
    return JSON.parse(text) as T
  } catch {
    throw new Error(`応答の JSON 解析に失敗しました (HTTP ${res.status})`)
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    headers: { Accept: 'application/json' },
  })
  const data = await parseJsonResponse<T>(res)
  if (!res.ok) {
    const errBody = data as ApiErrorBody
    throw new Error(errBody.error ?? `HTTP ${res.status}`)
  }
  return data
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  const data = await parseJsonResponse<T>(res)
  if (!res.ok) {
    const errBody = data as ApiErrorBody
    throw new Error(errBody.error ?? `HTTP ${res.status}`)
  }
  return data
}

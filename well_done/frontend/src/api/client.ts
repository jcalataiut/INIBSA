import type { Alerta, Stats, TreatedAlert, ClientDetail, FeedbackStats, MapPoint } from '../types'

const BASE = '/api'

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.json()
}

export function getAlerts(params: {
  today?: string
  family?: string
  segment?: string
  tipus?: string
  urgencia?: string
  pendents?: boolean
} = {}): Promise<Alerta[]> {
  const qs = new URLSearchParams()
  if (params.today) qs.set('today', params.today)
  if (params.family) qs.set('family', params.family)
  if (params.segment) qs.set('segment', params.segment)
  if (params.tipus) qs.set('tipus', params.tipus)
  if (params.urgencia) qs.set('urgencia', params.urgencia)
  if (params.pendents) qs.set('pendents', 'true')
  const query = qs.toString()
  return fetchJSON<Alerta[]>(`/alerts${query ? `?${query}` : ''}`)
}

export function getStats(today?: string): Promise<Stats> {
  const qs = today ? `?today=${today}` : ''
  return fetchJSON<Stats>(`/stats${qs}`)
}

export function getTreated(): Promise<TreatedAlert[]> {
  return fetchJSON<TreatedAlert[]>('/treated')
}

export function markTreated(id_cliente: number, familia_potencial: string, tipus_alerta: string, resultado?: string, importe_venta?: number): Promise<{ status: string }> {
  return fetchJSON('/treated', {
    method: 'POST',
    body: JSON.stringify({ id_cliente, familia_potencial, tipus_alerta, resultado, importe_venta }),
  })
}

export function updateFeedback(id_cliente: number, familia_potencial: string, tipus_alerta: string, resultado: string, importe_venta?: number): Promise<{ status: string }> {
  return fetchJSON('/treated/feedback', {
    method: 'POST',
    body: JSON.stringify({ id_cliente, familia_potencial, tipus_alerta, resultado, importe_venta }),
  })
}

export function getFeedbackStats(): Promise<FeedbackStats> {
  return fetchJSON<FeedbackStats>('/treated/stats')
}

export function unmarkTreated(id: number): Promise<{ status: string }> {
  return fetchJSON(`/treated/${id}`, { method: 'DELETE' })
}

export function getClient(id: number): Promise<ClientDetail> {
  return fetchJSON<ClientDetail>(`/clients/${id}`)
}

export function refreshCache(): Promise<{ status: string; today: string }> {
  return fetchJSON('/refresh', { method: 'POST' })
}

export function getMapData(today?: string): Promise<MapPoint[]> {
  const qs = today ? `?today=${today}` : ''
  return fetchJSON<MapPoint[]>(`/alerts/map${qs}`)
}

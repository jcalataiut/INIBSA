export interface Alerta {
  id_cliente: number
  provincia: string
  cod_postal: string | null
  city: string | null
  latitude: number | null
  longitude: number | null
  familia_potencial: string
  segment: string
  segment_anterior: string | null
  tipus_alerta: string
  urgencia: string
  canal: string
  share_12m: number
  share_velocity: number | null
  share_alerta: string | null
  potencial_anual_eur: number
  euros_12m: number
  gap_eur: number
  dies_sense_compra: number
  num_intervals: number
  cicle_mig_dies: number | null
  cicle_std_dies: number | null
  dies_retard: number
  z_score: number | null
  proxim_pedido_esperat: string | null
  dies_stock: number | null
  prioritat: number
  motiu: string
  data_alerta: string
  geo_neighbor_count: number | null
  geo_neighbor_avg_share: number | null
  geo_share_gap: number | null
  tractada: boolean
}

export interface Stats {
  total_alertes: number
  pendents: number
  tractades: number
  gap_total: number
  alta_urgencia: number
  per_segment: Record<string, number>
  per_tipus: Record<string, number>
}

export interface TreatedAlert {
  id: number
  client_familia_tipus: string
  id_cliente: number
  familia_potencial: string
  tipus_alerta: string
  treated_date: string
}

export const SEGMENT_COLORS: Record<string, string> = {
  leal: '#00B8A9',
  promiscuo: '#F4A261',
  fugat: '#6B7280',
}

export interface ClientDetail {
  id_cliente: number
  cod_postal: string
  provincia: string
  historial: { fecha: string; factura: string; familia: string; valor: number; unitats: number }[]
  alertes: { tipus_alerta: string; familia_potencial: string; prioritat: number; motiu: string }[]
}

export interface GeoPoint {
  id_cliente: number
  familia_potencial: string
  cod_postal: string
  city: string
  provincia: string
  latitude: number
  longitude: number
  share_12m: number
  gap_eur: number
}

export interface GeoContext {
  familia_potencial: string
  points: GeoPoint[]
}

export const ALERTA_LABELS: Record<string, string> = {
  anticipacio: 'Anticipació',
  reactiva: 'Reactiva',
  geografica: 'Geogràfica',
  fugat: 'Fugat',
}

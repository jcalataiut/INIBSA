export interface Alerta {
  id_cliente: number
  provincia: string
  familia_potencial: string
  segment: string
  segment_anterior: string | null
  tipus_alerta: string
  urgencia: string
  canal: string
  share_12m: number
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
  fidel: '#00B8A9',
  promiscu: '#F4A261',
  marginal: '#6B7280',
  en_risc: '#E76F51',
  nou: '#3498DB',
  perdut: '#6B7280',
  fugat: '#E74C3C',
}

export interface ClientDetail {
  id_cliente: number
  cod_postal: string
  provincia: string
  historial: { fecha: string; factura: string; familia: string; valor: number; unitats: number }[]
  alertes: { tipus_alerta: string; familia_potencial: string; prioritat: number; motiu: string }[]
}

export const ALERTA_LABELS: Record<string, string> = {
  finestra_captura: 'Finestra Captura',
  risc_fuga: 'Risc de Fuga',
  reposicio_endarrerida: 'Rep. Endarrerida',
  reposicio_preventiva: 'Rep. Preventiva',
  reposicio_pendent: 'Rep. Pendent',
  oportunitat_captura: 'Oport. Captura',
  monitoritzar: 'Monitoritzar',
  info: 'Info',
  fugat: 'Fugat',
  perdut: 'Perdut',
}

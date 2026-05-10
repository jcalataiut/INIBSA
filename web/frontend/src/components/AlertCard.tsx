import type { CSSProperties } from 'react'
import type { Alerta } from '../types'
import ContactActions from './ContactActions'

interface Props {
  alert: Alerta
  onToggleTreated: (a: Alerta) => void
  onClick?: (a: Alerta) => void
}

const TIPUS_STYLE: Record<string, { label: string; color: string }> = {
  anticipacio:        { label: 'ANTICIPAT', color: '#059669' },
  reactiva:           { label: 'REACTIVA',  color: '#DC2626' },
  fugat:              { label: 'FUGAT',     color: '#6B7280' },
  anomalia_groga:     { label: 'GROGA',     color: '#D97706' },
  anomalia_vermella:  { label: 'VERMELLA',  color: '#DC2626' },
  caiguda_volum:      { label: 'VOLUM',     color: '#8B5CF6' },
  monitoritzar:       { label: 'MONITOR',   color: '#3B82F6' },
}

const URGENCIA_STYLE: Record<string, string> = {
  critica: '#DC2626',
  alta:    '#D97706',
  mitjana: '#3B82F6',
  baixa:   '#718096',
}

export default function AlertCard({ alert, onToggleTreated, onClick }: Props) {
  const isLeal = alert.segment === 'leal' || alert.segment === 'actiu_regular' || alert.share_12m >= 0.70
  const shareLabel = isLeal ? 'leal' : 'promiscuo'
  const shareColor = isLeal ? '#00B8A9' : '#F4A261'

  const typeStyle = TIPUS_STYLE[alert.tipus_alerta] || { label: alert.tipus_alerta, color: '#718096' }
  const urgencyColor = URGENCIA_STYLE[alert.urgencia] || '#718096'

  return (
    <div style={styles.card} onClick={() => onClick && onClick(alert)}>
      <div style={styles.top}>
        <div style={styles.left}>
          <span style={styles.id}>#{alert.id_cliente}</span>
          <span style={styles.sep}>·</span>
          <span style={styles.familia}>{alert.familia_potencial}</span>
          <span style={{ ...styles.shareBadge, color: shareColor, borderColor: shareColor }}>
            {shareLabel}
          </span>
        </div>
        <div style={styles.right}>
          <div style={{ ...styles.tag, background: typeStyle.color }}>
            {typeStyle.label.replace(/_/g, ' ')}
          </div>
          <div style={{ ...styles.tagOutline, color: urgencyColor, borderColor: urgencyColor }}>
            {alert.urgencia}
          </div>
        </div>
      </div>

      <div style={styles.bottom}>
        <div style={styles.metric}>
          <span style={styles.mVal}>{alert.gap_eur.toLocaleString()}€</span>
          <span style={styles.mLbl}>gap</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.mVal}>{alert.dies_sense_compra}d</span>
          <span style={styles.mLbl}>sense compra</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.mVal}>{alert.cicle_mig_dies ? `${alert.cicle_mig_dies.toFixed(0)}d` : '-'}</span>
          <span style={styles.mLbl}>cicle</span>
        </div>
        <div style={{ flex: 1 }} />
        <ContactActions alert={alert} onToggleTreated={onToggleTreated} variant="compact" />
      </div>
    </div>
  )
}

const styles: Record<string, CSSProperties> = {
  card: {
    background: '#FFFFFF',
    borderRadius: 8,
    padding: '20px',
    marginBottom: 12,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    border: '1px solid #E2E8F0',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  top: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  id: {
    fontSize: 18,
    fontWeight: 800,
    color: '#1A202C',
  },
  sep: {
    color: '#CBD5E0',
    fontSize: 18,
  },
  familia: {
    fontSize: 16,
    fontWeight: 600,
    color: '#4A5568',
  },
  shareBadge: {
    fontSize: 11,
    fontWeight: 700,
    padding: '2px 8px',
    borderRadius: 4,
    border: '1px solid',
    textTransform: 'uppercase' as const,
    marginLeft: 4,
  },
  tag: {
    fontSize: 10,
    fontWeight: 800,
    color: '#FFFFFF',
    padding: '4px 10px',
    borderRadius: 4,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.02em',
  },
  tagOutline: {
    fontSize: 10,
    fontWeight: 800,
    padding: '3px 10px',
    borderRadius: 4,
    textTransform: 'uppercase' as const,
    border: '1px solid',
    letterSpacing: '0.02em',
  },
  bottom: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 24,
  },
  metric: {
    display: 'flex',
    flexDirection: 'column',
  },
  mVal: {
    fontSize: 16,
    fontWeight: 700,
    color: '#2D3748',
  },
  mLbl: {
    fontSize: 11,
    color: '#A0AEC0',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
  },
}


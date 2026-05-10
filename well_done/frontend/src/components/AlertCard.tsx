import type { Alerta } from '../types'

interface Props {
  alert: Alerta
  onToggleTreated: (a: Alerta) => void
  onClick?: (a: Alerta) => void
}

export default function AlertCard({ alert, onToggleTreated, onClick }: Props) {
  const borderColor = alert.tipus_alerta === 'anticipacio' ? '#00B8A9'
    : alert.tipus_alerta === 'reactiva' ? '#E74C3C'
    : alert.tipus_alerta === 'fugat' ? '#6B7280'
    : '#E5E7EB'

  const isFugat = alert.segment === 'fugat'
  const shareLabel = isFugat ? 'fugat' : (alert.share_12m >= 0.70 ? 'leal' : 'promiscuo')
  const shareColor = isFugat ? '#6B7280' : (alert.share_12m >= 0.70 ? '#00B8A9' : '#F4A261')

  return (
    <div
      style={{ ...styles.card, borderLeft: `3px solid ${borderColor}`, opacity: alert.tractada ? 0.4 : 1, cursor: 'pointer' }}
      onClick={() => onClick?.(alert)}
    >
      <div style={styles.row}>
        <div style={styles.colMain}>
          <span style={styles.id}>#{alert.id_cliente}</span>
          <span style={styles.dot}>·</span>
          <span style={styles.familia}>{alert.familia_potencial}</span>
        </div>

        <div style={styles.colShare}>
          <span style={{ ...styles.value, color: shareColor }}>{(alert.share_12m * 100).toFixed(0)}%</span>
          <span style={{ ...styles.tag, background: shareColor }}>{shareLabel}</span>
        </div>

        <div style={styles.colMetrics}>
          <span style={styles.value}>{alert.gap_eur.toLocaleString(undefined, { maximumFractionDigits: 0 })}€</span>
          <span style={styles.lbl}>gap</span>
        </div>

        <div style={styles.colMetrics}>
          <span style={styles.value}>{alert.dies_sense_compra}d</span>
          <span style={styles.lbl}>sense compra</span>
        </div>

        <div style={styles.colMetricsSm}>
          <span style={styles.value}>{alert.cicle_mig_dies ? alert.cicle_mig_dies.toFixed(0) : '-'}d</span>
          <span style={styles.lbl}>cicle</span>
        </div>

        <div style={styles.colToggle}>
          <button style={styles.toggle} onClick={e => { e.stopPropagation(); onToggleTreated(alert) }}>
            {alert.tractada ? '↩' : '✓'}
          </button>
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    marginBottom: 4,
    borderRadius: 6,
    transition: 'all 0.15s ease',
    boxShadow: '0 1px 2px rgba(0,0,0,0.01)',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    padding: '14px 20px',
  },
  colMain: {
    flex: '1.2',
    display: 'flex',
    alignItems: 'center',
    overflow: 'hidden',
  },
  colShare: {
    flex: '0.8',
    display: 'flex',
    alignItems: 'center',
  },
  colMetrics: {
    flex: '0.8',
    display: 'flex',
    alignItems: 'baseline',
  },
  colMetricsSm: {
    flex: '0.6',
    display: 'flex',
    alignItems: 'baseline',
  },
  colToggle: {
    width: '40px',
    display: 'flex',
    justifyContent: 'flex-end',
  },
  id: {
    fontSize: 14,
    fontWeight: 600,
    color: '#374151',
    fontVariantNumeric: 'tabular-nums',
    whiteSpace: 'nowrap' as const,
  },
  dot: {
    color: '#D1D5DB',
    margin: '0 8px',
    fontSize: 14,
  },
  familia: {
    fontSize: 13,
    fontWeight: 500,
    color: '#6B7280',
    whiteSpace: 'nowrap' as const,
    textOverflow: 'ellipsis',
    overflow: 'hidden',
  },
  value: {
    fontSize: 14,
    fontWeight: 600,
    color: '#111827',
    fontVariantNumeric: 'tabular-nums',
    whiteSpace: 'nowrap' as const,
  },
  lbl: {
    fontSize: 11,
    color: '#9CA3AF',
    marginLeft: 4,
    fontWeight: 500,
    whiteSpace: 'nowrap' as const,
  },
  tag: {
    fontSize: 10,
    fontWeight: 600,
    color: '#FFFFFF',
    padding: '2px 8px',
    borderRadius: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
    marginLeft: 8,
    whiteSpace: 'nowrap' as const,
  },
  toggle: {
    background: 'none',
    border: 'none',
    fontSize: 14,
    fontWeight: 600,
    color: '#9CA3AF',
    cursor: 'pointer',
    padding: '4px',
  },
}

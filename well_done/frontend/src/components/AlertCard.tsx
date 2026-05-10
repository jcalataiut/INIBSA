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
        <span style={styles.id}>#{alert.id_cliente}</span>
        <span style={styles.dot}>·</span>
        <span style={styles.familia}>{alert.familia_potencial}</span>
        <span style={styles.spacer} />

        <span style={{ ...styles.value, color: shareColor }}>{(alert.share_12m * 100).toFixed(0)}%</span>
        <span style={{ ...styles.tag, background: shareColor }}>{shareLabel}</span>
        <span style={styles.spacer} />

        <span style={styles.value}>{alert.gap_eur.toLocaleString()}€</span>
        <span style={styles.lbl}>gap</span>
        <span style={styles.spacer} />

        <span style={styles.value}>{alert.dies_sense_compra}d</span>
        <span style={styles.lbl}>sense compra</span>
        <span style={styles.spacer} />

        <span style={styles.value}>{alert.cicle_mig_dies ? alert.cicle_mig_dies.toFixed(0) : '-'}d</span>
        <span style={styles.lbl}>cicle</span>

        <button style={styles.toggle} onClick={e => { e.stopPropagation(); onToggleTreated(alert) }}>
          {alert.tractada ? '○' : '●'}
        </button>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    marginBottom: 3,
    transition: 'opacity 0.15s',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 0,
    padding: '10px 16px',
  },
  id: {
    fontSize: 14,
    fontWeight: 700,
    color: '#111827',
    fontVariantNumeric: 'tabular-nums',
    whiteSpace: 'nowrap' as const,
  },
  dot: {
    color: '#D1D5DB',
    margin: '0 6px',
    fontSize: 14,
  },
  familia: {
    fontSize: 14,
    fontWeight: 500,
    color: '#374151',
    whiteSpace: 'nowrap' as const,
  },
  spacer: {
    display: 'inline-block',
    width: 20,
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
    marginLeft: 3,
    whiteSpace: 'nowrap' as const,
  },
  tag: {
    fontSize: 9,
    fontWeight: 600,
    color: '#FFFFFF',
    padding: '1px 7px',
    textTransform: 'uppercase',
    letterSpacing: 0.3,
    marginLeft: 4,
    whiteSpace: 'nowrap' as const,
  },
  toggle: {
    background: 'none',
    border: 'none',
    fontSize: 14,
    color: '#D1D5DB',
    cursor: 'pointer',
    padding: '2px 0 2px 16px',
    marginLeft: 'auto',
    lineHeight: 1,
    fontFamily: "'Inter', sans-serif",
  },
}

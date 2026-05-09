import type { Alerta } from '../types'
import { SEGMENT_COLORS, ALERTA_LABELS } from '../types'

interface Props {
  alert: Alerta
  onToggleTreated: (a: Alerta) => void
}

export default function AlertCard({ alert, onToggleTreated }: Props) {
  const isFugat = alert.segment === 'fugat'
  const prioColor = alert.prioritat >= 500 ? '#E76F51' : alert.prioritat >= 100 ? '#F4A261' : '#6B7280'
  const borderColor = alert.tipus_alerta === 'finestra_captura' ? '#00B8A9'
    : alert.tipus_alerta === 'risc_fuga' ? '#E76F51'
    : '#1F1F1F'

  return (
    <div style={{ ...styles.card, borderLeft: `3px solid ${borderColor}`, opacity: alert.tractada ? 0.4 : 1 }}>
      <div style={styles.mainRow}>
        <div style={styles.colClient}>
          <span style={styles.clientId}>#{alert.id_cliente}</span>
          <span style={styles.provincia}>{alert.provincia || '?'}</span>
        </div>
        <div style={styles.colFamilia}>
          <span style={styles.familia}>{alert.familia_potencial}</span>
          <span style={styles.tipus}>{ALERTA_LABELS[alert.tipus_alerta] || alert.tipus_alerta}</span>
        </div>
        <div style={styles.colSegment}>
          <span style={{ ...styles.segmentBadge, background: SEGMENT_COLORS[alert.segment] || '#555' }}>
            {alert.segment}
          </span>
          <span style={styles.share}>share { (alert.share_12m * 100).toFixed(0) }%</span>
        </div>
        <div style={styles.colGap}>
          <span style={styles.gapValue}>{alert.gap_eur.toLocaleString()}€</span>
          <span style={styles.gapLabel}>gap</span>
          {alert.dies_stock !== null && alert.dies_stock !== undefined && (
            <span style={styles.stock}>stock: {Number(alert.dies_stock).toFixed(0)}d</span>
          )}
        </div>
        <div style={styles.colDies}>
          <span style={styles.diesValue}>{alert.dies_sense_compra}d</span>
          <span style={styles.diesLabel}>sense compra</span>
        </div>
        <div style={styles.colPrio}>
          <span style={{ ...styles.prioValue, color: prioColor }}>
            {alert.prioritat >= 500 ? 'CRÍTICA' : alert.prioritat >= 100 ? 'IMPORTANT' : 'INFO'}
          </span>
          <span style={styles.prioLabel}>prio {alert.prioritat.toFixed(0)}</span>
        </div>
        <div style={styles.colCanal}>
          <span style={styles.canalValue}>{alert.canal === 'delegat' ? '👤 Delegat' : '📞 Televenda'}</span>
          <span style={styles.urgenciaLabel}>{alert.urgencia.toUpperCase()}</span>
        </div>
        <div style={styles.colAction}>
          <button
            style={styles.actionBtn}
            onClick={() => onToggleTreated(alert)}
          >
            {alert.tractada ? '↩' : '✓'}
          </button>
        </div>
      </div>
      <div style={styles.motiuRow}>
        <span style={styles.motiuText}>{alert.motiu}</span>
        {alert.cicle_mig_dies !== null && (
          <span style={styles.cicleInfo}>cicle: {alert.cicle_mig_dies.toFixed(0)}d</span>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#111111',
    border: '1px solid #1F1F1F',
    marginBottom: 6,
    transition: 'opacity 0.15s',
  },
  mainRow: {
    display: 'grid',
    gridTemplateColumns: '1.5fr 1.5fr 1.2fr 1.2fr 0.8fr 1fr 1fr 48px',
    gap: 8,
    padding: '14px 20px',
    alignItems: 'center',
  },
  colClient: { display: 'flex', flexDirection: 'column', gap: 1 },
  clientId: { fontSize: 14, fontWeight: 600, color: '#FFFFFF' },
  provincia: { fontSize: 10, color: '#6B7280' },
  colFamilia: { display: 'flex', flexDirection: 'column', gap: 1 },
  familia: { fontSize: 13, fontWeight: 500, color: '#E5E7EB' },
  tipus: { fontSize: 10, color: '#9CA3AF' },
  colSegment: { display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' },
  segmentBadge: {
    fontSize: 10, fontWeight: 600, color: '#FFFFFF',
    padding: '2px 8px', textTransform: 'uppercase', letterSpacing: 0.5,
  },
  share: { fontSize: 10, color: '#6B7280' },
  colGap: { display: 'flex', flexDirection: 'column', gap: 1 },
  gapValue: { fontSize: 16, fontWeight: 700, color: '#00B8A9' },
  gapLabel: { fontSize: 10, color: '#6B7280' },
  stock: { fontSize: 10, color: '#F4A261' },
  colDies: { display: 'flex', flexDirection: 'column', gap: 1 },
  diesValue: { fontSize: 16, fontWeight: 600, color: '#E5E7EB' },
  diesLabel: { fontSize: 10, color: '#6B7280' },
  colPrio: { display: 'flex', flexDirection: 'column', gap: 1 },
  prioValue: { fontSize: 10, fontWeight: 700, letterSpacing: 0.5 },
  prioLabel: { fontSize: 10, color: '#6B7280' },
  colCanal: { display: 'flex', flexDirection: 'column', gap: 1 },
  canalValue: { fontSize: 11, fontWeight: 500, color: '#E5E7EB' },
  urgenciaLabel: { fontSize: 10, color: '#6B7280', letterSpacing: 0.5 },
  colAction: { display: 'flex', justifyContent: 'center' },
  actionBtn: {
    width: 32, height: 32,
    background: '#1A1A1A',
    border: '1px solid #2A2A2A',
    color: '#9CA3AF',
    fontSize: 14,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: "'Inter', sans-serif",
    transition: 'all 0.1s',
  },
  motiuRow: {
    borderTop: '1px solid #1A1A1A',
    padding: '8px 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 16,
  },
  motiuText: {
    fontSize: 11,
    color: '#6B7280',
    lineHeight: 1.4,
    flex: 1,
  },
  cicleInfo: {
    fontSize: 10,
    color: '#4B5563',
    whiteSpace: 'nowrap',
  },
}

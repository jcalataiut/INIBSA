import type { Alerta } from '../types'
import AlertCard from './AlertCard'

interface Props {
  alerts: Alerta[]
  loading: boolean
  onToggleTreated: (a: Alerta) => void
}

export default function AlertList({ alerts, loading, onToggleTreated }: Props) {
  if (loading) {
    return (
      <div style={styles.empty}>
        <div style={styles.spinner} />
        <span style={styles.emptyText}>Calculant alertes...</span>
      </div>
    )
  }

  if (alerts.length === 0) {
    return (
      <div style={styles.empty}>
        <span style={styles.emptyIcon}>✓</span>
        <span style={styles.emptyText}>Totes les alertes tractades. Bona feina!</span>
      </div>
    )
  }

  return (
    <div>
      <div style={styles.count}>
        {alerts.length} alertes
      </div>
      <div>
        {alerts.map((a, i) => (
          <AlertCard key={`${a.id_cliente}_${a.familia_potencial}_${a.tipus_alerta}_${i}`} alert={a} onToggleTreated={onToggleTreated} />
        ))}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '80px 0',
    gap: 16,
  },
  spinner: {
    width: 24,
    height: 24,
    border: '2px solid #E5E7EB',
    borderTop: '2px solid #00B8A9',
    animation: 'spin 0.8s linear infinite',
  },
  emptyIcon: {
    fontSize: 32,
    color: '#00B8A9',
    fontWeight: 700,
  },
  emptyText: {
    fontSize: 14,
    color: '#6B7280',
  },
  count: {
    fontSize: 11,
    fontWeight: 600,
    color: '#6B7280',
    textTransform: 'uppercase',
    letterSpacing: 1,
    paddingBottom: 12,
  },
}

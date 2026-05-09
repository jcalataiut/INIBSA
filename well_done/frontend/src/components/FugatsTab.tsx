import type { Alerta } from '../types'
import AlertCard from './AlertCard'

interface Props {
  alerts: Alerta[]
  loading: boolean
  onToggleTreated: (a: Alerta) => void
}

export default function FugatsTab({ alerts, loading, onToggleTreated }: Props) {
  if (loading) {
    return (
      <div style={styles.empty}>
        <div style={styles.spinner} />
        <span style={styles.emptyText}>Carregant...</span>
      </div>
    )
  }

  return (
    <div>
      <div style={styles.header}>
        <h2 style={styles.title}>Clients Fugats</h2>
        <p style={styles.subtitle}>
          Porten més d'un any sense comprar. Requereixen recuperació directa per delegat.
        </p>
      </div>

      {alerts.length === 0 ? (
        <div style={styles.empty}>
          <span style={styles.emptyIcon}>✓</span>
          <span style={styles.emptyText}>Cap client fugat. Bona feina!</span>
        </div>
      ) : (
        <>
          <div style={styles.count}>{alerts.length} fugats pendents de recuperació</div>
          <div>
            {alerts.map((a, i) => (
              <AlertCard key={`fugat_${a.id_cliente}_${i}`} alert={a} onToggleTreated={onToggleTreated} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    padding: '24px 0 16px',
  },
  title: {
    fontSize: 20,
    fontWeight: 700,
    color: '#FFFFFF',
    margin: 0,
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: 13,
    color: '#6B7280',
    margin: '6px 0 0',
  },
  count: {
    fontSize: 11,
    fontWeight: 600,
    color: '#6B7280',
    textTransform: 'uppercase',
    letterSpacing: 1,
    paddingBottom: 12,
  },
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
    border: '2px solid #1F1F1F',
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
}

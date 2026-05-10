import type { CSSProperties } from 'react'
import type { Alerta } from '../types'
import AlertCard from './AlertCard'

interface Props {
  alerts: Alerta[]
  loading: boolean
  onToggleTreated: (a: Alerta) => void
  onClickAlert?: (a: Alerta) => void
  listLabel?: string
}

export default function AlertList({ alerts, loading, onToggleTreated, onClickAlert, listLabel }: Props) {
  if (loading) {
    return (
      <div style={styles.empty}>
        <div style={styles.spinner} />
        <span style={styles.emptyText}>Actualitzant llista...</span>
      </div>
    )
  }

  if (alerts.length === 0) {
    const msg = listLabel === 'tractades'
      ? 'Encara no has tractat cap alerta.'
      : 'Bones notícies! No hi ha alertes pendents.'
    return (
      <div style={styles.empty}>
        <div style={styles.emptyIcon}>✓</div>
        <span style={styles.emptyText}>{msg}</span>
      </div>
    )
  }

  const LIMIT = 100
  const displayedAlerts = alerts.slice(0, LIMIT)

  return (
    <div style={styles.listWrapper}>
      <div style={styles.count}>
        Mostrant {displayedAlerts.length} de {alerts.length.toLocaleString()} alertes trobades
      </div>
      {displayedAlerts.map((a, i) => (
        <AlertCard 
          key={`${a.id_cliente}_${a.familia_potencial}_${a.tipus_alerta}_${i}`} 
          alert={a} 
          onToggleTreated={onToggleTreated} 
          onClick={onClickAlert} 
        />
      ))}
      {alerts.length > LIMIT && (
        <div style={styles.infoBox}>
          Refina els filtres per veure alertes més específiques (només es mostren les primeres {LIMIT}).
        </div>
      )}
    </div>
  )
}

const styles: Record<string, CSSProperties> = {
  listWrapper: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'stretch',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '100px 0',
    gap: 20,
    animation: 'fadeIn 0.6s ease-out',
  },
  spinner: {
    width: 28,
    height: 28,
    border: '3px solid #E5E5EA',
    borderTop: '3px solid #00B8A9',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  emptyIcon: {
    fontSize: 48,
    color: '#34C759',
    background: 'rgba(52, 199, 89, 0.1)',
    width: 80,
    height: 80,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 700,
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 17,
    fontWeight: 500,
    color: '#8E8E93',
    textAlign: 'center',
    maxWidth: 300,
    lineHeight: 1.4,
  },
  count: {
    fontSize: 13,
    fontWeight: 600,
    color: '#8E8E93',
    paddingBottom: 20,
    textAlign: 'center',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  infoBox: {
    padding: '24px',
    background: '#FFFFFF',
    borderRadius: 12,
    border: '1px dashed #CBD5E0',
    color: '#718096',
    textAlign: 'center',
    fontSize: 14,
    fontWeight: 500,
    margin: '20px auto',
    maxWidth: 600,
    width: '100%',
  },
}

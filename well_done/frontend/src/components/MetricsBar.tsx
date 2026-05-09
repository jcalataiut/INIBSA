import type { Stats } from '../types'

interface Props { stats: Stats }

export default function MetricsBar({ stats }: Props) {
  const items = [
    { label: 'Alertes', value: stats.total_alertes.toLocaleString(), color: '#111827' },
    { label: 'Pendents', value: stats.pendents.toLocaleString(), color: '#E67E22' },
    { label: 'Gap Total', value: `${stats.gap_total.toLocaleString()}€`, color: '#00B8A9' },
    { label: 'Alta Urgència', value: stats.alta_urgencia.toLocaleString(), color: '#E74C3C' },
  ]

  return (
    <div style={styles.bar}>
      <div style={styles.grid}>
        {items.map(item => (
          <div key={item.label} style={styles.card}>
            <span style={styles.value(item.color)}>{item.value}</span>
            <span style={styles.label}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

const styles: Record<string, any> = {
  bar: {
    padding: '24px 0 20px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 16,
  },
  card: {
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  value: (color: string) => ({
    fontSize: 28,
    fontWeight: 700,
    color,
    lineHeight: 1.1,
  }),
  label: {
    fontSize: 11,
    fontWeight: 500,
    color: '#6B7280',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
}

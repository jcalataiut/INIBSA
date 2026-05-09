import { useEffect, useState } from 'react'
import type { Alerta, ClientDetail } from '../types'
import { getClient } from '../api/client'
import { SEGMENT_COLORS, ALERTA_LABELS } from '../types'

interface Props {
  alert: Alerta
  onBack: () => void
  onToggleTreated: (a: Alerta) => void
}

export default function AlertDetail({ alert, onBack, onToggleTreated }: Props) {
  const [data, setData] = useState<ClientDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getClient(alert.id_cliente).then(d => { setData(d); setLoading(false) }).catch(() => setLoading(false))
  }, [alert.id_cliente])

  const prioColor = alert.prioritat >= 500 ? '#E74C3C' : alert.prioritat >= 100 ? '#E67E22' : '#6B7280'
  const borderColor = alert.tipus_alerta === 'finestra_captura' ? '#00B8A9'
    : alert.tipus_alerta === 'risc_fuga' ? '#E74C3C' : '#E5E7EB'

  const historial = data?.historial?.slice().reverse() || []

  const maxValor = Math.max(...historial.map(h => h.valor), 1)

  const W = 600, H = 180, BAR_GAP = 2

  return (
    <div>
      <button style={styles.backBtn} onClick={onBack}>← Tornar</button>

      <div style={{ ...styles.hero, borderLeft: `4px solid ${borderColor}` }}>
        <div style={styles.heroTop}>
          <div>
            <span style={styles.heroId}>#{alert.id_cliente}</span>
            <span style={styles.heroProv}>{alert.provincia || '?'}</span>
          </div>
          <button
            style={styles.treatBtn}
            onClick={() => onToggleTreated(alert)}
          >
            {alert.tractada ? '↩ Desmarcar' : 'Tractar'}
          </button>
        </div>
        <div style={styles.heroBadges}>
          <span style={{ ...styles.badge, background: SEGMENT_COLORS[alert.segment] || '#6B7280' }}>{alert.segment}</span>
          <span style={{ ...styles.badge, background: borderColor }}>{ALERTA_LABELS[alert.tipus_alerta] || alert.tipus_alerta}</span>
          <span style={{ ...styles.badge, background: prioColor }}>
            {alert.prioritat >= 500 ? 'CRÍTICA' : alert.prioritat >= 100 ? 'IMPORTANT' : 'INFO'}
          </span>
        </div>
        <p style={styles.heroMotiu}>{alert.motiu}</p>
      </div>

      <div style={styles.grid}>
        <div style={styles.metric}>
          <span style={styles.metricVal}>{alert.gap_eur.toLocaleString()}€</span>
          <span style={styles.metricLabel}>Gap anual</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.metricVal}>{(alert.share_12m * 100).toFixed(0)}%</span>
          <span style={styles.metricLabel}>Share of wallet</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.metricVal}>{alert.dies_sense_compra}d</span>
          <span style={styles.metricLabel}>Sense compra</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.metricVal}>{alert.cicle_mig_dies ? alert.cicle_mig_dies.toFixed(0) : '?'}d</span>
          <span style={styles.metricLabel}>Cicle mitjà</span>
        </div>
      </div>

      <div style={styles.section}>
        <span style={styles.sectionTitle}>Historial de compres</span>
        {loading ? (
          <p style={{ color: '#6B7280', fontSize: 13 }}>Carregant...</p>
        ) : historial.length === 0 ? (
          <p style={{ color: '#6B7280', fontSize: 13 }}>Sense historial</p>
        ) : (
          <svg width="100%" viewBox={`0 0 ${W} ${H + 40}`} style={styles.chart}>
            {historial.map((h, i) => {
              const x = i * (W / historial.length)
              const barW = Math.max(4, W / historial.length - BAR_GAP)
              const barH = (h.valor / maxValor) * H
              return (
                <g key={i}>
                  <rect x={x} y={H - barH} width={barW} height={barH} fill="#00B8A9" rx={1} />
                  <text x={x + barW / 2} y={H + 14} textAnchor="end" fontSize="8" fill="#9CA3AF" transform={`rotate(-45, ${x + barW / 2}, ${H + 14})`}>
                    {h.fecha.slice(5, 10)}
                  </text>
                </g>
              )
            })}
            <line x1={0} y1={H} x2={W} y2={H} stroke="#E5E7EB" />
          </svg>
        )}
      </div>

      {data?.alertes && data.alertes.length > 0 && (
        <div style={styles.section}>
          <span style={styles.sectionTitle}>Alertes del client</span>
          {data.alertes.map((a, i) => (
            <div key={i} style={styles.miniAlert}>
              <span style={{ ...styles.miniBadge, background: a.prioritat >= 500 ? '#E74C3C' : a.prioritat >= 100 ? '#E67E22' : '#6B7280' }}>
                {a.tipus_alerta.replace(/_/g, ' ')}
              </span>
              <span style={styles.miniFam}>{a.familia_potencial}</span>
              <span style={styles.miniPrio}>prio {a.prioritat.toFixed(0)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  backBtn: {
    background: 'none',
    border: 'none',
    color: '#00B8A9',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
    padding: '20px 0 16px',
    display: 'block',
  },
  hero: {
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    padding: '24px 28px',
    marginBottom: 20,
  },
  heroTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  heroId: {
    fontSize: 22,
    fontWeight: 700,
    color: '#111827',
    marginRight: 8,
  },
  heroProv: {
    fontSize: 13,
    color: '#6B7280',
  },
  treatBtn: {
    background: '#111827',
    border: 'none',
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: 600,
    padding: '8px 18px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
  },
  heroBadges: {
    display: 'flex',
    gap: 8,
    marginBottom: 12,
  },
  badge: {
    fontSize: 10,
    fontWeight: 600,
    color: '#FFFFFF',
    padding: '3px 10px',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  heroMotiu: {
    fontSize: 13,
    color: '#6B7280',
    lineHeight: 1.5,
    margin: 0,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 12,
    marginBottom: 20,
  },
  metric: {
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    padding: '16px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  metricVal: {
    fontSize: 22,
    fontWeight: 700,
    color: '#111827',
  },
  metricLabel: {
    fontSize: 10,
    color: '#6B7280',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    display: 'block',
    fontSize: 12,
    fontWeight: 600,
    color: '#111827',
    marginBottom: 12,
  },
  chart: {
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    padding: '16px 20px',
  },
  miniAlert: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '8px 16px',
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    marginBottom: 4,
  },
  miniBadge: {
    fontSize: 9,
    fontWeight: 600,
    color: '#FFFFFF',
    padding: '2px 8px',
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  miniFam: {
    fontSize: 12,
    color: '#111827',
    flex: 1,
  },
  miniPrio: {
    fontSize: 11,
    color: '#6B7280',
  },
}

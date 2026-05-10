import { useEffect, useState } from 'react'
import type { Alerta, ClientDetail } from '../types'
import { getClient } from '../api/client'

interface Props {
  alert: Alerta
  onBack: () => void
  onToggleTreated: (a: Alerta) => void
}

interface Purchase {
  day: number
  date: string
  valor: number
}

export default function AlertDetail({ alert, onBack, onToggleTreated }: Props) {
  const [data, setData] = useState<ClientDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getClient(alert.id_cliente).then(d => { setData(d); setLoading(false) }).catch(() => setLoading(false))
  }, [alert.id_cliente])

  const borderColor = alert.tipus_alerta === 'anticipacio' ? '#00B8A9'
    : alert.tipus_alerta === 'reactiva' ? '#E74C3C'
    : alert.tipus_alerta === 'fugat' ? '#6B7280'
    : '#E5E7EB'

  const isLeal = alert.share_12m >= 0.70
  const shareLabel = isLeal ? 'leal' : 'promiscuo'
  const shareColor = isLeal ? '#00B8A9' : '#F4A261'

  // ── Build purchase timeline ────────────────────────────
  const historial = data?.historial?.filter(h => h.familia === alert.familia_potencial).reverse() || []
  let purchases: Purchase[] = []
  let primerDate: Date | null = null
  let timelineDays = 0
  let maxValor = 1

  if (historial.length > 0) {
    const dates = historial.map(h => new Date(h.fecha))
    primerDate = new Date(Math.min(...dates.map(d => d.getTime())))
    purchases = historial.map(h => ({
      day: Math.round((new Date(h.fecha).getTime() - primerDate!.getTime()) / 86400000),
      date: h.fecha,
      valor: h.valor,
    }))
    purchases.sort((a, b) => a.day - b.day)
    timelineDays = Math.max(...purchases.map(p => p.day), 1)
    maxValor = Math.max(...purchases.map(p => p.valor), 1)
  }

  // ── Prediction zones ───────────────────────────────────
  const cicle = alert.cicle_mig_dies || 0
  const cicleStd = alert.cicle_std_dies || (cicle * 0.3)
  const diesSense = alert.dies_sense_compra
  const hoje = new Date()
  const hojeDay = primerDate
    ? Math.round((hoje.getTime() - primerDate.getTime()) / 86400000)
    : 0
  const lastPurchaseDay = purchases.length > 0 ? purchases[purchases.length - 1].day : hojeDay

  const properDay = lastPurchaseDay + cicle
  const low = properDay - 0.5 * cicleStd
  const high = properDay + 0.5 * cicleStd
  const riskHigh = properDay + 1.5 * cicleStd

  // ── Chart dimensions ───────────────────────────────────
  const W = 800
  const H = 200
  const PAD = { top: 20, bottom: 40, left: 10, right: 60 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom
  const xMax = Math.max(hojeDay + 30, properDay + riskHigh * 0.5, timelineDays * 1.1)
  const xScale = (d: number) => PAD.left + (d / xMax) * chartW
  const yScale = (v: number) => PAD.top + chartH - (v / maxValor) * chartH * 0.85

  return (
    <div>
      <button style={styles.backBtn} onClick={onBack}>← Tornar</button>

      {/* ── Header ──────────────────────────────────── */}
      <div style={{ ...styles.hero, borderLeft: `4px solid ${borderColor}` }}>
        <div style={styles.heroTop}>
          <div>
            <span style={styles.heroId}>#{alert.id_cliente}</span>
            <span style={styles.heroSep}>·</span>
            <span style={styles.heroFam}>{alert.familia_potencial}</span>
            <span style={styles.heroSep}>·</span>
            <span style={styles.heroProv}>{alert.provincia || '?'}</span>
          </div>
          <button
            style={styles.treatBtn}
            onClick={() => onToggleTreated(alert)}
          >
            {alert.tractada ? '↩' : '✓ Tractar'}
          </button>
        </div>

        {/* ── Chart ──────────────────────────────────── */}
        {loading ? (
          <p style={{ color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>Carregant historial...</p>
        ) : purchases.length === 0 ? (
          <p style={{ color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>Sense historial de compres</p>
        ) : (
          <svg width="100%" viewBox={`0 0 ${W} ${H + 50}`} style={styles.chartSvg}>
            {/* Prediction zones */}
            <rect x={xScale(low)} y={PAD.top} width={xScale(high) - xScale(low)} height={chartH}
              fill="rgba(0,184,169,0.10)" rx={2} />
            <rect x={xScale(high)} y={PAD.top} width={xScale(riskHigh) - xScale(high)} height={chartH}
              fill="rgba(231,76,60,0.08)" rx={2} />
            <line x1={xScale(properDay)} y1={PAD.top} x2={xScale(properDay)} y2={PAD.top + chartH}
              stroke="#00B8A9" strokeWidth={1} strokeDasharray="4,3" opacity={0.5} />

            {/* Purchase bars */}
            {purchases.map((p, i) => {
              const barW = Math.max(3, chartW / xMax * 4)
              const barH = chartH - yScale(p.valor) + PAD.top
              return (
                <g key={i}>
                  <rect x={xScale(p.day) - barW / 2} y={yScale(p.valor)} width={barW} height={barH}
                    fill={p.day <= hojeDay ? '#1565C0' : '#90A4AE'} rx={1} opacity={0.8} />
                  <text x={xScale(p.day)} y={yScale(p.valor) - 4} textAnchor="middle"
                    fontSize={9} fill="#374151" fontWeight={500}>
                    {p.valor.toFixed(0)}€
                  </text>
                </g>
              )
            })}

            {/* Today line */}
            <line x1={xScale(hojeDay)} y1={PAD.top} x2={xScale(hojeDay)} y2={PAD.top + chartH}
              stroke="#111827" strokeWidth={2.5} />
            <text x={xScale(hojeDay)} y={PAD.top + chartH + 16} textAnchor="middle"
              fontSize={10} fontWeight={700} fill="#111827">AVUI</text>

            {/* Baseline */}
            <line x1={PAD.left} y1={PAD.top + chartH} x2={PAD.left + chartW} y2={PAD.top + chartH}
              stroke="#E5E7EB" strokeWidth={1} />

            {/* X-axis labels */}
            {[0, Math.round(xMax * 0.25), Math.round(xMax * 0.5), Math.round(xMax * 0.75), Math.round(xMax)].map(d => (
              <text key={d} x={xScale(d)} y={PAD.top + chartH + 30} textAnchor="middle"
                fontSize={9} fill="#9CA3AF">dia {d}</text>
            ))}
          </svg>
        )}

        {/* ── Motiu ──────────────────────────────────── */}
        <p style={styles.motiu}>{alert.motiu}</p>
      </div>

      {/* ── Metrics ──────────────────────────────────── */}
      <div style={styles.metrics}>
        <span style={{ ...styles.metric, color: shareColor }}>
          {(alert.share_12m * 100).toFixed(0)}% <span style={styles.mLabel}>{shareLabel}</span>
        </span>
        <span style={styles.mDiv}>|</span>
        <span style={styles.metric}>
          {alert.gap_eur.toLocaleString()}€ <span style={styles.mLabel}>gap</span>
        </span>
        <span style={styles.mDiv}>|</span>
        <span style={styles.metric}>
          {diesSense}d <span style={styles.mLabel}>sense compra</span>
        </span>
        <span style={styles.mDiv}>|</span>
        <span style={styles.metric}>
          {cicle > 0 ? `${cicle.toFixed(0)}d` : '-'} <span style={styles.mLabel}>cicle{cicleStd > 0 ? ` ±${cicleStd.toFixed(0)}` : ''}</span>
        </span>
      </div>
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
    padding: '20px 24px',
    marginBottom: 12,
  },
  heroTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  heroId: {
    fontSize: 20,
    fontWeight: 700,
    color: '#111827',
    fontVariantNumeric: 'tabular-nums',
  },
  heroSep: {
    color: '#D1D5DB',
    margin: '0 6px',
    fontSize: 16,
  },
  heroFam: {
    fontSize: 16,
    fontWeight: 600,
    color: '#374151',
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
    padding: '7px 16px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
  },
  chartSvg: {
    display: 'block',
    marginBottom: 16,
  },
  motiu: {
    fontSize: 12,
    color: '#6B7280',
    lineHeight: 1.5,
    margin: 0,
  },
  metrics: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    padding: '14px 20px',
    flexWrap: 'wrap' as const,
  },
  metric: {
    fontSize: 15,
    fontWeight: 600,
    color: '#111827',
    fontVariantNumeric: 'tabular-nums',
  },
  mLabel: {
    fontSize: 11,
    fontWeight: 400,
    color: '#9CA3AF',
  },
  mDiv: {
    color: '#E5E7EB',
    fontSize: 14,
  },
}

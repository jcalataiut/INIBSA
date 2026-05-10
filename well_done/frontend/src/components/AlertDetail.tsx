import { useEffect, useState } from 'react'
import type { Alerta, ClientDetail, GeoContext } from '../types'
import { getClient, getGeoContext } from '../api/client'
import GeoAlertMap from './GeoAlertMap'

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
  const [geoContext, setGeoContext] = useState<GeoContext | null>(null)
  const [geoLoading, setGeoLoading] = useState(false)
  const [simDay, setSimDay] = useState<number | null>(null)

  useEffect(() => {
    setLoading(true)
    getClient(alert.id_cliente).then(d => { setData(d); setLoading(false) }).catch(() => setLoading(false))
  }, [alert.id_cliente])

  useEffect(() => {
    if (alert.tipus_alerta !== 'geografica') {
      setGeoContext(null)
      setGeoLoading(false)
      return
    }
    setGeoLoading(true)
    getGeoContext(alert.familia_potencial)
      .then(context => {
        setGeoContext(context)
        setGeoLoading(false)
      })
      .catch(() => {
        setGeoContext(null)
        setGeoLoading(false)
      })
  }, [alert.familia_potencial, alert.tipus_alerta])

  const borderColor = alert.tipus_alerta === 'anticipacio' ? '#00B8A9'
    : alert.tipus_alerta === 'reactiva' ? '#E74C3C'
    : alert.tipus_alerta === 'geografica' ? '#2563EB'
    : alert.tipus_alerta === 'fugat' ? '#6B7280'
    : '#E5E7EB'

  const isLeal = alert.share_12m >= 0.70
  const shareLabel = isLeal ? 'leal' : 'promiscuo'
  const shareColor = isLeal ? '#00B8A9' : '#F4A261'
  const locationLabel = [alert.city, alert.cod_postal, alert.provincia].filter(Boolean).join(' · ') || alert.provincia || '?'

  // ── Build purchase timeline ────────────────────────────
  const historial = data?.historial?.filter(h => h.familia === alert.familia_potencial).reverse() || []
  let purchases: Purchase[] = []
  let primerDate: Date | null = null
  let timelineDays = 0
  let maxValor = 1

  if (historial.length > 0) {
    const dates = historial.map(h => new Date(h.fecha))
    primerDate = new Date(Math.min(...dates.map(d => d.getTime())))
    
    const agrupades = new Map<number, Purchase>()
    
    historial.forEach(h => {
      const day = Math.round((new Date(h.fecha).getTime() - primerDate!.getTime()) / 86400000)
      if (agrupades.has(day)) {
        agrupades.get(day)!.valor += h.valor
      } else {
        agrupades.set(day, { day, date: h.fecha, valor: h.valor })
      }
    })
    
    purchases = Array.from(agrupades.values()).sort((a, b) => a.day - b.day)
    timelineDays = Math.max(...purchases.map(p => p.day), 1)
    maxValor = Math.max(...purchases.map(p => p.valor), 1)
  }

  // ── EWM (exponentially weighted) ─────────────────────
  function ewmStats(gaps: number[], halfLife = 4): { mean: number; std: number } {
    const n = gaps.length
    if (n === 0) return { mean: 0, std: 0 }
    const lam = Math.LN2 / Math.max(halfLife, 0.1)
    const weights = Array.from({ length: n }, (_, i) => Math.exp(lam * i))
    const wSum = weights.reduce((a, b) => a + b, 0)
    const normW = weights.map(w => w / wSum)
    const mean = normW.reduce((s, w, i) => s + w * gaps[i], 0)
    const variance = normW.reduce((s, w, i) => s + w * (gaps[i] - mean) ** 2, 0)
    const std = Math.sqrt(variance)
    return { mean, std: std > 0 ? std : mean * 0.3 }
  }

  // ── Prediction zones ───────────────────────────────────
  const cicle = alert.cicle_mig_dies || 0
  const cicleStd = alert.cicle_std_dies || (cicle * 0.3)
  const hoje = new Date()
  const actualHojeDay = primerDate
    ? Math.round((hoje.getTime() - primerDate.getTime()) / 86400000)
    : 0

  const hojeDay = simDay !== null ? simDay : actualHojeDay

  // Només tenim en compte les compres fetes fins a l'"avui" simulat
  const visiblePurchases = purchases.filter(p => p.day <= hojeDay)
  const lastPurchaseDay = visiblePurchases.length > 0 ? visiblePurchases[visiblePurchases.length - 1].day : hojeDay

  // Recalcular cicle EWM amb les dades disponibles fins al dia simulat.
  // Només recalculem si realment estem simulant un passat on falten compres (per sota del total de l'historial)
  // per evitar el "salt" inicial entre el cicle que ve del backend i el càlcul local.
  let simCicle = cicle
  let simCicleStd = cicleStd
  if (simDay !== null && visiblePurchases.length < purchases.length && visiblePurchases.length >= 2) {
    const gaps: number[] = []
    for (let i = 1; i < visiblePurchases.length; i++) {
      gaps.push(visiblePurchases[i].day - visiblePurchases[i - 1].day)
    }
    if (gaps.length > 0) {
      const stats = ewmStats(gaps)
      simCicle = Math.max(stats.mean, 1)
      simCicleStd = Math.max(stats.std, simCicle * 0.05)
    }
  }

  const diesSenseSimulats = hojeDay - lastPurchaseDay

  const properDay = lastPurchaseDay + simCicle
  const low = properDay - 0.5 * simCicleStd
  const high = properDay + 0.5 * simCicleStd
  const riskHigh = properDay + 1.5 * simCicleStd

  // ── Chart dimensions ───────────────────────────────────
  const W = 800
  const H = 200
  const PAD = { top: 30, bottom: 40, left: 10, right: 60 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom
  
  // Ajustem l'escala de l'eix X perquè no s'allargui a l'infinit.
  // Fem servir un xMax estable basat en la realitat completa (no en la simulació) per evitar que el gràfic "salti".
  const lastPurchaseDayReal = purchases.length > 0 ? purchases[purchases.length - 1].day : actualHojeDay
  const riskHighReal = lastPurchaseDayReal + cicle + 1.5 * cicleStd
  const xMax = Math.max(actualHojeDay, timelineDays, riskHighReal) + Math.max(30, cicle * 0.4)
  
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
            <span style={styles.heroProv}>{locationLabel}</span>
            {alert.share_alerta && (
              <>
                <span style={styles.heroSep}>·</span>
                <span style={{
                  ...styles.shareAlertBadge,
                  background: alert.share_alerta === 'fuga' ? '#FEE2E2' : '#ECFDF5',
                  color: alert.share_alerta === 'fuga' ? '#991B1B' : '#065F46',
                  borderColor: alert.share_alerta === 'fuga' ? '#FECACA' : '#A7F3D0',
                }}>
                  {alert.share_alerta === 'fuga' ? '🔴 FUGA' : '🟢 OPORTUNITAT'}
                </span>
              </>
            )}
          </div>
          <button
            style={{ ...styles.treatBtn, background: alert.tractada ? '#4B5563' : '#111827' }}
            onClick={() => onToggleTreated(alert)}
          >
            {alert.tractada ? '↩' : '✓ Tractar'}
          </button>
        </div>

        {/* ── Chart ──────────────────────────────────── */}
        {alert.tipus_alerta === 'geografica' ? (
          geoLoading ? (
            <p style={{ color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>Carregant mapa geogràfic...</p>
          ) : (
            <GeoAlertMap alert={alert} points={geoContext?.points || []} />
          )
        ) : loading ? (
          <p style={{ color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>Carregant historial...</p>
        ) : purchases.length === 0 ? (
          <p style={{ color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>Sense historial de compres</p>
        ) : (
          <svg width="100%" viewBox={`0 0 ${W} ${H + 50}`} style={styles.chartSvg}>
            {/* Prediction zones */}
            <rect x={xScale(low)} y={PAD.top} width={xScale(high) - xScale(low)} height={chartH}
              fill="rgba(0,184,169,0.10)" rx={0} />
            <rect x={xScale(high)} y={PAD.top} width={xScale(riskHigh) - xScale(high)} height={chartH}
              fill="rgba(231,76,60,0.08)" rx={0} />
            <line x1={xScale(properDay)} y1={PAD.top} x2={xScale(properDay)} y2={PAD.top + chartH}
              stroke="#00B8A9" strokeWidth={1} strokeDasharray="4,3" opacity={0.5} />

            {/* Purchase bars */}
            {(() => {
              // Donem prioritat a mostrar els imports de les compres més recents
              const visibility = new Array(purchases.length).fill(false);
              let lastLabelX = Infinity;
              for (let i = purchases.length - 1; i >= 0; i--) {
                const p = purchases[i];
                if (p.day > hojeDay) continue;
                
                const currentX = xScale(p.day);
                if (lastLabelX - currentX > 26) {
                  visibility[i] = true;
                  lastLabelX = currentX;
                }
              }

              return purchases.map((p, i) => {
                const currentX = xScale(p.day);
                const isFuture = p.day > hojeDay;
                const barW = Math.max(3, (chartW / xMax) * 4);
                const barH = chartH - yScale(p.valor) + PAD.top;
                const showLabel = visibility[i];

                // Si és una compra futura (en mode simulació), marcar si encerta la predicció
                let barColor: string, barOpacity: number;
                if (isFuture) {
                  const dinsFinestra = p.day >= low && p.day <= high;
                  barColor = dinsFinestra ? '#059669' : '#DC2626';
                  barOpacity = dinsFinestra ? 0.7 : 0.5;
                } else {
                  barColor = '#1565C0';
                  barOpacity = 0.8;
                }

                return (
                  <g key={i}>
                    <title>{p.valor.toFixed(0)}€ - dia {p.day}</title>
                    <rect x={currentX - barW / 2} y={yScale(p.valor)} width={barW} height={barH}
                      fill={barColor} rx={0} opacity={barOpacity} />
                    {showLabel && (
                      <text x={currentX} y={yScale(p.valor) - 6} textAnchor="middle"
                        fontSize={9} fill="#4B5563" fontWeight={600}>
                        {p.valor.toFixed(0)}€
                      </text>
                    )}
                  </g>
                )
              });
            })()}

            {/* Today line — color segons on cau respecte a la predicció */}
            {(() => {
              const hojeDinsVerd = hojeDay >= low && hojeDay <= high
              const hojeDinsVermell = hojeDay > high && hojeDay <= riskHigh
              const hojePassat = hojeDay > riskHigh
              const hojeColor = hojePassat ? '#DC2626' : hojeDinsVermell ? '#F59E0B' : hojeDinsVerd ? '#059669' : '#111827'
              const hojeLabel = hojePassat ? 'RETARD' : hojeDinsVermell ? 'ALERTA' : hojeDinsVerd ? 'FINESTRA' : 'AVUI'
              return <>
                <line x1={xScale(hojeDay)} y1={PAD.top} x2={xScale(hojeDay)} y2={PAD.top + chartH}
                  stroke={hojeColor} strokeWidth={2.5} />
                <text x={xScale(hojeDay)} y={PAD.top - 10} textAnchor="middle"
                  fontSize={10} fontWeight={700} fill={hojeColor}>
                  {simDay !== null ? hojeLabel.replace('AVUI', 'SIM') : hojeLabel}
                </text>
              </>
            })()}

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

        {/* ── Motiu i Slider ──────────────────────────────── */}
        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <p style={styles.motiu}>{alert.motiu}</p>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, background: '#F9FAFB', padding: '12px 16px', borderRadius: 0, border: '1px solid #E5E7EB' }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>Simular Dia Avui:</label>
            <input 
              type="range" 
              min={0} 
              max={actualHojeDay} 
              value={hojeDay} 
              onChange={(e) => {
                const v = Number(e.target.value)
                setSimDay(v >= actualHojeDay ? null : v)
              }} 
              style={{ flex: 1 }}
            />
            <span style={{ fontSize: 13, color: '#6B7280', minWidth: 50, textAlign: 'right' }}>
              Dia {hojeDay}
            </span>
          </div>
        </div>
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
          {diesSenseSimulats}d <span style={styles.mLabel}>sense compra</span>
        </span>
        <span style={styles.mDiv}>|</span>
        <span style={styles.metric}>
          {simCicle > 0 ? `${simCicle.toFixed(0)}d` : '-'} <span style={styles.mLabel}>cicle{simCicleStd > 0 ? ` ±${simCicleStd.toFixed(0)}` : ''}</span>
        </span>
        {alert.share_velocity !== null && alert.share_velocity !== undefined && (
          <>
            <span style={styles.mDiv}>|</span>
            <span style={{
              ...styles.metric,
              color: alert.share_velocity < -5 ? '#DC2626' : alert.share_velocity > 5 ? '#059669' : '#6B7280',
            }}>
              {alert.share_velocity > 0 ? '+' : ''}{alert.share_velocity.toFixed(1)}pp <span style={styles.mLabel}>share vel.</span>
            </span>
          </>
        )}
        {alert.tipus_alerta === 'geografica' && alert.geo_neighbor_avg_share !== null && alert.geo_neighbor_avg_share !== undefined && (
          <>
            <span style={styles.mDiv}>|</span>
            <span style={{ ...styles.metric, color: '#2563EB' }}>
              {(alert.geo_neighbor_avg_share * 100).toFixed(0)}% <span style={styles.mLabel}>mitjana veïns</span>
            </span>
          </>
        )}
        {alert.tipus_alerta === 'geografica' && alert.geo_share_gap !== null && alert.geo_share_gap !== undefined && (
          <>
            <span style={styles.mDiv}>|</span>
            <span style={{ ...styles.metric, color: '#1D4ED8' }}>
              +{(alert.geo_share_gap * 100).toFixed(0)}pp <span style={styles.mLabel}>oportunitat geo</span>
            </span>
          </>
        )}
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
    fontSize: 13,
    fontWeight: 700,
    padding: '6px 16px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
    lineHeight: 1,
  },
  shareAlertBadge: {
    fontSize: 10,
    fontWeight: 700,
    padding: '2px 8px',
    border: '1px solid',
    letterSpacing: 0.3,
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

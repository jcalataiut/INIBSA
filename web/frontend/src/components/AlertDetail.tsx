import { useEffect, useState, type CSSProperties } from 'react'
import type { Alerta, ClientDetail } from '../types'
import { getClient, updateFeedback, getMapData, getShareTrend } from '../api/client'
import type { ShareMonth } from '../api/client'
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { MapPoint } from '../types'
import ContactActions from './ContactActions'

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
  const [simDay, setSimDay] = useState<number | null>(null)
  const [mapPoints, setMapPoints] = useState<MapPoint[]>([])
  const [shareTrend, setShareTrend] = useState<ShareMonth[]>([])
  const [sharePotencial, setSharePotencial] = useState(0)

  useEffect(() => {
    setLoading(true)
    getClient(alert.id_cliente).then(d => { setData(d); setLoading(false) }).catch(() => setLoading(false))
    
    if (alert.tipus_alerta === 'geographical_alert') {
      getMapData().then(setMapPoints).catch(console.error)
    }
    if (alert.tipus_alerta === 'anticipacio' || alert.tipus_alerta === 'reactiva') {
      getShareTrend(alert.id_cliente, alert.familia_potencial)
        .then(d => { setShareTrend(d.mesos); setSharePotencial(d.potencial) })
        .catch(console.error)
    }
  }, [alert.id_cliente, alert.tipus_alerta, alert.familia_potencial])

  const borderColor = alert.tipus_alerta === 'anticipacio' ? '#00B8A9'
    : alert.tipus_alerta === 'reactiva' ? '#E74C3C'
    : alert.tipus_alerta === 'fugat' ? '#6B7280'
    : '#E5E7EB'

  const isLeal = alert.segment === 'lleial' || alert.share_12m >= 0.70
  const isFuga = alert.segment === 'fuga' || (alert.share_12m > 0 && alert.share_12m < 0.30)
  const shareLabel = isLeal ? 'lleial' : (isFuga ? 'fuga' : 'promiscu')
  const shareColor = isLeal ? '#00B8A9' : (isFuga ? '#E74C3C' : '#F4A261')

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
  const positiveVisible = visiblePurchases.filter(p => p.valor > 0)
  const lastPurchaseDay = positiveVisible.length > 0 ? positiveVisible[positiveVisible.length - 1].day : hojeDay

  // El cicle és fix — sempre usem els valors del backend
  const simCicle = cicle
  const simCicleStd = cicleStd

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
  
  // Ajustem l'escala de l'eix X perquè no s'allargui a l'infinit (evitem errors previs amb multiplicacions errònies)
  const maxDayInData = Math.max(actualHojeDay, timelineDays, riskHigh)
  const xMax = maxDayInData + Math.max(30, cicle * 0.4)
  
  const xScale = (d: number) => PAD.left + (d / xMax) * chartW
  const yScale = (v: number) => PAD.top + chartH - (v / maxValor) * chartH * 0.85

  return (
    <div>
      <button style={styles.backBtn} onClick={onBack}>← Tornar</button>

      {/* ── Header ──────────────────────────────────── */}
      <div style={{ ...styles.hero, borderLeft: `4px solid ${borderColor}`, padding: '24px 32px', marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={styles.heroId}>#{alert.id_cliente}</span>
            <span style={styles.heroSep}>·</span>
            <span style={styles.heroFam}>{alert.familia_potencial}</span>
            <span style={styles.heroSep}>·</span>
            <span style={styles.heroProv}>{alert.provincia || '?'}</span>
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <ContactActions alert={alert} onToggleTreated={onToggleTreated} variant="large" />
          </div>
        </div>
      </div>

      <div style={{ ...styles.hero, padding: '32px' }}>
        <p style={{ ...styles.motiu, marginBottom: 32, fontSize: 16, fontWeight: 500, color: '#111827' }}>
          {alert.motiu}
        </p>

        {/* ── Chart OR Map ──────────────────────────────────── */}
        {alert.tipus_alerta === 'geographical_alert' ? (
          <div style={{ height: 300, borderRadius: 8, overflow: 'hidden', marginBottom: 16 }}>
            {mapPoints.length > 0 ? (
              (() => {
                const centerPoint = mapPoints.find(p => p.id_cliente === alert.id_cliente)
                const centerLat = centerPoint ? centerPoint.lat : 28.29
                const centerLon = centerPoint ? centerPoint.lon : -16.62
                return (
                  <MapContainer center={[centerLat, centerLon]} zoom={11} style={{ height: '100%', width: '100%' }}>
                    <TileLayer
                      attribution='&copy; OpenStreetMap'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    {mapPoints.filter(p => p.familia === alert.familia_potencial).map((p, idx) => {
                      const isCenter = p.id_cliente === alert.id_cliente
                      return (
                        <CircleMarker
                          key={`${p.id_cliente}-${idx}`}
                          center={[p.lat, p.lon]}
                          radius={isCenter ? 12 : 8}
                          pathOptions={{
                            fillColor: isCenter ? '#111827' : (p.share_12m >= 0.7 ? '#00B8A9' : p.share_12m >= 0.4 ? '#F4A261' : '#E74C3C'),
                            fillOpacity: 0.8,
                            color: isCenter ? '#fff' : '#fff',
                            weight: isCenter ? 3 : 1,
                          }}
                        >
                          <Tooltip>
                            <div>
                              <strong>Client #{p.id_cliente}</strong>
                              <br />
                              Share of Wallet: {(p.share_12m * 100).toFixed(1)}%
                            </div>
                          </Tooltip>
                        </CircleMarker>
                      )
                    })}
                  </MapContainer>
                )
              })()
            ) : (
              <p style={{ color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>Carregant mapa...</p>
            )}
          </div>
        ) : (
          <>
            {loading ? (
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
                    if (p.valor <= 0) return null; // No dibuixem devolucions al plot
                    const currentX = xScale(p.day);
                    const isFuture = p.day > hojeDay;
                    const barW = Math.max(3, (chartW / xMax) * 4);
                    const barH = chartH - yScale(p.valor) + PAD.top;
                    const showLabel = visibility[i];

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

                {/* Today line */}
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
          </>
        )}

        {/* ── Slider ──────────────────────────────── */}
        {alert.tipus_alerta !== 'geographical_alert' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, background: '#F9FAFB', padding: '12px 16px', borderRadius: 8, border: '1px solid #E5E7EB', marginTop: 16 }}>
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
        )}
      {/* ── Share of Wallet Trend (anticipació + reactiva) ── */}
        {(alert.tipus_alerta === 'anticipacio' || alert.tipus_alerta === 'reactiva') && shareTrend.length > 3 && (() => {
          const SW = 800, SH = 250
          const sPAD = { top: 30, right: 30, bottom: 55, left: 50 }
          const sChartW = SW - sPAD.left - sPAD.right
          const sChartH = (SH - sPAD.top - sPAD.bottom) * 0.55
          const velH = (SH - sPAD.top - sPAD.bottom) * 0.35
          const velTop = sPAD.top + sChartH + 12

          const sxScale = (i: number) => sPAD.left + (i / (shareTrend.length - 1)) * sChartW
          const syScale = (v: number) => sPAD.top + sChartH - v * sChartH

          const maxVel = Math.max(...shareTrend.map(m => Math.abs(m.velocity)), 0.05)
          const vyScale = (v: number) => velTop + velH / 2 - (v / maxVel) * (velH / 2)

          const linePath = shareTrend.map((m, i) => 
            `${i === 0 ? 'M' : 'L'}${sxScale(i).toFixed(1)},${syScale(m.share).toFixed(1)}`
          ).join(' ')

          const areaPath = linePath + 
            ` L${sxScale(shareTrend.length - 1).toFixed(1)},${syScale(0).toFixed(1)}` +
            ` L${sxScale(0).toFixed(1)},${syScale(0).toFixed(1)} Z`

          // Show fewer tick labels to avoid clutter
          const tickStep = Math.max(1, Math.floor(shareTrend.length / 6))

          return (
            <div style={{ marginTop: 20, background: '#FFFFFF', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16 }}>
              <h4 style={{ fontSize: 14, fontWeight: 700, color: '#374151', marginBottom: 8 }}>
                Tendència Share of Wallet — Potencial: {sharePotencial.toLocaleString()}€/any
              </h4>
              <svg width="100%" viewBox={`0 0 ${SW} ${SH}`} style={{ display: 'block' }}>
                {/* Share area + line */}
                <path d={areaPath} fill="rgba(21, 101, 192, 0.06)" />
                <path d={linePath} fill="none" stroke="#1565C0" strokeWidth={2} />
                {shareTrend.map((m, i) => (
                  <circle key={i} cx={sxScale(i)} cy={syScale(m.share)} r={2} fill="#1565C0" />
                ))}
                {/* 70% loyalty threshold */}
                <line x1={sPAD.left} y1={syScale(0.7)} x2={sPAD.left + sChartW} y2={syScale(0.7)}
                  stroke="#2E7D32" strokeDasharray="4,3" strokeWidth={1} opacity={0.5} />
                <text x={sPAD.left + sChartW + 4} y={syScale(0.7) + 3} fontSize={8} fill="#2E7D32">70%</text>
                {/* 30% risk threshold */}
                <line x1={sPAD.left} y1={syScale(0.3)} x2={sPAD.left + sChartW} y2={syScale(0.3)}
                  stroke="#C62828" strokeDasharray="4,3" strokeWidth={1} opacity={0.5} />
                <text x={sPAD.left + sChartW + 4} y={syScale(0.3) + 3} fontSize={8} fill="#C62828">30%</text>
                {/* Y-axis labels */}
                {[0, 0.25, 0.5, 0.75, 1].map(v => (
                  <text key={v} x={sPAD.left - 6} y={syScale(v) + 3} fontSize={8} fill="#9CA3AF" textAnchor="end">{(v * 100).toFixed(0)}%</text>
                ))}
                {/* Velocity bars */}
                {shareTrend.map((m, i) => {
                  const barW = Math.max(2, sChartW / shareTrend.length * 0.7)
                  const vPP = m.velocity * 100
                  const bH = Math.abs(vPP / (maxVel * 100)) * (velH / 2)
                  const bY = vPP >= 0 ? vyScale(0) - bH : vyScale(0)
                  return (
                    <rect key={i} x={sxScale(i) - barW / 2} y={bY} width={barW} height={Math.max(bH, 0.5)}
                      fill={vPP >= 0 ? '#2E7D32' : '#C62828'} opacity={0.6} rx={1} />
                  )
                })}
                <line x1={sPAD.left} y1={vyScale(0)} x2={sPAD.left + sChartW} y2={vyScale(0)}
                  stroke="#9CA3AF" strokeWidth={0.5} />
                <text x={sPAD.left - 6} y={vyScale(0) + 3} fontSize={7} fill="#9CA3AF" textAnchor="end">0pp</text>
                {/* X-axis labels */}
                {shareTrend.map((m, i) => {
                  if (i % tickStep !== 0 && i !== shareTrend.length - 1) return null
                  const label = m.mes.substring(0, 7) // YYYY-MM
                  return (
                    <text key={i} x={sxScale(i)} y={SH - 18} fontSize={8} fill="#9CA3AF" textAnchor="end"
                      transform={`rotate(-40, ${sxScale(i)}, ${SH - 18})`}>{label}</text>
                  )
                })}
                {/* Labels */}
                <text x={sPAD.left} y={sPAD.top - 8} fontSize={9} fill="#1565C0" fontWeight={600}>Share of Wallet (rolling 12m)</text>
                <text x={sPAD.left} y={velTop - 4} fontSize={9} fill="#6B7280" fontWeight={600}>Velocitat (pp/mes)</text>
              </svg>
            </div>
          )
        })()}
      </div>

      {/* ── Metrics ──────────────────────────────────── */}
      <div style={styles.metrics}>
        <div style={styles.metric}>
          <span style={{ ...styles.mValue, color: shareColor }}>{(alert.share_12m * 100).toFixed(0)}%</span>
          <span style={styles.mLabel}>{shareLabel}</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.mValue}>{alert.gap_eur.toLocaleString()}€</span>
          <span style={styles.mLabel}>gap</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.mValue}>{diesSenseSimulats}d</span>
          <span style={styles.mLabel}>sense compra</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.mValue}>{simCicle > 0 ? `${simCicle.toFixed(0)}d` : '-'}</span>
          <span style={styles.mLabel}>cicle{simCicleStd > 0 ? ` ±${simCicleStd.toFixed(0)}` : ''}</span>
        </div>
      </div>

      {/* ── Lògica de l'Alerta ────────────────────────── */}
      <div style={styles.logicBox}>
        <h4 style={styles.logicTitle}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6, verticalAlign: 'text-bottom' }}><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
          Com funciona aquesta alerta?
        </h4>
        <p style={styles.logicText}>
          {alert.tipus_alerta === 'anticipacio' && (
            "Aquesta alerta es genera abans de la data prevista de compra per avisar que el client aviat necessitarà reposar material. És una notificació preventiva amb prioritat baixa, ideal per avançar-se a la demanda i evitar que la clínica recorri a la competència."
          )}
          {alert.tipus_alerta === 'reactiva' && (
            "Aquesta alerta s'activa un cop s'ha superat la data prevista de compra (i el seu marge de confiança). Ens indica que el client ja hauria d'haver realitzat una comanda. Com més dies de retard acumuli, més gran és el risc de pèrdua i més urgent és la intervenció."
          )}
          {alert.tipus_alerta === 'geographical_alert' && (
            "Aquesta alerta es genera quan es detecta que un client té una penetració (Share of Wallet) significativament inferior a la mitjana de les clíniques del seu voltant. Això assenyala una clara oportunitat de creixement a la zona, ja que el client probablement està adquirint part del material a través d'altres proveïdors."
          )}
          {alert.tipus_alerta === 'fugat' && (
            "Aquesta alerta classifica al client com a inactiu atès que fa molt temps que no realitza cap comanda. S'ha superat el llindar de retenció i caldria una estratègia específica de recuperació."
          )}
        </p>
      </div>

      {/* ── Feedback ───────────────────────────────────── */}
      {alert.tractada && (
        <FeedbackForm alert={alert} />
      )}
    </div>
  )
}

function FeedbackForm({ alert }: { alert: Alerta }) {
  const [resultado, setResultado] = useState<string | null>(null)
  const [importe, setImporte] = useState('')
  const [saved, setSaved] = useState(false)

  const handleSave = async () => {
    if (!resultado) return
    await updateFeedback(alert.id_cliente, alert.familia_potencial, alert.tipus_alerta, resultado, resultado === 'convertido' ? Number(importe) || 0 : undefined)
    setSaved(true)
  }

  return (
    <div style={feedbackStyles.box}>
      <span style={feedbackStyles.title}>Resultat de la intervenció</span>
      {saved ? (
        <span style={feedbackStyles.saved}>✓ Registrat</span>
      ) : (
        <>
          <div style={feedbackStyles.btns}>
            {(['convertido', 'no_convertido', 'sin_contacto'] as const).map(r => (
              <button
                key={r}
                style={{ ...feedbackStyles.btn, ...(resultado === r ? feedbackStyles.btnActive : {}) }}
                onClick={() => { setResultado(r); setSaved(false) }}
              >
                {r === 'convertido' ? '✓ Venda' : r === 'no_convertido' ? '✕ No venda' : '— Sense contacte'}
              </button>
            ))}
          </div>
          {resultado === 'convertido' && (
            <div style={feedbackStyles.importeRow}>
              <span style={feedbackStyles.importeLbl}>Import:</span>
              <input style={feedbackStyles.importeInput} type="number" value={importe} onChange={e => setImporte(e.target.value)} placeholder="0" />
              <span style={feedbackStyles.importeLbl}>€</span>
            </div>
          )}
          {resultado && (
            <button style={feedbackStyles.saveBtn} onClick={handleSave}>Guardar</button>
          )}
        </>
      )}
    </div>
  )
}

const styles: Record<string, CSSProperties> = {
  backBtn: {
    background: 'none',
    border: 'none',
    color: '#007AFF',
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    padding: '24px 0 16px',
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    transition: 'opacity 0.2s ease',
  },
  hero: {
    background: '#FFFFFF',
    borderRadius: 24,
    padding: '32px',
    marginBottom: 16,
    boxShadow: '0 4px 20px rgba(0,0,0,0.04)',
    border: '1px solid rgba(0,0,0,0.05)',
  },
  heroTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 32,
  },
  heroId: {
    fontSize: 28,
    fontWeight: 800,
    color: '#000000',
    fontVariantNumeric: 'tabular-nums',
    letterSpacing: '-0.02em',
  },
  heroSep: {
    color: '#D1D5DB',
    margin: '0 8px',
    fontSize: 24,
    fontWeight: 300,
  },
  heroFam: {
    fontSize: 22,
    fontWeight: 600,
    color: '#3A3A3C',
    letterSpacing: '-0.01em',
  },
  heroProv: {
    fontSize: 15,
    color: '#8E8E93',
    fontWeight: 500,
  },
  chartSvg: {
    display: 'block',
    marginBottom: 24,
  },
  motiu: {
    fontSize: 14,
    color: '#3A3A3C',
    lineHeight: 1.5,
    margin: 0,
    fontWeight: 400,
  },
  metrics: {
    display: 'flex',
    alignItems: 'center',
    gap: 32,
    background: '#FFFFFF',
    borderRadius: 20,
    padding: '20px 32px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.03)',
    border: '1px solid rgba(0,0,0,0.05)',
    flexWrap: 'wrap' as const,
  },
  metric: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  mValue: {
    fontSize: 20,
    fontWeight: 800,
    color: '#000000',
    fontVariantNumeric: 'tabular-nums',
  },
  mLabel: {
    fontSize: 13,
    fontWeight: 500,
    color: '#8E8E93',
  },
  mDiv: {
    color: '#F2F2F7',
    fontSize: 24,
    fontWeight: 200,
  },
  logicBox: {
    marginTop: 16,
    background: '#F8FAFC',
    borderRadius: 16,
    padding: '20px 24px',
    border: '1px solid #E2E8F0',
  },
  logicTitle: {
    margin: '0 0 8px 0',
    fontSize: 14,
    fontWeight: 700,
    color: '#0F172A',
    display: 'flex',
    alignItems: 'center',
  },
  logicText: {
    margin: 0,
    fontSize: 13,
    lineHeight: 1.6,
    color: '#475569',
  },
}

const feedbackStyles: Record<string, CSSProperties> = {
  box: {
    background: 'rgba(0, 122, 255, 0.03)',
    borderRadius: 20,
    padding: '24px 32px',
    marginTop: 16,
    border: '1px solid rgba(0, 122, 255, 0.08)',
  },
  title: {
    fontSize: 15,
    fontWeight: 700,
    color: '#000000',
    display: 'block',
    marginBottom: 16,
  },
  btns: {
    display: 'flex',
    gap: 10,
  },
  btn: {
    background: '#FFFFFF',
    border: '1px solid rgba(0,0,0,0.08)',
    color: '#3A3A3C',
    fontSize: 14,
    fontWeight: 600,
    padding: '10px 20px',
    cursor: 'pointer',
    borderRadius: 14,
    transition: 'all 0.2s ease',
  },
  btnActive: {
    background: '#000000',
    border: '1px solid #000000',
    color: '#FFFFFF',
  },
  importeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginTop: 16,
  },
  importeLbl: {
    fontSize: 14,
    fontWeight: 500,
    color: '#3A3A3C',
  },
  importeInput: {
    background: '#FFFFFF',
    border: '1px solid rgba(0,0,0,0.1)',
    color: '#000000',
    fontSize: 15,
    fontWeight: 700,
    padding: '10px 16px',
    width: 120,
    borderRadius: 12,
  },
  saveBtn: {
    background: '#007AFF',
    border: 'none',
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: 700,
    padding: '12px 32px',
    cursor: 'pointer',
    borderRadius: 16,
    marginTop: 16,
    transition: 'all 0.2s ease',
  },
  saved: {
    fontSize: 15,
    color: '#34C759',
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
}

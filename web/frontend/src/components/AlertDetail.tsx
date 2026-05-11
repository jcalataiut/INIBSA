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
    if (alert.tipus_alerta === 'anticipacio' || alert.tipus_alerta === 'reactiva' || alert.tipus_alerta.startsWith('sow_')) {
      getShareTrend(alert.id_cliente, alert.familia_potencial)
        .then(d => { setShareTrend(d.mesos); setSharePotencial(d.potencial) })
        .catch(console.error)
    }
  }, [alert.id_cliente, alert.tipus_alerta, alert.familia_potencial])

  const borderColor = alert.tipus_alerta === 'anticipacio' ? '#00B8A9'
    : alert.tipus_alerta === 'reactiva' ? '#E74C3C'
    : alert.tipus_alerta === 'fugat' ? '#6B7280'
    : alert.tipus_alerta.startsWith('sow_') ? '#6366F1'
    : '#E5E7EB'

  const isLeal = alert.segment === 'lleial' || alert.share_12m >= 0.70
  const isFuga = alert.segment === 'fuga' || (alert.share_12m > 0 && alert.share_12m < 0.30)
  const shareLabel = isLeal ? 'lleial' : (isFuga ? 'fuga' : 'promiscu')
  const shareColor = isLeal ? '#00B8A9' : (isFuga ? '#E74C3C' : '#F4A261')

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

  const cicle = alert.cicle_mig_dies || 0
  const cicleStd = alert.cicle_std_dies || (cicle * 0.3)
  const hoje = new Date()
  const actualHojeDay = primerDate ? Math.round((hoje.getTime() - primerDate.getTime()) / 86400000) : 0
  const hojeDay = simDay !== null ? simDay : actualHojeDay

  const visiblePurchases = purchases.filter(p => p.day <= hojeDay)
  const positiveVisible = visiblePurchases.filter(p => p.valor > 0)
  const lastPurchaseDay = positiveVisible.length > 0 ? positiveVisible[positiveVisible.length - 1].day : hojeDay

  const simCicle = cicle
  const simCicleStd = cicleStd
  const diesSenseSimulats = hojeDay - lastPurchaseDay
  const properDay = lastPurchaseDay + simCicle
  const low = properDay - 0.5 * simCicleStd
  const high = properDay + 0.5 * simCicleStd
  const riskHigh = properDay + 1.5 * simCicleStd

  const W = 800
  const H = 200
  const PAD = { top: 30, bottom: 40, left: 10, right: 60 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom
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
            <h2 style={styles.title}>#{alert.id_cliente} · {alert.familia_potencial === 'Biomateriales' ? 'Biomaterials' : alert.familia_potencial}</h2>
            <span style={styles.heroProv}>{alert.provincia && alert.provincia !== '?' ? alert.provincia : ''}</span>
          </div>
          <ContactActions alert={alert} onToggleTreated={onToggleTreated} variant="large" />
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
                    <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                    {mapPoints.filter(p => p.familia === alert.familia_potencial).map((p, idx) => {
                      const isCenter = p.id_cliente === alert.id_cliente
                      return (
                        <CircleMarker
                          key={`${p.id_cliente}-${idx}`}
                          center={[p.lat, p.lon]}
                          radius={isCenter ? 12 : 8}
                          pathOptions={{
                            fillColor: isCenter ? '#111827' : (p.share_12m >= 0.7 ? '#00B8A9' : p.share_12m >= 0.4 ? '#F4A261' : '#E74C3C'),
                            fillOpacity: 0.8, color: '#fff', weight: isCenter ? 3 : 1,
                          }}
                        >
                          <Tooltip>
                            <div><strong>Client #{p.id_cliente}</strong><br />Share of Wallet: {(p.share_12m * 100).toFixed(1)}%</div>
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
        ) : alert.tipus_alerta.startsWith('sow_') ? null : (
          <>
            {loading ? (
              <p style={{ color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>Carregant historial...</p>
            ) : purchases.length === 0 ? (
              <p style={{ color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>Sense historial de compres</p>
            ) : (
              <svg width="100%" viewBox={`0 0 ${W} ${H + 50}`} style={styles.chartSvg}>
                <rect x={xScale(low)} y={PAD.top} width={xScale(high) - xScale(low)} height={chartH} fill="rgba(0,184,169,0.10)" />
                <rect x={xScale(high)} y={PAD.top} width={xScale(riskHigh) - xScale(high)} height={chartH} fill="rgba(231,76,60,0.08)" />
                <line x1={xScale(properDay)} y1={PAD.top} x2={xScale(properDay)} y2={PAD.top + chartH} stroke="#00B8A9" strokeWidth={1} strokeDasharray="4,3" opacity={0.5} />
                {purchases.map((p, i) => {
                  if (p.valor <= 0) return null
                  const currentX = xScale(p.day)
                  const isFuture = p.day > hojeDay
                  const barW = Math.max(3, (chartW / xMax) * 4)
                  const barH = chartH - yScale(p.valor) + PAD.top
                  const barColor = isFuture ? (p.day >= low && p.day <= high ? '#059669' : '#DC2626') : '#1565C0'
                  return (
                    <g key={i}>
                      <title>{p.valor.toFixed(0)}€ - dia {p.day}</title>
                      <rect x={currentX - barW / 2} y={yScale(p.valor)} width={barW} height={barH} fill={barColor} opacity={isFuture ? 0.6 : 0.8} />
                    </g>
                  )
                })}
                <line x1={xScale(hojeDay)} y1={PAD.top} x2={xScale(hojeDay)} y2={PAD.top + chartH} stroke="#111827" strokeWidth={2.5} />
                <text x={xScale(hojeDay)} y={PAD.top - 10} textAnchor="middle" fontSize={10} fontWeight={700} fill="#111827">AVUI</text>
                <line x1={PAD.left} y1={PAD.top + chartH} x2={PAD.left + chartW} y2={PAD.top + chartH} stroke="#E5E7EB" strokeWidth={1} />
                {[0, Math.round(xMax * 0.25), Math.round(xMax * 0.5), Math.round(xMax * 0.75), Math.round(xMax)].map(d => (
                  <text key={d} x={xScale(d)} y={PAD.top + chartH + 30} textAnchor="middle" fontSize={9} fill="#9CA3AF">dia {d}</text>
                ))}
              </svg>
            )}
          </>
        )}

        {/* ── Slider ──────────────────────────────── */}
        {alert.tipus_alerta !== 'geographical_alert' && !alert.tipus_alerta.startsWith('sow_') && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, background: '#F9FAFB', padding: '12px 16px', borderRadius: 8, border: '1px solid #E5E7EB', marginTop: 16 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>Simular Dia Avui:</label>
            <input type="range" min={0} max={actualHojeDay} value={hojeDay} onChange={(e) => setSimDay(Number(e.target.value) >= actualHojeDay ? null : Number(e.target.value))} style={{ flex: 1 }} />
            <span style={{ fontSize: 13, color: '#6B7280', minWidth: 50, textAlign: 'right' }}>Dia {hojeDay}</span>
          </div>
        )}

        {/* ── Share of Wallet Trend (Només per a SOW) ── */}
        {alert.tipus_alerta.startsWith('sow_') && shareTrend.length > 3 && (() => {
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
          const linePath = shareTrend.map((m, i) => `${i === 0 ? 'M' : 'L'}${sxScale(i).toFixed(1)},${syScale(m.share).toFixed(1)}`).join(' ')
          const areaPath = linePath + ` L${sxScale(shareTrend.length - 1).toFixed(1)},${syScale(0).toFixed(1)} L${sxScale(0).toFixed(1)},${syScale(0).toFixed(1)} Z`
          const tickStep = Math.max(1, Math.floor(shareTrend.length / 6))
          return (
            <div style={{ marginTop: 20, background: '#FFFFFF', borderRadius: 12, border: '1px solid #E5E7EB', padding: 16 }}>
              <h4 style={{ fontSize: 14, fontWeight: 700, color: '#374151', marginBottom: 8 }}>Tendència Share of Wallet — Potencial: {sharePotencial.toLocaleString()}€/any</h4>
              <svg width="100%" viewBox={`0 0 ${SW} ${SH}`} style={{ display: 'block' }}>
                <path d={areaPath} fill="rgba(21, 101, 192, 0.06)" /><path d={linePath} fill="none" stroke="#1565C0" strokeWidth={2} />
                {shareTrend.map((m, i) => <circle key={i} cx={sxScale(i)} cy={syScale(m.share)} r={2} fill="#1565C0" />)}
                <line x1={sPAD.left} y1={syScale(0.7)} x2={sPAD.left + sChartW} y2={syScale(0.7)} stroke="#2E7D32" strokeDasharray="4,3" strokeWidth={1} opacity={0.5} />
                <line x1={sPAD.left} y1={syScale(0.3)} x2={sPAD.left + sChartW} y2={syScale(0.3)} stroke="#C62828" strokeDasharray="4,3" strokeWidth={1} opacity={0.5} />
                {shareTrend.map((m, i) => {
                  const barW = Math.max(2, sChartW / shareTrend.length * 0.7)
                  const vPP = m.velocity * 100
                  const bH = Math.abs(vPP / (maxVel * 100)) * (velH / 2)
                  const bY = vPP >= 0 ? vyScale(0) - bH : vyScale(0)
                  return <rect key={i} x={sxScale(i) - barW / 2} y={bY} width={barW} height={Math.max(bH, 0.5)} fill={vPP >= 0 ? '#2E7D32' : '#C62828'} opacity={0.6} rx={1} />
                })}
                <line x1={sPAD.left} y1={vyScale(0)} x2={sPAD.left + sChartW} y2={vyScale(0)} stroke="#9CA3AF" strokeWidth={0.5} />
                {shareTrend.map((m, i) => (i % tickStep === 0 || i === shareTrend.length - 1) && (
                  <text key={i} x={sxScale(i)} y={SH - 18} fontSize={8} fill="#9CA3AF" textAnchor="end" transform={`rotate(-40, ${sxScale(i)}, ${SH - 18})`}>{m.mes.substring(0, 7)}</text>
                ))}
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
          <span style={styles.mLabel}>cicle</span>
        </div>
      </div>

      {/* ── Lògica de l'Alerta ────────────────────────── */}
      <div style={styles.logicBox}>
        <h4 style={styles.logicTitle}>Com funciona aquesta alerta?</h4>
        <p style={styles.logicText}>
          {alert.tipus_alerta === 'anticipacio' && "Aquesta alerta preveu que aviat caldrà reposar material."}
          {alert.tipus_alerta === 'reactiva' && "Aquesta alerta s'activa quan s'ha superat la data prevista de compra."}
          {alert.tipus_alerta === 'sow_lleial_promiscu' && "El client ha reduït la seva dependència d'Inibsa."}
          {alert.tipus_alerta === 'sow_promiscu_fuga' && "ALERTA CRÍTICA: Risc imminent de pèrdua total (Fuga)."}
          {alert.tipus_alerta === 'sow_fuga_promiscu' && "BONA NOTÍCIA: Hem recuperat part del volum del client."}
          {alert.tipus_alerta === 'sow_promiscu_lleial' && "OBJECTIU ASSOLIT: El client s'ha consolidat com a Lleial."}
        </p>
      </div>

      {alert.tractada && <FeedbackForm alert={alert} />}
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
      <h4 style={feedbackStyles.title}>Registrar Resultat</h4>
      {saved ? <p style={{ color: '#059669', fontWeight: 600 }}>Registrat correctament!</p> : (
        <>
          <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
            <button onClick={() => setResultado('convertido')} style={{ ...feedbackStyles.btn, background: resultado === 'convertido' ? '#059669' : '#F3F4F6', color: resultado === 'convertido' ? '#fff' : '#000' }}>Venda</button>
            <button onClick={() => setResultado('no_convertido')} style={{ ...feedbackStyles.btn, background: resultado === 'no_convertido' ? '#DC2626' : '#F3F4F6', color: resultado === 'no_convertido' ? '#fff' : '#000' }}>No Venda</button>
          </div>
          {resultado === 'convertido' && <input type="number" placeholder="Import (€)" value={importe} onChange={e => setImporte(e.target.value)} style={feedbackStyles.input} />}
          <button onClick={handleSave} style={feedbackStyles.saveBtn}>Guardar</button>
        </>
      )}
    </div>
  )
}

const styles: Record<string, CSSProperties> = {
  backBtn: { background: 'none', border: 'none', color: '#1565C0', cursor: 'pointer', marginBottom: 16, fontSize: 14, fontWeight: 600 },
  hero: { background: '#FFF', borderRadius: 16, border: '1px solid #E5E7EB', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' },
  title: { margin: 0, fontSize: 24, fontWeight: 800, color: '#111827' },
  heroProv: { fontSize: 14, color: '#6B7280', fontWeight: 500 },
  motiu: { margin: 0, lineHeight: 1.5 },
  chartSvg: { background: '#FFF', padding: '10px 0' },
  metrics: { display: 'flex', gap: 24, marginTop: 16 },
  metric: { display: 'flex', flexDirection: 'column' },
  mValue: { fontSize: 18, fontWeight: 700 },
  mLabel: { fontSize: 12, color: '#6B7280', textTransform: 'uppercase' },
  logicBox: { marginTop: 24, padding: 20, background: '#F9FAFB', borderRadius: 12, border: '1px solid #E5E7EB' },
  logicTitle: { margin: '0 0 8px 0', fontSize: 15, fontWeight: 700 },
  logicText: { margin: 0, fontSize: 14, color: '#4B5563', lineHeight: 1.6 }
}

const feedbackStyles: Record<string, CSSProperties> = {
  box: { marginTop: 24, padding: 20, border: '2px solid #E5E7EB', borderRadius: 12 },
  title: { margin: '0 0 16px 0', fontSize: 16, fontWeight: 700 },
  btn: { padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600 },
  input: { padding: '8px', borderRadius: 8, border: '1px solid #E5E7EB', marginBottom: 16, width: '100%' },
  saveBtn: { background: '#000', color: '#fff', padding: '10px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600 }
}

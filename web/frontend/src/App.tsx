import { useState, useEffect, useCallback } from 'react'
import type { Alerta } from './types'
import { getAlerts, markTreated, unmarkTreated, getTreated, refreshCache } from './api/client'
import Header from './components/Header'
import AlertList from './components/AlertList'
import AlertDetail from './components/AlertDetail'
import FugatsTab from './components/FugatsTab'
import Filters from './components/Filters'
import MapView from './components/MapView'

const DIES = ['diumenge', 'dilluns', 'dimarts', 'dimecres', 'dijous', 'divendres', 'dissabte']
const MESOS = ['gener', 'febrer', 'març', 'abril', 'maig', 'juny', 'juliol', 'agost', 'setembre', 'octubre', 'novembre', 'desembre']

function formatDate(d: Date): string {
  return `${DIES[d.getDay()]}, ${d.getDate()} de ${MESOS[d.getMonth()]} de ${d.getFullYear()}`
}

const globalStyles = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #F3F4F6; color: #111827; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; -webkit-font-smoothing: antialiased; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #F3F4F6; }
  ::-webkit-scrollbar-thumb { background: #D1D5DB; }
  ::-webkit-scrollbar-thumb:hover { background: #9CA3AF; }
  @keyframes spin { to { transform: rotate(360deg); } }
`

const TITLE: Record<string, string> = {
  briefing: 'Briefing Diari',
  tractades: 'Tractades',
  fugats: 'Fugats',
  mapa: 'Mapa Geogràfic',
}

export default function App() {
  useEffect(() => {
    const style = document.createElement('style')
    style.textContent = globalStyles
    document.head.appendChild(style)
  }, [])

  const [alerts, setAlerts] = useState<Alerta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'briefing' | 'fugats' | 'tractades' | 'mapa'>('briefing')
  const [selectedAlert, setSelectedAlert] = useState<Alerta | null>(null)
  const [familiaFilter, setFamiliaFilter] = useState<'commodities' | 'technicals'>('commodities')

  // ── Filter state ────────────────────────────────────────
  const [filterSegment, setFilterSegment] = useState<string[]>([])
  const [filterTipus, setFilterTipus] = useState<string[]>([])
  const [filterUrgencia, setFilterUrgencia] = useState<string[]>([])
  const [showTreated, setShowTreated] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const a = await getAlerts()
      setAlerts(a)
    } catch (e) {
      setError('Error en carregar alertes')
      console.error('Error fetching data', e)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleRefresh = useCallback(async () => {
    setLoading(true)
    try {
      await refreshCache()
      await fetchData()
    } catch (e) {
      console.error('Error refreshing cache', e)
      setError('Error en refrescar cache')
    } finally {
      setLoading(false)
    }
  }, [fetchData])

  useEffect(() => { fetchData() }, [fetchData])

  const handleToggleTreated = async (alert: Alerta) => {
    if (alert.tractada) {
      const treated = await getTreated()
      const found = treated.find(
        t => t.id_cliente === alert.id_cliente
          && t.familia_potencial === alert.familia_potencial
          && t.tipus_alerta === alert.tipus_alerta
      )
      if (found) await unmarkTreated(found.id)
    } else {
      await markTreated(alert.id_cliente, alert.familia_potencial, alert.tipus_alerta)
    }
    fetchData()
  }

  if (selectedAlert) {
    return (
      <div style={styles.container}>
        <Header activeTab={activeTab} onTabChange={(t) => { setActiveTab(t); setSelectedAlert(null) }} />
        <div style={styles.content}>
          <AlertDetail
            alert={selectedAlert}
            onBack={() => setSelectedAlert(null)}
            onToggleTreated={async (a) => {
              await handleToggleTreated(a)
              setSelectedAlert(null)
            }}
          />
        </div>
      </div>
    )
  }

  // ── Client-side filtering ──────────────────────────────
  const filteredAlerts = alerts.filter(a => {
    if (filterSegment.length > 0 && !filterSegment.includes(a.segment)) return false
    if (filterTipus.length > 0 && !filterTipus.includes(a.tipus_alerta)) return false
    if (filterUrgencia.length > 0 && !filterUrgencia.includes(a.urgencia)) return false
    return familiaFilter === 'commodities'
      ? a.familia_potencial !== 'Biomateriales'
      : a.familia_potencial === 'Biomateriales'
  })
  const fugats = filteredAlerts.filter(a => a.tipus_alerta === 'fugat')
  const actives = filteredAlerts.filter(a => a.tipus_alerta !== 'fugat')
  const tractades = actives.filter(a => a.tractada)
  const pendents = showTreated ? actives : actives.filter(a => !a.tractada)

  const today = new Date()

  return (
    <div style={styles.container}>
      <Header activeTab={activeTab} onTabChange={setActiveTab} />
      <div style={styles.content}>
        <div style={styles.headerSection}>
          <h1 style={styles.title}>{TITLE[activeTab]}</h1>
          {activeTab === 'briefing' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Filters
                activeFamilia={familiaFilter}
                filterSegment={filterSegment}
                filterTipus={filterTipus}
                filterUrgencia={filterUrgencia}
                showTreated={showTreated}
                onSegmentChange={setFilterSegment}
                onTipusChange={setFilterTipus}
                onUrgenciaChange={setFilterUrgencia}
                onShowTreatedChange={setShowTreated}
              />
              <div style={styles.toggle}>
                <button
                  style={{ ...styles.toggleBtn, ...(familiaFilter === 'commodities' ? styles.toggleActive : {}) }}
                  onClick={() => {
                    setFamiliaFilter('commodities')
                    setFilterSegment([])
                    setFilterTipus([])
                  }}
                >Commodities</button>
                <button
                  style={{ ...styles.toggleBtn, ...(familiaFilter === 'technicals' ? styles.toggleActive : {}) }}
                  onClick={() => {
                    setFamiliaFilter('technicals')
                    setFilterSegment([])
                    setFilterTipus([])
                  }}
                >Tècnics</button>
              </div>
            </div>
          )}
        </div>
        <p style={styles.dateSub}>{formatDate(today)}</p>

        {/* ── Refresh button ────────────────────────────── */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
          <button onClick={handleRefresh} style={styles.refreshBtn} title="Recalcular alertes">
            ⟳ Recalcular
          </button>
        </div>

        {error ? (
          <div style={styles.loading}>
            <span style={{ ...styles.loadingText, color: '#E74C3C' }}>{error}</span>
          </div>
        ) : loading ? (
          <div style={styles.loading}>
            <div style={styles.spinner} />
            <span style={styles.loadingText}>Calculant alertes...</span>
          </div>
        ) : (
          <>
            {activeTab === 'briefing' && (
              <AlertList alerts={pendents} loading={false} onToggleTreated={handleToggleTreated} onClickAlert={setSelectedAlert} />
            )}
            {activeTab === 'tractades' && (
              <AlertList alerts={tractades} loading={false} onToggleTreated={handleToggleTreated} onClickAlert={setSelectedAlert} listLabel="tractades" />
            )}
            {activeTab === 'fugats' && (
              <FugatsTab alerts={fugats} loading={false} onToggleTreated={handleToggleTreated} onClickAlert={setSelectedAlert} />
            )}
            {activeTab === 'mapa' && (
              <MapView familiaFilter={familiaFilter} />
            )}
          </>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#F3F4F6',
    color: '#111827',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    display: 'flex',
    flexDirection: 'column',
  },
  content: {
    maxWidth: 1200,
    width: '100%',
    margin: '0 auto',
    padding: '0 48px 64px',
    flex: 1,
  },
  headerSection: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    paddingTop: 32,
  },
  title: {
    fontSize: 26,
    fontWeight: 700,
    color: '#111827',
    margin: 0,
    letterSpacing: -0.5,
  },
  dateSub: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 4,
    marginBottom: 24,
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '120px 0',
    gap: 20,
  },
  spinner: {
    width: 32,
    height: 32,
    border: '3px solid #E5E7EB',
    borderTop: '3px solid #00B8A9',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    fontSize: 15,
    color: '#6B7280',
    fontWeight: 500,
  },
  toggle: {
    display: 'flex',
    gap: 0,
  },
  toggleBtn: {
    background: '#FFFFFF',
    border: '1px solid #D1D5DB',
    color: '#6B7280',
    fontSize: 12,
    fontWeight: 600,
    padding: '6px 14px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
  },
  toggleActive: {
    background: '#111827',
    border: '1px solid #111827',
    color: '#FFFFFF',
  },

  refreshBtn: {
    background: '#FFFFFF',
    border: '1px solid #D1D5DB',
    color: '#6B7280',
    fontSize: 16,
    fontWeight: 600,
    padding: '4px 10px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
    lineHeight: 1,
  },
}

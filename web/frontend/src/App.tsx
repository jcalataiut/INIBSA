import { useState, useEffect, useCallback, type CSSProperties } from 'react'
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
  body { 
    background: #FFFFFF; 
    color: #1C1C1E; 
    font-family: -apple-system, BlinkMacSystemFont, "Inter", sans-serif; 
    -webkit-font-smoothing: antialiased;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes spin { to { transform: rotate(360deg); } }
`

const TITLE: Record<string, string> = {
  briefing: 'Alertes del Dia',
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
      <main style={styles.main}>
        <div style={styles.content}>
          <div style={styles.topHeader}>
            <div>
              <h1 style={styles.title}>{TITLE[activeTab]}</h1>
              <p style={styles.dateSub}>{formatDate(today)}</p>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {activeTab === 'briefing' && (
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
              )}
              <button style={styles.refreshBtn} onClick={handleRefresh}>
                Recalcular dades
              </button>
            </div>
          </div>

          {activeTab === 'briefing' && (
            <div style={styles.controlsRow}>
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

          <div style={styles.listContainer}>
            {error ? (
              <div style={styles.loading}>
                <span style={{ ...styles.loadingText, color: '#E74C3C' }}>{error}</span>
              </div>
            ) : loading ? (
              <div style={styles.loading}>
                <div style={styles.spinner} />
                <span style={styles.loadingText}>Carregant Dashboard...</span>
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
      </main>
    </div>
  )
}

const styles: Record<string, CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#F4F7F9',
    display: 'flex',
  },
  main: {
    flex: 1,
    padding: '0',
  },
  content: {
    padding: '40px 48px',
    maxWidth: 1200,
    margin: '0 auto',
    width: '100%',
  },
  topHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 800,
    color: '#1A202C',
    margin: 0,
    letterSpacing: '-0.02em',
  },
  dateSub: {
    fontSize: 14,
    fontWeight: 500,
    color: '#718096',
    marginTop: 4,
  },
  controlsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    marginBottom: 24,
  },
  listContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
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
    border: '3px solid #E2E8F0',
    borderTop: '3px solid #00B8A9',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    fontSize: 15,
    color: '#718096',
    fontWeight: 500,
  },
  toggle: {
    display: 'flex',
    background: '#E2E8F0',
    padding: 3,
    borderRadius: 8,
    gap: 2,
  },
  toggleBtn: {
    background: 'transparent',
    border: 'none',
    color: '#4A5568',
    fontSize: 13,
    fontWeight: 700,
    padding: '6px 16px',
    cursor: 'pointer',
    borderRadius: 6,
    transition: 'all 0.2s ease',
  },
  toggleActive: {
    background: '#FFFFFF',
    color: '#1A202C',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
  },
  refreshBtn: {
    background: '#FFFFFF',
    border: '1px solid #E2E8F0',
    color: '#4A5568',
    fontSize: 13,
    fontWeight: 700,
    padding: '10px 20px',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
}

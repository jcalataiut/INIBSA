import { useState, useEffect, useCallback } from 'react'
import type { Alerta, Stats } from './types'
import { getAlerts, getStats, markTreated, unmarkTreated, getTreated } from './api/client'
import Header from './components/Header'
import MetricsBar from './components/MetricsBar'
import Filters from './components/Filters'
import AlertList from './components/AlertList'
import FugatsTab from './components/FugatsTab'

const globalStyles = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0A0A0A; color: #E5E7EB; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; -webkit-font-smoothing: antialiased; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #0F0F0F; }
  ::-webkit-scrollbar-thumb { background: #2A2A2A; }
  ::-webkit-scrollbar-thumb:hover { background: #3A3A3A; }
  input[type="date"]::-webkit-calendar-picker-indicator { filter: invert(0.6); cursor: pointer; }
  @keyframes spin { to { transform: rotate(360deg); } }
`

export default function App() {
  useEffect(() => {
    const style = document.createElement('style')
    style.textContent = globalStyles
    document.head.appendChild(style)
  }, [])

  const [today, setToday] = useState(() => {
    const d = new Date()
    return d.toISOString().split('T')[0]
  })
  const [alerts, setAlerts] = useState<Alerta[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'briefing' | 'fugats'>('briefing')

  const [filterSegment, setFilterSegment] = useState<string[]>([])
  const [filterTipus, setFilterTipus] = useState<string[]>([])
  const [filterUrgencia, setFilterUrgencia] = useState<string[]>([])
  const [showTreated, setShowTreated] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [a, s] = await Promise.all([
        getAlerts({ today, pendents: !showTreated }),
        getStats(today),
      ])
      setAlerts(a)
      setStats(s)
    } catch (e) {
      console.error('Error fetching data', e)
    } finally {
      setLoading(false)
    }
  }, [today, showTreated])

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

  const fugats = alerts.filter(a => a.segment === 'fugat')
  const noFugats = alerts.filter(a => a.segment !== 'fugat')

  const filtered = noFugats.filter(a => {
    if (filterSegment.length && !filterSegment.includes(a.segment)) return false
    if (filterTipus.length && !filterTipus.includes(a.tipus_alerta)) return false
    if (filterUrgencia.length && !filterUrgencia.includes(a.urgencia)) return false
    return true
  })

  return (
    <div style={styles.container}>
      <Header today={today} onTodayChange={setToday} activeTab={activeTab} onTabChange={setActiveTab} />
      <div style={styles.content}>
        {stats && <MetricsBar stats={stats} />}
        {activeTab === 'briefing' && (
          <>
            <Filters
              filterSegment={filterSegment}
              filterTipus={filterTipus}
              filterUrgencia={filterUrgencia}
              showTreated={showTreated}
              onSegmentChange={setFilterSegment}
              onTipusChange={setFilterTipus}
              onUrgenciaChange={setFilterUrgencia}
              onShowTreatedChange={setShowTreated}
            />
            <AlertList alerts={filtered} loading={loading} onToggleTreated={handleToggleTreated} />
          </>
        )}
        {activeTab === 'fugats' && (
          <FugatsTab alerts={fugats} loading={loading} onToggleTreated={handleToggleTreated} />
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#0A0A0A',
    color: '#E5E7EB',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    display: 'flex',
    flexDirection: 'column',
  },
  content: {
    maxWidth: 1400,
    width: '100%',
    margin: '0 auto',
    padding: '0 32px 48px',
    flex: 1,
  },
}

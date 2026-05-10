import type { CSSProperties } from 'react'

interface HeaderProps {
  activeTab: 'briefing' | 'fugats' | 'tractades' | 'mapa'
  onTabChange: (t: 'briefing' | 'fugats' | 'tractades' | 'mapa') => void
}

export default function Header({ activeTab, onTabChange }: HeaderProps) {
  return (
    <div style={styles.sidebar}>
      <div style={styles.logoSection} onClick={() => onTabChange('briefing')}>
        <img src="/logo.jpg" alt="Inibsa" style={styles.logoImg} />
      </div>

      <nav style={styles.nav}>
        <button
          style={{ ...styles.navItem, ...(activeTab === 'briefing' ? styles.navItemActive : {}) }}
          onClick={() => onTabChange('briefing')}
        >
          {activeTab === 'briefing' && <div style={styles.activeLine} />}
          Alertes del Dia
        </button>
        <button
          style={{ ...styles.navItem, ...(activeTab === 'tractades' ? styles.navItemActive : {}) }}
          onClick={() => onTabChange('tractades')}
        >
          {activeTab === 'tractades' && <div style={styles.activeLine} />}
          Tractades
        </button>
        <button
          style={{ ...styles.navItem, ...(activeTab === 'fugats' ? styles.navItemActive : {}) }}
          onClick={() => onTabChange('fugats')}
        >
          {activeTab === 'fugats' && <div style={styles.activeLine} />}
          Fugats
        </button>
        <button
          style={{ ...styles.navItem, ...(activeTab === 'mapa' ? styles.navItemActive : {}) }}
          onClick={() => onTabChange('mapa')}
        >
          {activeTab === 'mapa' && <div style={styles.activeLine} />}
          Mapa
        </button>
      </nav>
    </div>
  )
}

const styles: Record<string, CSSProperties> = {
  sidebar: {
    width: 210,
    background: '#FFFFFF',
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    borderRight: '1px solid #E2E8F0',
    zIndex: 100,
    flexShrink: 0,
  },
  logoSection: {
    padding: '40px 20px',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoImg: {
    width: '100%',
    maxWidth: 160,
    height: 'auto',
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    padding: '0 10px',
  },
  navItem: {
    background: 'none',
    border: 'none',
    color: '#718096',
    fontSize: 14,
    fontWeight: 600,
    padding: '12px 16px',
    textAlign: 'left',
    cursor: 'pointer',
    borderRadius: 8,
    position: 'relative',
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
  },
  navItemActive: {
    color: '#00B8A9',
    background: '#F0FFF4',
  },
  activeLine: {
    position: 'absolute',
    left: 0,
    top: '15%',
    bottom: '15%',
    width: 4,
    background: '#00B8A9',
    borderRadius: '0 4px 4px 0',
  },
}

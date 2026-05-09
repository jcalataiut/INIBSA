interface HeaderProps {
  today: string
  onTodayChange: (d: string) => void
  activeTab: 'briefing' | 'fugats'
  onTabChange: (t: 'briefing' | 'fugats') => void
}

export default function Header({ today, onTodayChange, activeTab, onTabChange }: HeaderProps) {
  return (
    <div style={styles.wrapper}>
      <div style={styles.inner}>
        <div style={styles.left}>
          <div style={styles.logo}>
            <span style={styles.logoIcon}>◈</span>
            <span style={styles.logoText}>INIBSA</span>
            <span style={styles.logoDivider}>|</span>
            <span style={styles.logoSub}>Smart Demand Signals</span>
          </div>
        </div>
        <div style={styles.center}>
          <div style={styles.tabs}>
            <button
              style={{ ...styles.tab, ...(activeTab === 'briefing' ? styles.tabActive : {}) }}
              onClick={() => onTabChange('briefing')}
            >
              Daily Briefing
            </button>
            <button
              style={{ ...styles.tab, ...(activeTab === 'fugats' ? styles.tabActive : {}) }}
              onClick={() => onTabChange('fugats')}
            >
              Fugats
            </button>
          </div>
        </div>
        <div style={styles.right}>
          <input
            type="date"
            value={today}
            onChange={e => onTodayChange(e.target.value)}
            style={styles.dateInput}
          />
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    borderBottom: '1px solid #1F1F1F',
    background: '#0F0F0F',
    position: 'sticky',
    top: 0,
    zIndex: 100,
  },
  inner: {
    maxWidth: 1400,
    margin: '0 auto',
    padding: '0 32px',
    height: 64,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  left: {},
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  logoIcon: {
    color: '#00B8A9',
    fontSize: 22,
    fontWeight: 700,
  },
  logoText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: 700,
    letterSpacing: 1,
  },
  logoDivider: {
    color: '#333',
    margin: '0 8px',
  },
  logoSub: {
    color: '#6B7280',
    fontSize: 13,
    fontWeight: 400,
    letterSpacing: 0.3,
  },
  center: {},
  tabs: {
    display: 'flex',
    gap: 0,
  },
  tab: {
    background: 'none',
    border: 'none',
    borderBottom: '2px solid transparent',
    color: '#6B7280',
    fontSize: 13,
    fontWeight: 500,
    padding: '0 20px',
    height: 64,
    cursor: 'pointer',
    letterSpacing: 0.3,
    transition: 'color 0.1s, border-color 0.1s',
  },
  tabActive: {
    color: '#00B8A9',
    borderBottom: '2px solid #00B8A9',
  },
  right: {},
  dateInput: {
    background: '#1A1A1A',
    border: '1px solid #2A2A2A',
    color: '#E5E7EB',
    padding: '8px 12px',
    fontSize: 13,
    fontFamily: "'Inter', sans-serif",
    outline: 'none',
  },
}

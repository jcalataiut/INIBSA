interface HeaderProps {
  activeTab: 'briefing' | 'fugats'
  onTabChange: (t: 'briefing' | 'fugats') => void
}

export default function Header({ activeTab, onTabChange }: HeaderProps) {
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
          <span style={styles.todayBadge}>Avui</span>
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    borderBottom: '1px solid #E5E7EB',
    background: '#FFFFFF',
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
    color: '#111827',
    fontSize: 18,
    fontWeight: 700,
    letterSpacing: 1,
  },
  logoDivider: {
    color: '#D1D5DB',
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
  todayBadge: {
    background: '#00B8A9',
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: 600,
    padding: '4px 14px',
    letterSpacing: 0.5,
  },
}

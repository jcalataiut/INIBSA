interface HeaderProps {
  activeTab: 'briefing' | 'fugats' | 'tractades'
  onTabChange: (t: 'briefing' | 'fugats' | 'tractades') => void
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
            <span style={styles.logoSub}>Senyals de Demanda Intel·ligent</span>
          </div>
        </div>
        <div style={styles.center}>
          <div style={styles.tabs}>
            <button
              style={{ ...styles.tab, ...(activeTab === 'briefing' ? styles.tabActive : {}) }}
              onClick={() => onTabChange('briefing')}
            >
              Briefing Diari
            </button>
            <button
              style={{ ...styles.tab, ...(activeTab === 'tractades' ? styles.tabActive : {}) }}
              onClick={() => onTabChange('tractades')}
            >
              Tractades
            </button>
            <button
              style={{ ...styles.tab, ...(activeTab === 'fugats' ? styles.tabActive : {}) }}
              onClick={() => onTabChange('fugats')}
            >
              Fugats
            </button>
          </div>
        </div>
        <div style={styles.right} />
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
    maxWidth: 1200,
    margin: '0 auto',
    padding: '0 48px',
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
  },
  tabActive: {
    color: '#00B8A9',
    borderBottom: '2px solid #00B8A9',
  },
  right: {},
}

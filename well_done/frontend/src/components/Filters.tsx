interface Props {
  filterSegment: string[]
  filterTipus: string[]
  filterUrgencia: string[]
  showTreated: boolean
  onSegmentChange: (v: string[]) => void
  onTipusChange: (v: string[]) => void
  onUrgenciaChange: (v: string[]) => void
  onShowTreatedChange: (v: boolean) => void
}

const SEGMENTS = ['fidel', 'promiscu', 'marginal', 'en_risc', 'nou', 'perdut']
const TIPUS = ['finestra_captura', 'risc_fuga', 'reposicio_endarrerida', 'reposicio_preventiva', 'reposicio_pendent', 'oportunitat_captura', 'monitoritzar', 'info']
const URGENCIES = ['alta', 'mitjana', 'baixa']

export default function Filters(props: Props) {
  return (
    <div style={styles.bar}>
      <div style={styles.group}>
        <span style={styles.groupLabel}>Segment</span>
        <div style={styles.chips}>
          {SEGMENTS.map(s => (
            <button
              key={s}
              style={{ ...styles.chip, ...(props.filterSegment.includes(s) ? styles.chipActive : {}) }}
              onClick={() => {
                const next = props.filterSegment.includes(s)
                  ? props.filterSegment.filter(x => x !== s)
                  : [...props.filterSegment, s]
                props.onSegmentChange(next)
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
      <div style={styles.group}>
        <span style={styles.groupLabel}>Tipus</span>
        <div style={styles.chips}>
          {TIPUS.map(t => (
            <button
              key={t}
              style={{ ...styles.chip, ...(props.filterTipus.includes(t) ? styles.chipActive : {}) }}
              onClick={() => {
                const next = props.filterTipus.includes(t)
                  ? props.filterTipus.filter(x => x !== t)
                  : [...props.filterTipus, t]
                props.onTipusChange(next)
              }}
            >
              {t.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>
      <div style={styles.group}>
        <span style={styles.groupLabel}>Urgència</span>
        <div style={styles.chips}>
          {URGENCIES.map(u => (
            <button
              key={u}
              style={{ ...styles.chip, ...(props.filterUrgencia.includes(u) ? styles.chipActive : {}) }}
              onClick={() => {
                const next = props.filterUrgencia.includes(u)
                  ? props.filterUrgencia.filter(x => x !== u)
                  : [...props.filterUrgencia, u]
                props.onUrgenciaChange(next)
              }}
            >
              {u}
            </button>
          ))}
        </div>
      </div>
      <div style={styles.toggleGroup}>
        <label style={styles.toggle}>
          <input
            type="checkbox"
            checked={props.showTreated}
            onChange={e => props.onShowTreatedChange(e.target.checked)}
            style={styles.checkbox}
          />
          <span style={styles.toggleLabel}>Mostrar tractades</span>
        </label>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    paddingBottom: 20,
  },
  group: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  groupLabel: {
    fontSize: 10,
    fontWeight: 600,
    color: '#6B7280',
    textTransform: 'uppercase',
    letterSpacing: 1,
    minWidth: 60,
  },
  chips: {
    display: 'flex',
    gap: 6,
    flexWrap: 'wrap' as const,
  },
  chip: {
    background: '#FFFFFF',
    border: '1px solid #D1D5DB',
    color: '#6B7280',
    fontSize: 11,
    fontWeight: 500,
    padding: '4px 12px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
    transition: 'all 0.1s',
  },
  chipActive: {
    background: '#00B8A9',
    border: '1px solid #00B8A9',
    color: '#FFFFFF',
  },
  toggleGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    paddingTop: 4,
  },
  toggle: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    cursor: 'pointer',
  },
  checkbox: {
    accentColor: '#00B8A9',
  },
  toggleLabel: {
    fontSize: 12,
    color: '#374151',
  },
}

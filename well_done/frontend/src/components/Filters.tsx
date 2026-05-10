import { useState } from 'react'

interface Props {
  activeFamilia: 'commodities' | 'technicals'
  filterSegment: string[]
  filterTipus: string[]
  filterUrgencia: string[]
  showTreated: boolean
  onSegmentChange: (v: string[]) => void
  onTipusChange: (v: string[]) => void
  onUrgenciaChange: (v: string[]) => void
  onShowTreatedChange: (v: boolean) => void
}

const COMMODITIES_SEGMENTS = ['leal', 'promiscuo', 'fugat']
const COMMODITIES_TIPUS = ['anticipacio', 'reactiva', 'fugat', 'geographical_alert']

const TECHNICALS_SEGMENTS = ['actiu_regular', 'actiu_esporadic', 'inactiu_recent', 'inactiu_total', 'fugat']
const TECHNICALS_TIPUS = ['anomalia_groga', 'anomalia_vermella', 'monitoritzar', 'caiguda_volum', 'fugat', 'geographical_alert']

const LABEL_SEG: Record<string, string> = {
  leal: 'Leal', promiscuo: 'Promiscuo',
  actiu_regular: 'Actiu Regular', actiu_esporadic: 'Actiu Esporàdic',
  inactiu_recent: 'Inactiu Recent', inactiu_total: 'Inactiu Total',
  fugat: 'Fugat',
}
const URGENCIES = ['critica', 'alta', 'mitjana', 'baixa']

const LABEL_TIPUS: Record<string, string> = {
  anticipacio: 'Anticipació', reactiva: 'Reactiva',
  anomalia_groga: 'Anomalia Groga', anomalia_vermella: 'Anomalia Vermella',
  monitoritzar: 'Monitoritzar',
  caiguda_volum: 'Caiguda Volum',
  fugat: 'Fugat',
  geographical_alert: 'Alerta Geogràfica',
}

export default function Filters(props: Props) {
  const [open, setOpen] = useState(false)

  const activeCount =
    props.filterSegment.length + props.filterTipus.length + props.filterUrgencia.length

  const currentSegments = props.activeFamilia === 'commodities' ? COMMODITIES_SEGMENTS : TECHNICALS_SEGMENTS
  const currentTipus = props.activeFamilia === 'commodities' ? COMMODITIES_TIPUS : TECHNICALS_TIPUS

  return (
    <>
      <button style={styles.filterBtn} onClick={() => setOpen(true)}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"/></svg>
        Filtres
        {activeCount > 0 && <span style={styles.badge}>{activeCount}</span>}
      </button>

      {open && (
        <div style={styles.overlay} onClick={() => setOpen(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <span style={styles.modalTitle}>Filtres</span>
              <button style={styles.closeBtn} onClick={() => setOpen(false)}>✕</button>
            </div>

            <div style={styles.section}>
              <span style={styles.sectionLabel}>Segment</span>
              <div style={styles.chips}>
                {currentSegments.map(s => (
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
                    {LABEL_SEG[s] || s}
                  </button>
                ))}
              </div>
            </div>

            <div style={styles.section}>
              <span style={styles.sectionLabel}>Tipus</span>
              <div style={styles.chips}>
                {currentTipus.map(t => (
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
                    {LABEL_TIPUS[t] || t.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>

            <div style={styles.section}>
              <span style={styles.sectionLabel}>Urgència</span>
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

            <div style={styles.section}>
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

            <button style={styles.applyBtn} onClick={() => setOpen(false)}>
              Aplicar
            </button>
          </div>
        </div>
      )}
    </>
  )
}

const styles: Record<string, React.CSSProperties> = {
  filterBtn: {
    background: '#FFFFFF',
    border: '1px solid #D1D5DB',
    color: '#374151',
    fontSize: 13,
    fontWeight: 500,
    padding: '8px 16px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
  },
  badge: {
    background: '#00B8A9',
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: 700,
    width: 18,
    height: 18,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.4)',
    backdropFilter: 'blur(4px)',
    zIndex: 200,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modal: {
    background: '#FFFFFF',
    width: 440,
    maxWidth: '90vw',
    maxHeight: '80vh',
    overflowY: 'auto' as const,
    padding: 28,
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 700,
    color: '#111827',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: 20,
    color: '#6B7280',
    cursor: 'pointer',
    padding: 4,
    lineHeight: 1,
  },
  section: {
    marginBottom: 20,
  },
  sectionLabel: {
    display: 'block',
    fontSize: 10,
    fontWeight: 600,
    color: '#6B7280',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 8,
  },
  chips: {
    display: 'flex',
    gap: 6,
    flexWrap: 'wrap' as const,
  },
  chip: {
    background: '#F9FAFB',
    border: '1px solid #D1D5DB',
    color: '#6B7280',
    fontSize: 12,
    fontWeight: 500,
    padding: '6px 14px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
  },
  chipActive: {
    background: '#00B8A9',
    border: '1px solid #00B8A9',
    color: '#FFFFFF',
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
    fontSize: 13,
    color: '#374151',
  },
  applyBtn: {
    background: '#00B8A9',
    border: 'none',
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: 600,
    padding: '10px 0',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
    width: '100%',
    marginTop: 8,
  },
}

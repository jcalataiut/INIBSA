import type { CSSProperties } from 'react'
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

const COMMODITIES_SEGMENTS = ['lleial', 'promiscu', 'fuga']
const COMMODITIES_TIPUS = [
  'anticipacio', 'reactiva', 'geographical_alert',
  'sow_lleial_promiscu', 'sow_promiscu_fuga', 'sow_fuga_promiscu', 'sow_promiscu_lleial'
]

const LABEL_SEG: Record<string, string> = {
  lleial: 'Lleial', promiscu: 'Promiscu', fuga: 'Fuga'
}
const URGENCIES = ['critica', 'alta', 'mitjana', 'baixa']

const LABEL_TIPUS: Record<string, string> = {
  anticipacio: 'Anticipació', 
  reactiva: 'Reactiva',
  geographical_alert: 'Geogràfica',
  sow_lleial_promiscu: 'Lleial a Promiscu',
  sow_promiscu_fuga: 'Promiscu a Fuga',
  sow_fuga_promiscu: 'Fuga a Promiscu',
  sow_promiscu_lleial: 'Promiscu a Lleial',
}

export default function Filters(props: Props) {
  const [open, setOpen] = useState(false)

  const activeCount =
    props.filterSegment.length + props.filterTipus.length + props.filterUrgencia.length

  const currentSegments = COMMODITIES_SEGMENTS
  const currentTipus = COMMODITIES_TIPUS

  return (
    <>
      <button style={styles.filterBtn} onClick={() => setOpen(true)}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"/></svg>
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
              <span style={styles.sectionLabel}>Tipus d'Alerta</span>
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
                <span style={styles.toggleLabel}>Mostrar alertes tractades</span>
              </label>
            </div>

            <button style={styles.applyBtn} onClick={() => setOpen(false)}>
              Aplicar Filtres
            </button>
          </div>
        </div>
      )}
    </>
  )
}

const styles: Record<string, CSSProperties> = {
  filterBtn: {
    background: '#FFFFFF',
    border: 'none',
    color: '#007AFF',
    fontSize: 14,
    fontWeight: 600,
    padding: '8px 18px',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    borderRadius: 20,
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
    transition: 'all 0.2s ease',
  },
  badge: {
    background: '#007AFF',
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: 700,
    width: 18,
    height: 18,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.3)',
    backdropFilter: 'blur(8px)',
    WebkitBackdropFilter: 'blur(8px)',
    zIndex: 200,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    animation: 'fadeIn 0.3s ease-out',
  },
  modal: {
    background: '#FFFFFF',
    width: 440,
    maxWidth: '94vw',
    maxHeight: '86vh',
    overflowY: 'auto' as const,
    padding: 32,
    borderRadius: 24,
    boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 28,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: 800,
    color: '#000000',
    letterSpacing: '-0.02em',
  },
  closeBtn: {
    background: '#F2F2F7',
    border: 'none',
    width: 32,
    height: 32,
    borderRadius: '50%',
    fontSize: 14,
    color: '#8E8E93',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  section: {
    marginBottom: 28,
  },
  sectionLabel: {
    display: 'block',
    fontSize: 13,
    fontWeight: 600,
    color: '#8E8E93',
    marginBottom: 12,
  },
  chips: {
    display: 'flex',
    gap: 8,
    flexWrap: 'wrap' as const,
  },
  chip: {
    background: '#F2F2F7',
    border: 'none',
    color: '#3A3A3C',
    fontSize: 13,
    fontWeight: 500,
    padding: '8px 16px',
    cursor: 'pointer',
    borderRadius: 12,
    transition: 'all 0.2s ease',
  },
  chipActive: {
    background: '#007AFF',
    color: '#FFFFFF',
    fontWeight: 600,
  },
  toggle: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    cursor: 'pointer',
  },
  checkbox: {
    width: 18,
    height: 18,
    accentColor: '#007AFF',
  },
  toggleLabel: {
    fontSize: 15,
    fontWeight: 500,
    color: '#1C1C1E',
  },
  applyBtn: {
    background: '#000000',
    border: 'none',
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 600,
    padding: '12px 0',
    cursor: 'pointer',
    width: '100%',
    borderRadius: 14,
    marginTop: 8,
    transition: 'all 0.2s ease',
  },
}

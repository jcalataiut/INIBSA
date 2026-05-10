import type { Alerta } from '../types'

interface Props {
  alert: Alerta
  onToggleTreated: (a: Alerta) => void
  onClick?: (a: Alerta) => void
}

const URG: Record<string, { bg: string; txt: string }> = {
  critica: { bg: '#FEE2E2', txt: '#991B1B' },
  alta:    { bg: '#FEF3C7', txt: '#92400E' },
  mitjana: { bg: '#DBEAFE', txt: '#1E40AF' },
  baixa:   { bg: '#F3F4F6', txt: '#4B5563' },
}

export default function AlertCard({ alert, onToggleTreated, onClick }: Props) {
  const isFugat = alert.segment === 'fugat'
  const isGeo = alert.tipus_alerta === 'geografica'
  const shareLabel = isFugat ? 'fugat' : (alert.share_12m >= 0.70 ? 'leal' : 'promiscuo')
  const shareColor = isFugat ? '#6B7280' : (alert.share_12m >= 0.70 ? '#059669' : '#D97706')

  const tipusLabel = alert.tipus_alerta === 'anticipacio' ? 'ANTICIPAT'
    : alert.tipus_alerta === 'reactiva' ? 'REACTIVA'
    : alert.tipus_alerta === 'geografica' ? 'GEO'
    : 'FUGAT'
  const tipusColor = alert.tipus_alerta === 'anticipacio' ? '#059669'
    : alert.tipus_alerta === 'reactiva' ? '#DC2626'
    : alert.tipus_alerta === 'geografica' ? '#2563EB'
    : '#6B7280'

  const urg = URG[alert.urgencia] || URG.baixa

  return (
    <div
      style={styles.card}
      onClick={() => onClick?.(alert)}
    >
      <div style={styles.top}>
        <div style={styles.left}>
          <span style={styles.id}>#{alert.id_cliente}</span>
          <span style={styles.sep}>·</span>
          <span style={styles.familia}>{alert.familia_potencial}</span>
          {isGeo && alert.city && (
            <>
              <span style={styles.sep}>·</span>
              <span style={styles.location}>{alert.city}{alert.cod_postal ? ` ${alert.cod_postal}` : ''}</span>
            </>
          )}
          {!isFugat && (
            <>
              <span style={styles.sep}>·</span>
              <span style={{ ...styles.shareBadge, color: shareColor, borderColor: shareColor }}>
                {(alert.share_12m * 100).toFixed(0)}% {shareLabel}
              </span>
            </>
          )}
        </div>
        <div style={styles.right}>
          <span style={{ ...styles.tag, background: tipusColor }}>{tipusLabel}</span>
          {!isFugat && (
            <span style={{ ...styles.tagOutline, background: urg.bg, color: urg.txt }}>
              {alert.urgencia.toUpperCase()}
            </span>
          )}
          <button 
            style={styles.btn} 
            onClick={e => { e.stopPropagation(); onToggleTreated(alert) }}
          >
            {alert.tractada ? '↩' : '✓'}
          </button>
        </div>
      </div>

      <div style={styles.bottom}>
        <Metric val={`${alert.gap_eur.toLocaleString(undefined, {maximumFractionDigits: 0})}€`} lbl="gap" />
        <Metric val={`${alert.dies_sense_compra}d`} lbl="sense compra" />
        <Metric val={alert.cicle_mig_dies ? `${alert.cicle_mig_dies.toFixed(0)}d` : '-'} lbl="cicle" />
        {isGeo && alert.geo_neighbor_count !== null && alert.geo_neighbor_count !== undefined && (
          <Metric val={String(alert.geo_neighbor_count)} lbl="veïns forts" />
        )}
        {isGeo && alert.geo_neighbor_avg_share !== null && alert.geo_neighbor_avg_share !== undefined && (
          <Metric val={`${(alert.geo_neighbor_avg_share * 100).toFixed(0)}%`} lbl="share veïns" />
        )}
        {alert.share_velocity !== null && alert.share_velocity !== undefined && (
          <span style={{
            ...styles.velocityBadge,
            color: alert.share_velocity < -5 ? '#DC2626' : alert.share_velocity > 5 ? '#059669' : '#6B7280',
          }}>
            {alert.share_velocity < -5 ? '↓' : alert.share_velocity > 5 ? '↑' : '→'}
            {alert.share_velocity > 0 ? '+' : ''}{alert.share_velocity.toFixed(1)}pp
          </span>
        )}
      </div>
    </div>
  )
}

function Metric({ val, lbl }: { val: string; lbl: string }) {
  return (
    <div style={styles.metric}>
      <span style={styles.mVal}>{val}</span>
      <span style={styles.mLbl}>{lbl}</span>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    padding: '16px 20px',
    marginBottom: 8,
    cursor: 'pointer',
  },
  top: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap' as const,
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    flexShrink: 0,
  },
  id: {
    fontSize: 15,
    fontWeight: 700,
    color: '#111827',
    fontVariantNumeric: 'tabular-nums',
  },
  sep: {
    color: '#D1D5DB',
    fontSize: 15,
  },
  familia: {
    fontSize: 14,
    fontWeight: 500,
    color: '#374151',
  },
  location: {
    fontSize: 12,
    color: '#6B7280',
  },
  shareBadge: {
    fontSize: 11,
    fontWeight: 600,
    padding: '2px 8px',
    border: '1px solid',
    whiteSpace: 'nowrap' as const,
  },
  tag: {
    fontSize: 10,
    fontWeight: 700,
    color: '#FFFFFF',
    padding: '3px 10px',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    whiteSpace: 'nowrap' as const,
  },
  tagOutline: {
    fontSize: 10,
    fontWeight: 700,
    padding: '3px 10px',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    whiteSpace: 'nowrap' as const,
  },
  btn: {
    background: '#111827',
    border: 'none',
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: 700,
    padding: '6px 16px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
    marginLeft: 4,
    lineHeight: 1,
  },
  bottom: {
    display: 'flex',
    gap: 24,
    paddingTop: 10,
    borderTop: '1px solid #F3F4F6',
  },
  metric: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 5,
  },
  mVal: {
    fontSize: 14,
    fontWeight: 600,
    color: '#111827',
    fontVariantNumeric: 'tabular-nums',
  },
  mLbl: {
    fontSize: 12,
    color: '#9CA3AF',
    fontWeight: 500,
  },
  velocityBadge: {
    fontSize: 11,
    fontWeight: 700,
    fontVariantNumeric: 'tabular-nums',
    marginLeft: 'auto' as const,
  },
}

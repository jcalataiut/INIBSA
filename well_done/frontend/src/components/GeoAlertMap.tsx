import { useEffect } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { Alerta, GeoPoint } from '../types'

interface Props {
  alert: Alerta
  points: GeoPoint[]
}

function FitMapToPoints({ points }: { points: GeoPoint[] }) {
  const map = useMap()

  useEffect(() => {
    if (points.length === 0) return
    const bounds = points.map(point => [point.latitude, point.longitude] as [number, number])
    map.fitBounds(bounds, { padding: [32, 32], maxZoom: 11 })
  }, [map, points])

  return null
}

function shareColor(share: number): string {
  if (share >= 0.75) return '#0F766E'
  if (share >= 0.55) return '#22C55E'
  if (share >= 0.35) return '#F59E0B'
  return '#DC2626'
}

export default function GeoAlertMap({ alert, points }: Props) {
  const focusId = alert.id_cliente
  const focusPoint = points.find(point => point.id_cliente === focusId)

  if (!focusPoint) {
    return (
      <div style={styles.empty}>
        No hi ha coordenades disponibles per mostrar aquest client al mapa.
      </div>
    )
  }

  return (
    <div style={styles.wrapper}>
      <div style={styles.summary}>
        <div style={styles.summaryCard}>
          <span style={styles.summaryLabel}>Client</span>
          <strong style={styles.summaryValue}>#{alert.id_cliente}</strong>
          <span style={styles.summaryMeta}>
            {focusPoint.city}{focusPoint.cod_postal ? ` · ${focusPoint.cod_postal}` : ''}
          </span>
        </div>
        <div style={styles.summaryCard}>
          <span style={styles.summaryLabel}>Share actual</span>
          <strong style={styles.summaryValue}>{(alert.share_12m * 100).toFixed(0)}%</strong>
          <span style={styles.summaryMeta}>colorat per quota al mapa</span>
        </div>
        <div style={styles.summaryCard}>
          <span style={styles.summaryLabel}>Veïns destacats</span>
          <strong style={styles.summaryValue}>{alert.geo_neighbor_count ?? 0}</strong>
          <span style={styles.summaryMeta}>
            {(alert.geo_neighbor_avg_share ?? 0) > 0
              ? `mitjana ${(alert.geo_neighbor_avg_share! * 100).toFixed(0)}%`
              : 'sense comparables'}
          </span>
        </div>
      </div>

      <div style={styles.mapFrame}>
        <MapContainer
          center={[focusPoint.latitude, focusPoint.longitude]}
          zoom={8}
          scrollWheelZoom
          style={styles.map}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitMapToPoints points={points} />
          {points.map(point => {
            const isFocus = point.id_cliente === focusId
            return (
              <CircleMarker
                key={`${point.id_cliente}_${point.familia_potencial}`}
                center={[point.latitude, point.longitude]}
                radius={isFocus ? 11 : 8}
                pathOptions={{
                  color: isFocus ? '#111827' : '#FFFFFF',
                  fillColor: shareColor(point.share_12m),
                  fillOpacity: 0.92,
                  weight: isFocus ? 3 : 1.5,
                }}
              >
                <Tooltip direction="top" offset={[0, -8]} opacity={1}>
                  <div style={styles.tooltip}>
                    <strong>#{point.id_cliente}</strong>
                    <span>{point.city}{point.cod_postal ? ` · ${point.cod_postal}` : ''}</span>
                    <span>Share of wallet: {(point.share_12m * 100).toFixed(1)}%</span>
                  </div>
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  summary: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: 12,
  },
  summaryCard: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    padding: '14px 16px',
    border: '1px solid #DBEAFE',
    background: '#F8FBFF',
  },
  summaryLabel: {
    fontSize: 11,
    color: '#6B7280',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.4,
  },
  summaryValue: {
    fontSize: 22,
    color: '#111827',
    lineHeight: 1.1,
  },
  summaryMeta: {
    fontSize: 12,
    color: '#4B5563',
  },
  mapFrame: {
    border: '1px solid #DBEAFE',
    overflow: 'hidden',
  },
  map: {
    height: 420,
    width: '100%',
  },
  tooltip: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    fontSize: 12,
  },
  empty: {
    padding: '24px 20px',
    border: '1px dashed #CBD5E1',
    color: '#64748B',
    background: '#F8FAFC',
  },
}

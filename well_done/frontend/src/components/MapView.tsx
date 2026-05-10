import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { getMapData } from '../api/client'
import type { MapPoint } from '../types'

function getColor(share: number): string {
  if (share >= 0.7) return '#00B8A9' // Green
  if (share >= 0.4) return '#F4A261' // Orange
  return '#E74C3C' // Red
}

interface Props {
  familiaFilter: 'commodities' | 'technicals'
}

export default function MapView({ familiaFilter }: Props) {
  const [points, setPoints] = useState<MapPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMapData()
      .then((data) => {
        setPoints(data)
        setLoading(false)
      })
      .catch((err) => {
        console.error('Error loading map data', err)
        setLoading(false)
      })
  }, [])

  const filteredPoints = points.filter((p) => {
    return familiaFilter === 'commodities'
      ? p.familia !== 'Biomateriales'
      : p.familia === 'Biomateriales'
  })

  // Canary Islands roughly center around [28.29, -16.62] 
  // We can compute average center if we have points, otherwise default.
  const centerLat = filteredPoints.length > 0 ? filteredPoints.reduce((s, p) => s + p.lat, 0) / filteredPoints.length : 28.29
  const centerLon = filteredPoints.length > 0 ? filteredPoints.reduce((s, p) => s + p.lon, 0) / filteredPoints.length : -16.62

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '120px 0', color: '#6B7280' }}>
        Carregant mapa...
      </div>
    )
  }

  return (
    <div style={{ background: '#FFFFFF', borderRadius: 8, padding: 16, border: '1px solid #E5E7EB', marginTop: 16 }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, color: '#111827', marginBottom: 16 }}>
        Mapa de Clients - Share of Wallet
      </h2>
      <div style={{ height: 600, borderRadius: 8, overflow: 'hidden' }}>
        <MapContainer center={[centerLat, centerLon]} zoom={8} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {filteredPoints.map((p, idx) => (
            <CircleMarker
              key={`${p.id_cliente}-${p.familia}-${idx}`}
              center={[p.lat, p.lon]}
              radius={8}
              pathOptions={{
                fillColor: getColor(p.share_12m),
                fillOpacity: 0.8,
                color: '#fff',
                weight: 1,
              }}
            >
              <Tooltip>
                <div>
                  <strong>Client #{p.id_cliente}</strong>
                  <br />
                  Família: {p.familia}
                  <br />
                  CP: {p.cod_postal}
                  <br />
                  Share of Wallet: {(p.share_12m * 100).toFixed(1)}%
                </div>
              </Tooltip>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
      <div style={{ marginTop: 16, display: 'flex', gap: 16, fontSize: 13, color: '#6B7280' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#00B8A9' }} /> ≥ 70%
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#F4A261' }} /> 40% - 69%
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#E74C3C' }} /> &lt; 40%
        </div>
      </div>
    </div>
  )
}

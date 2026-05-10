import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { getMapData } from '../api/client';
function getColor(share) {
    if (share >= 0.7)
        return '#00B8A9'; // Green
    if (share >= 0.4)
        return '#F4A261'; // Orange
    return '#E74C3C'; // Red
}
export default function MapView({ familiaFilter }) {
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        getMapData()
            .then((data) => {
            setPoints(data);
            setLoading(false);
        })
            .catch((err) => {
            console.error('Error loading map data', err);
            setLoading(false);
        });
    }, []);
    const filteredPoints = points.filter((p) => {
        return familiaFilter === 'commodities'
            ? p.familia !== 'Biomateriales'
            : p.familia === 'Biomateriales';
    });
    // Canary Islands roughly center around [28.29, -16.62] 
    // We can compute average center if we have points, otherwise default.
    const centerLat = filteredPoints.length > 0 ? filteredPoints.reduce((s, p) => s + p.lat, 0) / filteredPoints.length : 28.29;
    const centerLon = filteredPoints.length > 0 ? filteredPoints.reduce((s, p) => s + p.lon, 0) / filteredPoints.length : -16.62;
    if (loading) {
        return (_jsx("div", { style: { display: 'flex', justifyContent: 'center', padding: '120px 0', color: '#6B7280' }, children: "Carregant mapa..." }));
    }
    return (_jsxs("div", { style: { background: '#FFFFFF', borderRadius: 8, padding: 16, border: '1px solid #E5E7EB', marginTop: 16 }, children: [_jsx("h2", { style: { fontSize: 18, fontWeight: 600, color: '#111827', marginBottom: 16 }, children: "Mapa de Clients - Share of Wallet" }), _jsx("div", { style: { height: 600, borderRadius: 8, overflow: 'hidden' }, children: _jsxs(MapContainer, { center: [centerLat, centerLon], zoom: 8, style: { height: '100%', width: '100%' }, children: [_jsx(TileLayer, { attribution: '\u00A9 <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" }), filteredPoints.map((p, idx) => (_jsx(CircleMarker, { center: [p.lat, p.lon], radius: 8, pathOptions: {
                                fillColor: getColor(p.share_12m),
                                fillOpacity: 0.8,
                                color: '#fff',
                                weight: 1,
                            }, children: _jsx(Tooltip, { children: _jsxs("div", { children: [_jsxs("strong", { children: ["Client #", p.id_cliente] }), _jsx("br", {}), "Fam\u00EDlia: ", p.familia, _jsx("br", {}), "CP: ", p.cod_postal, _jsx("br", {}), "Share of Wallet: ", (p.share_12m * 100).toFixed(1), "%"] }) }) }, `${p.id_cliente}-${p.familia}-${idx}`)))] }) }), _jsxs("div", { style: { marginTop: 16, display: 'flex', gap: 16, fontSize: 13, color: '#6B7280' }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 6 }, children: [_jsx("div", { style: { width: 12, height: 12, borderRadius: '50%', background: '#00B8A9' } }), " \u2265 70%"] }), _jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 6 }, children: [_jsx("div", { style: { width: 12, height: 12, borderRadius: '50%', background: '#F4A261' } }), " 40% - 69%"] }), _jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 6 }, children: [_jsx("div", { style: { width: 12, height: 12, borderRadius: '50%', background: '#E74C3C' } }), " < 40%"] })] })] }));
}

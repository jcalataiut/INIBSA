import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { getClient, updateFeedback, getMapData } from '../api/client';
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import ContactActions from './ContactActions';
export default function AlertDetail({ alert, onBack, onToggleTreated }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [simDay, setSimDay] = useState(null);
    const [mapPoints, setMapPoints] = useState([]);
    useEffect(() => {
        setLoading(true);
        getClient(alert.id_cliente).then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
        if (alert.tipus_alerta === 'geographical_alert') {
            getMapData().then(setMapPoints).catch(console.error);
        }
    }, [alert.id_cliente, alert.tipus_alerta]);
    const borderColor = alert.tipus_alerta === 'anticipacio' ? '#00B8A9'
        : alert.tipus_alerta === 'reactiva' ? '#E74C3C'
            : alert.tipus_alerta === 'fugat' ? '#6B7280'
                : alert.tipus_alerta === 'anomalia_vermella' ? '#E74C3C'
                    : alert.tipus_alerta === 'anomalia_groga' ? '#F4A261'
                        : alert.tipus_alerta === 'monitoritzar' ? '#3B82F6'
                            : '#E5E7EB';
    const isLeal = alert.segment === 'leal' || alert.segment === 'actiu_regular' || alert.share_12m >= 0.70;
    const shareLabel = isLeal ? 'leal' : 'promiscuo';
    const shareColor = isLeal ? '#00B8A9' : '#F4A261';
    // ── Build purchase timeline ────────────────────────────
    const historial = data?.historial?.filter(h => h.familia === alert.familia_potencial).reverse() || [];
    let purchases = [];
    let primerDate = null;
    let timelineDays = 0;
    let maxValor = 1;
    if (historial.length > 0) {
        const dates = historial.map(h => new Date(h.fecha));
        primerDate = new Date(Math.min(...dates.map(d => d.getTime())));
        const agrupades = new Map();
        historial.forEach(h => {
            const day = Math.round((new Date(h.fecha).getTime() - primerDate.getTime()) / 86400000);
            if (agrupades.has(day)) {
                agrupades.get(day).valor += h.valor;
            }
            else {
                agrupades.set(day, { day, date: h.fecha, valor: h.valor });
            }
        });
        purchases = Array.from(agrupades.values()).sort((a, b) => a.day - b.day);
        timelineDays = Math.max(...purchases.map(p => p.day), 1);
        maxValor = Math.max(...purchases.map(p => p.valor), 1);
    }
    // ── EWM (exponentially weighted) ─────────────────────
    function ewmStats(gaps, halfLife = 4) {
        const n = gaps.length;
        if (n === 0)
            return { mean: 0, std: 0 };
        const lam = Math.LN2 / Math.max(halfLife, 0.1);
        const weights = Array.from({ length: n }, (_, i) => Math.exp(lam * i));
        const wSum = weights.reduce((a, b) => a + b, 0);
        const normW = weights.map(w => w / wSum);
        const mean = normW.reduce((s, w, i) => s + w * gaps[i], 0);
        const variance = normW.reduce((s, w, i) => s + w * (gaps[i] - mean) ** 2, 0);
        const std = Math.sqrt(variance);
        return { mean, std: std > 0 ? std : mean * 0.3 };
    }
    // ── Prediction zones ───────────────────────────────────
    const cicle = alert.cicle_mig_dies || 0;
    const cicleStd = alert.cicle_std_dies || (cicle * 0.3);
    const hoje = new Date();
    const actualHojeDay = primerDate
        ? Math.round((hoje.getTime() - primerDate.getTime()) / 86400000)
        : 0;
    const hojeDay = simDay !== null ? simDay : actualHojeDay;
    // Només tenim en compte les compres fetes fins a l'"avui" simulat
    const visiblePurchases = purchases.filter(p => p.day <= hojeDay);
    const lastPurchaseDay = visiblePurchases.length > 0 ? visiblePurchases[visiblePurchases.length - 1].day : hojeDay;
    // Recalcular cicle EWM amb les dades disponibles fins al dia simulat
    let simCicle = cicle;
    let simCicleStd = cicleStd;
    if (simDay !== null && visiblePurchases.length >= 2) {
        const gaps = [];
        for (let i = 1; i < visiblePurchases.length; i++) {
            gaps.push(visiblePurchases[i].day - visiblePurchases[i - 1].day);
        }
        if (gaps.length > 0) {
            const stats = ewmStats(gaps);
            simCicle = Math.max(stats.mean, 1);
            simCicleStd = Math.max(stats.std, simCicle * 0.05);
        }
    }
    const diesSenseSimulats = hojeDay - lastPurchaseDay;
    const properDay = lastPurchaseDay + simCicle;
    const low = properDay - 0.5 * simCicleStd;
    const high = properDay + 0.5 * simCicleStd;
    const riskHigh = properDay + 1.5 * simCicleStd;
    // ── Chart dimensions ───────────────────────────────────
    const W = 800;
    const H = 200;
    const PAD = { top: 30, bottom: 40, left: 10, right: 60 };
    const chartW = W - PAD.left - PAD.right;
    const chartH = H - PAD.top - PAD.bottom;
    // Ajustem l'escala de l'eix X perquè no s'allargui a l'infinit (evitem errors previs amb multiplicacions errònies)
    const maxDayInData = Math.max(actualHojeDay, timelineDays, riskHigh);
    const xMax = maxDayInData + Math.max(30, cicle * 0.4);
    const xScale = (d) => PAD.left + (d / xMax) * chartW;
    const yScale = (v) => PAD.top + chartH - (v / maxValor) * chartH * 0.85;
    return (_jsxs("div", { children: [_jsx("button", { style: styles.backBtn, onClick: onBack, children: "\u2190 Tornar" }), _jsxs("div", { style: { ...styles.hero, borderLeft: `4px solid ${borderColor}` }, children: [_jsxs("div", { style: styles.heroTop, children: [_jsxs("div", { children: [_jsxs("span", { style: styles.heroId, children: ["#", alert.id_cliente] }), _jsx("span", { style: styles.heroSep, children: "\u00B7" }), _jsx("span", { style: styles.heroFam, children: alert.familia_potencial }), _jsx("span", { style: styles.heroSep, children: "\u00B7" }), _jsx("span", { style: styles.heroProv, children: alert.provincia || '?' })] }), _jsx("div", { style: { display: 'flex', gap: 6, alignItems: 'center' }, children: _jsx(ContactActions, { alert: alert, onToggleTreated: onToggleTreated, variant: "large" }) })] }), alert.tipus_alerta === 'geographical_alert' ? (_jsx("div", { style: { height: 300, borderRadius: 8, overflow: 'hidden', marginBottom: 16 }, children: mapPoints.length > 0 ? ((() => {
                            const centerPoint = mapPoints.find(p => p.id_cliente === alert.id_cliente);
                            const centerLat = centerPoint ? centerPoint.lat : 28.29;
                            const centerLon = centerPoint ? centerPoint.lon : -16.62;
                            return (_jsxs(MapContainer, { center: [centerLat, centerLon], zoom: 11, style: { height: '100%', width: '100%' }, children: [_jsx(TileLayer, { attribution: '\u00A9 OpenStreetMap', url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" }), mapPoints.filter(p => p.familia === alert.familia_potencial).map((p, idx) => {
                                        const isCenter = p.id_cliente === alert.id_cliente;
                                        return (_jsx(CircleMarker, { center: [p.lat, p.lon], radius: isCenter ? 12 : 8, pathOptions: {
                                                fillColor: isCenter ? '#111827' : (p.share_12m >= 0.7 ? '#00B8A9' : p.share_12m >= 0.4 ? '#F4A261' : '#E74C3C'),
                                                fillOpacity: 0.8,
                                                color: isCenter ? '#fff' : '#fff',
                                                weight: isCenter ? 3 : 1,
                                            }, children: _jsx(Tooltip, { children: _jsxs("div", { children: [_jsxs("strong", { children: ["Client #", p.id_cliente] }), _jsx("br", {}), "Share of Wallet: ", (p.share_12m * 100).toFixed(1), "%"] }) }) }, `${p.id_cliente}-${idx}`));
                                    })] }));
                        })()) : (_jsx("p", { style: { color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }, children: "Carregant mapa..." })) })) : (_jsx(_Fragment, { children: loading ? (_jsx("p", { style: { color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }, children: "Carregant historial..." })) : purchases.length === 0 ? (_jsx("p", { style: { color: '#9CA3AF', fontSize: 13, padding: '40px 0', textAlign: 'center' }, children: "Sense historial de compres" })) : (_jsxs("svg", { width: "100%", viewBox: `0 0 ${W} ${H + 50}`, style: styles.chartSvg, children: [_jsx("rect", { x: xScale(low), y: PAD.top, width: xScale(high) - xScale(low), height: chartH, fill: "rgba(0,184,169,0.10)", rx: 0 }), _jsx("rect", { x: xScale(high), y: PAD.top, width: xScale(riskHigh) - xScale(high), height: chartH, fill: "rgba(231,76,60,0.08)", rx: 0 }), _jsx("line", { x1: xScale(properDay), y1: PAD.top, x2: xScale(properDay), y2: PAD.top + chartH, stroke: "#00B8A9", strokeWidth: 1, strokeDasharray: "4,3", opacity: 0.5 }), (() => {
                                    const visibility = new Array(purchases.length).fill(false);
                                    let lastLabelX = Infinity;
                                    for (let i = purchases.length - 1; i >= 0; i--) {
                                        const p = purchases[i];
                                        if (p.day > hojeDay)
                                            continue;
                                        const currentX = xScale(p.day);
                                        if (lastLabelX - currentX > 26) {
                                            visibility[i] = true;
                                            lastLabelX = currentX;
                                        }
                                    }
                                    return purchases.map((p, i) => {
                                        const currentX = xScale(p.day);
                                        const isFuture = p.day > hojeDay;
                                        const barW = Math.max(3, (chartW / xMax) * 4);
                                        const barH = chartH - yScale(p.valor) + PAD.top;
                                        const showLabel = visibility[i];
                                        let barColor, barOpacity;
                                        if (isFuture) {
                                            const dinsFinestra = p.day >= low && p.day <= high;
                                            barColor = dinsFinestra ? '#059669' : '#DC2626';
                                            barOpacity = dinsFinestra ? 0.7 : 0.5;
                                        }
                                        else {
                                            barColor = '#1565C0';
                                            barOpacity = 0.8;
                                        }
                                        return (_jsxs("g", { children: [_jsxs("title", { children: [p.valor.toFixed(0), "\u20AC - dia ", p.day] }), _jsx("rect", { x: currentX - barW / 2, y: yScale(p.valor), width: barW, height: barH, fill: barColor, rx: 0, opacity: barOpacity }), showLabel && (_jsxs("text", { x: currentX, y: yScale(p.valor) - 6, textAnchor: "middle", fontSize: 9, fill: "#4B5563", fontWeight: 600, children: [p.valor.toFixed(0), "\u20AC"] }))] }, i));
                                    });
                                })(), (() => {
                                    const hojeDinsVerd = hojeDay >= low && hojeDay <= high;
                                    const hojeDinsVermell = hojeDay > high && hojeDay <= riskHigh;
                                    const hojePassat = hojeDay > riskHigh;
                                    const hojeColor = hojePassat ? '#DC2626' : hojeDinsVermell ? '#F59E0B' : hojeDinsVerd ? '#059669' : '#111827';
                                    const hojeLabel = hojePassat ? 'RETARD' : hojeDinsVermell ? 'ALERTA' : hojeDinsVerd ? 'FINESTRA' : 'AVUI';
                                    return _jsxs(_Fragment, { children: [_jsx("line", { x1: xScale(hojeDay), y1: PAD.top, x2: xScale(hojeDay), y2: PAD.top + chartH, stroke: hojeColor, strokeWidth: 2.5 }), _jsx("text", { x: xScale(hojeDay), y: PAD.top - 10, textAnchor: "middle", fontSize: 10, fontWeight: 700, fill: hojeColor, children: simDay !== null ? hojeLabel.replace('AVUI', 'SIM') : hojeLabel })] });
                                })(), _jsx("line", { x1: PAD.left, y1: PAD.top + chartH, x2: PAD.left + chartW, y2: PAD.top + chartH, stroke: "#E5E7EB", strokeWidth: 1 }), [0, Math.round(xMax * 0.25), Math.round(xMax * 0.5), Math.round(xMax * 0.75), Math.round(xMax)].map(d => (_jsxs("text", { x: xScale(d), y: PAD.top + chartH + 30, textAnchor: "middle", fontSize: 9, fill: "#9CA3AF", children: ["dia ", d] }, d)))] })) })), _jsxs("div", { style: { marginTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }, children: [_jsx("p", { style: styles.motiu, children: alert.motiu }), alert.tipus_alerta !== 'geographical_alert' && (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 12, background: '#F9FAFB', padding: '12px 16px', borderRadius: 0, border: '1px solid #E5E7EB' }, children: [_jsx("label", { style: { fontSize: 13, fontWeight: 600, color: '#374151' }, children: "Simular Dia Avui:" }), _jsx("input", { type: "range", min: 0, max: actualHojeDay, value: hojeDay, onChange: (e) => {
                                            const v = Number(e.target.value);
                                            setSimDay(v >= actualHojeDay ? null : v);
                                        }, style: { flex: 1 } }), _jsxs("span", { style: { fontSize: 13, color: '#6B7280', minWidth: 50, textAlign: 'right' }, children: ["Dia ", hojeDay] })] }))] })] }), _jsxs("div", { style: styles.metrics, children: [_jsxs("div", { style: styles.metric, children: [_jsxs("span", { style: { ...styles.mValue, color: shareColor }, children: [(alert.share_12m * 100).toFixed(0), "%"] }), _jsx("span", { style: styles.mLabel, children: shareLabel })] }), _jsxs("div", { style: styles.metric, children: [_jsxs("span", { style: styles.mValue, children: [alert.gap_eur.toLocaleString(), "\u20AC"] }), _jsx("span", { style: styles.mLabel, children: "gap" })] }), _jsxs("div", { style: styles.metric, children: [_jsxs("span", { style: styles.mValue, children: [diesSenseSimulats, "d"] }), _jsx("span", { style: styles.mLabel, children: "sense compra" })] }), _jsxs("div", { style: styles.metric, children: [_jsx("span", { style: styles.mValue, children: simCicle > 0 ? `${simCicle.toFixed(0)}d` : '-' }), _jsxs("span", { style: styles.mLabel, children: ["cicle", simCicleStd > 0 ? ` ±${simCicleStd.toFixed(0)}` : ''] })] })] }), alert.tractada && (_jsx(FeedbackForm, { alert: alert }))] }));
}
function FeedbackForm({ alert }) {
    const [resultado, setResultado] = useState(null);
    const [importe, setImporte] = useState('');
    const [saved, setSaved] = useState(false);
    const handleSave = async () => {
        if (!resultado)
            return;
        await updateFeedback(alert.id_cliente, alert.familia_potencial, alert.tipus_alerta, resultado, resultado === 'convertido' ? Number(importe) || 0 : undefined);
        setSaved(true);
    };
    return (_jsxs("div", { style: feedbackStyles.box, children: [_jsx("span", { style: feedbackStyles.title, children: "Resultat de la intervenci\u00F3" }), saved ? (_jsx("span", { style: feedbackStyles.saved, children: "\u2713 Registrat" })) : (_jsxs(_Fragment, { children: [_jsx("div", { style: feedbackStyles.btns, children: ['convertido', 'no_convertido', 'sin_contacto'].map(r => (_jsx("button", { style: { ...feedbackStyles.btn, ...(resultado === r ? feedbackStyles.btnActive : {}) }, onClick: () => { setResultado(r); setSaved(false); }, children: r === 'convertido' ? '✓ Venda' : r === 'no_convertido' ? '✕ No venda' : '— Sense contacte' }, r))) }), resultado === 'convertido' && (_jsxs("div", { style: feedbackStyles.importeRow, children: [_jsx("span", { style: feedbackStyles.importeLbl, children: "Import:" }), _jsx("input", { style: feedbackStyles.importeInput, type: "number", value: importe, onChange: e => setImporte(e.target.value), placeholder: "0" }), _jsx("span", { style: feedbackStyles.importeLbl, children: "\u20AC" })] })), resultado && (_jsx("button", { style: feedbackStyles.saveBtn, onClick: handleSave, children: "Guardar" }))] }))] }));
}
const styles = {
    backBtn: {
        background: 'none',
        border: 'none',
        color: '#007AFF',
        fontSize: 15,
        fontWeight: 600,
        cursor: 'pointer',
        padding: '24px 0 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        transition: 'opacity 0.2s ease',
    },
    hero: {
        background: '#FFFFFF',
        borderRadius: 24,
        padding: '32px',
        marginBottom: 16,
        boxShadow: '0 4px 20px rgba(0,0,0,0.04)',
        border: '1px solid rgba(0,0,0,0.05)',
    },
    heroTop: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 32,
    },
    heroId: {
        fontSize: 28,
        fontWeight: 800,
        color: '#000000',
        fontVariantNumeric: 'tabular-nums',
        letterSpacing: '-0.02em',
    },
    heroSep: {
        color: '#D1D5DB',
        margin: '0 8px',
        fontSize: 24,
        fontWeight: 300,
    },
    heroFam: {
        fontSize: 22,
        fontWeight: 600,
        color: '#3A3A3C',
        letterSpacing: '-0.01em',
    },
    heroProv: {
        fontSize: 15,
        color: '#8E8E93',
        fontWeight: 500,
    },
    chartSvg: {
        display: 'block',
        marginBottom: 24,
    },
    motiu: {
        fontSize: 14,
        color: '#3A3A3C',
        lineHeight: 1.5,
        margin: 0,
        fontWeight: 400,
    },
    metrics: {
        display: 'flex',
        alignItems: 'center',
        gap: 32,
        background: '#FFFFFF',
        borderRadius: 20,
        padding: '20px 32px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.03)',
        border: '1px solid rgba(0,0,0,0.05)',
        flexWrap: 'wrap',
    },
    metric: {
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
    },
    mValue: {
        fontSize: 20,
        fontWeight: 800,
        color: '#000000',
        fontVariantNumeric: 'tabular-nums',
    },
    mLabel: {
        fontSize: 13,
        fontWeight: 500,
        color: '#8E8E93',
    },
    mDiv: {
        color: '#F2F2F7',
        fontSize: 24,
        fontWeight: 200,
    },
};
const feedbackStyles = {
    box: {
        background: 'rgba(0, 122, 255, 0.03)',
        borderRadius: 20,
        padding: '24px 32px',
        marginTop: 16,
        border: '1px solid rgba(0, 122, 255, 0.08)',
    },
    title: {
        fontSize: 15,
        fontWeight: 700,
        color: '#000000',
        display: 'block',
        marginBottom: 16,
    },
    btns: {
        display: 'flex',
        gap: 10,
    },
    btn: {
        background: '#FFFFFF',
        border: '1px solid rgba(0,0,0,0.08)',
        color: '#3A3A3C',
        fontSize: 14,
        fontWeight: 600,
        padding: '10px 20px',
        cursor: 'pointer',
        borderRadius: 14,
        transition: 'all 0.2s ease',
    },
    btnActive: {
        background: '#000000',
        border: '1px solid #000000',
        color: '#FFFFFF',
    },
    importeRow: {
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginTop: 16,
    },
    importeLbl: {
        fontSize: 14,
        fontWeight: 500,
        color: '#3A3A3C',
    },
    importeInput: {
        background: '#FFFFFF',
        border: '1px solid rgba(0,0,0,0.1)',
        color: '#000000',
        fontSize: 15,
        fontWeight: 700,
        padding: '10px 16px',
        width: 120,
        borderRadius: 12,
    },
    saveBtn: {
        background: '#007AFF',
        border: 'none',
        color: '#FFFFFF',
        fontSize: 15,
        fontWeight: 700,
        padding: '12px 32px',
        cursor: 'pointer',
        borderRadius: 16,
        marginTop: 16,
        transition: 'all 0.2s ease',
    },
    saved: {
        fontSize: 15,
        color: '#34C759',
        fontWeight: 700,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
    },
};

const BASE = '/api';
async function fetchJSON(url, init) {
    const res = await fetch(`${BASE}${url}`, {
        headers: { 'Content-Type': 'application/json' },
        ...init,
    });
    if (!res.ok)
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
}
export function getAlerts(params = {}) {
    const qs = new URLSearchParams();
    if (params.today)
        qs.set('today', params.today);
    if (params.family)
        qs.set('family', params.family);
    if (params.segment)
        qs.set('segment', params.segment);
    if (params.tipus)
        qs.set('tipus', params.tipus);
    if (params.urgencia)
        qs.set('urgencia', params.urgencia);
    if (params.pendents)
        qs.set('pendents', 'true');
    const query = qs.toString();
    return fetchJSON(`/alerts${query ? `?${query}` : ''}`);
}
export function getStats(today) {
    const qs = today ? `?today=${today}` : '';
    return fetchJSON(`/stats${qs}`);
}
export function getTreated() {
    return fetchJSON('/treated');
}
export function markTreated(id_cliente, familia_potencial, tipus_alerta, resultado, importe_venta) {
    return fetchJSON('/treated', {
        method: 'POST',
        body: JSON.stringify({ id_cliente, familia_potencial, tipus_alerta, resultado, importe_venta }),
    });
}
export function updateFeedback(id_cliente, familia_potencial, tipus_alerta, resultado, importe_venta) {
    return fetchJSON('/treated/feedback', {
        method: 'POST',
        body: JSON.stringify({ id_cliente, familia_potencial, tipus_alerta, resultado, importe_venta }),
    });
}
export function getFeedbackStats() {
    return fetchJSON('/treated/stats');
}
export function unmarkTreated(id) {
    return fetchJSON(`/treated/${id}`, { method: 'DELETE' });
}
export function getClient(id) {
    return fetchJSON(`/clients/${id}`);
}
export function refreshCache() {
    return fetchJSON('/refresh', { method: 'POST' });
}
export function getMapData(today) {
    const qs = today ? `?today=${today}` : '';
    return fetchJSON(`/alerts/map${qs}`);
}

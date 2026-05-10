import { jsxs as _jsxs, jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
const URG = {
    critica: { bg: '#FEE2E2', txt: '#991B1B' },
    alta: { bg: '#FEF3C7', txt: '#92400E' },
    mitjana: { bg: '#DBEAFE', txt: '#1E40AF' },
    baixa: { bg: '#F3F4F6', txt: '#4B5563' },
};
const TIPUS_STYLE = {
    anticipacio: { label: 'ANTICIPAT', color: '#059669' },
    reactiva: { label: 'REACTIVA', color: '#DC2626' },
    fugat: { label: 'FUGAT', color: '#6B7280' },
    anomalia_groga: { label: 'GROGA', color: '#D97706' },
    anomalia_vermella: { label: 'VERMELLA', color: '#DC2626' },
    caiguda_volum: { label: 'VOLUM', color: '#8B5CF6' },
    monitoritzar: { label: 'MONITOR', color: '#3B82F6' },
};
const TECH_COLORS = {
    actiu_regular: '#059669',
    actiu_esporadic: '#D97706',
    inactiu_recent: '#E74C3C',
    inactiu_total: '#6B7280',
    fugat: '#6B7280',
};
function badgeInfo(alert) {
    if (alert.familia_potencial === 'Biomateriales') {
        const color = TECH_COLORS[alert.segment] || '#6B7280';
        const label = alert.segment === 'actiu_regular' ? 'actiu'
            : alert.segment === 'actiu_esporadic' ? 'esporàdic'
                : alert.segment === 'inactiu_recent' ? 'inactiu'
                    : alert.segment === 'inactiu_total' ? 'inactiu'
                        : alert.segment;
        return { label, color };
    }
    if (alert.segment === 'fugat')
        return { label: 'fugat', color: '#6B7280' };
    const isLeal = alert.segment === 'leal' || alert.segment === 'actiu_regular' || alert.share_12m >= 0.70;
    return { label: isLeal ? 'leal' : 'promiscuo', color: isLeal ? '#059669' : '#D97706' };
}
export default function AlertCard({ alert, onToggleTreated, onClick }) {
    const isFugat = alert.segment === 'fugat';
    const isTechnical = alert.familia_potencial === 'Biomateriales';
    const badge = badgeInfo(alert);
    const ts = TIPUS_STYLE[alert.tipus_alerta] || { label: alert.tipus_alerta.replace(/_/g, ' ').toUpperCase(), color: '#6B7280' };
    const urg = URG[alert.urgencia] || URG.baixa;
    return (_jsxs("div", { style: styles.card, onClick: () => onClick?.(alert), children: [_jsxs("div", { style: styles.top, children: [_jsxs("div", { style: styles.left, children: [_jsxs("span", { style: styles.id, children: ["#", alert.id_cliente] }), _jsx("span", { style: styles.sep, children: "\u00B7" }), _jsx("span", { style: styles.familia, children: alert.familia_potencial }), !isFugat && (_jsxs(_Fragment, { children: [_jsx("span", { style: styles.sep, children: "\u00B7" }), _jsx("span", { style: { ...styles.shareBadge, color: badge.color, borderColor: badge.color }, children: isTechnical ? badge.label : `${(alert.share_12m * 100).toFixed(0)}% ${badge.label}` })] }))] }), _jsxs("div", { style: styles.right, children: [_jsx("span", { style: { ...styles.tag, background: ts.color }, children: ts.label }), !isFugat && (_jsx("span", { style: { ...styles.tagOutline, background: urg.bg, color: urg.txt }, children: alert.urgencia.toUpperCase() })), _jsx("button", { style: styles.btn, onClick: e => { e.stopPropagation(); onToggleTreated(alert); }, children: alert.tractada ? '↩' : '✓' })] })] }), _jsxs("div", { style: styles.bottom, children: [_jsx(Metric, { val: `${alert.gap_eur.toLocaleString(undefined, { maximumFractionDigits: 0 })}€`, lbl: "gap" }), _jsx(Metric, { val: `${alert.dies_sense_compra}d`, lbl: "sense compra" }), _jsx(Metric, { val: alert.cicle_mig_dies ? `${alert.cicle_mig_dies.toFixed(0)}d` : '-', lbl: "cicle" })] })] }));
}
function Metric({ val, lbl }) {
    return (_jsxs("div", { style: styles.metric, children: [_jsx("span", { style: styles.mVal, children: val }), _jsx("span", { style: styles.mLbl, children: lbl })] }));
}
const styles = {
    card: {
        background: '#FFFFFF',
        border: '1px solid #E5E7EB',
        borderRadius: 6,
        padding: '16px 20px',
        marginBottom: 8,
        cursor: 'pointer',
        transition: 'box-shadow 0.15s ease',
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
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
        flexWrap: 'wrap',
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
    shareBadge: {
        fontSize: 11,
        fontWeight: 600,
        padding: '2px 8px',
        borderRadius: 4,
        border: '1px solid',
        whiteSpace: 'nowrap',
    },
    tag: {
        fontSize: 10,
        fontWeight: 700,
        color: '#FFFFFF',
        padding: '3px 10px',
        borderRadius: 4,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        whiteSpace: 'nowrap',
    },
    tagOutline: {
        fontSize: 10,
        fontWeight: 700,
        padding: '3px 10px',
        borderRadius: 4,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        whiteSpace: 'nowrap',
    },
    btn: {
        background: '#111827',
        border: 'none',
        color: '#FFFFFF',
        fontSize: 13,
        fontWeight: 700,
        padding: '6px 12px',
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
};

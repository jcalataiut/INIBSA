import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { memo } from 'react';
import ContactActions from './ContactActions';
const TIPUS_STYLE = {
    anticipacio: { label: 'ANTICIPAT', color: '#059669' },
    reactiva: { label: 'REACTIVA', color: '#DC2626' },
    fugat: { label: 'FUGAT', color: '#6B7280' },
    anomalia_groga: { label: 'GROGA', color: '#D97706' },
    anomalia_vermella: { label: 'VERMELLA', color: '#DC2626' },
    caiguda_volum: { label: 'VOLUM', color: '#8B5CF6' },
    monitoritzar: { label: 'MONITOR', color: '#3B82F6' },
};
const URGENCIA_STYLE = {
    critica: '#DC2626',
    alta: '#D97706',
    mitjana: '#3B82F6',
    baixa: '#718096',
};
const AlertCard = memo(function AlertCard({ alert, onToggleTreated, onClick }) {
    const isLeal = alert.segment === 'leal' || alert.segment === 'actiu_regular' || alert.share_12m >= 0.70;
    const sharePct = Math.round(alert.share_12m * 100);
    const shareLabel = `${sharePct}% ${isLeal ? 'leal' : 'promiscuo'}`;
    const shareColor = isLeal ? '#00B8A9' : '#F4A261';
    const typeStyle = TIPUS_STYLE[alert.tipus_alerta] || { label: alert.tipus_alerta, color: '#718096' };
    const urgencyColor = URGENCIA_STYLE[alert.urgencia] || '#718096';
    return (_jsxs("div", { style: styles.card, onClick: () => onClick && onClick(alert), children: [_jsxs("div", { style: styles.row, children: [_jsxs("div", { style: styles.left, children: [_jsxs("span", { style: styles.id, children: ["#", alert.id_cliente] }), _jsx("span", { style: styles.sep, children: "\u00B7" }), _jsx("span", { style: styles.familia, children: alert.familia_potencial })] }), _jsx("div", { style: styles.right, children: _jsx(ContactActions, { alert: alert, onToggleTreated: onToggleTreated, variant: "compact" }) })] }), _jsx("div", { style: styles.divider }), _jsxs("div", { style: styles.row, children: [_jsxs("div", { style: styles.metricsGroup, children: [_jsxs("div", { style: styles.metric, children: [_jsxs("span", { style: styles.mVal, children: [alert.gap_eur.toLocaleString(), "\u20AC"] }), _jsx("span", { style: styles.mLbl, children: "gap" })] }), _jsxs("div", { style: styles.metric, children: [_jsxs("span", { style: styles.mVal, children: [alert.dies_sense_compra, "d"] }), _jsx("span", { style: styles.mLbl, children: "sense compra" })] }), _jsxs("div", { style: styles.metric, children: [_jsx("span", { style: styles.mVal, children: alert.cicle_mig_dies ? `${alert.cicle_mig_dies.toFixed(0)}d` : '-' }), _jsx("span", { style: styles.mLbl, children: "cicle" })] })] }), _jsxs("div", { style: styles.badgesGroup, children: [_jsx("span", { style: { ...styles.shareBadge, color: shareColor, borderColor: shareColor }, children: shareLabel }), _jsx("div", { style: { ...styles.tag, background: typeStyle.color }, children: typeStyle.label.replace(/_/g, ' ') }), _jsx("div", { style: { ...styles.tagOutline, color: urgencyColor, borderColor: urgencyColor }, children: alert.urgencia })] })] })] }));
});
const styles = {
    card: {
        background: '#FFFFFF',
        borderRadius: 12,
        padding: '20px 24px',
        marginBottom: 12,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        border: '1px solid #E2E8F0',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        width: '100%',
        maxWidth: 600,
        margin: '0 auto 12px auto',
        boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
    },
    row: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
    },
    divider: {
        height: 1,
        background: '#F1F5F9',
        width: '100%',
    },
    left: {
        display: 'flex',
        alignItems: 'center',
        gap: 10,
    },
    right: {
        display: 'flex',
        alignItems: 'center',
        gap: 12,
    },
    id: {
        fontSize: 20,
        fontWeight: 800,
        color: '#1A202C',
        letterSpacing: '-0.02em',
    },
    sep: {
        color: '#CBD5E0',
        fontSize: 18,
    },
    familia: {
        fontSize: 18,
        fontWeight: 600,
        color: '#4A5568',
    },
    metricsGroup: {
        display: 'flex',
        gap: 28,
    },
    metric: {
        display: 'flex',
        flexDirection: 'column',
    },
    mVal: {
        fontSize: 16,
        fontWeight: 700,
        color: '#2D3748',
    },
    mLbl: {
        fontSize: 10,
        color: '#A0AEC0',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginTop: 2,
    },
    badgesGroup: {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
    },
    shareBadge: {
        fontSize: 10,
        fontWeight: 800,
        padding: '3px 8px',
        borderRadius: 4,
        border: '1px solid',
        textTransform: 'uppercase',
    },
    tag: {
        fontSize: 10,
        fontWeight: 800,
        color: '#FFFFFF',
        padding: '4px 10px',
        borderRadius: 4,
        textTransform: 'uppercase',
    },
    tagOutline: {
        fontSize: 10,
        fontWeight: 800,
        padding: '3px 10px',
        borderRadius: 4,
        textTransform: 'uppercase',
        border: '1px solid',
    },
};
export default AlertCard;

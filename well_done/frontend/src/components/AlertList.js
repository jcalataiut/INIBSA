import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import AlertCard from './AlertCard';
export default function AlertList({ alerts, loading, onToggleTreated, onClickAlert, listLabel }) {
    if (loading) {
        return (_jsxs("div", { style: styles.empty, children: [_jsx("div", { style: styles.spinner }), _jsx("span", { style: styles.emptyText, children: "Calculant alertes..." })] }));
    }
    if (alerts.length === 0) {
        const msg = listLabel === 'tractades'
            ? 'No hi ha cap alerta tractada'
            : 'No hi ha alertes pendents';
        return (_jsxs("div", { style: styles.empty, children: [_jsx("span", { style: styles.emptyIcon, children: "\u2713" }), _jsx("span", { style: styles.emptyText, children: msg })] }));
    }
    return (_jsxs("div", { children: [_jsxs("div", { style: styles.count, children: [alerts.length.toLocaleString(), " alertes"] }), alerts.map((a, i) => (_jsx(AlertCard, { alert: a, onToggleTreated: onToggleTreated, onClick: onClickAlert }, `${a.id_cliente}_${a.familia_potencial}_${a.tipus_alerta}_${i}`)))] }));
}
const styles = {
    empty: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '80px 0',
        gap: 16,
    },
    spinner: {
        width: 24,
        height: 24,
        border: '2px solid #E5E7EB',
        borderTop: '2px solid #00B8A9',
        animation: 'spin 0.8s linear infinite',
    },
    emptyIcon: {
        fontSize: 32,
        color: '#00B8A9',
        fontWeight: 700,
    },
    emptyText: {
        fontSize: 14,
        color: '#6B7280',
    },
    count: {
        fontSize: 12,
        fontWeight: 600,
        color: '#6B7280',
        paddingBottom: 12,
    },
};

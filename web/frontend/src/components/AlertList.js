import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import AlertCard from './AlertCard';
export default function AlertList({ alerts, loading, onToggleTreated, onClickAlert, listLabel }) {
    if (loading) {
        return (_jsxs("div", { style: styles.empty, children: [_jsx("div", { style: styles.spinner }), _jsx("span", { style: styles.emptyText, children: "Actualitzant llista..." })] }));
    }
    if (alerts.length === 0) {
        const msg = listLabel === 'tractades'
            ? 'Encara no has tractat cap alerta.'
            : 'Bones notícies! No hi ha alertes pendents.';
        return (_jsxs("div", { style: styles.empty, children: [_jsx("div", { style: styles.emptyIcon, children: "\u2713" }), _jsx("span", { style: styles.emptyText, children: msg })] }));
    }
    const LIMIT = 100;
    const displayedAlerts = alerts.slice(0, LIMIT);
    return (_jsxs("div", { style: styles.listWrapper, children: [_jsxs("div", { style: styles.count, children: ["Mostrant ", displayedAlerts.length, " de ", alerts.length.toLocaleString(), " alertes trobades"] }), displayedAlerts.map((a, i) => (_jsx(AlertCard, { alert: a, onToggleTreated: onToggleTreated, onClick: onClickAlert }, `${a.id_cliente}_${a.familia_potencial}_${a.tipus_alerta}_${i}`))), alerts.length > LIMIT && (_jsxs("div", { style: styles.infoBox, children: ["Refina els filtres per veure alertes m\u00E9s espec\u00EDfiques (nom\u00E9s es mostren les primeres ", LIMIT, ")."] }))] }));
}
const styles = {
    listWrapper: {
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
    },
    empty: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '100px 0',
        gap: 20,
        animation: 'fadeIn 0.6s ease-out',
    },
    spinner: {
        width: 28,
        height: 28,
        border: '3px solid #E5E5EA',
        borderTop: '3px solid #00B8A9',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
    },
    emptyIcon: {
        fontSize: 48,
        color: '#34C759',
        background: 'rgba(52, 199, 89, 0.1)',
        width: 80,
        height: 80,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        marginBottom: 8,
    },
    emptyText: {
        fontSize: 17,
        fontWeight: 500,
        color: '#8E8E93',
        textAlign: 'center',
        maxWidth: 300,
        lineHeight: 1.4,
    },
    count: {
        fontSize: 13,
        fontWeight: 600,
        color: '#8E8E93',
        paddingBottom: 20,
        textAlign: 'center',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
    },
    infoBox: {
        padding: '24px',
        background: '#FFFFFF',
        borderRadius: 12,
        border: '1px dashed #CBD5E0',
        color: '#718096',
        textAlign: 'center',
        fontSize: 14,
        fontWeight: 500,
        margin: '20px auto',
        maxWidth: 600,
        width: '100%',
    },
};

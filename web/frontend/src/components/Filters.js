import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from 'react';
const COMMODITIES_SEGMENTS = ['leal', 'promiscuo'];
const COMMODITIES_TIPUS = ['anticipacio', 'reactiva', 'geographical_alert'];
const TECHNICALS_SEGMENTS = ['actiu_regular', 'actiu_esporadic', 'inactiu_recent', 'inactiu_total'];
const TECHNICALS_TIPUS = ['anomalia_groga', 'anomalia_vermella', 'monitoritzar', 'caiguda_volum', 'geographical_alert'];
const LABEL_SEG = {
    leal: 'Leal', promiscuo: 'Promiscuo',
    actiu_regular: 'Actiu Regular', actiu_esporadic: 'Actiu Esporàdic',
    inactiu_recent: 'Inactiu Recent', inactiu_total: 'Inactiu Total',
};
const URGENCIES = ['critica', 'alta', 'mitjana', 'baixa'];
const LABEL_TIPUS = {
    anticipacio: 'Anticipació', reactiva: 'Reactiva',
    anomalia_groga: 'Anomalia Groga', anomalia_vermella: 'Anomalia Vermella',
    monitoritzar: 'Monitoritzar',
    caiguda_volum: 'Caiguda Volum',
    geographical_alert: 'Alerta Geogràfica',
};
export default function Filters(props) {
    const [open, setOpen] = useState(false);
    const activeCount = props.filterSegment.length + props.filterTipus.length + props.filterUrgencia.length;
    const currentSegments = props.activeFamilia === 'commodities' ? COMMODITIES_SEGMENTS : TECHNICALS_SEGMENTS;
    const currentTipus = props.activeFamilia === 'commodities' ? COMMODITIES_TIPUS : TECHNICALS_TIPUS;
    return (_jsxs(_Fragment, { children: [_jsxs("button", { style: styles.filterBtn, onClick: () => setOpen(true), children: [_jsx("svg", { width: "14", height: "14", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2.5", children: _jsx("path", { d: "M22 3H2l8 9.46V19l4 2v-8.54L22 3z" }) }), "Filtres", activeCount > 0 && _jsx("span", { style: styles.badge, children: activeCount })] }), open && (_jsx("div", { style: styles.overlay, onClick: () => setOpen(false), children: _jsxs("div", { style: styles.modal, onClick: e => e.stopPropagation(), children: [_jsxs("div", { style: styles.modalHeader, children: [_jsx("span", { style: styles.modalTitle, children: "Filtres" }), _jsx("button", { style: styles.closeBtn, onClick: () => setOpen(false), children: "\u2715" })] }), _jsxs("div", { style: styles.section, children: [_jsx("span", { style: styles.sectionLabel, children: "Segment" }), _jsx("div", { style: styles.chips, children: currentSegments.map(s => (_jsx("button", { style: { ...styles.chip, ...(props.filterSegment.includes(s) ? styles.chipActive : {}) }, onClick: () => {
                                            const next = props.filterSegment.includes(s)
                                                ? props.filterSegment.filter(x => x !== s)
                                                : [...props.filterSegment, s];
                                            props.onSegmentChange(next);
                                        }, children: LABEL_SEG[s] || s }, s))) })] }), _jsxs("div", { style: styles.section, children: [_jsx("span", { style: styles.sectionLabel, children: "Tipus d'Alerta" }), _jsx("div", { style: styles.chips, children: currentTipus.map(t => (_jsx("button", { style: { ...styles.chip, ...(props.filterTipus.includes(t) ? styles.chipActive : {}) }, onClick: () => {
                                            const next = props.filterTipus.includes(t)
                                                ? props.filterTipus.filter(x => x !== t)
                                                : [...props.filterTipus, t];
                                            props.onTipusChange(next);
                                        }, children: LABEL_TIPUS[t] || t.replace(/_/g, ' ') }, t))) })] }), _jsxs("div", { style: styles.section, children: [_jsx("span", { style: styles.sectionLabel, children: "Urg\u00E8ncia" }), _jsx("div", { style: styles.chips, children: URGENCIES.map(u => (_jsx("button", { style: { ...styles.chip, ...(props.filterUrgencia.includes(u) ? styles.chipActive : {}) }, onClick: () => {
                                            const next = props.filterUrgencia.includes(u)
                                                ? props.filterUrgencia.filter(x => x !== u)
                                                : [...props.filterUrgencia, u];
                                            props.onUrgenciaChange(next);
                                        }, children: u }, u))) })] }), _jsx("div", { style: styles.section, children: _jsxs("label", { style: styles.toggle, children: [_jsx("input", { type: "checkbox", checked: props.showTreated, onChange: e => props.onShowTreatedChange(e.target.checked), style: styles.checkbox }), _jsx("span", { style: styles.toggleLabel, children: "Mostrar alertes tractades" })] }) }), _jsx("button", { style: styles.applyBtn, onClick: () => setOpen(false), children: "Aplicar Filtres" })] }) }))] }));
}
const styles = {
    filterBtn: {
        background: '#FFFFFF',
        border: 'none',
        color: '#007AFF',
        fontSize: 14,
        fontWeight: 600,
        padding: '8px 18px',
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        borderRadius: 20,
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
        transition: 'all 0.2s ease',
    },
    badge: {
        background: '#007AFF',
        color: '#FFFFFF',
        fontSize: 10,
        fontWeight: 700,
        width: 18,
        height: 18,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    },
    overlay: {
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.3)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        zIndex: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        animation: 'fadeIn 0.3s ease-out',
    },
    modal: {
        background: '#FFFFFF',
        width: 440,
        maxWidth: '94vw',
        maxHeight: '86vh',
        overflowY: 'auto',
        padding: 32,
        borderRadius: 24,
        boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
    },
    modalHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 28,
    },
    modalTitle: {
        fontSize: 22,
        fontWeight: 800,
        color: '#000000',
        letterSpacing: '-0.02em',
    },
    closeBtn: {
        background: '#F2F2F7',
        border: 'none',
        width: 32,
        height: 32,
        borderRadius: '50%',
        fontSize: 14,
        color: '#8E8E93',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    },
    section: {
        marginBottom: 28,
    },
    sectionLabel: {
        display: 'block',
        fontSize: 13,
        fontWeight: 600,
        color: '#8E8E93',
        marginBottom: 12,
    },
    chips: {
        display: 'flex',
        gap: 8,
        flexWrap: 'wrap',
    },
    chip: {
        background: '#F2F2F7',
        border: 'none',
        color: '#3A3A3C',
        fontSize: 13,
        fontWeight: 500,
        padding: '8px 16px',
        cursor: 'pointer',
        borderRadius: 12,
        transition: 'all 0.2s ease',
    },
    chipActive: {
        background: '#007AFF',
        color: '#FFFFFF',
        fontWeight: 600,
    },
    toggle: {
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        cursor: 'pointer',
    },
    checkbox: {
        width: 18,
        height: 18,
        accentColor: '#007AFF',
    },
    toggleLabel: {
        fontSize: 15,
        fontWeight: 500,
        color: '#1C1C1E',
    },
    applyBtn: {
        background: '#000000',
        border: 'none',
        color: '#FFFFFF',
        fontSize: 16,
        fontWeight: 600,
        padding: '12px 0',
        cursor: 'pointer',
        width: '100%',
        borderRadius: 14,
        marginTop: 8,
        transition: 'all 0.2s ease',
    },
};

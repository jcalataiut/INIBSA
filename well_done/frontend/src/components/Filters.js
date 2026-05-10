import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from 'react';
const COMMODITIES_SEGMENTS = ['leal', 'promiscuo', 'fugat'];
const COMMODITIES_TIPUS = ['anticipacio', 'reactiva', 'fugat', 'geographical_alert'];
const TECHNICALS_SEGMENTS = ['actiu_regular', 'actiu_esporadic', 'inactiu_recent', 'inactiu_total', 'fugat'];
const TECHNICALS_TIPUS = ['anomalia_groga', 'anomalia_vermella', 'monitoritzar', 'caiguda_volum', 'fugat', 'geographical_alert'];
const LABEL_SEG = {
    leal: 'Leal', promiscuo: 'Promiscuo',
    actiu_regular: 'Actiu Regular', actiu_esporadic: 'Actiu Esporàdic',
    inactiu_recent: 'Inactiu Recent', inactiu_total: 'Inactiu Total',
    fugat: 'Fugat',
};
const URGENCIES = ['critica', 'alta', 'mitjana', 'baixa'];
const LABEL_TIPUS = {
    anticipacio: 'Anticipació', reactiva: 'Reactiva',
    anomalia_groga: 'Anomalia Groga', anomalia_vermella: 'Anomalia Vermella',
    monitoritzar: 'Monitoritzar',
    caiguda_volum: 'Caiguda Volum',
    fugat: 'Fugat',
    geographical_alert: 'Alerta Geogràfica',
};
export default function Filters(props) {
    const [open, setOpen] = useState(false);
    const activeCount = props.filterSegment.length + props.filterTipus.length + props.filterUrgencia.length;
    const currentSegments = props.activeFamilia === 'commodities' ? COMMODITIES_SEGMENTS : TECHNICALS_SEGMENTS;
    const currentTipus = props.activeFamilia === 'commodities' ? COMMODITIES_TIPUS : TECHNICALS_TIPUS;
    return (_jsxs(_Fragment, { children: [_jsxs("button", { style: styles.filterBtn, onClick: () => setOpen(true), children: [_jsx("svg", { width: "14", height: "14", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", children: _jsx("path", { d: "M22 3H2l8 9.46V19l4 2v-8.54L22 3z" }) }), "Filtres", activeCount > 0 && _jsx("span", { style: styles.badge, children: activeCount })] }), open && (_jsx("div", { style: styles.overlay, onClick: () => setOpen(false), children: _jsxs("div", { style: styles.modal, onClick: e => e.stopPropagation(), children: [_jsxs("div", { style: styles.modalHeader, children: [_jsx("span", { style: styles.modalTitle, children: "Filtres" }), _jsx("button", { style: styles.closeBtn, onClick: () => setOpen(false), children: "\u2715" })] }), _jsxs("div", { style: styles.section, children: [_jsx("span", { style: styles.sectionLabel, children: "Segment" }), _jsx("div", { style: styles.chips, children: currentSegments.map(s => (_jsx("button", { style: { ...styles.chip, ...(props.filterSegment.includes(s) ? styles.chipActive : {}) }, onClick: () => {
                                            const next = props.filterSegment.includes(s)
                                                ? props.filterSegment.filter(x => x !== s)
                                                : [...props.filterSegment, s];
                                            props.onSegmentChange(next);
                                        }, children: LABEL_SEG[s] || s }, s))) })] }), _jsxs("div", { style: styles.section, children: [_jsx("span", { style: styles.sectionLabel, children: "Tipus" }), _jsx("div", { style: styles.chips, children: currentTipus.map(t => (_jsx("button", { style: { ...styles.chip, ...(props.filterTipus.includes(t) ? styles.chipActive : {}) }, onClick: () => {
                                            const next = props.filterTipus.includes(t)
                                                ? props.filterTipus.filter(x => x !== t)
                                                : [...props.filterTipus, t];
                                            props.onTipusChange(next);
                                        }, children: LABEL_TIPUS[t] || t.replace(/_/g, ' ') }, t))) })] }), _jsxs("div", { style: styles.section, children: [_jsx("span", { style: styles.sectionLabel, children: "Urg\u00E8ncia" }), _jsx("div", { style: styles.chips, children: URGENCIES.map(u => (_jsx("button", { style: { ...styles.chip, ...(props.filterUrgencia.includes(u) ? styles.chipActive : {}) }, onClick: () => {
                                            const next = props.filterUrgencia.includes(u)
                                                ? props.filterUrgencia.filter(x => x !== u)
                                                : [...props.filterUrgencia, u];
                                            props.onUrgenciaChange(next);
                                        }, children: u }, u))) })] }), _jsx("div", { style: styles.section, children: _jsxs("label", { style: styles.toggle, children: [_jsx("input", { type: "checkbox", checked: props.showTreated, onChange: e => props.onShowTreatedChange(e.target.checked), style: styles.checkbox }), _jsx("span", { style: styles.toggleLabel, children: "Mostrar tractades" })] }) }), _jsx("button", { style: styles.applyBtn, onClick: () => setOpen(false), children: "Aplicar" })] }) }))] }));
}
const styles = {
    filterBtn: {
        background: '#FFFFFF',
        border: '1px solid #D1D5DB',
        color: '#374151',
        fontSize: 13,
        fontWeight: 500,
        padding: '8px 16px',
        cursor: 'pointer',
        fontFamily: "'Inter', sans-serif",
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
    },
    badge: {
        background: '#00B8A9',
        color: '#FFFFFF',
        fontSize: 10,
        fontWeight: 700,
        width: 18,
        height: 18,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    },
    overlay: {
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        backdropFilter: 'blur(4px)',
        zIndex: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    },
    modal: {
        background: '#FFFFFF',
        width: 440,
        maxWidth: '90vw',
        maxHeight: '80vh',
        overflowY: 'auto',
        padding: 28,
    },
    modalHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
    },
    modalTitle: {
        fontSize: 18,
        fontWeight: 700,
        color: '#111827',
    },
    closeBtn: {
        background: 'none',
        border: 'none',
        fontSize: 20,
        color: '#6B7280',
        cursor: 'pointer',
        padding: 4,
        lineHeight: 1,
    },
    section: {
        marginBottom: 20,
    },
    sectionLabel: {
        display: 'block',
        fontSize: 10,
        fontWeight: 600,
        color: '#6B7280',
        textTransform: 'uppercase',
        letterSpacing: 1,
        marginBottom: 8,
    },
    chips: {
        display: 'flex',
        gap: 6,
        flexWrap: 'wrap',
    },
    chip: {
        background: '#F9FAFB',
        border: '1px solid #D1D5DB',
        color: '#6B7280',
        fontSize: 12,
        fontWeight: 500,
        padding: '6px 14px',
        cursor: 'pointer',
        fontFamily: "'Inter', sans-serif",
    },
    chipActive: {
        background: '#00B8A9',
        border: '1px solid #00B8A9',
        color: '#FFFFFF',
    },
    toggle: {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        cursor: 'pointer',
    },
    checkbox: {
        accentColor: '#00B8A9',
    },
    toggleLabel: {
        fontSize: 13,
        color: '#374151',
    },
    applyBtn: {
        background: '#00B8A9',
        border: 'none',
        color: '#FFFFFF',
        fontSize: 13,
        fontWeight: 600,
        padding: '10px 0',
        cursor: 'pointer',
        fontFamily: "'Inter', sans-serif",
        width: '100%',
        marginTop: 8,
    },
};

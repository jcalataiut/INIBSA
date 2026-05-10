import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export default function Header({ activeTab, onTabChange }) {
    return (_jsx("div", { style: styles.wrapper, children: _jsxs("div", { style: styles.inner, children: [_jsx("div", { style: styles.left, children: _jsxs("div", { style: styles.logo, children: [_jsx("span", { style: styles.logoIcon, children: "\u25C8" }), _jsx("span", { style: styles.logoText, children: "INIBSA" }), _jsx("span", { style: styles.logoDivider, children: "|" }), _jsx("span", { style: styles.logoSub, children: "Senyals de Demanda Intel\u00B7ligent" })] }) }), _jsx("div", { style: styles.center, children: _jsxs("div", { style: styles.tabs, children: [_jsx("button", { style: { ...styles.tab, ...(activeTab === 'briefing' ? styles.tabActive : {}) }, onClick: () => onTabChange('briefing'), children: "Briefing Diari" }), _jsx("button", { style: { ...styles.tab, ...(activeTab === 'tractades' ? styles.tabActive : {}) }, onClick: () => onTabChange('tractades'), children: "Tractades" }), _jsx("button", { style: { ...styles.tab, ...(activeTab === 'fugats' ? styles.tabActive : {}) }, onClick: () => onTabChange('fugats'), children: "Fugats" }), _jsx("button", { style: { ...styles.tab, ...(activeTab === 'mapa' ? styles.tabActive : {}) }, onClick: () => onTabChange('mapa'), children: "Mapa" })] }) }), _jsx("div", { style: styles.right })] }) }));
}
const styles = {
    wrapper: {
        borderBottom: '1px solid #E5E7EB',
        background: '#FFFFFF',
        position: 'sticky',
        top: 0,
        zIndex: 100,
    },
    inner: {
        maxWidth: 1200,
        margin: '0 auto',
        padding: '0 48px',
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
    },
    left: {},
    logo: {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
    },
    logoIcon: {
        color: '#00B8A9',
        fontSize: 22,
        fontWeight: 700,
    },
    logoText: {
        color: '#111827',
        fontSize: 18,
        fontWeight: 700,
        letterSpacing: 1,
    },
    logoDivider: {
        color: '#D1D5DB',
        margin: '0 8px',
    },
    logoSub: {
        color: '#6B7280',
        fontSize: 13,
        fontWeight: 400,
    },
    center: {},
    tabs: {
        display: 'flex',
        gap: 0,
    },
    tab: {
        background: 'none',
        border: 'none',
        borderBottom: '2px solid transparent',
        color: '#6B7280',
        fontSize: 13,
        fontWeight: 500,
        padding: '0 20px',
        height: 64,
        cursor: 'pointer',
        letterSpacing: 0.3,
    },
    tabActive: {
        color: '#00B8A9',
        borderBottom: '2px solid #00B8A9',
    },
    right: {},
};

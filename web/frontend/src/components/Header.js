import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export default function Header({ activeTab, onTabChange }) {
    return (_jsxs("div", { style: styles.sidebar, children: [_jsx("div", { style: styles.logoSection, onClick: () => onTabChange('briefing'), children: _jsx("img", { src: "/logo.jpg", alt: "Inibsa", style: styles.logoImg }) }), _jsxs("nav", { style: styles.nav, children: [_jsxs("button", { style: { ...styles.navItem, ...(activeTab === 'briefing' ? styles.navItemActive : {}) }, onClick: () => onTabChange('briefing'), children: [activeTab === 'briefing' && _jsx("div", { style: styles.activeLine }), "Alertes del Dia"] }), _jsxs("button", { style: { ...styles.navItem, ...(activeTab === 'tractades' ? styles.navItemActive : {}) }, onClick: () => onTabChange('tractades'), children: [activeTab === 'tractades' && _jsx("div", { style: styles.activeLine }), "Tractades"] }), _jsxs("button", { style: { ...styles.navItem, ...(activeTab === 'fugats' ? styles.navItemActive : {}) }, onClick: () => onTabChange('fugats'), children: [activeTab === 'fugats' && _jsx("div", { style: styles.activeLine }), "Fugats"] }), _jsxs("button", { style: { ...styles.navItem, ...(activeTab === 'mapa' ? styles.navItemActive : {}) }, onClick: () => onTabChange('mapa'), children: [activeTab === 'mapa' && _jsx("div", { style: styles.activeLine }), "Mapa"] })] })] }));
}
const styles = {
    sidebar: {
        width: 210,
        background: '#FFFFFF',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid #E2E8F0',
        zIndex: 100,
        flexShrink: 0,
    },
    logoSection: {
        padding: '40px 20px',
        cursor: 'pointer',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
    },
    logoImg: {
        width: '100%',
        maxWidth: 160,
        height: 'auto',
    },
    nav: {
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        padding: '0 10px',
    },
    navItem: {
        background: 'none',
        border: 'none',
        color: '#718096',
        fontSize: 14,
        fontWeight: 600,
        padding: '12px 16px',
        textAlign: 'left',
        cursor: 'pointer',
        borderRadius: 8,
        position: 'relative',
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
    },
    navItemActive: {
        color: '#00B8A9',
        background: '#F0FFF4',
    },
    activeLine: {
        position: 'absolute',
        left: 0,
        top: '15%',
        bottom: '15%',
        width: 4,
        background: '#00B8A9',
        borderRadius: '0 4px 4px 0',
    },
};

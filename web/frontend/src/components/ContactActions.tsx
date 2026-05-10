import { useState, type MouseEvent, type CSSProperties } from 'react'
import { MailIcon, PhoneIcon, CheckIcon, UndoIcon } from './Icons'
import type { Alerta } from '../types'

interface Props {
  alert: Alerta
  onToggleTreated: (a: Alerta) => void
  variant?: 'compact' | 'large'
}

export default function ContactActions({ alert, onToggleTreated, variant = 'compact' }: Props) {
  const isCompact = variant === 'compact'
  const [modalType, setModalType] = useState<'mail' | 'phone' | null>(null)
  
  const getEmailTemplate = (a: Alerta) => {
    const { tipus_alerta, familia_potencial, id_cliente, provincia } = a;
    
    if (tipus_alerta === 'anticipacio') {
      return `ASSUMPTE: Anticipació de comanda - ${familia_potencial} - Inibsa\n\nHola,\n\nHem previst que properament necessitareu reposar estoc de ${familia_potencial}. Segons el vostre cicle habitual, aquest és el moment ideal per assegurar la comanda i evitar trencaments d'estoc. Si voleu, podem gestionar-ho ara mateix.\n\nSalutacions,\nEquip Inibsa (Client #${id_cliente})`;
    }
    
    if (tipus_alerta === 'reactiva') {
      return `ASSUMPTE: Seguiment de comanda pendent - ${familia_potencial} - Inibsa\n\nHola,\n\nHem detectat que ja ha passat la data prevista per a la vostra reposició habitual de ${familia_potencial}. Volem assegurar-nos que teniu tot el que necessiteu. Si us sembla bé, podem revisar la comanda ara mateix.\n\nSalutacions,\nEquip Inibsa (Client #${id_cliente})`;
    }
    
    if (tipus_alerta === 'geographical_alert') {
      return `ASSUMPTE: Oportunitat a ${provincia || 'la zona'} - ${familia_potencial} - Inibsa\n\nHola,\n\nEstem analitzant la zona de ${provincia || 'la vostra clínica'} i hem vist que hi ha una gran oportunitat per optimitzar el vostre Share of Wallet en ${familia_potencial}. Moltes clíniques veïnes ja ho estan aprofitant. Ens agradaria comentar com millorar les vostres condicions.\n\nSalutacions,\nEquip Inibsa (Client #${id_cliente})`;
    }

    if (tipus_alerta.startsWith('sow_')) {
      const sharePct = (a.share_12m * 100).toFixed(0);
      if (tipus_alerta === 'sow_promiscu_fuga') {
        return `ASSUMPTE: Revisió de col·laboració - ${familia_potencial} - Inibsa\n\nHola,\n\nEns posem en contacte amb vosaltres perquè hem detectat una disminució molt important en el vostre volum de ${familia_potencial}. Per a Inibsa sou un client preferencial i ens agradaria saber si hi ha hagut algun inconvenient o si podem oferir-vos millors condicions per recuperar la vostra confiança.\n\nSalutacions,\nEquip Inibsa (Client #${id_cliente})`;
      }
      return `ASSUMPTE: Millora de condicions en ${familia_potencial} - Inibsa\n\nHola,\n\nEstem revisant els nostres acords comercials per a la línia de ${familia_potencial}. Hem vist que actualment el vostre share és del ${sharePct}%, i ens agradaria parlar sobre com podríem arribar a un acord més global que us beneficiï econòmicament.\n\nSalutacions,\nEquip Inibsa (Client #${id_cliente})`;
    }

    return `ASSUMPTE: Seguiment comercial - Inibsa\n\nHola,\n\nEs posa en contacte amb vosaltres el vostre gestor d'Inibsa per comentar l'evolució de la línia de ${familia_potencial} i revisar si teniu alguna necessitat pendent que puguem resoldre.\n\nQuedem a la vostra disposició.\n\nSalutacions,\nEquip Inibsa (Client #${id_cliente})`;
  }

  const handleMail = (e: MouseEvent) => {
    e.stopPropagation()
    setModalType('mail')
  }
  
  const handlePhone = (e: MouseEvent) => {
    e.stopPropagation()
    setModalType('phone')
  }
  
  const handleTreat = (e: MouseEvent) => {
    e.stopPropagation()
    onToggleTreated(alert)
  }

  const emailText = getEmailTemplate(alert)

  return (
    <div style={styles.group}>
      <button 
        style={styles.actionBtn} 
        onClick={handleMail} 
        title="Enviar correu"
        className="action-btn-mail"
      >
        <MailIcon size={isCompact ? 16 : 18} />
        {!isCompact && <span style={styles.label}>Correu</span>}
      </button>
      
      <button 
        style={styles.actionBtn} 
        onClick={handlePhone} 
        title="Trucar"
        className="action-btn-phone"
      >
        <PhoneIcon size={isCompact ? 16 : 18} />
        {!isCompact && <span style={styles.label}>Trucar</span>}
      </button>
      
      <button 
        style={{
          ...styles.treatBtn,
          ...(alert.tractada ? styles.treated : styles.untreated),
          ...(isCompact ? styles.treatBtnCompact : styles.treatBtnLarge)
        }} 
        onClick={handleTreat}
        className="btn-treat"
      >
        {alert.tractada ? <UndoIcon size={isCompact ? 18 : 20} /> : <CheckIcon size={isCompact ? 18 : 20} />}
        <span style={styles.label}>{alert.tractada ? 'Desfer' : 'Tractar'}</span>
      </button>

      {/* Modal Overlay */}
      {modalType && (
        <div style={styles.overlay} onClick={() => setModalType(null)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ 
                  padding: 10, 
                  borderRadius: 12, 
                  background: modalType === 'mail' ? 'rgba(0, 122, 255, 0.1)' : 'rgba(52, 199, 89, 0.1)',
                  color: modalType === 'mail' ? '#007AFF' : '#34C759'
                }}>
                  {modalType === 'mail' ? <MailIcon size={24} /> : <PhoneIcon size={24} />}
                </div>
                <div>
                  <h3 style={styles.modalTitle}>{modalType === 'mail' ? 'Proposta de Correu' : 'Trucada Comercial'}</h3>
                  <p style={{ fontSize: 13, color: '#8E8E93', fontWeight: 500 }}>Client #{alert.id_cliente} · {alert.familia_potencial}</p>
                </div>
              </div>
              <button style={styles.closeBtn} onClick={() => setModalType(null)}>✕</button>
            </div>

            <div style={styles.modalBody}>
              {modalType === 'mail' ? (
                <>
                  <p style={styles.bodyLabel}>Pots copiar aquest text per al teu correu:</p>
                  <div style={styles.textContainer}>
                    <pre style={styles.pre}>{emailText}</pre>
                  </div>
                  <button 
                    style={styles.copyBtn} 
                    onClick={() => {
                      // Simulem enviament
                      setModalType(null)
                      window.alert('📧 Correu enviat correctament al client #' + alert.id_cliente)
                    }}
                  >
                    Enviar Correu
                  </button>
                </>
              ) : (
                <>
                  <div style={styles.phoneInfo}>
                    <span style={styles.bodyLabel}>Telèfon del client</span>
                    <span style={styles.phoneNum}>+34 93{Math.floor(1000000 + Math.random() * 9000000)}</span>
                  </div>
                  
                  <p style={{ ...styles.bodyLabel, marginTop: 24 }}>Guió proposat per a la trucada:</p>
                  <div style={styles.scriptBox}>
                    {alert.tipus_alerta === 'anticipacio' && (
                      <p>"Bon dia, soc de l'equip comercial d'Inibsa. Trucava per comentar-vos que hem vist que aviat us tocaria reposar {alert.familia_potencial}. Voldríeu que us gestionéssim la comanda per avançat i així assegurar l'estoc?"</p>
                    )}
                    {alert.tipus_alerta === 'reactiva' && (
                      <p>"Hola, em poso en contacte amb vosaltres perquè hem vist un petit retard en la vostra comanda habitual de {alert.familia_potencial}. Ha anat tot bé amb l'última entrega? Necessiteu que us ajudem a preparar la següent?"</p>
                    )}
                    {alert.tipus_alerta === 'geographical_alert' && (
                      <p>"Bones, estem revisant les clíniques de la zona de {alert.provincia} i m'agradaria comentar-vos algunes promocions especials que tenim ara en {alert.familia_potencial} per als nostres clients més actius. Us aniria bé parlar-ne un moment?"</p>
                    )}
                    {alert.tipus_alerta === 'fugat' && (
                      <p>"Hola, fa temps que no tenim el plaer de parlar. He vist que fa un temps que no ens demaneu {alert.familia_potencial} i voldríem saber si ha passat alguna cosa o si podem fer alguna oferta per recuperar-vos com a clients."</p>
                    )}
                    {alert.tipus_alerta === 'sow_lleial_promiscu' && (
                      <p>"Bones! Trucava perquè he vist que darrerament heu baixat una mica el volum de {alert.familia_potencial}. Hi ha hagut algun canvi en la clínica o algun preu de la competència que vulgueu que revisem per tornar a ser el vostre proveïdor principal?"</p>
                    )}
                    {alert.tipus_alerta === 'sow_promiscu_fuga' && (
                      <p>"Hola, em poso en contacte amb caràcter urgent perquè hem detectat una caiguda molt forta en {alert.familia_potencial}. No voldríem perdre la vostra confiança. Què podem fer per millorar la nostra oferta actual?"</p>
                    )}
                    {alert.tipus_alerta === 'sow_fuga_promiscu' && (
                      <p>"Bon dia! Estem molt contents de veure que heu tornat a confiar en nosaltres per a {alert.familia_potencial}. Trucava per agrair-vos la comanda i saber si podem fer res més per consolidar aquesta tornada."</p>
                    )}
                    {alert.tipus_alerta === 'sow_promiscu_lleial' && (
                      <p>"Hola! Enhorabona, hem vist que ja sou clients 100% lleials en {alert.familia_potencial}. Us truco per agrair-vos la fidelitat i confirmar que teniu les millors condicions aplicades al vostre compte."</p>
                    )}
                  </div>
                  
                  <button style={styles.callBtn} onClick={() => setModalType(null)}>
                    Registrar Trucada com a feta
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      <style>{`
        .action-btn-mail:hover {
          background-color: rgba(0, 122, 255, 0.1) !important;
          color: #007AFF !important;
          transform: scale(1.05);
        }
        .action-btn-phone:hover {
          background-color: rgba(52, 199, 89, 0.1) !important;
          color: #34C759 !important;
          transform: scale(1.05);
        }
        .btn-treat:hover {
          transform: scale(1.02);
          filter: brightness(1.15);
        }
        button {
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
          outline: none;
        }
        button:hover svg {
          transform: scale(1.1);
        }
        svg {
          transition: transform 0.2s ease-in-out;
        }
        button:active {
          transform: scale(0.94) !important;
        }
      `}</style>
    </div>
  )
}

const styles: Record<string, CSSProperties> = {
  group: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  actionBtn: {
    background: 'rgba(0,0,0,0.03)',
    border: 'none',
    color: '#3A3A3C',
    padding: '8px',
    borderRadius: 20,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    transition: 'all 0.2s ease',
  },
  treatBtn: {
    border: 'none',
    color: '#FFFFFF',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 20,
    transition: 'all 0.2s ease',
  },
  treatBtnCompact: {
    padding: '8px 18px',
    fontSize: '14px',
  },
  treatBtnLarge: {
    padding: '10px 24px',
    fontSize: '14px',
  },
  untreated: {
    background: '#000000',
  },
  treated: {
    background: '#AEAEB2',
  },
  label: {
    fontSize: '14px',
    fontWeight: 500,
  },
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.3)',
    backdropFilter: 'blur(8px)',
    WebkitBackdropFilter: 'blur(8px)',
    zIndex: 1000,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  modal: {
    background: '#FFFFFF',
    width: 500,
    maxWidth: '100%',
    borderRadius: 24,
    boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
    padding: 32,
    animation: 'fadeIn 0.3s ease-out',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 800,
    margin: 0,
    color: '#000000',
  },
  closeBtn: {
    background: '#F2F2F7',
    border: 'none',
    width: 32,
    height: 32,
    borderRadius: '50%',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#8E8E93',
  },
  modalBody: {
    display: 'flex',
    flexDirection: 'column',
  },
  bodyLabel: {
    fontSize: 13,
    fontWeight: 700,
    color: '#8E8E93',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: 8,
  },
  textContainer: {
    background: '#F9FAFB',
    border: '1px solid #E5E7EB',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    maxHeight: 300,
    overflowY: 'auto',
  },
  pre: {
    margin: 0,
    whiteSpace: 'pre-wrap',
    fontFamily: 'inherit',
    fontSize: 14,
    color: '#374151',
    lineHeight: 1.5,
  },
  copyBtn: {
    background: '#007AFF',
    color: '#FFFFFF',
    border: 'none',
    padding: '14px',
    borderRadius: 14,
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: 15,
  },
  phoneInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  phoneNum: {
    fontSize: 32,
    fontWeight: 800,
    color: '#000000',
    letterSpacing: '-0.03em',
  },
  scriptBox: {
    background: 'rgba(52, 199, 89, 0.05)',
    border: '1px solid rgba(52, 199, 89, 0.1)',
    borderRadius: 12,
    padding: 16,
    fontSize: 15,
    color: '#1C1C1E',
    fontStyle: 'italic',
    lineHeight: 1.5,
    marginBottom: 24,
  },
  callBtn: {
    background: '#34C759',
    color: '#FFFFFF',
    border: 'none',
    padding: '14px',
    borderRadius: 14,
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: 15,
  },
}

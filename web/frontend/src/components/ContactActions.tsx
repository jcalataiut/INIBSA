import type { MouseEvent, CSSProperties } from 'react'
import { MailIcon, PhoneIcon, CheckIcon, UndoIcon } from './Icons'
import type { Alerta } from '../types'

interface Props {
  alert: Alerta
  onToggleTreated: (a: Alerta) => void
  variant?: 'compact' | 'large'
}

export default function ContactActions({ alert, onToggleTreated, variant = 'compact' }: Props) {
  const isCompact = variant === 'compact'
  
  const handleMail = (e: MouseEvent) => {
    e.stopPropagation()
    window.alert(`📧 Simulant enviament de correu al client #${alert.id_cliente}...`)
  }
  
  const handlePhone = (e: MouseEvent) => {
    e.stopPropagation()
    window.alert(`📞 Simulant trucada al client #${alert.id_cliente}...`)
  }
  
  const handleTreat = (e: MouseEvent) => {
    e.stopPropagation()
    onToggleTreated(alert)
  }

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
        {alert.tractada ? <UndoIcon size={isCompact ? 16 : 20} /> : <CheckIcon size={isCompact ? 16 : 20} />}
        <span style={styles.label}>{alert.tractada ? 'Desfer' : 'Tractar'}</span>
      </button>

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
    padding: '6px 14px',
    fontSize: '13px',
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
}

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
        {alert.tractada ? (
          <>
            <UndoIcon size={isCompact ? 16 : 18} />
            {!isCompact && <span style={styles.label}>Desfer</span>}
          </>
        ) : (
          <>
            <CheckIcon size={isCompact ? 16 : 18} />
            {!isCompact && <span style={styles.label}>Tractar</span>}
          </>
        )}
      </button>

      <style>{`
        .action-btn-mail:hover {
          background-color: #F0F7FF !important;
          color: #004F9F !important;
          border-color: #004F9F !important;
          transform: translateY(-2px);
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        }
        .action-btn-phone:hover {
          background-color: #F0FDF4 !important;
          color: #059669 !important;
          border-color: #059669 !important;
          transform: translateY(-2px);
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        }
        .btn-treat:hover {
          transform: translateY(-2px);
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2), 0 4px 6px -2px rgba(0, 0, 0, 0.1) !important;
          filter: brightness(1.1);
        }
        button {
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
          outline: none;
        }
        button:hover svg {
          transform: scale(1.1);
        }
        svg {
          transition: transform 0.2s ease-in-out;
        }
        button:active {
          transform: scale(0.92) !important;
        }
      `}</style>
    </div>
  )
}

const styles: Record<string, CSSProperties> = {
  group: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  actionBtn: {
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    color: '#4B5563',
    padding: '8px',
    borderRadius: '8px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
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
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  treatBtnCompact: {
    padding: '8px',
  },
  treatBtnLarge: {
    padding: '8px 20px',
    fontSize: '14px',
  },
  untreated: {
    background: '#111827',
  },
  treated: {
    background: '#9CA3AF',
  },
  label: {
    fontSize: '13px',
  },
}

import React from 'react'
import type { Page } from '../App'
import { useTheme } from '../hooks/useTheme'
import { useDemoStore } from '../stores/demoStore'

interface NavProps {
  currentPage: Page
  onNavigate:  (page: Page) => void
}

const pages: { id: Page; label: string }[] = [
  { id: 'dashboard',     label: 'Dashboard'     },
  { id: 'simulation',    label: 'Simulation'    },
  { id: 'drilldown',     label: 'Drill-Down'    },
  { id: 'predictive',    label: 'Predictive'    },
  { id: 'forecast',      label: 'Forecast'      },
  { id: 'compensation',  label: 'Compensation'  },
  { id: 'knowledge',     label: 'Knowledge'     },
  { id: 'mobility',      label: 'Mobility'      },
  { id: 'fairness',       label: 'Fairness'      },
  { id: 'decision-room',  label: 'Decision Room' },
  { id: 'resilience',     label: 'Resilience'    },
  { id: 'strategic',      label: 'Strategic'     },
  { id: 'notifications', label: 'Alerts'        },
  { id: 'admin',         label: 'Admin'         },
  { id: 'info',          label: 'Overview'      },
]

const navStyle: React.CSSProperties = {
  backgroundColor: 'rgba(0,51,102,0.97)',
  backdropFilter:  'blur(12px)',
  height:          'var(--nav-height)',
  position:        'sticky',
  top:             0,
  zIndex:          999,
  borderBottom:    '1px solid rgba(255,255,255,0.08)',
  padding:         '0 40px',
  display:         'flex',
  alignItems:      'center',
  justifyContent:  'space-between',
}

const navLinkBase: React.CSSProperties = {
  background:      'none',
  backgroundColor: 'transparent',  // prevents white flash when deactivating in light mode
  border:          'none',
  color:           'rgba(255,255,255,0.45)',
  cursor:          'pointer',
  fontFamily:      'var(--fb)',
  fontSize:        9,
  fontWeight:      500,
  letterSpacing:   '2px',
  textTransform:   'uppercase',
  padding:         '5px 8px',
  borderRadius:    'var(--radius-sm)',
  transition:      'color 0.15s, background-color 0.15s',
  whiteSpace:      'nowrap',
}

const navLinkActive: React.CSSProperties = {
  color:           'var(--gold-light)',
  backgroundColor: 'rgba(201,168,76,0.12)',
}

export default function Nav({ currentPage, onNavigate }: NavProps) {
  const { theme, toggleTheme } = useTheme()
  const { enabled: demoEnabled } = useDemoStore()

  return (
    <nav style={navStyle}>
      {/* OPB Monogram — Fraunces, O white / PB italic gold-light */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 1, flexShrink: 0 }}>
        <span style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: '#fff', lineHeight: 1 }}>
          O
        </span>
        <em style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, fontStyle: 'italic', color: 'var(--gold-light)', lineHeight: 1 }}>
          PB
        </em>
      </div>

      {/* App title */}
      <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)' }}>
        EMPLOYEE IMPACT &amp; BUDGET OPTIMIZER
      </span>

      {/* Right cluster: nav links + demo badge + theme toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {pages.map(({ id, label }) => (
          <button
            key={id}
            style={currentPage === id ? { ...navLinkBase, ...navLinkActive } : navLinkBase}
            onClick={() => onNavigate(id)}
          >
            {label}
          </button>
        ))}

        {demoEnabled && (
          <span style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(232,196,106,0.55)', marginLeft: 12, whiteSpace: 'nowrap' }}>
            DEMO
          </span>
        )}

        <button
          style={{ ...navLinkBase, marginLeft: 8, fontSize: 14, padding: '3px 8px' }}
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? '☀' : '◑'}
        </button>
      </div>
    </nav>
  )
}

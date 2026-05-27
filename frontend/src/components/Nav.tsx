import React, { useState } from 'react'
import type { Page } from '../App'
import { useTheme } from '../hooks/useTheme'
import { useDemoStore } from '../stores/demoStore'

interface NavProps {
  currentPage: Page
  onNavigate:  (page: Page) => void
}

type NavGroupDef = {
  label: string
  pages: { id: Page; label: string }[]
}

const GROUPS: NavGroupDef[] = [
  {
    label: 'Analytics',
    pages: [
      { id: 'dashboard',  label: 'Dashboard'  },
      { id: 'drilldown',  label: 'Drill-Down' },
      { id: 'predictive', label: 'Predictive' },
      { id: 'forecast',   label: 'Forecast'   },
    ],
  },
  {
    label: 'Workforce',
    pages: [
      { id: 'compensation', label: 'Compensation' },
      { id: 'knowledge',    label: 'Knowledge'    },
      { id: 'mobility',     label: 'Mobility'     },
      { id: 'fairness',     label: 'Fairness'     },
    ],
  },
  {
    label: 'Strategy',
    pages: [
      { id: 'simulation', label: 'Simulation' },
      { id: 'strategic',  label: 'Strategic'  },
      { id: 'resilience', label: 'Resilience' },
      { id: 'ld',         label: 'L&D'        },
    ],
  },
  {
    label: 'Engagement',
    pages: [
      { id: 'pulse',     label: 'Pulse'     },
      { id: 'ohi',       label: 'OHI'       },
      { id: 'narrative', label: 'Narrative' },
    ],
  },
  {
    label: 'Operations',
    pages: [
      { id: 'decision-room', label: 'Decision Room' },
      { id: 'notifications', label: 'Alerts'        },
      { id: 'admin',         label: 'Admin'         },
      { id: 'info',          label: 'Overview'      },
    ],
  },
]

// ── Dropdown item ─────────────────────────────────────────────────────────────

function DropdownItem({
  id, label, isActive, onNavigate,
}: {
  id: Page; label: string; isActive: boolean; onNavigate: (p: Page) => void
}) {
  const [hovered, setHovered] = useState(false)

  return (
    <button
      style={{
        background:      'none',
        border:          'none',
        cursor:          'pointer',
        width:           '100%',
        textAlign:       'left' as const,
        fontFamily:      'var(--fb)',
        fontSize:        11,
        fontWeight:      isActive ? 600 : 400,
        letterSpacing:   '0.5px',
        color:           isActive ? 'var(--gold-light)' : hovered ? '#fff' : 'rgba(255,255,255,0.65)',
        backgroundColor: isActive ? 'rgba(201,168,76,0.10)' : hovered ? 'rgba(255,255,255,0.06)' : 'transparent',
        padding:         '7px 12px',
        borderRadius:    6,
        transition:      'background-color 0.1s, color 0.1s',
        whiteSpace:      'nowrap' as const,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onNavigate(id)}
    >
      {label}
    </button>
  )
}

// ── Group button + dropdown ───────────────────────────────────────────────────

function GroupMenu({
  group, currentPage, onNavigate,
}: {
  group: NavGroupDef; currentPage: Page; onNavigate: (p: Page) => void
}) {
  const [open, setOpen] = useState(false)
  const isActive = group.pages.some(p => p.id === currentPage)

  const btnStyle: React.CSSProperties = {
    background:      'none',
    border:          'none',
    cursor:          'pointer',
    fontFamily:      'var(--fb)',
    fontSize:        9,
    fontWeight:      500,
    letterSpacing:   '2px',
    textTransform:   'uppercase' as const,
    padding:         '5px 10px',
    borderRadius:    'var(--radius-sm)',
    color:           isActive ? 'var(--gold-light)' : open ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.45)',
    backgroundColor: isActive ? 'rgba(201,168,76,0.12)' : open ? 'rgba(255,255,255,0.05)' : 'transparent',
    display:         'flex',
    alignItems:      'center',
    gap:             5,
    transition:      'color 0.15s, background-color 0.15s',
    whiteSpace:      'nowrap' as const,
  }

  return (
    <div
      style={{
        position:  'relative',
        alignSelf: 'stretch',
        display:   'flex',
        alignItems:'center',
      }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button style={btnStyle}>
        {group.label}
        <span style={{
          fontSize:   7,
          opacity:    0.55,
          display:    'inline-block',
          transform:  open ? 'rotate(180deg)' : 'none',
          transition: 'transform 0.15s',
        }}>
          ▾
        </span>
      </button>

      {open && (
        <div style={{
          position:        'absolute',
          top:             'calc(100% + 1px)',
          left:            0,
          backgroundColor: 'rgba(0,32,76,0.98)',
          backdropFilter:  'blur(16px)',
          border:          '1px solid rgba(255,255,255,0.1)',
          borderRadius:    'var(--radius-md)',
          boxShadow:       '0 8px 32px rgba(0,0,0,0.45)',
          padding:         '6px',
          minWidth:        156,
          zIndex:          1000,
          display:         'flex',
          flexDirection:   'column' as const,
          gap:             2,
        }}>
          {group.pages.map(p => (
            <DropdownItem
              key={p.id}
              id={p.id}
              label={p.label}
              isActive={currentPage === p.id}
              onNavigate={(page) => { onNavigate(page); setOpen(false) }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Nav ───────────────────────────────────────────────────────────────────────

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

export default function Nav({ currentPage, onNavigate }: NavProps) {
  const { theme, toggleTheme } = useTheme()
  const { enabled: demoEnabled } = useDemoStore()

  return (
    <nav style={navStyle}>
      {/* OPB Monogram */}
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

      {/* Right cluster */}
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 2 }}>
        {GROUPS.map(group => (
          <GroupMenu
            key={group.label}
            group={group}
            currentPage={currentPage}
            onNavigate={onNavigate}
          />
        ))}

        {demoEnabled && (
          <span style={{
            fontFamily:  'var(--fb)',
            fontSize:    8,
            letterSpacing: '2px',
            textTransform: 'uppercase',
            color:       'rgba(232,196,106,0.55)',
            marginLeft:  12,
            whiteSpace:  'nowrap',
            alignSelf:   'center',
          }}>
            DEMO
          </span>
        )}

        <button
          style={{
            background:      'none',
            backgroundColor: 'transparent',
            border:          'none',
            color:           'rgba(255,255,255,0.45)',
            cursor:          'pointer',
            fontSize:        14,
            padding:         '3px 8px',
            borderRadius:    'var(--radius-sm)',
            marginLeft:      8,
            alignSelf:       'center',
          }}
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? '☀' : '◑'}
        </button>
      </div>
    </nav>
  )
}

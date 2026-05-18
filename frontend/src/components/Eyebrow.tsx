// UI_Decisions.md §9: Eyebrow component.
// Renders a gold rule + uppercase label. Props: children, light?.
// Labels are max 4 words. No leading numbers.

import React from 'react'

interface EyebrowProps {
  children: React.ReactNode
  light?:   boolean
}

const base: React.CSSProperties = {
  display:       'inline-flex',
  alignItems:    'center',
  gap:           8,
  fontFamily:    'var(--fb)',
  fontSize:      9,
  fontWeight:    700,
  letterSpacing: '4px',
  textTransform: 'uppercase',
  marginBottom:  10,
}

const lineBase: React.CSSProperties = {
  width:      24,
  height:     1,
  flexShrink: 0,
}

export default function Eyebrow({ children, light = false }: EyebrowProps) {
  const color = light ? 'var(--gold-light)' : 'var(--gold)'
  return (
    <div style={{ ...base, color }}>
      <div style={{ ...lineBase, background: color }} />
      {children}
    </div>
  )
}

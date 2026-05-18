import React from 'react'

const month = new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' }).toUpperCase()

const style: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  padding:         '20px 48px',
  display:         'flex',
  justifyContent:  'space-between',
  alignItems:      'center',
  fontFamily:      'var(--fb)',
  fontSize:        9,
  letterSpacing:   '3px',
  textTransform:   'uppercase',
  color:           'rgba(255,255,255,0.35)',
  marginTop:       64,
}

export default function Footer() {
  return (
    <footer style={style}>
      <span>OPB · OCTAVIO PÉREZ BRAVO · EIBO</span>
      <span>{month}</span>
    </footer>
  )
}

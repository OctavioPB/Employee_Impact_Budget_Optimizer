// UI_Decisions.md §10: Theme stored in localStorage under 'spb-theme'.
// Applied by setting data-theme on document.documentElement.
// Defaults to light — OS preference is intentionally ignored.

import { useState, useEffect } from 'react'

export type Theme = 'light' | 'dark'

function getInitialTheme(): Theme {
  const stored = localStorage.getItem('spb-theme')
  return stored === 'dark' ? 'dark' : 'light'
}

function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme)
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem('spb-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'))

  return { theme, toggleTheme }
}

// UI_Decisions.md §11: Zustand — no Provider, no reducers.
// Demo settings persist across page navigations within the session.

import { create } from 'zustand'

export type Scenario = 'A' | 'B' | 'C'
export type OrgSize  = 'small' | 'medium' | 'large'

interface DemoState {
  enabled:     boolean
  scenario:    Scenario
  size:        OrgSize
  setEnabled:  (v: boolean)   => void
  setScenario: (v: Scenario) => void
  setSize:     (v: OrgSize)  => void
}

export const useDemoStore = create<DemoState>((set) => ({
  enabled:     true,
  scenario:    'A',
  size:        'small',
  setEnabled:  (enabled)  => set({ enabled }),
  setScenario: (scenario) => set({ scenario }),
  setSize:     (size)     => set({ size }),
}))

// UI_Decisions.md §7: Page routing — single useState<Page>, no router library.
// Adding a new page: (1) add to Page union, (2) add case to renderPage,
// (3) add entry to Nav's pages array.

import { useState } from 'react'
import Nav             from './components/Nav'
import Footer          from './components/Footer'
import InfoPage        from './pages/InfoPage'
import DashboardPage   from './pages/DashboardPage'
import SimulationPage  from './pages/SimulationPage'
import DrillDownPage   from './pages/DrillDownPage'
import PredictivePage  from './pages/PredictivePage'
import StrategicPage   from './pages/StrategicPage'
import NotificationsPage from './pages/NotificationsPage'
import AdminPage       from './pages/AdminPage'

export type Page =
  | 'info'
  | 'dashboard'
  | 'simulation'
  | 'drilldown'
  | 'predictive'
  | 'strategic'
  | 'notifications'
  | 'admin'

export default function App() {
  const [page, setPage] = useState<Page>('info')

  const renderPage = () => {
    switch (page) {
      case 'info':          return <InfoPage onLaunch={() => setPage('dashboard')} />
      case 'dashboard':     return <DashboardPage />
      case 'simulation':    return <SimulationPage />
      case 'drilldown':     return <DrillDownPage />
      case 'predictive':    return <PredictivePage />
      case 'strategic':     return <StrategicPage />
      case 'notifications': return <NotificationsPage />
      case 'admin':         return <AdminPage />
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--light)' }}>
      {/* Nav is hidden on the Info page — it has its own dedicated header */}
      {page !== 'info' && <Nav currentPage={page} onNavigate={setPage} />}
      <main style={{ flex: 1 }}>
        {renderPage()}
      </main>
      <Footer />
    </div>
  )
}

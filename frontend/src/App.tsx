import { useState } from 'react'
import Nav             from './components/Nav'
import Footer          from './components/Footer'
import InfoPage        from './pages/InfoPage'
import DashboardPage   from './pages/DashboardPage'
import SimulationPage  from './pages/SimulationPage'
import DrillDownPage   from './pages/DrillDownPage'
import ForecastPage    from './pages/ForecastPage'
import PredictivePage  from './pages/PredictivePage'
import StrategicPage   from './pages/StrategicPage'
import NotificationsPage from './pages/NotificationsPage'
import AdminPage       from './pages/AdminPage'
import CompensationPage from './pages/CompensationPage'
import KnowledgePage    from './pages/KnowledgePage'
import MobilityPage     from './pages/MobilityPage'
import FairnessPage      from './pages/FairnessPage'
import DecisionRoomPage  from './pages/DecisionRoomPage'
import ResiliencePage    from './pages/ResiliencePage'
import LDPage            from './pages/LDPage'
import NarrativePage     from './pages/NarrativePage'

export type Page =
  | 'info'
  | 'dashboard'
  | 'simulation'
  | 'drilldown'
  | 'predictive'
  | 'forecast'
  | 'strategic'
  | 'notifications'
  | 'admin'
  | 'compensation'
  | 'knowledge'
  | 'mobility'
  | 'fairness'
  | 'decision-room'
  | 'resilience'
  | 'ld'
  | 'narrative'

export default function App() {
  const [page, setPage] = useState<Page>('info')

  const renderPage = () => {
    switch (page) {
      case 'info':          return <InfoPage onLaunch={() => setPage('dashboard')} />
      case 'dashboard':     return <DashboardPage />
      case 'simulation':    return <SimulationPage />
      case 'drilldown':     return <DrillDownPage />
      case 'predictive':    return <PredictivePage />
      case 'forecast':      return <ForecastPage />
      case 'strategic':     return <StrategicPage />
      case 'notifications': return <NotificationsPage />
      case 'admin':         return <AdminPage />
      case 'compensation':  return <CompensationPage />
      case 'knowledge':     return <KnowledgePage />
      case 'mobility':      return <MobilityPage />
      case 'fairness':       return <FairnessPage />
      case 'decision-room':  return <DecisionRoomPage />
      case 'resilience':     return <ResiliencePage />
      case 'ld':             return <LDPage />
      case 'narrative':      return <NarrativePage />
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

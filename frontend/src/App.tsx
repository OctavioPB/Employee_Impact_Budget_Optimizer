import { Suspense, lazy, useState } from 'react'
import Nav             from './components/Nav'
import Footer          from './components/Footer'
import InfoPage        from './pages/InfoPage'
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const SimulationPage = lazy(() => import('./pages/SimulationPage'))
const DrillDownPage = lazy(() => import('./pages/DrillDownPage'))
const ForecastPage = lazy(() => import('./pages/ForecastPage'))
const PredictivePage = lazy(() => import('./pages/PredictivePage'))
const StrategicPage = lazy(() => import('./pages/StrategicPage'))
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const CompensationPage = lazy(() => import('./pages/CompensationPage'))
const KnowledgePage = lazy(() => import('./pages/KnowledgePage'))
const MobilityPage = lazy(() => import('./pages/MobilityPage'))
const FairnessPage = lazy(() => import('./pages/FairnessPage'))
const DecisionRoomPage = lazy(() => import('./pages/DecisionRoomPage'))
const ResiliencePage = lazy(() => import('./pages/ResiliencePage'))
const LDPage = lazy(() => import('./pages/LDPage'))
const NarrativePage = lazy(() => import('./pages/NarrativePage'))
const OHIPage = lazy(() => import('./pages/OHIPage'))
const PulsePage = lazy(() => import('./pages/PulsePage'))

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
  | 'ohi'
  | 'pulse'

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
      case 'ohi':            return <OHIPage />
      case 'pulse':          return <PulsePage />
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--light)' }}>
      {/* Nav is hidden on the Info page — it has its own dedicated header */}
      {page !== 'info' && <Nav currentPage={page} onNavigate={setPage} />}
      <main style={{ flex: 1 }}>
        <Suspense fallback={<div style={{ padding: 24 }}>Loading…</div>}>
          {renderPage()}
        </Suspense>
      </main>
      <Footer />
    </div>
  )
}

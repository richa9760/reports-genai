import { useEffect, useState } from 'react'
import { getHealth } from './api/reports'
import ManagerReports from './components/ManagerReports'
import ReportDetail from './components/ReportDetail'
import ReportForm from './components/ReportForm'
import ReportList from './components/ReportList'
import LLMOpsDashboard from './pages/LLMOpsDashboard'

const STATUS_LABELS = {
  ok: 'Connected',
  error: 'Disconnected',
  loading: 'Checking...',
}

const VIEWS = {
  create: { label: 'Create Report', path: '/' },
  list: { label: 'My Reports', path: '/reports' },
  manager: { label: 'Manager Reports', path: '/manager' },
  llmops: { label: 'LLMOps', path: '/llmops' },
}

function viewFromPath(pathname) {
  if (pathname === '/llmops') return 'llmops'
  if (pathname === '/manager') return 'manager'
  if (pathname === '/reports') return 'list'
  return 'create'
}

function App() {
  const [status, setStatus] = useState('loading')
  const [view, setView] = useState(() => viewFromPath(window.location.pathname))
  const [editingId, setEditingId] = useState(null)
  const [viewingId, setViewingId] = useState(null)

  useEffect(() => {
    getHealth()
      .then((data) => setStatus(data.status === 'ok' ? 'ok' : 'error'))
      .catch(() => setStatus('error'))
  }, [])

  useEffect(() => {
    function onPop() {
      setEditingId(null)
      setViewingId(null)
      setView(viewFromPath(window.location.pathname))
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  function navigate(target) {
    setEditingId(null)
    setViewingId(null)
    setView(target)
    window.history.pushState(null, '', VIEWS[target].path)
  }

  const showCreate = () => navigate('create')
  const showList = () => navigate('list')
  const showManager = () => navigate('manager')
  const showLLMOps = () => navigate('llmops')

  function showEdit(id) {
    setViewingId(null)
    setEditingId(id)
    setView('create')
    window.history.pushState(null, '', VIEWS.create.path)
  }

  function showView(id) {
    setEditingId(null)
    setViewingId(id)
    setView('detail')
  }

  const HANDLERS = { create: showCreate, list: showList, manager: showManager, llmops: showLLMOps }

  return (
    <div className="app">
      <header className="header">
        <h1>Reports Application</h1>
        <p className="status">
          Backend Status:{' '}
          <span className={`badge badge--${status}`}>{STATUS_LABELS[status]}</span>
        </p>

        <nav className="nav">
          {Object.entries(VIEWS).map(([key, { label }]) => (
            <button
              key={key}
              type="button"
              className={`nav__link ${view === key ? 'nav__link--active' : ''}`}
              aria-current={view === key ? 'page' : undefined}
              onClick={HANDLERS[key]}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main className="content">
        {view === 'create' && (
          <ReportForm
            key={editingId ?? 'new'}
            reportId={editingId}
            onSaved={showList}
            onCancel={editingId ? showList : undefined}
          />
        )}

        {view === 'list' && <ReportList onEdit={showEdit} onView={showView} />}

        {view === 'detail' && (
          <ReportDetail reportId={viewingId} onEdit={showEdit} onBack={showList} />
        )}

        {view === 'manager' && <ManagerReports />}

        {view === 'llmops' && <LLMOpsDashboard />}
      </main>
    </div>
  )
}

export default App
import { useEffect, useState } from 'react'
import { deleteReport, getReports } from '../api/reports'
import { MONTHS } from '../constants'
import { EmptyMessage, ErrorMessage, LoadingMessage } from './Feedback'

export default function ReportList({ onEdit, onView }) {
  const [reports, setReports] = useState([])
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    let active = true

    getReports()
      .then((data) => {
        if (!active) return
        setReports(data)
        setState('ready')
      })
      .catch(() => {
        if (!active) return
        setError('Unable to load reports. Please try again.')
        setState('error')
      })

    return () => {
      active = false
    }
  }, [])

  async function handleDelete(id) {
    setDeletingId(id)
    try {
      await deleteReport(id)
      setReports((previous) => previous.filter((report) => report.id !== id))
    } catch {
      setError('Unable to delete the report. Please try again.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="panel">
      <h2>My Reports</h2>

      {state === 'loading' && <LoadingMessage>Loading reports...</LoadingMessage>}
      {state === 'error' && <ErrorMessage>{error}</ErrorMessage>}
      {state === 'ready' && reports.length === 0 && (
        <EmptyMessage>No reports yet. Create your first monthly report.</EmptyMessage>
      )}

      {state === 'ready' && reports.length > 0 && (
        <>
          {error && <ErrorMessage>{error}</ErrorMessage>}
          <table className="table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Project</th>
                <th>Business Group</th>
                <th>Month</th>
                <th>Year</th>
                <th>Summary</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id}>
                  <td>{report.employee_name}</td>
                  <td>{report.project_name}</td>
                  <td>{report.business_group}</td>
                  <td>{MONTHS[report.month - 1] ?? report.month}</td>
                  <td>{report.year}</td>
                  <td className="table__summary">{report.summary || '—'}</td>
                  <td className="table__actions">
                    <button type="button" className="button button--small" onClick={() => onView(report.id)}>
                      View
                    </button>
                    <button type="button" className="button button--small" onClick={() => onEdit(report.id)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className="button button--small button--danger"
                      onClick={() => handleDelete(report.id)}
                      disabled={deletingId === report.id}
                    >
                      {deletingId === report.id ? 'Deleting...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  )
}

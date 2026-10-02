import { useEffect, useState } from 'react'
import { getReport } from '../api/reports'
import { ITEM_SECTIONS, MONTHS } from '../constants'
import { ErrorMessage, LoadingMessage } from './Feedback'

export default function ReportDetail({ reportId, onEdit, onBack }) {
  const [report, setReport] = useState(null)
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    getReport(reportId)
      .then((data) => {
        if (!active) return
        setReport(data)
        setState('ready')
      })
      .catch(() => {
        if (!active) return
        setError('Unable to load the report. Please try again.')
        setState('error')
      })

    return () => {
      active = false
    }
  }, [reportId])

  if (state === 'loading') return <LoadingMessage>Loading report...</LoadingMessage>
  if (state === 'error') return <ErrorMessage>{error}</ErrorMessage>

  const items = report.items ?? {}

  return (
    <section className="panel">
      <h2>
        {report.employee_name} — {MONTHS[report.month - 1] ?? report.month} {report.year}
      </h2>

      <dl className="detail">
        <div>
          <dt>Employee</dt>
          <dd>{report.employee_name}</dd>
        </div>
        <div>
          <dt>Project</dt>
          <dd>{report.project_name}</dd>
        </div>
        <div>
          <dt>Business Group</dt>
          <dd>{report.business_group}</dd>
        </div>
        <div>
          <dt>Month</dt>
          <dd>{MONTHS[report.month - 1] ?? report.month}</dd>
        </div>
        <div>
          <dt>Year</dt>
          <dd>{report.year}</dd>
        </div>
      </dl>

      <h3>Monthly Summary</h3>
      <p className="detail__summary">{report.summary || 'No summary provided.'}</p>

      {ITEM_SECTIONS.map((section) => {
        const entries = items[section.type] ?? []
        return (
          <div key={section.type} className="detail__group">
            <h3>{section.label}</h3>
            {entries.length === 0 ? (
              <p className="section__empty">No entries.</p>
            ) : (
              <ul className="detail__list">
                {entries.map((item) => (
                  <li key={item.id}>{item.content}</li>
                ))}
              </ul>
            )}
          </div>
        )
      })}

      <div className="actions">
        <button type="button" className="button" onClick={() => onEdit(report.id)}>
          Edit Report
        </button>
        <button type="button" className="button button--secondary" onClick={onBack}>
          Back to My Reports
        </button>
      </div>
    </section>
  )
}

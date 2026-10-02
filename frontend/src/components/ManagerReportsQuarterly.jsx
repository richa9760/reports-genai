import { useState } from 'react'
import { generateQuarterlyManagerReport, getReport, getReports } from '../api/reports'
import { MONTHS, QUARTERS, QUARTER_MONTHS, yearOptions } from '../constants'
import { EmptyMessage, ErrorMessage, LoadingMessage } from './Feedback'
import ManagerReportDetail from './ManagerReportDetail'

export default function ManagerReportsQuarterly() {
  const [quarter, setQuarter] = useState('3')
  const [year, setYear] = useState(() => String(new Date().getFullYear()))

  const [loadState, setLoadState] = useState('idle')
  const [loadError, setLoadError] = useState('')
  const [reports, setReports] = useState([])

  const [generateState, setGenerateState] = useState('idle')
  const [generateError, setGenerateError] = useState('')
  const [teamReport, setTeamReport] = useState('')

  const [detail, setDetail] = useState(null)
  const [detailState, setDetailState] = useState('idle')

  const isLoading = loadState === 'loading'
  const isGenerating = generateState === 'generating'

  async function loadReports() {
    setLoadState('loading')
    setLoadError('')
    setTeamReport('')
    setGenerateError('')
    setDetail(null)

    try {
      const months = QUARTER_MONTHS[Number(quarter)]
      const results = await Promise.all(
        months.map((month) => getReports({ month, year: Number(year) }))
      )
      const merged = results
        .flat()
        .sort((a, b) => a.month - b.month || a.employee_name.localeCompare(b.employee_name))
      setReports(merged)
      setLoadState('ready')
    } catch {
      setLoadError('Unable to load employee reports. Please try again.')
      setLoadState('error')
    }
  }

  async function generate() {
    setGenerateState('generating')
    setGenerateError('')
    setTeamReport('')

    try {
      const data = await generateQuarterlyManagerReport({ quarter: Number(quarter), year: Number(year) })
      setTeamReport(data.report ?? '')
      setGenerateState('ready')
    } catch (error) {
      setGenerateState('error')
      setGenerateError(error.message || 'Unable to generate the quarterly team report. Please try again.')
    }
  }

  async function toggleDetail(report) {
    if (detail && detail.id === report.id) {
      setDetail(null)
      return
    }

    setDetailState('loading')
    setDetail(null)
    try {
      const data = await getReport(report.id)
      setDetail(data)
      setDetailState('ready')
    } catch {
      setDetailState('error')
      setGenerateError('Unable to load the report details. Please try again.')
    }
  }

  const quarterLabel = QUARTERS.find((entry) => entry.value === Number(quarter))?.label ?? quarter
  const filteredLabel = `${quarterLabel} ${year}`

  return (
    <>
      <div className="field-row">
        <div className="field">
          <label htmlFor="managerYear">Year</label>
          <select
            id="managerYear"
            value={year}
            disabled={isLoading || isGenerating}
            onChange={(event) => setYear(event.target.value)}
          >
            {yearOptions().map((entry) => (
              <option key={entry} value={entry}>
                {entry}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="managerQuarter">Quarter</label>
          <select
            id="managerQuarter"
            value={quarter}
            disabled={isLoading || isGenerating}
            onChange={(event) => setQuarter(event.target.value)}
          >
            {QUARTERS.map((entry) => (
              <option key={entry.value} value={entry.value}>
                {entry.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="actions">
        <button type="button" className="button" onClick={loadReports} disabled={isLoading || isGenerating}>
          {isLoading ? 'Loading Reports...' : 'Load Reports'}
        </button>
      </div>

      {loadError && <ErrorMessage>{loadError}</ErrorMessage>}

      <div className="actions">
        <button
          type="button"
          className="button"
          onClick={generate}
          disabled={loadState !== 'ready' || reports.length === 0 || isGenerating}
        >
          {isGenerating ? 'Generating Quarterly Team Report...' : 'Generate Quarterly Team Report'}
        </button>
      </div>
      {generateError && <ErrorMessage>{generateError}</ErrorMessage>}

      <h3>Employee Reports</h3>
      {loadState === 'loading' && <LoadingMessage>Loading employee reports...</LoadingMessage>}
      {loadState === 'ready' && reports.length === 0 && (
        <EmptyMessage>No employee reports were submitted for {filteredLabel}.</EmptyMessage>
      )}
      {loadState === 'ready' && reports.length > 0 && (
        <>
          <table className="table">
            <thead>
              <tr>
                <th>Month</th>
                <th>Employee</th>
                <th>Project</th>
                <th>Business Group</th>
                <th>Summary</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id}>
                  <td>{MONTHS[report.month - 1] ?? report.month}</td>
                  <td>{report.employee_name}</td>
                  <td>{report.project_name}</td>
                  <td>{report.business_group}</td>
                  <td className="table__summary">{report.summary}</td>
                  <td className="table__actions">
                    <button
                      type="button"
                      className="button button--small button--secondary"
                      onClick={() => toggleDetail(report)}
                    >
                      {detail && detail.id === report.id ? 'Hide' : 'View'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {detailState === 'loading' && <LoadingMessage>Loading report details...</LoadingMessage>}
          {detailState === 'ready' && <ManagerReportDetail detail={detail} />}
        </>
      )}

      {teamReport && (
        <>
          <h3>Generated Quarterly Team Report</h3>
          <div className="manager-report">{teamReport}</div>
        </>
      )}
    </>
  )
}
import { useState } from 'react'
import { generateManagerReport, getReport, getReports } from '../api/reports'
import { MONTHS, yearOptions } from '../constants'
import { EmptyMessage, ErrorMessage, LoadingMessage } from './Feedback'
import ManagerReportDetail from './ManagerReportDetail'

export default function ManagerReportsMonthly() {
  const [month, setMonth] = useState(() => String(new Date().getMonth() + 1))
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
      const data = await getReports({ month: Number(month), year: Number(year) })
      setReports(data)
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
      const data = await generateManagerReport({ month: Number(month), year: Number(year) })
      setTeamReport(data.report ?? '')
      setGenerateState('ready')
    } catch (error) {
      setGenerateState('error')
      setGenerateError(error.message || 'Unable to generate the team report. Please try again.')
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

  const filteredLabel = `${MONTHS[Number(month) - 1] ?? month} ${year}`

  return (
    <>
      <div className="field-row">
        <div className="field">
          <label htmlFor="managerMonth">Month</label>
          <select
            id="managerMonth"
            value={month}
            disabled={isLoading || isGenerating}
            onChange={(event) => setMonth(event.target.value)}
          >
            {MONTHS.map((name, index) => (
              <option key={name} value={index + 1}>
                {name}
              </option>
            ))}
          </select>
        </div>

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
          {isGenerating ? 'Generating Monthly Team Report...' : 'Generate Monthly Team Report'}
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
                <th>Employee</th>
                <th>Project</th>
                <th>Business Group</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id}>
                  <td>{report.employee_name}</td>
                  <td>{report.project_name}</td>
                  <td>{report.business_group}</td>
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
          <h3>Generated Monthly Team Report</h3>
          <div className="manager-report">{teamReport}</div>
        </>
      )}
    </>
  )
}
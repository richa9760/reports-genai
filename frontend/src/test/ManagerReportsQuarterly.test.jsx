import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ManagerReportsQuarterly from '../components/ManagerReportsQuarterly'

function jsonResponse(status, body) {
  return { ok: status < 400, status, text: async () => JSON.stringify(body) }
}

function routeFetch(routes) {
  return vi.fn(async (url, options = {}) => {
    const method = options.method ?? 'GET'
    const handler = routes[`${method} ${url}`]
    if (!handler) return jsonResponse(404, { detail: 'Not found.' })
    return typeof handler === 'function' ? handler() : handler
  })
}

const JULY = [
  { id: 1, employee_name: 'Ada Lovelace', project_name: 'Analytics', business_group: 'Research', month: 7, year: 2026, summary: 'July: analytics pipelines.' },
]

const AUGUST = [
  { id: 2, employee_name: 'Richa Verma', project_name: 'AI Platform', business_group: 'DC Engineering', month: 8, year: 2026, summary: 'August: shipped auth.' },
]

const SEPTEMBER = [
  { id: 3, employee_name: 'John Smith', project_name: 'Automation', business_group: 'Cloud', month: 9, year: 2026, summary: '' },
]

function routesFor(year) {
  return {
    [`GET http://localhost:8000/api/reports/?month=7&year=${year}`]: jsonResponse(200, JULY),
    [`GET http://localhost:8000/api/reports/?month=8&year=${year}`]: jsonResponse(200, AUGUST),
    [`GET http://localhost:8000/api/reports/?month=9&year=${year}`]: jsonResponse(200, SEPTEMBER),
    [`POST http://localhost:8000/api/manager-reports/quarterly/generate/`]: jsonResponse(200, {
      year,
      quarter: 3,
      months: [7, 8, 9],
      report_count: 3,
      report: 'Q3 highlights: analytics, auth and automation.',
    }),
  }
}

describe('ManagerReportsQuarterly', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders year and quarter selectors and the action buttons', () => {
    vi.stubGlobal('fetch', routeFetch({}))
    render(<ManagerReportsQuarterly />)

    expect(screen.getByLabelText('Year')).toBeInTheDocument()
    expect(screen.getByLabelText('Quarter')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Load Reports' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate Quarterly Team Report' })).toBeDisabled()
  })

  it('loads reports across the three quarter months into a table', async () => {
    const fetchMock = routeFetch(routesFor(2026))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReportsQuarterly />)

    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.selectOptions(screen.getByLabelText('Quarter'), '3')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))

    await waitFor(() => expect(screen.getByText('Richa Verma')).toBeInTheDocument())

    expect(screen.getByText('July')).toBeInTheDocument()
    expect(screen.getByText('August')).toBeInTheDocument()
    expect(screen.getByText('September')).toBeInTheDocument()
    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('Research')).toBeInTheDocument()
    expect(screen.getByText('John Smith')).toBeInTheDocument()
    expect(screen.getByText('Automation')).toBeInTheDocument()
    expect(screen.getByText('August: shipped auth.')).toBeInTheDocument()

    const loadCalls = fetchMock.mock.calls.filter(([url]) => url.includes('/api/reports/'))
    expect(loadCalls).toHaveLength(3)
    expect(loadCalls.map(([url]) => url).sort()).toEqual([
      'http://localhost:8000/api/reports/?month=7&year=2026',
      'http://localhost:8000/api/reports/?month=8&year=2026',
      'http://localhost:8000/api/reports/?month=9&year=2026',
    ])
  })

  it('shows an empty message when the quarter has no reports', async () => {
    const fetchMock = routeFetch({
      'GET http://localhost:8000/api/reports/?month=1&year=2026': jsonResponse(200, []),
      'GET http://localhost:8000/api/reports/?month=2&year=2026': jsonResponse(200, []),
      'GET http://localhost:8000/api/reports/?month=3&year=2026': jsonResponse(200, []),
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReportsQuarterly />)

    await user.selectOptions(screen.getByLabelText('Quarter'), '1')
    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))

    expect(
      await screen.findByText('No employee reports were submitted for Q1 2026.')
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate Quarterly Team Report' })).toBeDisabled()
  })

  it('delegates to the correct month list URLs per quarter', async () => {
    const fetchMock = routeFetch({
      'GET http://localhost:8000/api/reports/?month=10&year=2026': jsonResponse(200, []),
      'GET http://localhost:8000/api/reports/?month=11&year=2026': jsonResponse(200, []),
      'GET http://localhost:8000/api/reports/?month=12&year=2026': jsonResponse(200, []),
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReportsQuarterly />)

    await user.selectOptions(screen.getByLabelText('Quarter'), '4')
    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))

    await waitFor(() =>
      expect(
        screen.getByText('No employee reports were submitted for Q4 2026.')
      ).toBeInTheDocument()
    )

    const loadCalls = fetchMock.mock.calls
      .filter(([url]) => url.includes('/api/reports/'))
      .map(([url]) => url)
      .sort()
    expect(loadCalls).toEqual([
      'http://localhost:8000/api/reports/?month=10&year=2026',
      'http://localhost:8000/api/reports/?month=11&year=2026',
      'http://localhost:8000/api/reports/?month=12&year=2026',
    ])
  })

  it('generates a quarterly team report', async () => {
    const fetchMock = routeFetch(routesFor(2026))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReportsQuarterly />)

    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.selectOptions(screen.getByLabelText('Quarter'), '3')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))
    await waitFor(() => expect(screen.getByText('Richa Verma')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Generate Quarterly Team Report' }))

    expect(
      await screen.findByText('Q3 highlights: analytics, auth and automation.')
    ).toBeInTheDocument()
    expect(screen.getByText('Generated Quarterly Team Report')).toBeInTheDocument()

    const generateCall = fetchMock.mock.calls.find(([url]) => url.includes('/quarterly/generate/'))
    expect(generateCall[1].method).toBe('POST')
    expect(JSON.parse(generateCall[1].body)).toEqual({ quarter: 3, year: 2026 })
  })

  it('shows an error message when generation fails', async () => {
    const fetchMock = routeFetch({
      ...routesFor(2026),
      'POST http://localhost:8000/api/manager-reports/quarterly/generate/': jsonResponse(502, {
        detail: 'The AI team report could not be generated. Please try again.',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReportsQuarterly />)

    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.selectOptions(screen.getByLabelText('Quarter'), '3')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))
    await waitFor(() => expect(screen.getByText('Richa Verma')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Generate Quarterly Team Report' }))

    expect(
      await screen.findByText('The AI team report could not be generated. Please try again.')
    ).toBeInTheDocument()
  })

  it('loads and shows the details of an underlying report', async () => {
    const fetchMock = routeFetch({
      ...routesFor(2026),
      'GET http://localhost:8000/api/reports/2/': jsonResponse(200, {
        ...AUGUST[0],
        items: {
          TASK: [{ id: 10, item_type: 'TASK', content: 'Built the login flow' }],
          ACHIEVEMENT: [],
          COURSE: [],
          HOLIDAY: [],
          IDEA: [],
        },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReportsQuarterly />)

    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.selectOptions(screen.getByLabelText('Quarter'), '3')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))
    await waitFor(() => expect(screen.getByText('Richa Verma')).toBeInTheDocument())

    await user.click(screen.getAllByRole('button', { name: 'View' })[1])

    expect(await screen.findByText('Richa Verma — August 2026')).toBeInTheDocument()
    expect(screen.getByText('Built the login flow')).toBeInTheDocument()
  })
})
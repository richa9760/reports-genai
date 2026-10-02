import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ManagerReports from '../components/ManagerReports'

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

const SEPT_REPORTS = [
  {
    id: 1,
    employee_name: 'Richa Verma',
    project_name: 'AI Platform',
    business_group: 'DC Engineering',
    month: 9,
    year: 2026,
    summary: 'Shipped auth.',
  },
  {
    id: 2,
    employee_name: 'John Smith',
    project_name: 'Automation',
    business_group: 'Cloud',
    month: 9,
    year: 2026,
    summary: '',
  },
]

function routesFor(month, year) {
  const q = `month=${month}&year=${year}`
  return {
    [`GET http://localhost:8000/api/reports/?${q}`]: jsonResponse(200, SEPT_REPORTS),
    'POST http://localhost:8000/api/manager-reports/monthly/generate/': jsonResponse(200, {
      month,
      year,
      reports_count: 2,
      report: 'During September 2026, the team worked across AI Platform and Automation.',
    }),
  }
}

describe('ManagerReports', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the month/year selectors and both buttons', () => {
    vi.stubGlobal('fetch', routeFetch({}))
    render(<ManagerReports />)

    expect(screen.getByRole('heading', { name: 'Manager Reports' })).toBeInTheDocument()
    expect(screen.getByLabelText('Month')).toBeInTheDocument()
    expect(screen.getByLabelText('Year')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Load Reports' })).toBeInTheDocument()
  })

  it('loads employee reports filtered by month and year', async () => {
    const fetchMock = routeFetch(routesFor(9, 2026))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReports />)

    await user.selectOptions(screen.getByLabelText('Month'), '9')
    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))

    await waitFor(() => expect(screen.getByText('Richa Verma')).toBeInTheDocument())

    expect(screen.getByText('AI Platform')).toBeInTheDocument()
    expect(screen.getByText('DC Engineering')).toBeInTheDocument()
    expect(screen.getByText('John Smith')).toBeInTheDocument()
    expect(screen.getByText('Automation')).toBeInTheDocument()
    expect(screen.getByText('Cloud')).toBeInTheDocument()

    const loadCall = fetchMock.mock.calls.find(([url]) => url.includes('/api/reports/'))
    expect(loadCall[0]).toContain('month=9&year=2026')
  })

  it('shows an empty message when no reports exist for the selected month/year', async () => {
    const fetchMock = routeFetch({
      'GET http://localhost:8000/api/reports/?month=9&year=2026': jsonResponse(200, []),
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReports />)

    await user.selectOptions(screen.getByLabelText('Month'), '9')
    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))

    expect(
      await screen.findByText('No employee reports were submitted for September 2026.')
    ).toBeInTheDocument()
  })

  it('disables the generate button until reports are loaded', async () => {
    vi.stubGlobal('fetch', routeFetch({}))
    render(<ManagerReports />)

    expect(screen.getByRole('button', { name: 'Generate Monthly Team Report' })).toBeDisabled()
  })

  it('generates a monthly team report from the loaded reports', async () => {
    const fetchMock = routeFetch(routesFor(9, 2026))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReports />)

    await user.selectOptions(screen.getByLabelText('Month'), '9')
    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))
    await waitFor(() => expect(screen.getByText('Richa Verma')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Generate Monthly Team Report' }))

    expect(
      await screen.findByText(
        'During September 2026, the team worked across AI Platform and Automation.'
      )
    ).toBeInTheDocument()

    const generateCall = fetchMock.mock.calls.find(([url]) => url.includes('/manager-reports/'))
    expect(generateCall[1].method).toBe('POST')
    expect(JSON.parse(generateCall[1].body)).toEqual({ month: 9, year: 2026 })
  })

  it('shows a generating state and disables the button while running', async () => {
    let resolveGenerate
    const generatePromise = new Promise((resolve) => {
      resolveGenerate = resolve
    })

    const fetchMock = routeFetch({
      'GET http://localhost:8000/api/reports/?month=9&year=2026': jsonResponse(200, SEPT_REPORTS),
      'POST http://localhost:8000/api/manager-reports/monthly/generate/': async () => {
        await generatePromise
        return jsonResponse(200, {
          month: 9,
          year: 2026,
          reports_count: 2,
          report: 'Done.',
        })
      },
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReports />)

    await user.selectOptions(screen.getByLabelText('Month'), '9')
    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))
    await waitFor(() => expect(screen.getByText('Richa Verma')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Generate Monthly Team Report' }))

    const generatingButton = await screen.findByRole('button', {
      name: 'Generating Monthly Team Report...',
    })
    expect(generatingButton).toBeDisabled()

    resolveGenerate()
    await screen.findByText('Done.')
  })

  it('shows an error message when generation fails', async () => {
    const fetchMock = routeFetch({
      'GET http://localhost:8000/api/reports/?month=9&year=2026': jsonResponse(200, SEPT_REPORTS),
      'POST http://localhost:8000/api/manager-reports/monthly/generate/': jsonResponse(502, {
        detail: 'The AI team report could not be generated. Please try again.',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ManagerReports />)

    await user.selectOptions(screen.getByLabelText('Month'), '9')
    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))
    await waitFor(() => expect(screen.getByText('Richa Verma')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Generate Monthly Team Report' }))

    expect(
      await screen.findByText('The AI team report could not be generated. Please try again.')
    ).toBeInTheDocument()
  })

  it('shows an error when reports cannot be loaded', async () => {
    vi.stubGlobal(
      'fetch',
      routeFetch({ 'GET http://localhost:8000/api/reports/?month=9&year=2026': jsonResponse(500, {}) })
    )
    const user = userEvent.setup()
    render(<ManagerReports />)

    await user.selectOptions(screen.getByLabelText('Month'), '9')
    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))

    expect(
      await screen.findByText('Unable to load employee reports. Please try again.')
    ).toBeInTheDocument()
  })

  it('loads and shows the details of an underlying employee report', async () => {
    const fetchMock = routeFetch({
      'GET http://localhost:8000/api/reports/?month=9&year=2026': jsonResponse(200, SEPT_REPORTS),
      'GET http://localhost:8000/api/reports/1/': jsonResponse(200, {
        ...SEPT_REPORTS[0],
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
    render(<ManagerReports />)

    await user.selectOptions(screen.getByLabelText('Month'), '9')
    await user.selectOptions(screen.getByLabelText('Year'), '2026')
    await user.click(screen.getByRole('button', { name: 'Load Reports' }))
    await waitFor(() => expect(screen.getByText('Richa Verma')).toBeInTheDocument())

    await user.click(screen.getAllByRole('button', { name: 'View' })[0])

    expect(await screen.findByText('Richa Verma — September 2026')).toBeInTheDocument()
    expect(screen.getByText('Built the login flow')).toBeInTheDocument()
  })
})
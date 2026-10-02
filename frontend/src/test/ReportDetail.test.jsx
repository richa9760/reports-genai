import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReportDetail from '../components/ReportDetail'

const REPORT = {
  id: 1,
  employee_name: 'Ada Lovelace',
  project_name: 'Project Alpha',
  business_group: 'Cloud Infrastructure',
  month: 9,
  year: 2026,
  summary: 'September summary',
  items: {
    TASK: [{ id: 11, item_type: 'TASK', content: 'Completed API development' }],
    ACHIEVEMENT: [{ id: 12, item_type: 'ACHIEVEMENT', content: 'Employee of the month' }],
    COURSE: [],
    HOLIDAY: [{ id: 14, item_type: 'HOLIDAY', content: 'Summer holiday' }],
    IDEA: [],
  },
}

function jsonResponse(status, body) {
  return { ok: status < 400, status, text: async () => JSON.stringify(body) }
}

describe('ReportDetail', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the report with items grouped by type', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(200, REPORT)))
    render(<ReportDetail reportId={1} onEdit={vi.fn()} onBack={vi.fn()} />)

    await waitFor(() => expect(screen.getByText('Completed API development')).toBeInTheDocument())

    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.getByText('Project Alpha')).toBeInTheDocument()
    expect(screen.getByText('Cloud Infrastructure')).toBeInTheDocument()
    expect(screen.getByText('September')).toBeInTheDocument()
    expect(screen.getByText('2026')).toBeInTheDocument()
    expect(screen.getByText('September summary')).toBeInTheDocument()

    expect(screen.getByText('Employee of the month')).toBeInTheDocument()
    expect(screen.getByText('Summer holiday')).toBeInTheDocument()
  })

  it('shows an empty state for item types without entries', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(200, REPORT)))
    render(<ReportDetail reportId={1} onEdit={vi.fn()} onBack={vi.fn()} />)

    await waitFor(() => expect(screen.getByText('Completed API development')).toBeInTheDocument())
    expect(screen.getAllByText('No entries.')).toHaveLength(2)
  })

  it('shows an error when the report cannot be loaded', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(404, { detail: 'Not found.' })))
    render(<ReportDetail reportId={1} onEdit={vi.fn()} onBack={vi.fn()} />)

    expect(await screen.findByText('Unable to load the report. Please try again.')).toBeInTheDocument()
  })

  it('navigates back to the report list', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(200, REPORT)))
    const onBack = vi.fn()
    const user = userEvent.setup()
    render(<ReportDetail reportId={1} onEdit={vi.fn()} onBack={onBack} />)

    await waitFor(() => expect(screen.getByText('Completed API development')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Back to My Reports' }))

    expect(onBack).toHaveBeenCalled()
  })
})

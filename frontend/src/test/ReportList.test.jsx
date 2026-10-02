import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReportList from '../components/ReportList'

const REPORTS = [
  {
    id: 1,
    employee_name: 'Ada Lovelace',
    project_name: 'Project Alpha',
    business_group: 'Cloud Infrastructure',
    month: 9,
    year: 2026,
    summary: 'September summary',
  },
  {
    id: 2,
    employee_name: 'Alan Turing',
    project_name: 'Project Beta',
    business_group: 'Data Science',
    month: 10,
    year: 2026,
    summary: '',
  },
]

function jsonResponse(status, body) {
  return { ok: status < 400, status, text: async () => JSON.stringify(body) }
}

describe('ReportList', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('displays existing reports with employee, project and business group', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(200, REPORTS)))
    render(<ReportList onEdit={vi.fn()} onView={vi.fn()} />)

    await waitFor(() => expect(screen.getByText('Ada Lovelace')).toBeInTheDocument())

    expect(screen.getByText('Project Alpha')).toBeInTheDocument()
    expect(screen.getByText('Cloud Infrastructure')).toBeInTheDocument()
    expect(screen.getByText('September')).toBeInTheDocument()
    expect(screen.getByText('Alan Turing')).toBeInTheDocument()
    expect(screen.getByText('Data Science')).toBeInTheDocument()
    expect(screen.getByText('October')).toBeInTheDocument()
  })

  it('shows a loading state before the reports arrive', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<ReportList onEdit={vi.fn()} onView={vi.fn()} />)

    expect(screen.getByText('Loading reports...')).toBeInTheDocument()
  })

  it('shows an error message when loading fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(500, {})))
    render(<ReportList onEdit={vi.fn()} onView={vi.fn()} />)

    expect(await screen.findByText('Unable to load reports. Please try again.')).toBeInTheDocument()
  })

  it('shows an empty state when there are no reports', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(200, [])))
    render(<ReportList onEdit={vi.fn()} onView={vi.fn()} />)

    expect(
      await screen.findByText('No reports yet. Create your first monthly report.')
    ).toBeInTheDocument()
  })

  it('calls onEdit and onView for the selected report', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(200, REPORTS)))
    const onEdit = vi.fn()
    const onView = vi.fn()
    const user = userEvent.setup()
    render(<ReportList onEdit={onEdit} onView={onView} />)

    await waitFor(() => expect(screen.getByText('Ada Lovelace')).toBeInTheDocument())

    await user.click(screen.getAllByRole('button', { name: 'View' })[0])
    expect(onView).toHaveBeenCalledWith(1)

    await user.click(screen.getAllByRole('button', { name: 'Edit' })[0])
    expect(onEdit).toHaveBeenCalledWith(1)
  })

  it('deletes a report and removes it from the table', async () => {
    const fetchMock = vi.fn(async (url, options = {}) => {
      if (options.method === 'DELETE') return { ok: true, status: 204, text: async () => '' }
      return jsonResponse(200, REPORTS)
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<ReportList onEdit={vi.fn()} onView={vi.fn()} />)

    await waitFor(() => expect(screen.getByText('Ada Lovelace')).toBeInTheDocument())
    await user.click(screen.getAllByRole('button', { name: 'Delete' })[0])

    await waitFor(() => expect(screen.queryByText('Ada Lovelace')).not.toBeInTheDocument())
    expect(screen.getByText('Alan Turing')).toBeInTheDocument()

    const deleteCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'DELETE')
    expect(deleteCall[0]).toBe('http://localhost:8000/api/reports/1/')
  })
})

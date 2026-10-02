import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReportForm from '../components/ReportForm'

function mockFetch(routes) {
  return vi.fn(async (url, options = {}) => {
    const method = options.method ?? 'GET'
    const key = `${method} ${url}`

    const handler = routes[key]
    if (!handler) {
      return { ok: false, status: 404, text: async () => JSON.stringify({ detail: 'Not found.' }) }
    }

    const result = typeof handler === 'function' ? await handler(JSON.parse(options.body ?? 'null')) : handler
    const status = result.status ?? 200

    return {
      ok: status < 400,
      status,
      text: async () => JSON.stringify(result.body ?? {}),
    }
  })
}

describe('ReportForm', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the form with month and year defaulted to today', async () => {
    vi.stubGlobal('fetch', mockFetch({}))
    render(<ReportForm />)

    const now = new Date()
    const monthSelect = await screen.findByLabelText('Month')
    const yearInput = screen.getByLabelText('Year')

    expect(monthSelect.value).toBe(String(now.getMonth() + 1))
    expect(yearInput.value).toBe(String(now.getFullYear()))
  })

  it('renders free-text fields and the five item sections in the required order', async () => {
    const { container } = render(<ReportForm />)

    const labels = [
      'Month',
      'Year',
      'Employee Name',
      'Project Name',
      'Business Group',
      'Tasks Completed',
      'Achievements / Rewards',
      'Courses Taken',
      'Planned Holidays',
      'Ideas Submitted',
      'Summary',
    ]

    const elements = labels.map((label) => {
      if (label === 'Tasks Completed' || label === 'Achievements / Rewards' || label === 'Courses Taken' || label === 'Planned Holidays' || label === 'Ideas Submitted') {
        return screen.getByText(label)
      }
      return screen.getByLabelText(label)
    })

    elements.forEach((element) => {
      expect(element).toBeInTheDocument()
    })

    const iterator = document.createNodeIterator(container, NodeFilter.SHOW_ELEMENT)
    const docOrder = []
    let node
    while ((node = iterator.nextNode())) {
      if (elements.includes(node)) docOrder.push(node)
    }
    expect(docOrder).toEqual(elements)

    expect(screen.queryByRole('combobox', { name: 'Employee' })).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Project' })).not.toBeInTheDocument()
  })

  it('does not call the employees or projects endpoints', async () => {
    const fetchMock = mockFetch({})
    vi.stubGlobal('fetch', fetchMock)
    render(<ReportForm />)

    const called = fetchMock.mock.calls.map(([url]) => url)
    expect(called).not.toContain('http://localhost:8000/api/employees/')
    expect(called).not.toContain('http://localhost:8000/api/projects/')
  })

  it('renders an input row for all five item sections', async () => {
    const user = userEvent.setup()
    render(<ReportForm />)

    for (const label of ['Tasks Completed', 'Achievements / Rewards', 'Courses Taken', 'Planned Holidays', 'Ideas Submitted']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }

    await user.click(screen.getByRole('button', { name: '+ Add Task' }))
    await user.click(screen.getByRole('button', { name: '+ Add Achievement' }))
    await user.click(screen.getByRole('button', { name: '+ Add Course' }))
    await user.click(screen.getByRole('button', { name: '+ Add Holiday' }))
    await user.click(screen.getByRole('button', { name: '+ Add Idea' }))

    expect(screen.getByLabelText('Tasks Completed entry 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Achievements / Rewards entry 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Courses Taken entry 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Planned Holidays entry 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Ideas Submitted entry 1')).toBeInTheDocument()
  })

  it('validates required fields and does not call the reports API', async () => {
    const fetchMock = mockFetch({})
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<ReportForm />)

    await screen.findByLabelText('Employee Name')
    await user.click(screen.getByRole('button', { name: 'Save Report' }))

    expect(await screen.findByText('Employee Name is required.')).toBeInTheDocument()
    expect(screen.getByText('Project Name is required.')).toBeInTheDocument()
    expect(screen.getByText('Business Group is required.')).toBeInTheDocument()
    expect(screen.getByText('Add at least one report item before saving.')).toBeInTheDocument()

    const reportCalls = fetchMock.mock.calls.filter(([url]) => url.endsWith('/api/reports/'))
    expect(reportCalls).toHaveLength(0)
  })

  it('submits a new report with free-text fields and its items to the API', async () => {
    const fetchMock = mockFetch({
      'POST http://localhost:8000/api/reports/': { status: 201, body: { id: 7 } },
      'POST http://localhost:8000/api/reports/7/items/': { status: 201, body: { id: 1 } },
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    const onSaved = vi.fn()
    render(<ReportForm onSaved={onSaved} />)

    await screen.findByLabelText('Employee Name')
    await user.type(screen.getByLabelText('Employee Name'), 'Richa Verma')
    await user.type(screen.getByLabelText('Project Name'), 'AI Automation')
    await user.type(screen.getByLabelText('Business Group'), 'Data Center')

    await user.click(screen.getByRole('button', { name: '+ Add Task' }))
    await user.type(screen.getByLabelText('Tasks Completed entry 1'), 'Completed API development')
    await user.click(screen.getByRole('button', { name: '+ Add Idea' }))
    await user.type(screen.getByLabelText('Ideas Submitted entry 1'), 'Improve onboarding')
    await user.type(screen.getByLabelText('Summary'), 'A productive month.')

    await user.click(screen.getByRole('button', { name: 'Save Report' }))

    expect(await screen.findByText(/Report saved successfully/)).toBeInTheDocument()
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ id: 7 }))

    const reportCall = fetchMock.mock.calls.find(([url, options]) => url.endsWith('/api/reports/') && options?.method === 'POST')
    expect(JSON.parse(reportCall[1].body)).toMatchObject({
      employee_name: 'Richa Verma',
      project_name: 'AI Automation',
      business_group: 'Data Center',
      summary: 'A productive month.',
    })

    const itemCalls = fetchMock.mock.calls.filter(([url, options]) => url.includes('/items/') && options?.method === 'POST')
    expect(itemCalls).toHaveLength(2)

    const itemBodies = itemCalls.map(([, options]) => JSON.parse(options.body))
    expect(itemBodies).toContainEqual({ item_type: 'TASK', content: 'Completed API development' })
    expect(itemBodies).toContainEqual({ item_type: 'IDEA', content: 'Improve onboarding' })
  })

  it('trims whitespace from the free-text fields before submitting', async () => {
    const fetchMock = mockFetch({
      'POST http://localhost:8000/api/reports/': { status: 201, body: { id: 8 } },
      'POST http://localhost:8000/api/reports/8/items/': { status: 201, body: { id: 1 } },
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<ReportForm />)

    await screen.findByLabelText('Employee Name')
    await user.type(screen.getByLabelText('Employee Name'), '  Richa Verma  ')
    await user.type(screen.getByLabelText('Project Name'), '  AI Automation  ')
    await user.type(screen.getByLabelText('Business Group'), '  Data Center  ')
    await user.click(screen.getByRole('button', { name: '+ Add Task' }))
    await user.type(screen.getByLabelText('Tasks Completed entry 1'), '  Task with spaces  ')

    await user.click(screen.getByRole('button', { name: 'Save Report' }))

    await screen.findByText(/Report saved successfully/)

    const reportCall = fetchMock.mock.calls.find(([url, options]) => url.endsWith('/api/reports/') && options?.method === 'POST')
    expect(JSON.parse(reportCall[1].body)).toMatchObject({
      employee_name: 'Richa Verma',
      project_name: 'AI Automation',
      business_group: 'Data Center',
    })

    const itemCall = fetchMock.mock.calls.find(([url, options]) => url.includes('/items/') && options?.method === 'POST')
    expect(JSON.parse(itemCall[1].body)).toEqual({ item_type: 'TASK', content: 'Task with spaces' })
  })

  it('shows the backend validation error when saving fails', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        'POST http://localhost:8000/api/reports/': {
          status: 400,
          body: { non_field_errors: ['The fields employee_name, project_name, business_group, month, year must make a unique set.'] },
        },
      })
    )

    const user = userEvent.setup()
    render(<ReportForm />)

    await screen.findByLabelText('Employee Name')
    await user.type(screen.getByLabelText('Employee Name'), 'Richa Verma')
    await user.type(screen.getByLabelText('Project Name'), 'AI Automation')
    await user.type(screen.getByLabelText('Business Group'), 'Data Center')
    await user.click(screen.getByRole('button', { name: '+ Add Task' }))
    await user.type(screen.getByLabelText('Tasks Completed entry 1'), 'Duplicate attempt')
    await user.click(screen.getByRole('button', { name: 'Save Report' }))

    expect(
      await screen.findByText('The fields employee_name, project_name, business_group, month, year must make a unique set.')
    ).toBeInTheDocument()
  })

  it('does not send a second submission while saving is in progress', async () => {
    let resolveCreate
    const createPromise = new Promise((resolve) => {
      resolveCreate = resolve
    })

    const fetchMock = mockFetch({
      'POST http://localhost:8000/api/reports/': async () => {
        await createPromise
        return { status: 201, body: { id: 9 } }
      },
      'POST http://localhost:8000/api/reports/9/items/': { status: 201, body: { id: 1 } },
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<ReportForm />)

    await screen.findByLabelText('Employee Name')
    await user.type(screen.getByLabelText('Employee Name'), 'Richa Verma')
    await user.type(screen.getByLabelText('Project Name'), 'AI Automation')
    await user.type(screen.getByLabelText('Business Group'), 'Data Center')
    await user.click(screen.getByRole('button', { name: '+ Add Task' }))
    await user.type(screen.getByLabelText('Tasks Completed entry 1'), 'Guard against double submit')

    await user.click(screen.getByRole('button', { name: 'Save Report' }))

    const savingButton = await screen.findByRole('button', { name: 'Saving...' })
    expect(savingButton).toBeDisabled()

    await user.click(savingButton)
    expect(savingButton).toBeDisabled()

    resolveCreate()
    await screen.findByText(/Report saved successfully/)
  })

  it('populates the form and removes deleted items when editing', async () => {
    const report = {
      id: 3,
      employee_name: 'Richa Verma',
      project_name: 'AI Automation',
      business_group: 'Data Center',
      month: 4,
      year: 2025,
      summary: 'April recap',
      items: {
        TASK: [{ id: 11, item_type: 'TASK', content: 'Existing task' }],
        ACHIEVEMENT: [{ id: 12, item_type: 'ACHIEVEMENT', content: 'Existing award' }],
        COURSE: [],
        HOLIDAY: [],
        IDEA: [],
      },
    }

    const fetchMock = mockFetch({
      'GET http://localhost:8000/api/reports/3/': { body: report },
      'PATCH http://localhost:8000/api/reports/3/': { body: report },
      'PATCH http://localhost:8000/api/report-items/11/': { body: { id: 11 } },
      'POST http://localhost:8000/api/reports/3/items/': { status: 201, body: { id: 20 } },
      'DELETE http://localhost:8000/api/report-items/12/': { status: 204 },
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<ReportForm reportId={3} />)

    await waitFor(() => {
      expect(screen.getByLabelText('Tasks Completed entry 1')).toHaveValue('Existing task')
    })

    expect(screen.getByLabelText('Achievements / Rewards entry 1')).toHaveValue('Existing award')
    expect(screen.getByLabelText('Month')).toHaveValue('4')
    expect(screen.getByLabelText('Year')).toHaveValue(2025)
    expect(screen.getByLabelText('Employee Name')).toHaveValue('Richa Verma')
    expect(screen.getByLabelText('Project Name')).toHaveValue('AI Automation')
    expect(screen.getByLabelText('Business Group')).toHaveValue('Data Center')
    expect(screen.getByLabelText('Summary')).toHaveValue('April recap')

    // Edit an existing item, delete another, and add a new one.
    await user.clear(screen.getByLabelText('Tasks Completed entry 1'))
    await user.type(screen.getByLabelText('Tasks Completed entry 1'), 'Updated task')
    await user.click(screen.getByRole('button', { name: 'Remove Achievements / Rewards entry 1' }))
    await user.click(screen.getByRole('button', { name: '+ Add Course' }))
    await user.type(screen.getByLabelText('Courses Taken entry 1'), 'New course')

    await user.click(screen.getByRole('button', { name: 'Save Report' }))
    await waitFor(() => expect(screen.getByText(/Report saved successfully/)).toBeInTheDocument())

    const keys = fetchMock.mock.calls.map(([url, options]) => `${options?.method ?? 'GET'} ${url}`)

    expect(keys).toContain('PATCH http://localhost:8000/api/reports/3/')
    expect(keys).toContain('PATCH http://localhost:8000/api/report-items/11/')
    expect(keys).toContain('DELETE http://localhost:8000/api/report-items/12/')
    expect(keys).toContain('POST http://localhost:8000/api/reports/3/items/')

    const courseCall = fetchMock.mock.calls.find(([url, options]) => url.includes('/items/') && options?.method === 'POST')
    expect(JSON.parse(courseCall[1].body)).toEqual({ item_type: 'COURSE', content: 'New course' })
  })

  it('shows an error when the report being edited cannot be loaded', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        'GET http://localhost:8000/api/reports/3/': { status: 404, body: { detail: 'Not found.' } },
      })
    )
    render(<ReportForm reportId={3} />)

    expect(await screen.findByText('Unable to load the report. Please try again.')).toBeInTheDocument()
  })

  it('keeps the AI button inert', async () => {
    const fetchMock = mockFetch({})
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<ReportForm />)

    await screen.findByLabelText('Employee Name')
    await user.click(screen.getByRole('button', { name: 'Generate Summary with AI' }))

    expect(await screen.findByText('Employee Name is required.')).toBeInTheDocument()

    const llmCalls = fetchMock.mock.calls.filter(([url]) => url.endsWith('/api/reports/generate-summary/'))
    expect(llmCalls).toHaveLength(0)
  })

  it('generates an AI summary draft without saving the report', async () => {
    const fetchMock = mockFetch({
      'POST http://localhost:8000/api/reports/generate-summary/': {
        body: { summary: 'A productive month focused on the data pipeline.' },
      },
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<ReportForm />)

    await screen.findByLabelText('Employee Name')
    await user.type(screen.getByLabelText('Employee Name'), 'Richa Verma')
    await user.type(screen.getByLabelText('Project Name'), 'AI Automation')
    await user.type(screen.getByLabelText('Business Group'), 'Data Center')
    await user.click(screen.getByRole('button', { name: '+ Add Task' }))
    await user.type(screen.getByLabelText('Tasks Completed entry 1'), 'Shipped the auth module')
    await user.click(screen.getByRole('button', { name: '+ Add Idea' }))
    await user.type(screen.getByLabelText('Ideas Submitted entry 1'), 'Automate CI checks')

    await user.click(screen.getByRole('button', { name: 'Generate Summary with AI' }))

    expect(await screen.findByLabelText('Summary')).toHaveValue(
      'A productive month focused on the data pipeline.'
    )

    const generateCall = fetchMock.mock.calls.find(([url]) => url.endsWith('/api/reports/generate-summary/'))
    expect(JSON.parse(generateCall[1].body)).toEqual({
      employee_name: 'Richa Verma',
      project_name: 'AI Automation',
      business_group: 'Data Center',
      month: new Date().getMonth() + 1,
      year: new Date().getFullYear(),
      tasks: ['Shipped the auth module'],
      achievements: [],
      courses: [],
      planned_holidays: [],
      ideas: ['Automate CI checks'],
    })

    const reportCalls = fetchMock.mock.calls.filter(([url, options]) => url.endsWith('/api/reports/') && options?.method === 'POST')
    expect(reportCalls).toHaveLength(0)
  })

  it('shows Generating state and disables the button while the summary is being generated', async () => {
    let resolveGenerate
    const generatePromise = new Promise((resolve) => {
      resolveGenerate = resolve
    })

    const fetchMock = mockFetch({
      'POST http://localhost:8000/api/reports/generate-summary/': async () => {
        await generatePromise
        return { body: { summary: 'Done.' } }
      },
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<ReportForm />)

    await screen.findByLabelText('Employee Name')
    await user.type(screen.getByLabelText('Employee Name'), 'Richa Verma')
    await user.type(screen.getByLabelText('Project Name'), 'AI Automation')
    await user.type(screen.getByLabelText('Business Group'), 'Data Center')
    await user.click(screen.getByRole('button', { name: '+ Add Task' }))
    await user.type(screen.getByLabelText('Tasks Completed entry 1'), 'API work')

    await user.click(screen.getByRole('button', { name: 'Generate Summary with AI' }))

    const generatingButton = await screen.findByRole('button', { name: 'Generating...' })
    expect(generatingButton).toBeDisabled()

    resolveGenerate()
    await screen.findByRole('button', { name: 'Generate Summary with AI' })
    expect(screen.getByLabelText('Summary')).toHaveValue('Done.')
  })

  it('asks for confirmation before replacing an existing summary', async () => {
    const fetchMock = mockFetch({
      'POST http://localhost:8000/api/reports/generate-summary/': {
        body: { summary: 'New AI summary.' },
      },
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<ReportForm />)

    await screen.findByLabelText('Employee Name')
    await user.type(screen.getByLabelText('Employee Name'), 'Richa Verma')
    await user.type(screen.getByLabelText('Project Name'), 'AI Automation')
    await user.type(screen.getByLabelText('Business Group'), 'Data Center')
    await user.click(screen.getByRole('button', { name: '+ Add Task' }))
    await user.type(screen.getByLabelText('Tasks Completed entry 1'), 'API work')
    await user.type(screen.getByLabelText('Summary'), 'Existing manual summary.')

    // Cancel the confirmation: nothing is overwritten and no request is sent.
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await user.click(screen.getByRole('button', { name: 'Generate Summary with AI' }))

    const generateCalls = fetchMock.mock.calls.filter(([url]) => url.endsWith('/api/reports/generate-summary/'))
    expect(generateCalls).toHaveLength(0)
    expect(screen.getByLabelText('Summary')).toHaveValue('Existing manual summary.')

    // Confirm: the summary is replaced.
    confirmSpy.mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: 'Generate Summary with AI' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Summary')).toHaveValue('New AI summary.')
    })
    expect(confirmSpy).toHaveBeenCalledTimes(2)
  })

  it('keeps the form data and existing summary when generation fails', async () => {
    const fetchMock = mockFetch({
      'POST http://localhost:8000/api/reports/generate-summary/': {
        status: 502,
        body: { detail: 'The AI summary could not be generated. Please try again.' },
      },
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<ReportForm />)

    await screen.findByLabelText('Employee Name')
    await user.type(screen.getByLabelText('Employee Name'), 'Richa Verma')
    await user.type(screen.getByLabelText('Project Name'), 'AI Automation')
    await user.type(screen.getByLabelText('Business Group'), 'Data Center')
    await user.click(screen.getByRole('button', { name: '+ Add Task' }))
    await user.type(screen.getByLabelText('Tasks Completed entry 1'), 'API work')
    await user.type(screen.getByLabelText('Summary'), 'Keep me.')

    vi.spyOn(window, 'confirm').mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: 'Generate Summary with AI' }))

    expect(
      await screen.findByText('The AI summary could not be generated. Please try again.')
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Summary')).toHaveValue('Keep me.')
    expect(screen.getByLabelText('Employee Name')).toHaveValue('Richa Verma')
    expect(screen.getByLabelText('Tasks Completed entry 1')).toHaveValue('API work')
  })
})
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

const HEALTH = [{ ok: true, status: 200, text: async () => JSON.stringify({ status: 'ok' }) }]

function jsonResponse(status, body) {
  return { ok: status < 400, status, text: async () => JSON.stringify(body) }
}

function routeFetch(routes) {
  return vi.fn(async (url, options = {}) => {
    const key = `${options.method ?? 'GET'} ${url}`
    const handler = routes[key]
    if (!handler) return jsonResponse(404, { detail: 'Not found.' })
    return typeof handler === 'function' ? handler() : handler
  })
}

const BASE = {
  'GET http://localhost:8000/api/health/': HEALTH[0],
  'GET http://localhost:8000/api/reports/': jsonResponse(200, []),
  'GET http://localhost:8000/api/llmops/metrics/': jsonResponse(200, {
    total_requests: 0,
    successful_requests: 0,
    failed_requests: 0,
    average_latency_ms: null,
    total_input_tokens: 0,
    total_output_tokens: 0,
    total_tokens: 0,
    total_cost: '0',
    error_breakdown: [],
    daily_usage: [],
    feature_usage: [],
  }),
}

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.history.pushState(null, '', '/')
  })

  it('shows the header, backend status and navigation', async () => {
    vi.stubGlobal('fetch', routeFetch(BASE))
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Reports Application' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Connected')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Create Report' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'My Reports' })).toBeInTheDocument()
  })

  it('shows Disconnected when the health check fails', async () => {
    vi.stubGlobal('fetch', routeFetch({ ...BASE, 'GET http://localhost:8000/api/health/': jsonResponse(500, {}) }))
    render(<App />)

    await waitFor(() => expect(screen.getByText('Disconnected')).toBeInTheDocument())
  })

  it('starts on the create report form and switches to the report list', async () => {
    vi.stubGlobal('fetch', routeFetch(BASE))
    const user = userEvent.setup()
    render(<App />)

    await waitFor(() => expect(screen.getByLabelText('Employee Name')).toBeInTheDocument())
    expect(screen.getByRole('heading', { name: 'Create Monthly Report' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'My Reports' }))

    await waitFor(() =>
      expect(screen.getByText('No reports yet. Create your first monthly report.')).toBeInTheDocument()
    )
  })

  it('opens the manager reports page from the navigation', async () => {
    vi.stubGlobal('fetch', routeFetch(BASE))
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByRole('button', { name: 'Manager Reports' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Manager Reports' }))

    expect(screen.getByRole('heading', { name: 'Manager Reports' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Load Reports' })).toBeInTheDocument()
  })

  it('opens the LLMOps dashboard from the navigation', async () => {
    vi.stubGlobal('fetch', routeFetch(BASE))
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByRole('button', { name: 'LLMOps' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'LLMOps' }))

    expect(screen.getByRole('heading', { name: 'LLMOps Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument()
  })

  it('opens the LLMOps dashboard directly at the /llmops route', async () => {
    vi.stubGlobal('fetch', routeFetch(BASE))
    window.history.pushState(null, '', '/llmops')
    render(<App />)

    expect(screen.getByRole('heading', { name: 'LLMOps Dashboard' })).toBeInTheDocument()
  })
})

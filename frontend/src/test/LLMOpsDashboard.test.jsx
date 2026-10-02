import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LLMOpsDashboard from '../pages/LLMOpsDashboard'

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

const METRICS_URL = 'GET http://localhost:8000/api/llmops/metrics/'

const METRICS = {
  total_requests: 6,
  successful_requests: 5,
  failed_requests: 1,
  average_latency_ms: 842.5,
  total_input_tokens: 1100,
  total_output_tokens: 450,
  total_tokens: 1550,
  total_cost: '0.00109500',
  error_breakdown: [{ error_type: 'LLMResponseError', count: 1 }],
  daily_usage: [
    { date: '2026-09-28', requests: 2, total_tokens: 500, total_cost: '0.00037500' },
    { date: '2026-09-29', requests: 4, total_tokens: 1050, total_cost: '0.00072000' },
  ],
  feature_usage: [
    {
      feature: 'manager_quarterly_report',
      requests: 6,
      successful_requests: 5,
      failed_requests: 1,
      total_tokens: 1550,
      total_cost: '0.00109500',
      average_latency_ms: 842.5,
    },
  ],
  quality_metrics: {
    relevance: 5,
    faithfulness: 4.5,
    completeness: 4,
    clarity: 5,
    quality_score: 4.75,
  },
  reference_metrics: {
    rouge1: 0.32,
    rouge2: 0.21,
    rougeL: 0.35,
    semantic_similarity: 0.81,
  },
  prompt_comparison: {
    v1: {
      rouge1: 0.410526315789474,
      rouge2: 0.170212765957447,
      rougeL: 0.315789473684211,
      semantic_similarity: 0.873221635818481,
    },
    v2: {
      rouge1: 0.243243243243243,
      rouge2: 0.085972850678733,
      rougeL: 0.148648648648649,
      semantic_similarity: 0.689671635627747,
    },
  },
}

describe('LLMOpsDashboard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the heading and a refresh button', async () => {
    vi.stubGlobal('fetch', routeFetch({ [METRICS_URL]: jsonResponse(200, METRICS) }))
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Feature Usage' })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument()
  })

  it('shows loading state while fetching', async () => {
    let resolveFetch
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise((resolve) => {
            resolveFetch = () => resolve(jsonResponse(200, METRICS))
          })
      )
    )
    render(<LLMOpsDashboard />)

    expect(screen.getByText('Loading LLM metrics...')).toBeInTheDocument()
    resolveFetch()
    await waitFor(() => expect(screen.queryByText('Loading LLM metrics...')).not.toBeInTheDocument())
  })

  it('shows the summary cards', async () => {
    vi.stubGlobal('fetch', routeFetch({ [METRICS_URL]: jsonResponse(200, METRICS) }))
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getAllByText('Total Requests').length).toBeGreaterThan(0))

    const cards = screen.getAllByText('Total Requests')[0].closest('.cards')

    expect(within(cards).getByText('Successful Requests')).toBeInTheDocument()
    expect(within(cards).getByText('Failed Requests')).toBeInTheDocument()
    expect(within(cards).getByText('Avg Latency')).toBeInTheDocument()
    expect(within(cards).getByText('Input Tokens')).toBeInTheDocument()
    expect(within(cards).getByText('Output Tokens')).toBeInTheDocument()
    expect(within(cards).getByText('Total Tokens')).toBeInTheDocument()
    expect(within(cards).getByText('Total Cost')).toBeInTheDocument()

    expect(screen.getAllByText('1,550').length).toBeGreaterThan(0)
    expect(screen.getAllByText('842.5 ms').length).toBeGreaterThan(0)
    expect(screen.getAllByText('$0.00109500').length).toBeGreaterThan(0)
  })

  it('renders the feature usage table', async () => {
    vi.stubGlobal('fetch', routeFetch({ [METRICS_URL]: jsonResponse(200, METRICS) }))
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Feature Usage' })).toBeInTheDocument())

    const table = screen.getAllByRole('table')[0]

    expect(within(table).getByRole('columnheader', { name: 'Feature' })).toBeInTheDocument()
    expect(within(table).getAllByRole('columnheader', { name: 'Requests' }).length).toBeGreaterThan(0)
    expect(within(table).getByRole('columnheader', { name: 'Successful' })).toBeInTheDocument()
    expect(within(table).getByRole('columnheader', { name: 'Failed' })).toBeInTheDocument()
    expect(within(table).getAllByRole('columnheader', { name: 'Total Tokens' }).length).toBeGreaterThan(0)
    expect(within(table).getAllByRole('columnheader', { name: 'Total Cost' }).length).toBeGreaterThan(0)
    expect(within(table).getByRole('columnheader', { name: 'Avg Latency' })).toBeInTheDocument()

    expect(screen.getByText('manager_quarterly_report')).toBeInTheDocument()
    expect(screen.getAllByText('842.5 ms').length).toBeGreaterThan(0)
  })

  it('renders the daily usage table', async () => {
    vi.stubGlobal('fetch', routeFetch({ [METRICS_URL]: jsonResponse(200, METRICS) }))
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Daily Usage' })).toBeInTheDocument())

    expect(screen.getByText('2026-09-28')).toBeInTheDocument()
    expect(screen.getByText('2026-09-29')).toBeInTheDocument()
    expect(screen.getByText('$0.00072000')).toBeInTheDocument()
  })

  it('renders the quality metrics section from the API', async () => {
    vi.stubGlobal('fetch', routeFetch({ [METRICS_URL]: jsonResponse(200, METRICS) }))
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Quality Metrics' })).toBeInTheDocument())

    expect(screen.getByText('Relevance')).toBeInTheDocument()
    expect(screen.getByText('Faithfulness')).toBeInTheDocument()
    expect(screen.getByText('Completeness')).toBeInTheDocument()
    expect(screen.getByText('Clarity')).toBeInTheDocument()
    expect(screen.getByText('Overall Quality Score')).toBeInTheDocument()

    expect(screen.getByText('4.75')).toBeInTheDocument()
    expect(screen.getByText('4.5')).toBeInTheDocument()
  })

  it('renders the reference metrics section from the API', async () => {
    vi.stubGlobal('fetch', routeFetch({ [METRICS_URL]: jsonResponse(200, METRICS) }))
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Reference Metrics' })).toBeInTheDocument())

    expect(screen.getAllByText('ROUGE-1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ROUGE-2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ROUGE-L').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Semantic Similarity').length).toBeGreaterThan(0)

    expect(screen.getByText('0.32')).toBeInTheDocument()
    expect(screen.getByText('0.21')).toBeInTheDocument()
    expect(screen.getByText('0.35')).toBeInTheDocument()
    expect(screen.getByText('0.81')).toBeInTheDocument()
  })

  it('renders the prompt version comparison section from the API', async () => {
    vi.stubGlobal('fetch', routeFetch({ [METRICS_URL]: jsonResponse(200, METRICS) }))
    render(<LLMOpsDashboard />)

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Prompt Version Comparison' })).toBeInTheDocument()
    )

    expect(screen.getByRole('columnheader', { name: 'v1' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'v2' })).toBeInTheDocument()

    expect(screen.getByText('0.411')).toBeInTheDocument()
    expect(screen.getByText('0.170')).toBeInTheDocument()
    expect(screen.getByText('0.316')).toBeInTheDocument()
    expect(screen.getByText('0.873')).toBeInTheDocument()

    expect(screen.getByText('0.243')).toBeInTheDocument()
    expect(screen.getByText('0.086')).toBeInTheDocument()
    expect(screen.getByText('0.149')).toBeInTheDocument()
    expect(screen.getByText('0.690')).toBeInTheDocument()
  })

  it('shows an empty message when no prompt comparison data is available', async () => {
    vi.stubGlobal(
      'fetch',
      routeFetch({ [METRICS_URL]: jsonResponse(200, { ...METRICS, prompt_comparison: {} }) })
    )
    render(<LLMOpsDashboard />)

    await waitFor(() =>
      expect(screen.getByText('No prompt comparison data available.')).toBeInTheDocument()
    )
  })

  it('shows a dash for a missing comparison version without crashing', async () => {
    vi.stubGlobal(
      'fetch',
      routeFetch({
        [METRICS_URL]: jsonResponse(200, {
          ...METRICS,
          prompt_comparison: { v1: { rouge1: 0.41, rouge2: 0.17, rougeL: 0.32, semantic_similarity: 0.87 } },
        }),
      })
    )
    render(<LLMOpsDashboard />)

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Prompt Version Comparison' })).toBeInTheDocument()
    )

    expect(screen.getByText('0.410')).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('renders the error breakdown table when errors exist', async () => {
    vi.stubGlobal('fetch', routeFetch({ [METRICS_URL]: jsonResponse(200, METRICS) }))
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Error Breakdown' })).toBeInTheDocument())

    expect(screen.getByText('LLMResponseError')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Count' })).toBeInTheDocument()
  })

  it('shows an empty message when no errors were recorded', async () => {
    vi.stubGlobal(
      'fetch',
      routeFetch({ [METRICS_URL]: jsonResponse(200, { ...METRICS, error_breakdown: [] }) })
    )
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getByText('No LLM errors recorded.')).toBeInTheDocument())
  })

  it('shows an error message when the request fails', async () => {
    vi.stubGlobal('fetch', routeFetch({ [METRICS_URL]: jsonResponse(500, {}) }))
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getByText('Unable to load LLM metrics.')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument()
  })

  it('reloads the metrics when refresh is clicked', async () => {
    const fetchMock = routeFetch({ [METRICS_URL]: jsonResponse(200, METRICS) })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<LLMOpsDashboard />)

    await waitFor(() => expect(screen.getAllByText('1,550').length).toBeGreaterThan(0))
    await user.click(screen.getByRole('button', { name: 'Refresh' }))

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
import { useEffect, useState } from 'react'
import { getLLMOpsMetrics } from '../api/llmops'
import { EmptyMessage, ErrorMessage, LoadingMessage } from '../components/Feedback'

function formatCount(value) {
  if (value == null) return '0'
  return Number(value).toLocaleString()
}

function formatCost(value) {
  if (value == null) return '—'
  return `$${value}`
}

function formatLatency(value) {
  if (value == null) return '—'
  return `${formatCount(value)} ms`
}

function formatQualityScore(value) {
  if (value == null) return '—'
  return String(parseFloat(Number(value).toFixed(2)))
}

function formatReferenceScore(value) {
  if (value == null) return '—'
  return Number(value).toFixed(2)
}

function formatComparisonScore(value) {
  if (value == null) return '—'
  return Number(value).toFixed(3)
}

const CARD_FIELDS = [
  { key: 'total_requests', label: 'Total Requests', render: formatCount },
  { key: 'successful_requests', label: 'Successful Requests', render: formatCount },
  { key: 'failed_requests', label: 'Failed Requests', render: formatCount },
  { key: 'average_latency_ms', label: 'Avg Latency', render: formatLatency },
  { key: 'total_input_tokens', label: 'Input Tokens', render: formatCount },
  { key: 'total_output_tokens', label: 'Output Tokens', render: formatCount },
  { key: 'total_tokens', label: 'Total Tokens', render: formatCount },
  { key: 'total_cost', label: 'Total Cost', render: formatCost },
]

function SummaryCard({ label, value }) {
  return (
    <div className="card">
      <p className="card__label">{label}</p>
      <p className="card__value">{value}</p>
    </div>
  )
}

const QUALITY_METRIC_ENTRIES = [
  { key: 'relevance', label: 'Relevance' },
  { key: 'faithfulness', label: 'Faithfulness' },
  { key: 'completeness', label: 'Completeness' },
  { key: 'clarity', label: 'Clarity' },
  { key: 'quality_score', label: 'Overall Quality Score' },
]

const REFERENCE_METRIC_ENTRIES = [
  { key: 'rouge1', label: 'ROUGE-1' },
  { key: 'rouge2', label: 'ROUGE-2' },
  { key: 'rougeL', label: 'ROUGE-L' },
  { key: 'semantic_similarity', label: 'Semantic Similarity' },
]

const PROMPT_COMPARISON_ENTRIES = [
  { key: 'rouge1', label: 'ROUGE-1' },
  { key: 'rouge2', label: 'ROUGE-2' },
  { key: 'rougeL', label: 'ROUGE-L' },
  { key: 'semantic_similarity', label: 'Semantic Similarity' },
]

function MetricRow({ label, value }) {
  return (
    <tr>
      <td>{label}</td>
      <td className="table__num">{value}</td>
    </tr>
  )
}

export default function LLMOpsDashboard() {
  const [state, setState] = useState('loading')
  const [metrics, setMetrics] = useState(null)

  useEffect(() => {
    let active = true

    getLLMOpsMetrics()
      .then((data) => {
        if (!active) return
        setMetrics(data)
        setState('ready')
      })
      .catch(() => {
        if (!active) return
        setState('error')
      })

    return () => {
      active = false
    }
  }, [])

  async function load() {
    setState('loading')
    try {
      const data = await getLLMOpsMetrics()
      setMetrics(data)
      setState('ready')
    } catch {
      setState('error')
    }
  }

  return (
    <>
      <div className="section-header">
        <h2>LLMOps Dashboard</h2>
        <div className="actions">
          <button
            type="button"
            className="button"
            onClick={load}
            disabled={state === 'loading'}
          >
            {state === 'loading' ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {state === 'loading' && <LoadingMessage>Loading LLM metrics...</LoadingMessage>}
      {state === 'error' && <ErrorMessage>Unable to load LLM metrics.</ErrorMessage>}

      {state === 'ready' && metrics && (
        <>
          <div className="cards">
            {CARD_FIELDS.map((field) => (
              <SummaryCard
                key={field.key}
                label={field.label}
                value={field.render(metrics[field.key])}
              />
            ))}
          </div>

          <h3>Feature Usage</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Feature</th>
                <th className="table__num">Requests</th>
                <th className="table__num">Successful</th>
                <th className="table__num">Failed</th>
                <th className="table__num">Total Tokens</th>
                <th className="table__num">Total Cost</th>
                <th className="table__num">Avg Latency</th>
              </tr>
            </thead>
            <tbody>
              {(metrics.feature_usage ?? []).map((entry) => (
                <tr key={entry.feature}>
                  <td>{entry.feature}</td>
                  <td className="table__num">{formatCount(entry.requests)}</td>
                  <td className="table__num">{formatCount(entry.successful_requests)}</td>
                  <td className="table__num">{formatCount(entry.failed_requests)}</td>
                  <td className="table__num">{formatCount(entry.total_tokens)}</td>
                  <td className="table__num">{formatCost(entry.total_cost)}</td>
                  <td className="table__num">{formatLatency(entry.average_latency_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Daily Usage</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th className="table__num">Requests</th>
                <th className="table__num">Total Tokens</th>
                <th className="table__num">Total Cost</th>
              </tr>
            </thead>
            <tbody>
              {(metrics.daily_usage ?? []).map((entry) => (
                <tr key={entry.date}>
                  <td>{entry.date}</td>
                  <td className="table__num">{formatCount(entry.requests)}</td>
                  <td className="table__num">{formatCount(entry.total_tokens)}</td>
                  <td className="table__num">{formatCost(entry.total_cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Quality Metrics</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Metric</th>
                <th className="table__num">Score</th>
              </tr>
            </thead>
            <tbody>
              {QUALITY_METRIC_ENTRIES.map(({ key, label }) => (
                <MetricRow
                  key={key}
                  label={label}
                  value={formatQualityScore(metrics.quality_metrics?.[key])}
                />
              ))}
            </tbody>
          </table>

          <h3>Reference Metrics</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Metric</th>
                <th className="table__num">Score</th>
              </tr>
            </thead>
            <tbody>
              {REFERENCE_METRIC_ENTRIES.map(({ key, label }) => (
                <MetricRow
                  key={key}
                  label={label}
                  value={formatReferenceScore(metrics.reference_metrics?.[key])}
                />
              ))}
            </tbody>
          </table>

          <h3>Prompt Version Comparison</h3>
          {!metrics.prompt_comparison || Object.keys(metrics.prompt_comparison).length === 0 ? (
            <EmptyMessage>No prompt comparison data available.</EmptyMessage>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th className="table__num">v1</th>
                  <th className="table__num">v2</th>
                </tr>
              </thead>
              <tbody>
                {PROMPT_COMPARISON_ENTRIES.map(({ key, label }) => (
                  <tr key={key}>
                    <td>{label}</td>
                    <td className="table__num">
                      {formatComparisonScore(metrics.prompt_comparison.v1?.[key])}
                    </td>
                    <td className="table__num">
                      {formatComparisonScore(metrics.prompt_comparison.v2?.[key])}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3>Error Breakdown</h3>
          {(metrics.error_breakdown ?? []).length === 0 ? (
            <EmptyMessage>No LLM errors recorded.</EmptyMessage>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Error Type</th>
                  <th className="table__num">Count</th>
                </tr>
              </thead>
              <tbody>
                {metrics.error_breakdown.map((entry) => (
                  <tr key={entry.error_type}>
                    <td>{entry.error_type}</td>
                    <td className="table__num">{formatCount(entry.count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </>
  )
}
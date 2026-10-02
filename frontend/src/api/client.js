const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/** Error carrying the HTTP status and any field-level validation messages. */
export class ApiError extends Error {
  constructor(message, { status = 0, fieldErrors = {} } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

function toFieldErrors(body) {
  if (!body || typeof body !== 'object') return {}

  const entries = Object.entries(body)
    .filter(([, value]) => Array.isArray(value))
    .map(([key, value]) => [key, value.join(' ')])

  if (Array.isArray(body.non_field_errors)) {
    entries.push(['_non_field_errors', body.non_field_errors.join(' ')])
  }

  if (typeof body.detail === 'string') {
    entries.push(['_detail', body.detail])
  }

  return Object.fromEntries(entries)
}

async function request(path, { method = 'GET', body } = {}) {
  let response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Unable to reach the backend. Please try again.', { status: 0 })
  }

  if (response.status === 204) return null

  const text = await response.text()
  const data = text ? JSON.parse(text) : null

  if (!response.ok) {
    const fieldErrors = toFieldErrors(data)
    const [firstMessage] = Object.values(fieldErrors)
    throw new ApiError(firstMessage ?? 'Request failed.', {
      status: response.status,
      fieldErrors,
    })
  }

  return data
}

export { API_BASE_URL }
export { request }

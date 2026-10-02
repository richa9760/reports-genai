import { request } from './client'

export function getHealth() {
  return request('/api/health/')
}

export function getReports(params = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  }
  const qs = query.toString()
  return request(`/api/reports/${qs ? `?${qs}` : ''}`)
}

export function getReport(id) {
  return request(`/api/reports/${id}/`)
}

export function createReport(data) {
  return request('/api/reports/', { method: 'POST', body: data })
}

export function updateReport(id, data) {
  return request(`/api/reports/${id}/`, { method: 'PATCH', body: data })
}

export function deleteReport(id) {
  return request(`/api/reports/${id}/`, { method: 'DELETE' })
}

export function createReportItem(reportId, data) {
  return request(`/api/reports/${reportId}/items/`, { method: 'POST', body: data })
}

export function updateReportItem(itemId, data) {
  return request(`/api/report-items/${itemId}/`, { method: 'PATCH', body: data })
}

export function deleteReportItem(itemId) {
  return request(`/api/report-items/${itemId}/`, { method: 'DELETE' })
}

export function generateManagerReport({ month, year }) {
  return request('/api/manager-reports/monthly/generate/', {
    method: 'POST',
    body: { month, year },
  })
}

export function generateQuarterlyManagerReport({ quarter, year }) {
  return request('/api/manager-reports/quarterly/generate/', {
    method: 'POST',
    body: { quarter, year },
  })
}

export function generateReportSummary(data) {
  return request('/api/reports/generate-summary/', { method: 'POST', body: data })
}

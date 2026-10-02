import { request } from './client'

export function getLLMOpsMetrics() {
  return request('/api/llmops/metrics/')
}
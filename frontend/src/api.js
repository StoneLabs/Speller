export async function fetchStrictnessLevels() {
  const response = await fetch('/api/strictness-levels')
  if (!response.ok) throw new Error('Failed to load strictness levels')
  return response.json()
}

function parseError(body, fallback) {
  const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
  return detail || fallback
}

export async function fetchModels({ apiBase, apiKey }) {
  const response = await fetch('/api/models', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_base: apiBase, api_key: apiKey }),
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(parseError(body, `Failed to load models (${response.status})`))
  return body.models || []
}

export async function testConnection({ apiBase, model, apiKey }) {
  const response = await fetch('/api/test-connection', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_base: apiBase,
      model,
      api_key: apiKey,
    }),
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(parseError(body, `Connection failed (${response.status})`))
  return body
}

export async function checkLine({
  targetLine,
  lineNumber,
  contextBefore,
  contextAfter,
  strictness,
  apiBase,
  model,
  apiKey,
}) {
  const response = await fetch('/api/check-line', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_line: targetLine,
      line_number: lineNumber,
      context_before: contextBefore,
      context_after: contextAfter,
      strictness,
      api_base: apiBase,
      model,
      api_key: apiKey,
    }),
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(parseError(body, `Check failed (${response.status})`))
  return body
}

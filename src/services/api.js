// Small wrapper around fetch() for our backend. Every error becomes an ApiError
// whose message can be shown to the user as-is.
export class ApiError extends Error {
  constructor(status, message, data = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status // 0 means the server couldn't be reached
    this.data = data
  }
}

export async function apiFetch(path, { method = 'GET', body, token } = {}) {
  // FormData (file uploads) is sent as-is; the browser sets its Content-Type
  const isForm = body instanceof FormData
  const headers = {}
  if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      body: body === undefined || isForm ? body : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.')
  }

  // 204 No Content has no body; other bodies may not be JSON if something broke
  const data = response.status === 204 ? null : await response.json().catch(() => null)

  if (!response.ok) {
    const detail = data?.detail
    const message = detail?.message ?? 'Something went wrong. Please try again.'
    throw new ApiError(response.status, message, detail)
  }
  return data
}

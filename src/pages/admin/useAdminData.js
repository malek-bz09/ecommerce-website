import { useEffect, useState } from 'react'
import { useAuth } from '../../context/auth'

// Loads data for an admin page, e.g. useAdminData('/admin/products').
// Call reload() after changing something to fetch it again.
export function useAdminData(path) {
  const { authFetch } = useAuth()
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [version, setVersion] = useState(0)

  useEffect(() => {
    // Ignore answers that arrive after the page was left or a newer load started
    let ignore = false
    authFetch(path).then(
      (data) => !ignore && setState({ data, error: null, loading: false }),
      (error) => !ignore && setState({ data: null, error: error.message, loading: false }),
    )
    return () => {
      ignore = true
    }
  }, [authFetch, path, version])

  return { ...state, reload: () => setVersion((v) => v + 1) }
}

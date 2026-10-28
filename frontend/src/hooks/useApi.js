import { useCallback, useEffect, useState } from 'react'

// Loads data from one API call and exposes the three states every screen must
// handle: loading, error (with reload() for the "Thử lại" button) and data.
//
// `deps` works like a dependency list: when any value changes, the call is
// repeated. State is only written when a response arrives; "loading" is derived
// from whether the stored response belongs to the current request.
export function useApi(loader, deps) {
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState({ key: null, data: null, error: null })
  const requestKey = JSON.stringify([...deps, attempt])

  useEffect(() => {
    let cancelled = false
    loader()
      .then((data) => { if (!cancelled) setResult({ key: requestKey, data, error: null }) })
      .catch((error) => { if (!cancelled) setResult({ key: requestKey, data: null, error }) })
    return () => { cancelled = true }
    // `loader` is a new function on every render; requestKey captures its inputs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  const current = result.key === requestKey
  return {
    data: current ? result.data : null,
    error: current ? result.error : null,
    loading: !current,
    reload,
  }
}

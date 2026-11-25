import { useEffect, useState } from 'react'
import { Button } from 'react-bootstrap'

type CheckState =
  | { kind: 'idle' }
  | { kind: 'checking' }
  | { kind: 'success' }
  | { kind: 'error'; message: string }

export function BackendCheck() {
  const [state, setState] = useState<CheckState>({ kind: 'idle' })
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:7071'

  useEffect(() => {
    if (state.kind !== 'checking') return

    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      controller.abort()
      setState({ kind: 'error', message: 'Health check timed out after 5 seconds.' })
    }, 5000)

    async function check() {
      try {
        const url = new URL('api/health', `${baseUrl.replace(/\/+$/, '')}/`)
        if (url.protocol !== 'http:' && url.protocol !== 'https:') {
          throw new Error('VITE_API_BASE_URL must be an absolute HTTP(S) URL.')
        }
        const response = await fetch(url.href, {
          method: 'GET',
          mode: 'cors',
          credentials: 'omit',
          cache: 'no-store',
          redirect: 'error',
          signal: controller.signal,
        })
        if (response.status !== 200) throw new Error(`HTTP ${response.status}.`)
        const body: unknown = await response.json()
        if (typeof body !== 'object' || body === null || !('status' in body) || body.status !== 'ok') {
          throw new Error('Unexpected health response (expected status "ok").')
        }
        if (!controller.signal.aborted) setState({ kind: 'success' })
      } catch (error) {
        if (!controller.signal.aborted) {
          const reason = error instanceof Error ? error.message : 'Unknown request failure.'
          setState({ kind: 'error', message: `Health check failed: ${reason}` })
        }
      } finally {
        window.clearTimeout(timeout)
      }
    }

    void check()
    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [state.kind, baseUrl])

  return <div className="backend-check">
    <Button
      variant="outline-secondary"
      size="sm"
      disabled={state.kind === 'checking'}
      onClick={() => setState({ kind: 'checking' })}
      title={`Check health at ${baseUrl}`}
    >Check backend</Button>
    <span role={state.kind === 'error' ? 'alert' : 'status'} className={state.kind === 'error' ? 'text-danger' : undefined}>
      {state.kind === 'idle' ? 'Not checked.'
        : state.kind === 'checking' ? 'Checking backend...'
          : state.kind === 'success' ? 'Health check passed.'
            : state.message}
    </span>
  </div>
}

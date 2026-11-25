import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BackendCheck } from './BackendCheck'

describe('manual backend health check', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:7071')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  async function check() {
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Check backend' }))
    })
  }

  it('only requests the configured API on click and requires an OK health response', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:7072/')
    vi.mocked(fetch).mockResolvedValue(new Response('{"status":"ok"}'))
    render(<BackendCheck />)
    expect(fetch).not.toHaveBeenCalled()
    await check()
    expect(fetch).toHaveBeenCalledExactlyOnceWith('http://127.0.0.1:7072/api/health', {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
      cache: 'no-store',
      redirect: 'error',
      signal: expect.any(AbortSignal),
    })
    expect(screen.getByRole('status')).toHaveTextContent('Health check passed.')
    await act(async () => { await vi.advanceTimersByTimeAsync(10000) })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['HTTP error', () => Promise.resolve(new Response('unavailable', { status: 503 })), 'HTTP 503'],
    ['wrong payload', () => Promise.resolve(new Response('{"status":"failed"}')), 'Unexpected health response'],
    ['non-JSON response', () => Promise.resolve(new Response('<html>Not the API</html>')), 'Health check failed'],
    ['unavailable host', () => Promise.reject(new TypeError('Failed to fetch')), 'Failed to fetch'],
  ])('reports %s without substituting sample success or retrying', async (_name, response, message) => {
    vi.mocked(fetch).mockImplementation(response)
    render(<BackendCheck />)
    await check()
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(screen.queryByText('Health check passed.')).not.toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(10000) })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('bounds a slow response, aborts it and ignores late success until another click', async () => {
    let finish: (value: Response) => void = () => { throw new Error('Request not started.') }
    vi.mocked(fetch).mockImplementation(() => new Promise<Response>((resolve) => { finish = resolve }))
    render(<BackendCheck />)
    await check()
    expect(screen.getByRole('status')).toHaveTextContent('Checking backend...')
    expect(screen.getByRole('button', { name: 'Check backend' })).toBeDisabled()
    await act(async () => { await vi.advanceTimersByTimeAsync(4999) })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(screen.getByRole('alert')).toHaveTextContent('timed out after 5 seconds')
    expect(vi.mocked(fetch).mock.calls[0][1]?.signal?.aborted).toBe(true)
    await act(async () => { finish(new Response('{"status":"ok"}')) })
    expect(screen.getByRole('alert')).toHaveTextContent('timed out')
    expect(fetch).toHaveBeenCalledTimes(1)
    vi.mocked(fetch).mockResolvedValue(new Response('{"status":"ok"}'))
    await check()
    expect(screen.getByRole('status')).toHaveTextContent('Health check passed.')
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('aborts pending work on unmount and clears the timeout', async () => {
    vi.mocked(fetch).mockImplementation(() => new Promise(() => {}))
    const { unmount } = render(<BackendCheck />)
    await check()
    const signal = vi.mocked(fetch).mock.calls[0][1]?.signal
    unmount()
    expect(signal?.aborted).toBe(true)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('also times out when headers arrive but the response body stalls', async () => {
    const response = new Response()
    vi.spyOn(response, 'json').mockImplementation(() => new Promise(() => {}))
    vi.mocked(fetch).mockResolvedValue(response)
    render(<BackendCheck />)
    await check()
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(screen.getByRole('alert')).toHaveTextContent('timed out after 5 seconds')
    expect(vi.mocked(fetch).mock.calls[0][1]?.signal?.aborted).toBe(true)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('reports invalid configuration without falling back to another address', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    render(<BackendCheck />)
    await check()
    expect(screen.getByRole('alert')).toHaveTextContent('Health check failed')
    expect(fetch).not.toHaveBeenCalled()
  })
})

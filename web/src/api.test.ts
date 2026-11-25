import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, listProjects, loadProject, saveProject } from './api'

const size = { width: 1600, height: 900 }
const detail = {
  project_id: 'trip', canvas: size,
  photos: [{ photo_id: 1, width: 20, height: 10 }, { photo_id: 2, width: 10, height: 20 }],
}
const files = [new File(['a'], 'a.jpg'), new File(['b'], 'b.png')]
function signal() { return new AbortController().signal }
function response(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status })
}
beforeEach(() => { vi.useFakeTimers() })

describe('bounded API requests', () => {
  it('includes response parsing in the read deadline', async () => {
    vi.mocked(fetch).mockResolvedValue({
      status: 200, json: () => new Promise(() => {}),
    } as Response)
    const result = expect(listProjects(signal())).rejects.toMatchObject({ message: 'Backend request timed out.' })
    await vi.advanceTimersByTimeAsync(10_000)
    await result
    expect(vi.mocked(fetch).mock.calls[0][1]?.signal?.aborted).toBe(true)
  })

  it('marks a timed-out create as uncertain without retrying', async () => {
    vi.mocked(fetch).mockImplementation(() => new Promise(() => {}))
    const result = expect(saveProject('trip', size, files, signal())).rejects.toMatchObject({ uncertain: true })
    await vi.advanceTimersByTimeAsync(59_999)
    expect(fetch).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1)
    await result
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('cancels requests, clears timers and never sends an already-aborted request', async () => {
    vi.mocked(fetch).mockImplementation(() => new Promise(() => {}))
    const controller = new AbortController()
    const result = expect(listProjects(controller.signal)).rejects.toMatchObject({ name: 'AbortError' })
    controller.abort()
    await result
    expect(vi.getTimerCount()).toBe(0)
    await expect(listProjects(controller.signal)).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('handles host HTML, useful application errors and lost create responses honestly', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response('<html>too large</html>', { status: 413 }))
      .mockResolvedValueOnce(new Response('', { status: 500 }))
      .mockResolvedValueOnce(response({ error: { code: 'project_exists', message: 'Already saved.' } }, 409))
      .mockRejectedValueOnce(new TypeError('disconnected'))
    await expect(saveProject('trip', size, files, signal())).rejects.toMatchObject({ status: 413, uncertain: false })
    await expect(saveProject('trip', size, files, signal())).rejects.toMatchObject({ status: 500, uncertain: true })
    await expect(saveProject('trip', size, files, signal())).rejects.toMatchObject({
      status: 409, code: 'project_exists', message: 'Already saved.',
    })
    await expect(saveProject('trip', size, files, signal())).rejects.toMatchObject({ uncertain: true })
    expect(fetch).toHaveBeenCalledTimes(4)
  })

  it('rejects malformed, mismatched and out-of-order success DTOs', async () => {
    for (const value of [
      { ...detail, canvas: { width: '1600', height: 900 } },
      { ...detail, project_id: '../trip' },
      { ...detail, photos: [...detail.photos].reverse() },
      { ...detail, photos: [{ photo_id: 1, width: 40_000_000, height: 2 }, detail.photos[1]] },
      { ...detail, project_id: 'other' },
    ]) {
      vi.mocked(fetch).mockResolvedValueOnce(response(value, 201))
      await expect(saveProject('trip', size, files, signal())).rejects.toBeInstanceOf(ApiError)
    }
    vi.mocked(fetch).mockResolvedValueOnce(response({
      projects: [1, 2].map(() => ({ project_id: 'trip', canvas: size, photo_count: 2 })),
    }))
    await expect(listProjects(signal())).rejects.toThrow('Unexpected project-list')
  })

  it('validates independently loaded identity and omits credentials/storage paths', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response(detail))
    expect(await loadProject('trip', signal())).toEqual({
      id: 'trip', kind: 'saved', canvas: size, photos: [
        { number: 1, src: 'http://127.0.0.1:7071/api/projects/trip/photos/1' },
        { number: 2, src: 'http://127.0.0.1:7071/api/projects/trip/photos/2' },
      ],
    })
    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:7071/api/projects/trip', expect.objectContaining({
      credentials: 'omit', cache: 'no-store', redirect: 'error', mode: 'cors',
    }))
    expect(vi.getTimerCount()).toBe(0)
  })
})

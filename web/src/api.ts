import { projectIdError } from './projects'
import type { Project } from './projects'

export interface Summary {
  project_id: string
  canvas: { width: number; height: number }
  photo_count: number
}

export class ApiError extends Error {
  status: number
  code: string
  uncertain: boolean

  constructor(message: string, status = 0, code = '', uncertain = false) {
    super(message)
    this.status = status
    this.code = code
    this.uncertain = uncertain
  }
}

export function apiUrl(path: string) {
  const base = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:7071'
  try {
    const url = new URL(path, `${base.replace(/\/+$/, '')}/`)
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error()
    return url.href
  } catch {
    throw new ApiError('VITE_API_BASE_URL must be an absolute HTTP(S) URL without credentials.')
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function integer(value: unknown, min: number, max: number): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= min && value <= max
}

function canvas(value: unknown): value is Summary['canvas'] {
  return record(value) && integer(value.width, 1, 4096) && integer(value.height, 1, 4096)
}

function validId(value: unknown): value is string {
  return typeof value === 'string' && !projectIdError(value)
}

interface RequestOptions {
  body?: FormData | string
  timeout?: number
  statuses?: number[]
  json?: boolean
  binary?: boolean
}

export async function request(path: string, signal: AbortSignal, options: RequestOptions = {}): Promise<unknown> {
  const { body, timeout = body ? 60_000 : 10_000, statuses = [body ? 201 : 200], json = false } = options
  const url = apiUrl(path)
  const controller = new AbortController()
  if (signal.aborted) throw new DOMException('Request cancelled.', 'AbortError')
  let cancel: () => void = () => {}
  let timer: ReturnType<typeof setTimeout> | undefined
  const deadline = new Promise<never>((_, reject) => {
    cancel = () => {
      controller.abort()
      reject(new DOMException('Request cancelled.', 'AbortError'))
    }
    timer = setTimeout(() => {
      controller.abort()
      reject(new ApiError('Backend request timed out.', 0, '', Boolean(body)))
    }, timeout)
  })
  signal.addEventListener('abort', cancel, { once: true })
  const work = async () => {
    let response: Response
    try {
      response = await fetch(url, {
        method: body ? 'POST' : 'GET', body, signal: controller.signal,
        ...(json ? { headers: { 'Content-Type': 'application/json' } } : {}),
        mode: 'cors', credentials: 'omit', cache: 'no-store', redirect: 'error',
      })
    } catch (error) {
      if (controller.signal.aborted) throw error
      throw new ApiError('Could not reach the backend. Check that it is running and the API address/CORS are correct.',
        0, '', Boolean(body))
    }
    let value: unknown
    if (options.binary && statuses.includes(response.status)) {
      if (response.headers.get('Content-Type')?.split(';', 1)[0].trim() !== 'image/png') {
        throw new ApiError('Backend did not return a PNG. No image was downloaded.')
      }
      return await response.blob()
    }
    try {
      value = await response.json()
    } catch {
      throw new ApiError(`Backend returned HTTP ${response.status} without valid JSON.`,
        response.status, '', Boolean(body) && (json || response.status !== 413))
    }
    if (!statuses.includes(response.status)) {
      const error = record(value) && record(value.error) ? value.error : null
      throw new ApiError(
        error && typeof error.message === 'string' ? error.message : `Backend returned HTTP ${response.status}.`,
        response.status, error && typeof error.code === 'string' ? error.code : '',
        Boolean(body) && (json || response.status >= 500),
      )
    }
    return value
  }
  try {
    return await Promise.race([work(), deadline])
  } finally {
    clearTimeout(timer)
    signal.removeEventListener('abort', cancel)
  }
}

function project(value: unknown): Project {
  if (!record(value) || !validId(value.project_id) || !canvas(value.canvas) ||
      !Array.isArray(value.photos) || value.photos.length < 2 || value.photos.length > 6) {
    throw new ApiError('Unexpected saved-project response.', 0, '', true)
  }
  const id = value.project_id
  const photos = value.photos.map((photo: unknown, index: number) => {
    if (!record(photo) || photo.photo_id !== index + 1 ||
        !integer(photo.width, 1, 40_000_000) || !integer(photo.height, 1, 40_000_000) ||
        photo.width * photo.height > 40_000_000) {
      throw new ApiError('Unexpected saved-photo response.', 0, '', true)
    }
    return { number: index + 1, src: apiUrl(`api/projects/${id}/photos/${index + 1}`) }
  })
  return { id, canvas: value.canvas, photos }
}

export async function listProjects(signal: AbortSignal): Promise<Summary[]> {
  const value = await request('api/projects', signal)
  if (!record(value) || !Array.isArray(value.projects)) throw new ApiError('Unexpected project-list response.')
  const ids = new Set<string>()
  return value.projects.map((item: unknown) => {
    if (!record(item) || !validId(item.project_id) || !canvas(item.canvas) ||
        !integer(item.photo_count, 2, 6) || ids.has(item.project_id)) {
      throw new ApiError('Unexpected project-list response.')
    }
    ids.add(item.project_id)
    return { project_id: item.project_id, canvas: item.canvas, photo_count: item.photo_count }
  })
}

export async function loadProject(id: string, signal: AbortSignal): Promise<Project> {
  const result = project(await request(`api/projects/${encodeURIComponent(id)}`, signal))
  if (result.id !== id) throw new ApiError('Backend returned a different project.')
  return result
}

export async function saveProject(id: string, size: Project['canvas'], files: File[], signal: AbortSignal) {
  const body = new FormData()
  body.append('metadata', JSON.stringify({ project_id: id, canvas: size }))
  files.forEach((file, index) => body.append(`photo_${index + 1}`, file))
  const result = project(await request('api/projects', signal, { body }))
  if (result.id !== id || result.canvas.width !== size.width || result.canvas.height !== size.height ||
      result.photos.length !== files.length) throw new ApiError('Backend returned a different project.', 0, '', true)
  return result
}

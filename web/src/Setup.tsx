import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Form } from 'react-bootstrap'
import { Link } from './Link'
import { ApiError, loadProject, saveProject } from './api'
import { canvasPresets, projectIdError } from './projects'
import type { Photo, Project } from './projects'

interface LocalPhoto extends Photo {
  status: 'loading' | 'ready' | 'error'
  file: File
}

export function Setup({ onCreate, onUncertain }: {
  onCreate: (project: Project) => void
  onUncertain: (id: string) => void
}) {
  const [id, setId] = useState('')
  const [selected, setSelected] = useState<LocalPhoto[]>([])
  const [error, setError] = useState('')
  const [preset, setPreset] = useState('2:3')
  const [width, setWidth] = useState('1200')
  const [height, setHeight] = useState('1800')
  const urls = useRef<string[]>([])
  const pending = useRef<AbortController | null>(null)
  const pendingCreate = useRef('')
  const [busy, setBusy] = useState(false)
  const [lookupId, setLookupId] = useState('')

  useEffect(() => () => {
    pending.current?.abort()
    if (pendingCreate.current) onUncertain(pendingCreate.current)
    urls.current.forEach((url) => URL.revokeObjectURL(url))
  }, [onUncertain])

  function chooseFiles(files: FileList | null) {
    urls.current.forEach((url) => URL.revokeObjectURL(url))
    urls.current = []
    setSelected([])
    setError('')
    const values = Array.from(files ?? [])
    if (!values.length) return
    if (values.length < 2 || values.length > 6) {
      setError('Choose between 2 and 6 photos together.')
      return
    }
    if (values.some((file) => !['image/jpeg', 'image/png'].includes(file.type))) {
      setError('Choose JPEG or PNG photos only.')
      return
    }
    if (values.some((file) => file.size > 25 * 1024 * 1024)) {
      setError('Each photo must be 25 MiB or smaller.')
      return
    }
    setSelected(values.map((file, index) => {
      const src = URL.createObjectURL(file)
      urls.current.push(src)
      return { number: index + 1, src, status: 'loading', file }
    }))
  }

  function imageStatus(src: string, status: LocalPhoto['status']) {
    setSelected((previous) => previous.map((photo) => photo.src === src ? { ...photo, status } : photo))
  }

  async function create() {
    if (pending.current) return
    const invalidId = projectIdError(id)
    if (invalidId) {
      setError(invalidId)
      return
    }
    if (![width, height].every((value) => /^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 4096)) {
      setError('Width and height must each be whole pixels from 1 to 4096.')
      return
    }
    if (selected.length < 2 || selected.some((photo) => photo.status !== 'ready')) {
      setError('Choose 2-6 readable photos and wait for their previews to load.')
      return
    }
    const controller = new AbortController()
    pending.current = controller
    pendingCreate.current = id
    setBusy(true)
    setError('')
    setLookupId('')
    try {
      const project = await saveProject(id, { width: Number(width), height: Number(height) },
        selected.map((photo) => photo.file), controller.signal)
      if (!controller.signal.aborted) {
        pendingCreate.current = ''
        onCreate(project)
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        const uncertain = cause instanceof ApiError && cause.uncertain
        setError(`${cause instanceof Error ? cause.message : 'Project could not be saved.'}${uncertain
          ? ' The project may have been saved. Check its saved state before trying again.' : ''}`)
        if (uncertain || (cause instanceof ApiError && ['project_exists', 'project_busy'].includes(cause.code))) {
          setLookupId(id)
        }
      }
    } finally {
      if (!controller.signal.aborted) {
        pendingCreate.current = ''
        pending.current = null
        setBusy(false)
      }
    }
  }

  async function checkSaved() {
    if (pending.current) return
    const controller = new AbortController()
    pending.current = controller
    setBusy(true)
    try {
      const project = await loadProject(lookupId, controller.signal)
      if (!controller.signal.aborted) onCreate(project)
    } catch (cause) {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Lookup failed.')
    } finally {
      if (!controller.signal.aborted) {
        pending.current = null
        setBusy(false)
      }
    }
  }

  return <>
    <div className="page-heading"><h1>New project</h1></div>
    <Form className="surface project-setup" noValidate onSubmit={(event) => {
      event.preventDefault()
      void create()
    }}>
      <fieldset className="setup-fields" disabled={busy}>
        <Form.Group controlId="project-id">
          <Form.Label>Project ID</Form.Label>
          <Form.Control value={id} placeholder="project-1" aria-describedby="id-help" maxLength={64}
            onChange={(event) => setId(event.currentTarget.value)} />
          <Form.Text id="id-help">Lowercase letters, digits and hyphens; used in the project URL.</Form.Text>
        </Form.Group>
        <fieldset className="canvas-fields">
          <legend>Canvas</legend>
          <Form.Group controlId="canvas">
            <Form.Label>Canvas preset</Form.Label>
            <Form.Select value={preset} onChange={(event) => {
              const value = event.currentTarget.value
              setPreset(value)
              const choice = canvasPresets.find((item) => item.value === value)
              if (choice) {
                setWidth(String(choice.width))
                setHeight(String(choice.height))
              }
            }}>
              {canvasPresets.map((item) => <option key={item.value} value={item.value}>
                {item.label} - {item.width} x {item.height}
              </option>)}
              <option value="custom">Custom pixels</option>
            </Form.Select>
          </Form.Group>
          <div className="canvas-dimensions">
            <Form.Group controlId="canvas-width">
              <Form.Label>Width (px)</Form.Label>
              <Form.Control type="number" min={1} max={4096} step={1} value={width}
                aria-describedby="canvas-help" onChange={(event) => {
                  setWidth(event.currentTarget.value)
                  setPreset('custom')
                }} />
            </Form.Group>
            <Form.Group controlId="canvas-height">
              <Form.Label>Height (px)</Form.Label>
              <Form.Control type="number" min={1} max={4096} step={1} value={height}
                aria-describedby="canvas-help" onChange={(event) => {
                  setHeight(event.currentTarget.value)
                  setPreset('custom')
                }} />
            </Form.Group>
          </div>
          <Form.Text id="canvas-help">1-4096 pixels per side, matching the Python layout contract.</Form.Text>
        </fieldset>
      </fieldset>
      <fieldset className="setup-photos" disabled={busy}>
        <Form.Group controlId="photos">
          <Form.Label>Choose 2-6 photos</Form.Label>
          <input id="photos" className="form-control" type="file" accept="image/jpeg,image/png" multiple
            aria-describedby="photo-help" onChange={(event) => chooseFiles(event.currentTarget.files)} />
          <Form.Text id="photo-help">JPEG/PNG, up to 25 MiB each. Uploaded only when you create the project.</Form.Text>
        </Form.Group>
        <div className="photo-strip local-photos" aria-label="Selected photos">
          {selected.map((photo) => <figure key={photo.src} className="photo-tile">
            <img src={photo.src} alt={`Selected photo ${photo.number}`}
              onLoad={() => imageStatus(photo.src, 'ready')}
              onError={() => imageStatus(photo.src, 'error')} />
            <figcaption>{photo.number}</figcaption>
          </figure>)}
        </div>
        {selected.some((photo) => photo.status === 'error') &&
          <Alert variant="warning" role="alert">Could not display a selected photo. Choose readable JPEG or PNG files.</Alert>}
      </fieldset>
      <div className="setup-actions">
        {error && <Alert variant="warning" role="alert">{error}</Alert>}
        <p>Photos and canvas settings will be saved locally by the backend. Rendering and chat are not connected yet.</p>
        <p>Leaving while saving does not guarantee cancellation. Check the saved project before trying again.</p>
        <div className="d-flex flex-wrap gap-2">
          <Button type="submit" disabled={busy}>{busy ? 'Working...' : 'Create project'}</Button>
          {lookupId && <Button variant="outline-primary" disabled={busy} onClick={() => void checkSaved()}>
            Check saved project {lookupId}
          </Button>}
          <Link href="/" className="btn btn-outline-secondary">Cancel</Link>
        </div>
      </div>
    </Form>
  </>
}

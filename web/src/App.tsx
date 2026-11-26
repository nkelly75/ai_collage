import { useEffect, useState } from 'react'
import { Alert, Badge, Button, Container } from 'react-bootstrap'
import { ApiError, listProjects, loadProject } from './api'
import type { Summary } from './api'
import { Link } from './Link'
import { navigate, usePath } from './navigation'
import { projectIdError } from './projects'
import type { Project } from './projects'
import { RealWorkspace } from './RealWorkspace'
import { Setup } from './Setup'

function Projects() {
  const [items, setItems] = useState<Summary[] | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    void listProjects(controller.signal).then((value) => {
      if (!controller.signal.aborted) setItems(value)
    }, (cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not load projects.')
    })
    return () => controller.abort()
  }, [attempt])
  return <>
    <div className="page-heading"><h1>Projects</h1><Link href="/new" className="btn btn-primary">New project</Link></div>
    {error ? <Alert variant="warning" role="alert">{error}{' '}
      <Button size="sm" variant="outline-secondary" onClick={() => {
        setError(''); setItems(null); setAttempt((value) => value + 1)
      }}>Retry</Button></Alert>
      : items === null ? <p role="status">Loading projects...</p>
        : items.length === 0 ? <p>No saved projects yet.</p>
          : <div className="surface project-list">{items.map((item) => <article className="project-row" key={item.project_id}>
            <div><Link href={`/projects/${item.project_id}`} className="project-link">{item.project_id}</Link>
              <p>{item.photo_count} photos / {item.canvas.width} x {item.canvas.height} px</p></div>
            <Badge bg="light" text="dark">Saved locally</Badge>
          </article>)}</div>}
  </>
}

function SavedProject({ id }: { id: string }) {
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState('')
  const [missing, setMissing] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    void loadProject(id, controller.signal).then((value) => {
      if (!controller.signal.aborted) setProject(value)
    }, (cause: unknown) => {
      if (!controller.signal.aborted) {
        setError(cause instanceof Error ? cause.message : 'Could not load project.')
        setMissing(cause instanceof ApiError && cause.status === 404)
      }
    })
    return () => controller.abort()
  }, [id, attempt])
  if (error) return <div className="page-heading not-found">
    <h1>{missing ? 'Project not found' : 'Could not load project'}</h1>
    <Alert variant="warning" role="alert">{error}</Alert>
    <Button variant="outline-secondary" onClick={() => {
      setError(''); setAttempt((value) => value + 1)
    }}>Retry</Button>{' '}<Link href="/">Back to projects</Link>
  </div>
  if (!project) return <p role="status">Loading project...</p>
  return <RealWorkspace project={project} />
}

export default function App() {
  const path = usePath()
  const [uncertainId, setUncertainId] = useState('')
  const id = path.startsWith('/projects/') ? path.slice('/projects/'.length) : ''
  const isProject = Boolean(id) && !projectIdError(id)
  useEffect(() => {
    document.title = `${isProject ? id : path === '/new' ? 'New project' : 'Projects'} - Collage studio`
  }, [id, isProject, path])
  return <Container fluid className={`app-shell${isProject ? ' project-shell' : ''}`}>
    <a className="visually-hidden-focusable skip-link" href="#main">Skip to content</a>
    <header className="app-header">
      <Link href="/" className="brand">Collage studio</Link>
      <nav aria-label="Main navigation">
        <Link href="/" aria-current={path === '/' ? 'page' : undefined}>Projects</Link>
        <Link href="/new" aria-current={path === '/new' ? 'page' : undefined}>New project</Link>
      </nav>
    </header>
    <div className="storage-notice">
      Local project storage. Conversations use the backend; original photos are rendered without AI image regeneration.
    </div>
    <main id="main">
      {uncertainId && <Alert variant="warning" role="alert" dismissible onClose={() => setUncertainId('')}>
        Creation of {uncertainId} may have finished after you left setup.{' '}
        <Link href={`/projects/${uncertainId}`} onClick={() => setUncertainId('')}>
          Check saved project {uncertainId}
        </Link> before trying again.
      </Alert>}
      {path === '/' ? <Projects />
        : path === '/new' ? <Setup onUncertain={setUncertainId} onCreate={(project) => navigate(`/projects/${project.id}`)} />
          : isProject ? <SavedProject id={id} key={id} />
            : <div className="page-heading not-found"><h1>Page not found</h1><Link href="/">Back to projects</Link></div>}
    </main>
  </Container>
}

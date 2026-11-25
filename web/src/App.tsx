import { useEffect, useRef, useState } from 'react'
import { Badge, Button, Container } from 'react-bootstrap'
import { BackendCheck } from './BackendCheck'
import { Link } from './Link'
import { navigate, usePath } from './navigation'
import { sampleProject } from './projects'
import type { Project } from './projects'
import { Setup } from './Setup'
import { Workspace } from './Workspace'
import { useDemo } from './useDemo'

function Session({ onReset }: { onReset: () => void }) {
  const [projects, setProjects] = useState<Project[]>([sampleProject])
  const ownedUrls = useRef<string[]>([])
  const path = usePath()
  const demo = useDemo()
  const project = projects.find((item) => path === `/projects/${item.id}`)

  useEffect(() => () => {
    ownedUrls.current.forEach((url) => URL.revokeObjectURL(url))
  }, [])

  useEffect(() => {
    document.title = `${project?.id ?? (path === '/' ? 'Projects' : path === '/new' ? 'New project' : 'Not found')} - Collage studio`
  }, [path, project])

  function create(project: Project) {
    ownedUrls.current.push(...project.photos.map((photo) => photo.src))
    setProjects((previous) => [...previous, project])
    navigate(`/projects/${project.id}`)
  }

  return <Container fluid className={`app-shell${project ? ' project-shell' : ''}`}>
    <a className="visually-hidden-focusable skip-link" href="#main">Skip to content</a>
    <header className="app-header">
      <Link href="/" className="brand">Collage studio</Link>
      <nav aria-label="Main navigation">
        <Link href="/" aria-current={path === '/' ? 'page' : undefined}>Projects</Link>
        <Link href="/new" aria-current={path === '/new' ? 'page' : undefined}>New project</Link>
        <Button variant="outline-secondary" size="sm" onClick={onReset}>Reset prototype</Button>
      </nav>
    </header>
    <div className="sample-notice">
      <span><strong>Frontend prototype.</strong> Projects and chat are browser-only and reset on refresh. No AI.</span>
      <BackendCheck />
    </div>
    <main id="main">
      {project ? <Workspace key={project.id} project={project} demo={demo} />
        : path === '/new' ? <Setup onCreate={create} projectIds={projects.map((item) => item.id)} />
          : path === '/' ? <>
            <div className="page-heading">
              <h1>Projects</h1>
              <Link href="/new" className="btn btn-primary">New project</Link>
            </div>
            <div className="surface project-list">
              {projects.map((item) => <article key={item.id} className="project-row">
                <div>
                  <Link href={`/projects/${item.id}`} className="project-link">{item.id}</Link>
                  <p>{item.photos.length} photos / {item.canvas.width} x {item.canvas.height} px</p>
                </div>
                <Badge bg="light" text="dark">{item.kind === 'sample' ? 'Scripted sample' : 'Browser draft'}</Badge>
              </article>)}
            </div>
          </> : <div className="page-heading not-found">
            <h1>Project or page not found</h1>
            <p>Browser drafts are cleared on refresh. No saved projects are loaded by this prototype.</p>
            <Link href="/">Back to projects</Link>
          </div>}
    </main>
  </Container>
}

export default function App() {
  const [session, setSession] = useState(0)
  return <Session key={session} onReset={() => {
    navigate('/')
    setSession((value) => value + 1)
  }} />
}

import { useEffect, useRef, useState } from 'react'
import { Alert, Badge, Button, Form, Spinner } from 'react-bootstrap'
import { proposals } from './demo'
import { PhotoStrip } from './PhotoStrip'
import type { Project } from './projects'
import type { useDemo } from './useDemo'

export function Workspace({ project, demo }: { project: Project; demo: ReturnType<typeof useDemo> }) {
  const [draft, setDraft] = useState('')
  const end = useRef<HTMLDivElement>(null)
  const isSample = project.kind === 'sample'
  const active = isSample && demo.active ? proposals[demo.active] : null

  useEffect(() => {
    end.current?.scrollIntoView?.({ block: 'nearest', behavior: 'instant' })
  }, [demo.messages.length, demo.progress])

  return <div className="workspace">
    <div className="page-heading workspace-heading">
      <h1>{project.id}</h1>
      <span>{project.photos.length} photos / {project.canvas.width} x {project.canvas.height} px
        <Badge bg="light" text="dark">{isSample ? 'Scripted sample' : 'Browser draft'}</Badge>
      </span>
    </div>
    {isSample ? <div className="workspace-grid">
      <section className="surface conversation-panel" aria-labelledby="conversation-title">
        <div className="panel-heading"><h2 id="conversation-title">Conversation</h2></div>
        <div className="message-list" role="log" aria-label="Conversation" aria-live="polite">
          {demo.messages.map((message) => {
            const proposal = message.proposal ? proposals[message.proposal] : null
            return <article key={message.id}
              className={`message message-${message.role}${proposal ? ' message-with-proposal' : ''}`}>
              <div className="message-copy">
                <p className="message-author">{message.role === 'user' ? 'You' : 'Assistant'}</p>
                <p>{message.text}</p>
              </div>
              {proposal && <div className="proposal-card">
                <img src={proposal.image} alt={`Proposal ${proposal.id} thumbnail`} />
                <span>{proposal.id}{demo.active === proposal.id && ' / Active'}</span>
                <Button size="sm" variant="outline-primary"
                  aria-label={`Continue from here: ${proposal.id}`}
                  disabled={demo.busy || demo.active === proposal.id}
                  onClick={() => demo.select(proposal.id)}>Use {proposal.id}</Button>
              </div>}
            </article>
          })}
          <div ref={end} />
        </div>
        <div className="composer">
          <div className="progress-line" role="status">
            {demo.busy
              ? <><Spinner size="sm" animation="border" aria-hidden="true" /> {demo.progress} (simulated)</>
              : demo.next ? null : 'Sample walkthrough complete.'}
          </div>
          {demo.error && <Alert variant="warning" className="small py-2" role="alert">{demo.error}</Alert>}
          {demo.next && <Button variant="light" className="suggested-prompt" disabled={demo.busy}
            aria-label={`Use suggested message: ${demo.next.prompt}`}
            onClick={() => setDraft(demo.next?.prompt ?? '')}>{demo.next.prompt}</Button>}
          <Form onSubmit={(event) => {
            event.preventDefault()
            if (demo.submit(draft)) setDraft('')
          }}>
            <Form.Group controlId="prompt">
              <Form.Label className="visually-hidden">Your message</Form.Label>
              <Form.Control as="textarea" rows={2} placeholder="Use the suggested message above"
                value={draft} disabled={demo.busy} aria-describedby="prompt-help"
                onChange={(event) => setDraft(event.currentTarget.value)} />
            </Form.Group>
            <div className="composer-actions">
              <span id="prompt-help">Scripted messages only.</span>
              <Button type="submit" disabled={demo.busy || !draft.trim()}>Send</Button>
            </div>
          </Form>
        </div>
      </section>
      <section className="surface preview-panel" aria-labelledby="preview-title">
        <div className="panel-heading">
          <h2 id="preview-title">Preview</h2>
          {active && <span>Baseline: {active.id}</span>}
        </div>
        <div className="preview-stage">
          {active ? <img className="active-preview" src={active.image} alt={`Proposal ${active.id}`} />
            : <p className="empty-note">Send the first suggested message to see a sample proposal.</p>}
        </div>
        <div className="preview-details">
          <PhotoStrip items={project.photos} />
          <div className="preview-actions">
            <Button disabled={!active || demo.busy || demo.accepted === demo.active} onClick={demo.accept}>
              {active && demo.accepted === demo.active ? 'Accepted' : 'Accept proposal'}
            </Button>
            {active ? <a className="btn btn-outline-secondary" href={active.image}
              download={`london-${active.id}-sample.png`}>Download PNG</a>
              : <Button variant="outline-secondary" disabled>Download PNG</Button>}
          </div>
          <p className="acceptance-note">{demo.accepted
            ? `Accepted: ${demo.accepted} (this tab only)` : 'No accepted proposal'}</p>
          <p className="visually-hidden" role="status">{demo.notice}</p>
        </div>
      </section>
    </div> : <section className="surface draft-details" aria-labelledby="photos-title">
      <h2 id="photos-title">Photos</h2>
      <PhotoStrip items={project.photos} />
      <p className="empty-note">Browser draft only. Rendering and chat for your own photos are not connected.</p>
    </section>}
  </div>
}

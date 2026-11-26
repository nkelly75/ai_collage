import { useCallback, useEffect, useRef, useState } from 'react'
import { Alert, Badge, Button, Form, Modal, Spinner } from 'react-bootstrap'
import { downloadCollage, previewUrl } from './conversationApi'
import { PhotoStrip } from './PhotoStrip'
import type { Project } from './projects'
import { useConversation } from './useConversation'

function PreviewLoading({ message, overlay = false }: { message: string; overlay?: boolean }) {
  return <p className={overlay ? 'preview-update' : 'preview-loading empty-note'} aria-live="polite">
    <Spinner as="span" size="sm" animation="border" aria-hidden="true" /> {message}
  </p>
}

function Preview({ projectId, proposalId, current = false, updating = false }: {
  projectId: string; proposalId: string; current?: boolean; updating?: boolean
}) {
  const [failed, setFailed] = useState(false)
  const [loaded, setLoaded] = useState(false)
  return failed ? <p role="alert">Preview {proposalId} could not load. The saved proposal may be unavailable.
    {' '}<Button size="sm" variant="outline-secondary" onClick={() => setFailed(false)}>Reload preview</Button></p>
    : <>
      {(!loaded || updating) && <PreviewLoading overlay={current}
        message={updating ? 'Updating current collage...' : `Loading preview ${proposalId}...`} />}
      <img className="active-preview" crossOrigin="anonymous" src={previewUrl(projectId, proposalId)}
        alt={`Proposal ${proposalId}`} aria-busy={!loaded || updating} onLoad={() => setLoaded(true)}
        onError={() => { setLoaded(false); setFailed(true) }} />
    </>
}

function Download({ projectId, proposalId }: { projectId: string; proposalId: string }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const active = useRef<AbortController | null>(null)
  useEffect(() => () => active.current?.abort(), [])
  const download = async () => {
    if (active.current && !active.current.signal.aborted) return
    const controller = new AbortController()
    active.current = controller
    setBusy(true)
    setError('')
    try { await downloadCollage(projectId, proposalId, controller.signal) }
    catch (error) {
      if (!controller.signal.aborted) setError(error instanceof Error ? error.message : 'PNG download failed.')
    } finally {
      if (!controller.signal.aborted) {
        active.current = null
        setBusy(false)
      }
    }
  }
  return <div className="collage-download">
    <Button size="sm" variant="outline-primary" onClick={() => { void download() }} disabled={busy}>
      {busy ? 'Downloading PNG...' : 'Download PNG'}
    </Button>
    {error && <p role="alert">{error} Try downloading again.</p>}
  </div>
}

function Thumbnail({ projectId, proposalId, onOpen }: { projectId: string; proposalId: string; onOpen: () => void }) {
  const [failed, setFailed] = useState(false)
  return <Button variant="link" className="history-thumbnail" aria-label={`View collage ${proposalId}`} onClick={onOpen}>
    {failed ? <span>Thumbnail unavailable; open saved preview.</span>
      : <img loading="lazy" crossOrigin="anonymous" src={previewUrl(projectId, proposalId)}
        alt={`Collage ${proposalId} thumbnail`} onError={() => setFailed(true)} />}
    <span>Collage {proposalId}</span>
  </Button>
}

export function RealWorkspace({ project }: { project: Project }) {
  const [draft, setDraft] = useState('')
  const [viewed, setViewed] = useState<string | null>(null)
  const [confirmation, setConfirmation] = useState<{ revision: string; text: string } | null>(null)
  const [attempted, setAttempted] = useState(false)
  const selectionSaved = useCallback(() => { setViewed(null); setAttempted(false) }, [])
  const conversation = useConversation(project.id, selectionSaved)
  const end = useRef<HTMLDivElement>(null)
  const { snapshot, operation, busy, blocked } = conversation
  const baseline = snapshot?.baseline?.proposal_id
  const completedProposal = conversation.selectionActionId && conversation.selectionOutcome?.status === 'completed'
    ? conversation.selectionOutcome.proposal_id : operation?.status === 'completed' ? operation.proposal_id : null
  const updating = busy === 'checking' && Boolean(completedProposal && completedProposal !== baseline)
  const understanding = busy === 'interpreting' || operation?.status === 'interpreting'
  const creating = busy === 'generating' || operation?.status === 'generating'
  const failed = Boolean(conversation.failure) || operation?.status === 'failed'
  const confirmed = operation?.status === 'completed' || failed
  const unknown = blocked && snapshot !== null && !confirmed || operation?.status === 'uncertain'
  const working = understanding || creating
  const pending = !conversation.submission && !operation && !working ? snapshot?.pending : null
  const recovery = blocked || conversation.paused || Boolean(operation) || snapshot?.live_enabled === false
  const displayed = snapshot?.proposals.find((item) => item.proposal_id === viewed)
  const currentProposal = snapshot?.proposals.find((item) => item.proposal_id === baseline)
  const redundant = viewed === baseline && !snapshot?.selection.confirmation
  const showHistory = (id: string) => { setViewed(id); setConfirmation(null); setAttempted(false) }
  const choose = async (confirmed = false) => {
    if (!viewed || !snapshot || !conversation.canSelect) return
    if (!confirmed && snapshot.selection.confirmation) {
      setConfirmation({ revision: snapshot.revision, text: snapshot.selection.confirmation })
      return
    }
    setAttempted(true)
    const saved = await conversation.select(viewed, confirmed, confirmed ? confirmation?.revision : snapshot.revision)
    setConfirmation(null)
    if (saved) { setViewed(null); setAttempted(false) }
  }

  const submit = () => {
    if (conversation.send(draft)) setDraft('')
  }

  useEffect(() => {
    end.current?.scrollIntoView?.({ block: 'nearest', behavior: 'instant' })
  }, [snapshot?.messages.length, conversation.submission, busy, operation?.status])

  return <div className="workspace">
    <div className="page-heading workspace-heading"><h1>{project.id}</h1>
      <span>{project.photos.length} photos / {project.canvas.width} x {project.canvas.height} px
        <Badge bg="light" text="dark">Saved locally</Badge></span></div>
    <div className="workspace-grid">
      <section className="surface conversation-panel" aria-labelledby="conversation-title">
        <div className="panel-heading"><h2 id="conversation-title">Conversation</h2>
          {!recovery && <Button size="sm" variant="outline-secondary" onClick={conversation.check}
            disabled={Boolean(busy)} aria-label="Refresh saved conversation and preview"
            title="Refresh saved conversation and preview">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 12a9 9 0 0 1 15.36-6.36L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.36 6.36L3 16M8 16H3v5" />
            </svg>
          </Button>}
        </div>
        <div className="message-list" role="log" aria-label="Conversation" aria-live="polite">
          {snapshot?.messages.map((item) => <article className={`message message-${item.role}`} key={item.id}>
            <p className="message-author">{item.role === 'user' ? 'You' : item.role === 'activity' ? 'Activity' : 'Assistant'}</p>
            <p className="message-text">{item.text}</p>
            {item.proposal_id && <Thumbnail projectId={project.id} proposalId={item.proposal_id}
              onOpen={() => { if (item.proposal_id) showHistory(item.proposal_id) }} />}
          </article>)}
          {conversation.submission && <article className="message message-user">
            <p className="message-author">You</p><p className="message-text">{conversation.submission.prompt}</p>
          </article>}
          {snapshot?.messages.length === 0 && !conversation.submission &&
            <p className="empty-note">Describe the collage you would like to make using your numbered photos.</p>}
          <div ref={end} />
        </div>
        <div className="composer">
          <div role="status" className="progress-line">
            {busy === 'loading' ? 'Loading conversation...'
              : busy === 'checking' ? 'Checking saved status...'
                : busy === 'selecting' ? 'Saving your collage starting point...'
                : unknown ? 'Outcome unknown. New requests are blocked until saved status is confirmed.'
                  : blocked && confirmed ? `Request ${failed ? 'failed' : 'completed'}. Saved conversation still needs refreshing.`
                  : working ? <><Spinner size="sm" animation="border" aria-hidden="true" />
                    {understanding ? 'Understanding your request' : 'Creating your layout'}</>
                    : operation?.status === 'prepared' ? 'Generation is prepared; it has not started in this view.' : null}
          </div>
          {(operation?.status === 'prepared' || creating) && operation?.summary &&
            <p className="operation-summary">{operation.summary}</p>}
          {operation?.status === 'uncertain' && <Alert variant="warning">
            {operation.message ?? 'A stage was interrupted. Inspect saved status before making another request.'}
            {operation.error && <p>{operation.error.message}</p>}
          </Alert>}
          {conversation.error && <Alert variant="warning" role="alert">{conversation.error}</Alert>}
          {conversation.failure && !conversation.error && <Alert variant="warning" role="alert">{conversation.failure}</Alert>}
          {conversation.notice && <p aria-live="polite">{conversation.notice}</p>}
          {snapshot && !snapshot.live_enabled && <Alert variant="info">
            Live conversation is disabled. Start the local backend with <code>.\api\start.ps1 -Live</code>,
            {' '}then check status. Photos and saved conversations remain available.
          </Alert>}
          {pending && <div className="pending-interaction">
            <p>{pending.kind === 'question' ? 'Question awaiting your reply.' : 'Photo-name confirmation awaiting your reply.'}</p>
            {!snapshot?.messages.some((item) => item.role === 'assistant' && item.text === pending.message) && <p>{pending.message}</p>}
          </div>}
          {conversation.paused && <p className="empty-note">Automatic status checks stopped after 225 seconds.
            Work may still be running. Check status when ready.</p>}
          {!busy && recovery && <div className="recovery-actions">
            {operation?.status === 'prepared' && operation.can_continue && !busy && !blocked &&
              <Button size="sm" onClick={conversation.continueGeneration}
                disabled={!snapshot?.live_enabled}>Continue generation</Button>}
            <Button size="sm" variant="outline-secondary" onClick={conversation.check}>Check status</Button>
          </div>}
          {!busy && recovery && <p className="empty-note">Check saved results without resending or making model calls.</p>}
          <Form onSubmit={(event) => {
            event.preventDefault()
            submit()
          }}>
            <Form.Group controlId="real-prompt">
              <Form.Label className="visually-hidden">Your message</Form.Label>
              <Form.Control as="textarea" rows={2} placeholder={pending?.kind === 'question'
                ? "Answer the assistant's question" : pending?.kind === 'name_confirmation'
                  ? 'Confirm or correct the photo name' : 'Describe a layout or ask for a change'}
                value={draft} disabled={!conversation.canSend} aria-describedby="real-prompt-help"
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault()
                    if (!event.repeat) submit()
                  }
                }}
                onChange={(event) => setDraft(event.currentTarget.value)} />
            </Form.Group>
            <div className="composer-actions"><span id="real-prompt-help">
              {pending ? 'Reply in your own words.' : 'Use photo numbers or names. Send may make paid model requests.'}
              {' '}Enter sends; Shift+Enter adds a newline.
            </span><Button type="submit" disabled={!conversation.canSend || !draft.trim()}>Send</Button></div>
          </Form>
        </div>
      </section>
      <section className="surface preview-panel" aria-labelledby="preview-title">
        <div className="panel-heading"><h2 id="preview-title">Current collage</h2>
          {baseline && <span>Collage {baseline}</span>}</div>
        <p className="empty-note">Edits start from this collage.</p>
        <div className="preview-stage">
          {baseline ? <Preview key={`${project.id}:${baseline}`} projectId={project.id} proposalId={baseline} current updating={updating} />
            : <p className="empty-note">{!snapshot ? 'Preview status is not available until the conversation loads.'
              : snapshot.messages.some((item) => item.proposal_id) ? 'No current preview is available.'
                : 'No collage yet. Send a message to create your first proposal.'}</p>}
          {!baseline && updating && <PreviewLoading overlay message="Updating current collage..." />}
        </div>
        {baseline && <div className="current-collage-actions">
          {currentProposal && <span>{currentProposal.width} x {currentProposal.height} px</span>}
          <Download key={`${project.id}:${baseline}`} projectId={project.id} proposalId={baseline} />
        </div>}
        <div className="preview-details"><PhotoStrip items={project.photos} /></div>
      </section>
    </div>
    <Modal show={Boolean(viewed)} onHide={() => { if (busy !== 'selecting') setViewed(null) }} size="lg"
      aria-labelledby="historical-collage-title">
      <Modal.Header closeButton><Modal.Title id="historical-collage-title">Collage {viewed}</Modal.Title></Modal.Header>
      <Modal.Body>
        {viewed && <div className="preview-stage historical-preview">
          <Preview key={`${project.id}:${viewed}`} projectId={project.id} proposalId={viewed} />
        </div>}
        {displayed && <p>{displayed.width} x {displayed.height} px</p>}
        {!conversation.canSelect && snapshot?.selection.reason && <p role="status">{snapshot.selection.reason}</p>}
        {attempted && conversation.error && <Alert variant="warning">{conversation.error}</Alert>}
        {confirmation && <Alert variant="warning">
          <p>{confirmation.text}</p>
          <Button onClick={() => { void choose(true) }} disabled={!conversation.canSelect}>
            Confirm and edit from this collage
          </Button>{' '}
          <Button variant="outline-secondary" onClick={() => setConfirmation(null)} disabled={Boolean(busy)}>Keep pending request</Button>
        </Alert>}
        {attempted && conversation.selectionActionId && !busy &&
          <Button variant="outline-secondary" onClick={conversation.check}>Check selection status</Button>}
      </Modal.Body>
      <Modal.Footer className="historical-collage-actions">
        {viewed && <Download key={`${project.id}:${viewed}`} projectId={project.id} proposalId={viewed} />}
        {!confirmation && <div className="collage-selection-action">
          <Button size="sm" onClick={() => { void choose() }} disabled={!conversation.canSelect || redundant}
            aria-describedby={redundant ? undefined : 'collage-selection-help'}>
            {redundant ? 'Already current' : 'Edit from this collage'}
          </Button>
          {!redundant && <p id="collage-selection-help">
            Use this as the starting point for future edits. Your history stays saved.
          </p>}
        </div>}
      </Modal.Footer>
    </Modal>
  </div>
}

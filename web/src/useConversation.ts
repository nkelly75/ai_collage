import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from './api'
import { generateRequest, interpretRequest, loadConversation, loadOperation, loadSelection, selectCollage } from './conversationApi'
import type { ConversationView, OperationView, SelectionView } from './conversationApi'

interface State {
  snapshot: ConversationView | null
  operation: OperationView | null
  submission: { requestId: string; prompt: string } | null
  busy: 'loading' | 'checking' | 'interpreting' | 'generating' | 'selecting' | null
  error: string
  notice: string
  failure: string
  blocked: boolean
  paused: boolean
  selectionOutcome: SelectionView | null
  selectionActionId: string | null
}

function running(operation: OperationView | null) {
  return operation?.status === 'interpreting' || operation?.status === 'generating'
}

function message(error: unknown) {
  return error instanceof Error ? error.message : 'Could not read saved conversation status.'
}

function refreshFailure(error: unknown, operation: OperationView | null, failure = '') {
  if (failure || operation?.status === 'failed') {
    return `${failure || operation?.error?.message || 'Stage failed.'} Saved conversation could not refresh. ${message(error)} Check status to refresh it; this request will not be retried.`
  }
  return operation?.status === 'completed'
    ? `Request completed${operation.proposal_id ? ` as ${operation.proposal_id}` : ''}, but saved conversation could not refresh. ${message(error)} Check status to load the result; do not resend.`
    : message(error)
}

export function useConversation(projectId: string, onSelectionSaved?: () => void) {
  const [state, setState] = useState<State>({
    snapshot: null, operation: null, submission: null, busy: 'loading', error: '', notice: '', failure: '', blocked: true, paused: false,
    selectionOutcome: null, selectionActionId: null,
  })
  const latest = useRef(state)
  const epoch = useRef(0)
  const active = useRef<AbortController | null>(null)
  const unknownRequest = useRef<string | null>(null)
  const unknownSelection = useRef<string | null>(null)
  const observation = useRef<{ requestId: string; start: number } | null>(null)
  const update = useCallback((patch: Partial<State>) => {
    latest.current = { ...latest.current, ...patch }
    setState(latest.current)
  }, [])

  const begin = useCallback(() => {
    active.current?.abort()
    const controller = new AbortController()
    active.current = controller
    const token = ++epoch.current
    return { signal: controller.signal, current: () => !controller.signal.aborted && token === epoch.current }
  }, [])
  const stop = useCallback(() => { ++epoch.current; active.current?.abort() }, [])

  const applySnapshot = useCallback((snapshot: ConversationView, observed = latest.current.operation) => {
    const saved = snapshot.operation
    const terminal = observed && ['completed', 'failed', 'abandoned'].includes(observed.status)
    const stages = ['interpreting', 'prepared', 'generating']
    const regressed = observed && saved?.request_id === observed.request_id &&
      (terminal || stages.includes(observed.status) && stages.includes(saved.status) &&
        stages.indexOf(saved.status) < stages.indexOf(observed.status))
    // Revisions are opaque: use stage progression and stable outcome IDs, never hash ordering.
    if (observed && (regressed || !saved &&
      !snapshot.messages.some((item) => item.id === `${observed.request_id}:assistant`))) {
      unknownRequest.current = observed.request_id
      update({ blocked: true, error: 'Saved status is not yet consistent with this request. Check status again before continuing.' })
      return false
    }
    const submission = latest.current.submission
    update({
      snapshot, operation: snapshot.operation,
      submission: submission && !snapshot.messages.some((item) => item.id === `${submission.requestId}:user`)
        ? submission : null,
    })
    return true
  }, [update])

  const refresh = useCallback(async (task: ReturnType<typeof begin>, confirmedSelection: SelectionView | null = null) => {
    const actionId = unknownSelection.current
    if (actionId) {
      const selection = confirmedSelection ?? await loadSelection(projectId, actionId, task.signal)
      if (!task.current()) return
      update({ selectionOutcome: selection })
      if (selection.status !== 'completed') {
        update({ blocked: true, error: selection.message })
        return
      }
      const snapshot = await loadConversation(projectId, task.signal)
      if (!task.current()) return
      if (!snapshot.messages.some((item) => item.id === `${actionId}:activity` &&
        item.proposal_id === selection.proposal_id)) {
        update({ blocked: true, error: 'Saved selection and conversation do not yet agree. Check status; do not repeat the action.' })
        return
      }
      if (!applySnapshot(snapshot)) return
      unknownSelection.current = null
      update({ blocked: Boolean(snapshot.selection.action), error: '', failure: '', selectionActionId: null,
        notice: `Collage selection saved for ${selection.proposal_id}. Current saved conversation refreshed.` })
      onSelectionSaved?.()
      return
    }
    const requestId = unknownRequest.current
    let lookupError = ''
    let saved: OperationView | null = null
    if (requestId) {
      try { saved = await loadOperation(projectId, requestId, task.signal) }
      catch (error) { lookupError = message(error) }
    }
    if (!task.current()) return
    if (latest.current.failure && saved && saved.status !== 'failed') {
      update({ blocked: true, error: 'Saved status disagrees with the confirmed failure. Check status again before continuing.' })
      return
    }
    if (saved?.status === 'completed' || saved?.status === 'failed') update({ operation: saved })
    const snapshot = await loadConversation(projectId, task.signal)
    if (!task.current()) return
    if (!applySnapshot(snapshot, saved ?? latest.current.operation)) return
    if (!lookupError) unknownRequest.current = null
    update({
      error: lookupError, blocked: Boolean(lookupError || snapshot.selection.action),
      failure: lookupError ? latest.current.failure : '',
      notice: requestId && !lookupError && saved?.status === 'completed'
        ? `Original request completed${saved.proposal_id ? ` as ${saved.proposal_id}` : ''}. Saved conversation refreshed.`
        : requestId && !lookupError && saved?.status === 'failed'
          ? 'Original request failed. Saved conversation refreshed. No request was retried.' : '',
    })
  }, [projectId, applySnapshot, update, onSelectionSaved])

  const select = async (proposalId: string, abandonPending = false, expectedRevision?: string) => {
    const current = latest.current
    if (current.busy || current.blocked || !current.snapshot?.selection.enabled) return false
    const actionId = crypto.randomUUID()
    const task = begin()
    unknownSelection.current = actionId
    update({ busy: 'selecting', selectionActionId: actionId, selectionOutcome: null, error: '', failure: '', notice: '' })
    try {
      const result = await selectCollage(projectId, actionId, proposalId,
        expectedRevision ?? current.snapshot.revision, abandonPending, task.signal)
      if (!task.current()) return false
      update({ selectionOutcome: result, busy: 'checking' })
      await refresh(task, result)
      return task.current() && !unknownSelection.current
    } catch (error) {
      if (!task.current()) return false
      const rejected = error instanceof ApiError && [
        'stale_revision', 'confirmation_required', 'already_current', 'project_busy', 'operation_unresolved',
        'action_id_conflict', 'selection_unresolved', 'stale_preparation', 'invalid_request',
        'forbidden_host', 'forbidden_origin', 'unsupported_media', 'not_found', 'request_too_large',
      ].includes(error.code) && [400, 403, 404, 409, 413, 415].includes(error.status)
      if (rejected) {
        unknownSelection.current = null
        update({ selectionActionId: null, error: message(error) })
        try {
          const snapshot = await loadConversation(projectId, task.signal)
          if (task.current() && applySnapshot(snapshot)) update({ blocked: Boolean(snapshot.selection.action) })
        } catch (readError) {
          if (task.current()) update({ blocked: true, error: `${message(error)} Saved conversation could not refresh. ${message(readError)}` })
        }
      } else update({ blocked: true, error: `${message(error)} Selection outcome not confirmed. Check status; do not repeat the action.` })
      return false
    } finally {
      if (task.current()) update({ busy: null })
    }
  }

  const check = useCallback(async (initial = false) => {
    if (latest.current.busy && !initial) return
    const task = begin()
    observation.current = null
    update({ busy: initial ? 'loading' : 'checking', error: '', notice: '', paused: false })
    try { await refresh(task) }
    catch (error) {
      if (task.current()) update({ error: refreshFailure(error, latest.current.operation, latest.current.failure), blocked: true })
    } finally {
      if (task.current()) update({ busy: null })
    }
  }, [begin, refresh, update])

  useEffect(() => {
    void check(true)
    return stop
  }, [check, stop])

  const run = (prompt?: string) => {
    const current = latest.current
    if (current.busy || current.blocked || !current.snapshot?.live_enabled) return false
    const prepared = current.operation
    if (prompt !== undefined ? Boolean(prepared) || !prompt.trim()
      : prepared?.status !== 'prepared' || !prepared.can_continue) return false
    if (prompt !== undefined && new TextEncoder().encode(prompt).length > 256 * 1024) {
      update({ error: 'Messages must be at most 256 KiB of UTF-8 text.' })
      return false
    }
    const requestId = prompt !== undefined ? crypto.randomUUID() : prepared!.request_id
    const task = begin()
    observation.current = null
    update({
      busy: prompt !== undefined ? 'interpreting' : 'generating', error: '', notice: '', failure: '', paused: false,
      ...(prompt !== undefined ? { submission: { requestId, prompt } } : {}),
    })
    const execute = async () => {
      try {
        let operation = prompt !== undefined
          ? await interpretRequest(projectId, requestId, prompt, current.snapshot!.revision, task.signal)
          : prepared!
        if (!task.current()) return
        update({ operation })
        if (operation.status === 'prepared' && operation.can_continue) {
          update({ busy: 'generating' })
          operation = await generateRequest(projectId, requestId, operation.revision, task.signal)
          if (!task.current()) return
          update({ operation })
        }
        update({ busy: 'checking' })
        await refresh(task)
      } catch (error) {
        if (task.current()) {
          unknownRequest.current = requestId
          if (error instanceof ApiError && (
            error.code === 'stage_failed' && error.status === 422 ||
            error.code === 'stage_timeout' && error.status === 504
          )) {
            update({ blocked: true, failure: message(error), error: '', busy: 'checking' })
            try { await refresh(task) }
            catch (readError) {
              if (task.current()) update({
                blocked: true, error: refreshFailure(readError, latest.current.operation, latest.current.failure),
              })
            }
            return
          }
          const completed = latest.current.operation?.request_id === requestId &&
            latest.current.operation.status === 'completed' ? latest.current.operation : null
          update({
            blocked: true,
            error: completed
              ? refreshFailure(error, completed)
              : `${message(error)} Outcome not confirmed. Check status; do not resend this request.`,
          })
        }
      } finally {
        if (task.current()) update({ busy: null })
      }
    }
    void execute()
    return true
  }

  const operationId = state.operation?.request_id
  const operationStatus = state.operation?.status
  useEffect(() => {
    if (!operationId || !running(latest.current.operation) || state.busy || state.blocked || state.paused) return
    if (observation.current?.requestId !== operationId) {
      observation.current = { requestId: operationId, start: Date.now() }
    }
    const remaining = Math.max(0, 225_000 - (Date.now() - observation.current.start))
    const task = begin()
    let timer: ReturnType<typeof setTimeout>
    const expiry = setTimeout(() => {
      if (task.current()) {
        active.current?.abort()
        update({ paused: true })
      }
    }, remaining)
    const tick = async () => {
      try {
        const snapshot = await loadConversation(projectId, task.signal)
        if (!task.current()) return
        if (!applySnapshot(snapshot)) return
        if (running(snapshot.operation)) timer = setTimeout(() => { void tick() }, 2_000)
      } catch (error) {
        if (task.current()) update({ error: message(error), blocked: true })
      }
    }
    timer = setTimeout(() => { void tick() }, Math.min(2_000, remaining))
    return () => {
      clearTimeout(timer)
      clearTimeout(expiry)
      if (task.current()) active.current?.abort()
    }
  }, [projectId, operationId, operationStatus, state.busy, state.blocked, state.paused, begin, applySnapshot, update])

  return {
    ...state,
    canSend: Boolean(state.snapshot?.live_enabled && !state.busy && !state.operation && !state.blocked &&
      !state.snapshot.selection.action),
    canSelect: Boolean(state.snapshot?.selection.enabled && !state.busy && !state.blocked),
    select,
    check: () => { void check() },
    send: (prompt: string) => run(prompt),
    continueGeneration: () => { void run() },
  }
}

import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RealWorkspace } from './RealWorkspace'
import type { ConversationView, OperationView } from './conversationApi'
import { conversation, json, operation, preparedRevision, requestId, revision, savedProject, selection, transcript } from './test/conversation'

function deferred() {
  let resolve!: (value: Response) => void
  const promise = new Promise<Response>((done) => { resolve = done })
  return { promise, resolve }
}

async function open(snapshot: ConversationView = conversation()) {
  vi.mocked(fetch).mockResolvedValueOnce(json(snapshot))
  const view = render(<RealWorkspace project={savedProject} />)
  await act(async () => {})
  return view
}

function send(prompt = 'Make a collage') {
  fireEvent.change(screen.getByLabelText('Your message'), { target: { value: prompt } })
  fireEvent.submit(screen.getByRole('button', { name: 'Send' }).closest('form')!)
}

function done(patch: Partial<OperationView> = {}) {
  return operation({ status: 'completed', can_continue: false, result_kind: 'proposal', proposal_id: 'P002', ...patch })
}

beforeEach(() => { vi.spyOn(crypto, 'randomUUID').mockReturnValue(requestId) })

function history() {
  return [
    { id: 'old:user', role: 'user' as const, text: 'First layout', kind: 'prompt', proposal_id: null },
    { id: 'old:assistant', role: 'assistant' as const, text: 'Created P001.', kind: 'proposal', proposal_id: 'P001' },
    ...transcript(),
  ]
}

function selectedSnapshot() {
  return conversation({ baseline: { proposal_id: 'P001' }, messages: [...history(), {
    id: `${requestId}:activity`, role: 'activity', kind: 'local_selection', proposal_id: 'P001',
    text: 'You chose collage P001 as the starting point for further edits.',
  }] })
}

describe('real conversational workspace', () => {
  it('keeps failed thumbnails explicit and opens the full preview only on request', async () => {
    await open(conversation({ baseline: { proposal_id: 'P002' }, messages: history() }))
    const button = screen.getByRole('button', { name: 'View collage P001' })
    fireEvent.error(within(button).getByRole('img'))
    expect(within(button).queryByRole('img')).not.toBeInTheDocument()
    expect(button).toHaveTextContent('Thumbnail unavailable; open saved preview.')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    fireEvent.click(button)
    expect(within(screen.getByRole('dialog')).getByAltText('Proposal P001')).toHaveAttribute('src',
      'http://127.0.0.1:7071/api/projects/trip/proposals/P001/preview')
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('loads once on ordinary mount/rerender and retains explicit refresh and project-switch reads', async () => {
    const view = await open()
    view.rerender(<RealWorkspace project={{ ...savedProject }} />)
    await act(async () => {})
    expect(fetch).toHaveBeenCalledTimes(1)
    const pendingRefresh = deferred()
    vi.mocked(fetch).mockReturnValueOnce(pendingRefresh.promise)
    fireEvent.click(screen.getByRole('button', { name: 'Refresh saved conversation and preview' }))
    await act(async () => {})
    expect(fetch).toHaveBeenCalledTimes(2)
    const previous = vi.mocked(fetch).mock.calls[1][1]?.signal
    vi.mocked(fetch).mockResolvedValueOnce(json(conversation({ project_id: 'other' })))
    view.rerender(<RealWorkspace project={{ ...savedProject, id: 'other' }} />)
    await act(async () => {})
    expect(previous?.aborted).toBe(true)
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(vi.mocked(fetch).mock.calls[2][0]).toBe('http://127.0.0.1:7071/api/projects/other/conversation')
    await act(async () => { pendingRefresh.resolve(json(conversation())) })
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('views historical results transiently and restores keyboard focus without changing Current collage', async () => {
    await open(conversation({ baseline: { proposal_id: 'P002' }, messages: history() }))
    const user = userEvent.setup()
    const thumbnail = screen.getByRole('button', { name: 'View collage P001' })
    expect(within(thumbnail).getByRole('img')).toHaveAttribute('src',
      'http://127.0.0.1:7071/api/projects/trip/proposals/P001/thumbnail')
    await user.click(thumbnail)
    const modal = screen.getByRole('dialog', { name: 'Collage P001' })
    expect(within(modal).getByRole('button', { name: 'Edit from this collage' })).toHaveAccessibleDescription(
      'Use this as the starting point for future edits. Your history stays saved.',
    )
    expect(within(modal).queryByText('Future changes will start from this collage. Your later history stays saved.')).not.toBeInTheDocument()
    expect(within(modal).getByAltText('Proposal P001')).toBeVisible()
    expect(within(modal).getByAltText('Proposal P001')).toHaveAttribute('src',
      'http://127.0.0.1:7071/api/projects/trip/proposals/P001/preview')
    expect(within(screen.getByRole('region', { name: 'Current collage' })).getByAltText('Proposal P002')).toBeVisible()
    expect(fetch).toHaveBeenCalledTimes(1)
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(thumbnail).toHaveFocus()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('omits source-selection helper text when the modal is Already current', async () => {
    await open(conversation({ baseline: { proposal_id: 'P002' }, messages: history() }))
    fireEvent.click(screen.getByRole('button', { name: 'View collage P002' }))
    const modal = screen.getByRole('dialog')
    expect(within(modal).getByRole('button', { name: 'Already current' })).toBeDisabled()
    expect(within(modal).queryByText('Use this as the starting point for future edits. Your history stays saved.')).not.toBeInTheDocument()
    expect(within(modal).getByRole('button', { name: 'Download PNG' })).toBeEnabled()
  })

  it.each(['load', 'error'])('covers the saved-state handoff and incoming image until its %s event', async (event) => {
    await open(conversation({ baseline: { proposal_id: 'P001' } }))
    const current = screen.getByRole('region', { name: 'Current collage' })
    const previous = within(current).getByAltText('Proposal P001')
    fireEvent.load(previous)
    const generation = deferred()
    const refreshed = deferred()
    vi.mocked(fetch).mockResolvedValueOnce(json(operation(), 201))
      .mockReturnValueOnce(generation.promise).mockReturnValueOnce(refreshed.promise)
    send()
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Creating your layout'))
    expect(within(current).queryByText('Updating current collage...')).not.toBeInTheDocument()
    await act(async () => { generation.resolve(json(done())) })
    expect(within(current).getByText('Updating current collage...')).toBeVisible()
    expect(previous).toBeVisible()
    expect(previous).toHaveAttribute('aria-busy', 'true')
    await act(async () => { refreshed.resolve(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() }))) })
    const incoming = within(current).getByAltText('Proposal P002')
    expect(within(current).getByText('Loading preview P002...')).toBeVisible()
    expect(incoming).toHaveAttribute('aria-busy', 'true')
    if (event === 'error') {
      fireEvent.error(incoming)
      expect(within(current).getByRole('alert')).toHaveTextContent('Preview P002 could not load')
      expect(within(current).queryByText('Loading preview P002...')).not.toBeInTheDocument()
      fireEvent.click(within(current).getByRole('button', { name: 'Reload preview' }))
    }
    fireEvent.load(within(current).getByAltText('Proposal P002'))
    expect(within(current).queryByText('Loading preview P002...')).not.toBeInTheDocument()
    expect(within(current).getByAltText('Proposal P002')).toHaveAttribute('aria-busy', 'false')
  })

  it('shows the completed first collage handoff even before a baseline can be displayed', async () => {
    await open()
    const refreshed = deferred()
    vi.mocked(fetch).mockResolvedValueOnce(json(operation(), 201))
      .mockResolvedValueOnce(json(done())).mockReturnValueOnce(refreshed.promise)
    send()
    const current = screen.getByRole('region', { name: 'Current collage' })
    await waitFor(() => expect(within(current).getByText('Updating current collage...')).toBeVisible())
    await act(async () => { refreshed.resolve(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() }))) })
    fireEvent.load(within(current).getByAltText('Proposal P002'))
    expect(within(current).queryByText('Updating current collage...')).not.toBeInTheDocument()
  })

  it('stops the updating overlay on a failed saved-state read and keeps recovery read-only', async () => {
    await open(conversation({ baseline: { proposal_id: 'P001' } }))
    const current = screen.getByRole('region', { name: 'Current collage' })
    fireEvent.load(within(current).getByAltText('Proposal P001'))
    const refreshed = deferred()
    vi.mocked(fetch).mockResolvedValueOnce(json(operation(), 201))
      .mockResolvedValueOnce(json(done())).mockReturnValueOnce(refreshed.promise)
    send()
    await waitFor(() => expect(within(current).getByText('Updating current collage...')).toBeVisible())
    await act(async () => { refreshed.resolve(json({ error: { code: 'storage_error', message: 'Saved read failed.' } }, 500)) })
    await screen.findByText(/Request completed as P002, but saved conversation could not refresh/)
    expect(within(current).queryByText('Updating current collage...')).not.toBeInTheDocument()
    expect(within(current).getByAltText('Proposal P001')).toHaveAttribute('aria-busy', 'false')
    vi.mocked(fetch).mockResolvedValueOnce(json(done()))
      .mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() })))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    await waitFor(() => expect(within(current).getByAltText('Proposal P002')).toBeInTheDocument())
    fireEvent.load(within(current).getByAltText('Proposal P002'))
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(2)
  })

  it('saves one explicit local selection and preserves historical thumbnails and activity', async () => {
    await open(conversation({ baseline: { proposal_id: 'P002' }, messages: history() }))
    vi.mocked(fetch).mockResolvedValueOnce(json(selection(), 201)).mockResolvedValueOnce(json(selectedSnapshot()))
    fireEvent.click(screen.getByRole('button', { name: 'View collage P001' }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit from this collage' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(within(screen.getByRole('region', { name: 'Current collage' })).getByAltText('Proposal P001')).toBeVisible()
    expect(screen.getByText('You chose collage P001 as the starting point for further edits.')).toBeVisible()
    expect(screen.getByRole('button', { name: 'View collage P002' })).toBeVisible()
    expect(JSON.parse(vi.mocked(fetch).mock.calls[1][1]!.body as string)).toEqual({
      action_id: requestId, proposal_id: 'P001', revision, abandon_pending: false,
    })
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
    expect(vi.mocked(fetch).mock.calls[1][0]).toContain('/conversation/selections')
  })

  it.each(['question', 'names', 'prepared'])('confirms abandoning %s and declining is read-only', async (kind) => {
    const snapshot = conversation({ baseline: { proposal_id: 'P002' }, messages: history(),
      revision: preparedRevision, operation: kind === 'prepared' ? operation() : null,
      pending: kind === 'prepared' ? null : { kind: kind === 'names' ? 'name_confirmation' : 'question', message: 'Please reply.' },
      selection: { enabled: true, reason: '', confirmation: 'End this pending request; names stay saved.', action: null },
    })
    await open(snapshot)
    fireEvent.click(screen.getByRole('button', { name: 'View collage P001' }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit from this collage' }))
    expect(fetch).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Keep pending request' }))
    expect(fetch).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Edit from this collage' }))
    vi.mocked(fetch).mockResolvedValueOnce(json(selection(), 201)).mockResolvedValueOnce(json(selectedSnapshot()))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm and edit from this collage' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(JSON.parse(vi.mocked(fetch).mock.calls[1][1]!.body as string)).toMatchObject({
      revision: preparedRevision, abandon_pending: true,
    })
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith('/generate'))).toBe(false)
  })

  it('keeps the modal open on a lost save and reconciles with reads, not another POST', async () => {
    await open(conversation({ baseline: { proposal_id: 'P002' }, messages: history() }))
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('response lost'))
    fireEvent.click(screen.getByRole('button', { name: 'View collage P001' }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit from this collage' }))
    await screen.findByRole('button', { name: 'Check selection status' })
    expect(screen.getByRole('dialog')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Edit from this collage' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    vi.mocked(fetch).mockResolvedValueOnce(json(selection())).mockResolvedValueOnce(json(selectedSnapshot()))
    fireEvent.click(screen.getByRole('button', { name: 'Check selection status' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
    expect(vi.mocked(fetch).mock.calls[2][0]).toContain(`/selections/${requestId}`)
  })

  it('keeps rejected selection visible and refreshes the revision without optimistic switching', async () => {
    const snapshot = conversation({ baseline: { proposal_id: 'P002' }, messages: history() })
    await open(snapshot)
    vi.mocked(fetch).mockResolvedValueOnce(json({ error: { code: 'stale_revision', message: 'Conversation changed.' } }, 409))
      .mockResolvedValueOnce(json({ ...snapshot, revision: preparedRevision }))
    fireEvent.click(screen.getByRole('button', { name: 'View collage P001' }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit from this collage' }))
    await waitFor(() => expect(within(screen.getByRole('dialog')).getByText('Conversation changed.')).toBeVisible())
    expect(within(screen.getByRole('region', { name: 'Current collage' })).getByAltText('Proposal P002')).toBeVisible()
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('allows model-free viewing but blocks selection while an existing request is uncertain', async () => {
    await open(conversation({ baseline: { proposal_id: 'P002' }, messages: history(), live_enabled: false,
      operation: operation({ status: 'uncertain', can_continue: false }),
      selection: { enabled: false, reason: 'Existing request is uncertain.', confirmation: null, action: null },
    }))
    fireEvent.click(screen.getByRole('button', { name: 'View collage P001' }))
    expect(screen.getByRole('button', { name: 'Edit from this collage' })).toBeDisabled()
    expect(within(screen.getByRole('dialog')).getByRole('button', { name: 'Download PNG' })).toBeEnabled()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('loads real photos/canvas without generating, keeps the composer accessible and has no future controls', async () => {
    await open()
    expect(screen.getByRole('heading', { name: 'trip' })).toBeVisible()
    expect(screen.getByText(/2 photos.*1200 x 1800/)).toBeVisible()
    expect(screen.getByAltText('Photo 1')).toHaveAttribute('src', savedProject.photos[0].src)
    expect(screen.getByLabelText('Your message')).toBeEnabled()
    expect(screen.getByText(/No collage yet/)).toBeVisible()
    expect(screen.queryByRole('button', { name: /Accept|Continue from|Use P/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Download/ })).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('uses keyboard Send, shows real stages/summary and publishes only the current saved baseline', async () => {
    await open(conversation({ baseline: { proposal_id: 'P001' } }))
    const interpretation = deferred()
    const generation = deferred()
    vi.mocked(fetch).mockReturnValueOnce(interpretation.promise).mockReturnValueOnce(generation.promise)
      .mockResolvedValueOnce(json(conversation({ revision: 'c'.repeat(64), baseline: { proposal_id: 'P003' }, messages: transcript() })))
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Your message'), 'Make a collage')
    screen.getByRole('button', { name: 'Send' }).focus()
    await user.keyboard('{Enter}')
    fireEvent.submit(screen.getByRole('button', { name: 'Send' }).closest('form')!)
    expect(crypto.randomUUID).toHaveBeenCalledTimes(1)
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('status')).toHaveTextContent('Understanding your request')
    expect(screen.getByLabelText('Your message')).toBeDisabled()
    expect(within(screen.getByRole('log')).getAllByText('Make a collage')).toHaveLength(1)
    expect(screen.getByAltText('Proposal P001')).toBeVisible()
    await act(async () => { interpretation.resolve(json(operation(), 201)) })
    expect(screen.getByRole('status')).toHaveTextContent('Creating your layout')
    expect(screen.queryByRole('button', { name: 'Continue generation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Check status|Refresh saved conversation and preview/ })).not.toBeInTheDocument()
    expect(screen.getByText(operation().summary)).toBeVisible()
    expect(screen.getByAltText('Proposal P001')).toBeVisible()
    const calls = vi.mocked(fetch).mock.calls
    expect(JSON.parse(calls[1][1]!.body as string)).toEqual({ request_id: requestId, prompt: 'Make a collage', revision })
    expect(JSON.parse(calls[2][1]!.body as string)).toEqual({ revision: preparedRevision })
    await act(async () => { generation.resolve(json(done())) })
    expect(screen.getByAltText('Proposal P003')).toHaveAttribute('src',
      'http://127.0.0.1:7071/api/projects/trip/proposals/P003/preview')
    expect(screen.queryByAltText('Proposal P002')).not.toBeInTheDocument()
    expect(within(screen.getByRole('log')).getAllByText('Make a collage')).toHaveLength(1)
    expect(screen.getByLabelText('Your message')).toBeEnabled()
    expect(fetch).toHaveBeenCalledTimes(4)
  })

  it.each(['question', 'name_confirmation', 'acknowledgement', 'selection'] as const)(
    'renders %s without generation and allows ordinary follow-up text', async (kind) => {
      await open()
      const text = kind === 'question' ? 'Which photo is Emma?' : kind === 'name_confirmation'
        ? 'Reassign Emma to photo 2?' : kind === 'selection' ? 'Returned to P001.' : 'Photo 2 is now called Emma.'
      vi.mocked(fetch).mockResolvedValueOnce(json(done({ result_kind: kind, message: text, proposal_id: kind === 'selection' ? 'P001' : null }), 201))
        .mockResolvedValueOnce(json(conversation({
          messages: transcript(text, kind === 'selection' ? 'P001' : null),
          baseline: kind === 'selection' ? { proposal_id: 'P001' } : null,
          pending: ['question', 'name_confirmation'].includes(kind)
            ? { kind: kind as 'question' | 'name_confirmation', message: text } : null,
        })))
      send()
      await waitFor(() => expect(screen.getByLabelText('Your message')).toBeEnabled())
      expect(within(screen.getByRole('log')).getByText(text)).toBeVisible()
      expect(fetch).toHaveBeenCalledTimes(3)
      expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).endsWith('/generate'))).toHaveLength(0)
    })

  it('requires explicit Continue for restored prepared work and consumes its saved revision once', async () => {
    await open(conversation({ operation: operation(), revision: preparedRevision }))
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    vi.mocked(fetch).mockResolvedValueOnce(json(done()))
      .mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() })))
    const continueButton = screen.getByRole('button', { name: 'Continue generation' })
    fireEvent.click(continueButton)
    fireEvent.click(continueButton)
    expect(screen.queryByRole('button', { name: 'Continue generation' })).not.toBeInTheDocument()
    await screen.findByAltText('Proposal P002')
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(crypto.randomUUID).not.toHaveBeenCalled()
    expect(JSON.parse(vi.mocked(fetch).mock.calls[1][1]!.body as string)).toEqual({ revision: preparedRevision })
  })

  it('reconciles a lost interpretation to prepared without automatically starting generation', async () => {
    await open()
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('response lost'))
    send()
    await screen.findByText(/Outcome not confirmed/)
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(fetch).toHaveBeenCalledTimes(2)
    vi.mocked(fetch).mockResolvedValueOnce(json(operation()))
      .mockResolvedValueOnce(json(conversation({ operation: operation(), revision: preparedRevision })))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Continue generation' })).toBeEnabled())
    expect(fetch).toHaveBeenCalledTimes(4)
    expect(vi.mocked(fetch).mock.calls[2][0]).toContain(`/conversation/requests/${requestId}`)
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith('/generate'))).toBe(false)
  })

  it('does not retry a generation whose response was lost but whose recorded result completed', async () => {
    await open()
    vi.mocked(fetch).mockResolvedValueOnce(json(operation(), 201))
      .mockRejectedValueOnce(new TypeError('lost'))
    send()
    await screen.findByText(/Outcome not confirmed/)
    vi.mocked(fetch).mockResolvedValueOnce(json(done()))
      .mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() })))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    await screen.findByAltText('Proposal P002')
    expect(screen.getByRole('button', { name: 'Refresh saved conversation and preview' })).toBeEnabled()
    expect(screen.queryByRole('button', { name: 'Check status' })).not.toBeInTheDocument()
    expect(screen.getByText('Original request completed as P002. Saved conversation refreshed.')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Continue generation' })).not.toBeInTheDocument()
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(2)
  })

  it('retains completion confirmed by Check status when the following transcript read fails', async () => {
    await open()
    vi.mocked(fetch).mockResolvedValueOnce(json(operation(), 201)).mockRejectedValueOnce(new TypeError('lost'))
    send()
    await screen.findByText(/Outcome not confirmed/)
    vi.mocked(fetch).mockResolvedValueOnce(json(done())).mockRejectedValueOnce(new TypeError('offline'))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    await screen.findByText(/Request completed as P002, but saved conversation could not refresh/)
    expect(screen.getByRole('status')).toHaveTextContent('Request completed. Saved conversation still needs refreshing.')
    expect(screen.getByLabelText('Your message')).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Continue generation' })).not.toBeInTheDocument()
    vi.mocked(fetch).mockResolvedValueOnce(json(done()))
      .mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() })))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    await screen.findByAltText('Proposal P002')
    expect(screen.getByText('Original request completed as P002. Saved conversation refreshed.')).toBeVisible()
    expect(screen.getByLabelText('Your message')).toBeEnabled()
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(2)
  })

  it.each([409, 504])('does not resend after HTTP %s and permits an explicit new attempt only after confirmed terminal failure', async (status) => {
    await open()
    vi.mocked(fetch).mockResolvedValueOnce(json({ error: { code: 'stage_failed', message: 'Stage stopped.' } }, status))
    send()
    await screen.findByText(/Stage stopped/)
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    vi.mocked(fetch).mockResolvedValueOnce(json(operation({ status: 'failed', can_continue: false,
      error: { code: 'stage_failed', message: 'Stage stopped.' } })))
      .mockResolvedValueOnce(json(conversation({ messages: transcript('Stage stopped. Send a new message to try again.', null) })))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    await waitFor(() => expect(screen.getByLabelText('Your message')).toBeEnabled())
    expect(within(screen.getByRole('log')).getByText(/Stage stopped/)).toBeVisible()
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
  })

  it.each([
    { status: 422, code: 'stage_failed', generation: true },
    { status: 504, code: 'stage_timeout', generation: false },
  ])('automatically reads saved state after a confirmed $code without retrying the stage', async ({ status, code, generation }) => {
    await open(conversation({ baseline: { proposal_id: 'P001' } }))
    const lookup = deferred()
    if (generation) vi.mocked(fetch).mockResolvedValueOnce(json(operation(), 201))
    vi.mocked(fetch).mockResolvedValueOnce(json({ error: { code, message: 'Stage stopped; previous preview unchanged.' } }, status))
      .mockReturnValueOnce(lookup.promise)
      .mockResolvedValueOnce(json(conversation({
        baseline: { proposal_id: 'P001' },
        messages: transcript('Stage stopped; previous preview unchanged.', null),
      })))
    send()
    await screen.findByText('Stage stopped; previous preview unchanged.')
    expect(screen.getByRole('status')).toHaveTextContent('Checking saved status')
    expect(screen.getByRole('status')).not.toHaveTextContent('Outcome unknown')
    expect(screen.queryByText(/Outcome not confirmed/)).not.toBeInTheDocument()
    expect(screen.getByLabelText('Your message')).toBeDisabled()
    await act(async () => { lookup.resolve(json(operation({
      status: 'failed', can_continue: false, error: { code, message: 'Stage stopped; previous preview unchanged.' },
    }))) })
    expect(screen.getByText('Original request failed. Saved conversation refreshed. No request was retried.')).toBeVisible()
    expect(screen.getByLabelText('Your message')).toBeEnabled()
    expect(screen.getByAltText('Proposal P001')).toBeVisible()
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(generation ? 2 : 1)
    expect(vi.mocked(fetch).mock.calls.at(-2)![0]).toContain(`/conversation/requests/${requestId}`)
  })

  it('preserves known failure when automatic refresh fails and restores the composer on a manual read', async () => {
    await open(conversation({ baseline: { proposal_id: 'P001' } }))
    const failed = operation({ status: 'failed', can_continue: false,
      error: { code: 'stage_failed', message: 'Stage failed; previous preview unchanged.' } })
    vi.mocked(fetch).mockResolvedValueOnce(json({ error: failed.error }, 422))
      .mockResolvedValueOnce(json(failed)).mockRejectedValueOnce(new TypeError('offline'))
    send()
    await screen.findByText(/Saved conversation could not refresh/)
    expect(screen.getByRole('status')).toHaveTextContent('Request failed. Saved conversation still needs refreshing.')
    expect(screen.queryByText(/Outcome not confirmed/)).not.toBeInTheDocument()
    expect(screen.getByLabelText('Your message')).toBeDisabled()
    vi.mocked(fetch).mockResolvedValueOnce(json(failed))
      .mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P001' },
        messages: transcript(failed.error!.message, null) })))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    await waitFor(() => expect(screen.getByLabelText('Your message')).toBeEnabled())
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
  })

  it('does not offer Continue or unblock Send when saved status contradicts a confirmed failure', async () => {
    await open()
    vi.mocked(fetch).mockResolvedValueOnce(json({ error: { code: 'stage_failed', message: 'Stage failed.' } }, 422))
      .mockResolvedValueOnce(json(operation()))
    send()
    await screen.findByText(/Saved status disagrees with the confirmed failure/)
    expect(screen.getByLabelText('Your message')).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Continue generation' })).not.toBeInTheDocument()
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
  })

  it('keeps an unknown/missing request blocked rather than inferring safety from an empty conversation', async () => {
    await open()
    vi.mocked(fetch).mockResolvedValueOnce(json({ unexpected: 'invalid success' }, 201))
    send()
    await screen.findByText(/Unexpected conversation response/)
    vi.mocked(fetch).mockResolvedValueOnce(json({ error: { code: 'missing', message: 'Operation not found.' } }, 404))
      .mockResolvedValueOnce(json(conversation()))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    await screen.findByText('Operation not found.')
    expect(screen.getByLabelText('Your message')).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent('Outcome unknown')
  })

  it('shows actionable disabled-live setup and never sends paid requests', async () => {
    await open(conversation({ live_enabled: false }))
    expect(screen.getByText('.\\api\\start.ps1 -Live')).toBeVisible()
    expect(screen.getByLabelText('Your message')).toBeDisabled()
    send()
    expect(fetch).toHaveBeenCalledTimes(1)
    vi.mocked(fetch).mockResolvedValueOnce(json(conversation()))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    await waitFor(() => expect(screen.getByLabelText('Your message')).toBeEnabled())
  })

  it('handles live availability changing after load without retrying a rejected submission', async () => {
    await open()
    vi.mocked(fetch).mockResolvedValueOnce(json({
      error: { code: 'live_disabled', message: 'Live conversation is disabled.' },
    }, 503))
    send()
    await screen.findByText(/Outcome not confirmed/)
    expect(screen.getByLabelText('Your message')).toBeDisabled()
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
  })

  it('rejects a regressed snapshot after a completed POST instead of replacing the preview or offering Continue', async () => {
    await open(conversation({ baseline: { proposal_id: 'P001' } }))
    vi.mocked(fetch).mockResolvedValueOnce(json(operation(), 201)).mockResolvedValueOnce(json(done()))
      .mockResolvedValueOnce(json(conversation({ operation: operation(), baseline: null })))
    send()
    await screen.findByText(/Saved status is not yet consistent/)
    expect(screen.getByAltText('Proposal P001')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Continue generation' })).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(4)
  })

  it('distinguishes unavailable conversation from empty history, and reports immutable-preview load failure', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('offline'))
    render(<RealWorkspace project={savedProject} />)
    await screen.findByText(/Could not reach the backend/)
    expect(screen.queryByText(/No collage yet/)).not.toBeInTheDocument()
    vi.mocked(fetch).mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P001' } })))
    fireEvent.click(screen.getByRole('button', { name: 'Check status' }))
    fireEvent.error(await screen.findByAltText('Proposal P001'))
    expect(screen.getByRole('alert')).toHaveTextContent('Preview P001 could not load')
    fireEvent.click(screen.getByRole('button', { name: 'Reload preview' }))
    expect(screen.getByAltText('Proposal P001')).toBeVisible()
  })

  it('aborts an obsolete interpretation callback before it can dispatch generation', async () => {
    const view = await open()
    const pending = deferred()
    vi.mocked(fetch).mockReturnValueOnce(pending.promise)
    send()
    const signal = vi.mocked(fetch).mock.calls[1][1]?.signal
    view.unmount()
    expect(signal?.aborted).toBe(true)
    await act(async () => { pending.resolve(json(operation(), 201)) })
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it.each(['question', 'name_confirmation'] as const)(
    'uses a contextual %s composer and hides the answered interaction during automatic generation', async (kind) => {
      await open(conversation({ pending: { kind, message: 'Which photo?' } }))
      expect(screen.getByLabelText('Your message')).toHaveAttribute('placeholder',
        kind === 'question' ? "Answer the assistant's question" : 'Confirm or correct the photo name')
      const interpretation = deferred()
      const generation = deferred()
      vi.mocked(fetch).mockReturnValueOnce(interpretation.promise).mockReturnValueOnce(generation.promise)
        .mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() })))
      send('photo 2')
      expect(screen.queryByText(/awaiting your reply/)).not.toBeInTheDocument()
      await act(async () => { interpretation.resolve(json(operation(), 201)) })
      expect(screen.getByRole('status')).toHaveTextContent('Creating your layout')
      expect(screen.queryByText(/awaiting your reply/)).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Continue generation' })).not.toBeInTheDocument()
      await act(async () => { generation.resolve(json(done())) })
      expect(screen.getByLabelText('Your message')).toHaveAttribute('placeholder', 'Describe a layout or ask for a change')
    })

  it('sends with Enter, inserts a newline with Shift+Enter and ignores composition, empty input and repeats', async () => {
    await open()
    const textbox = screen.getByLabelText('Your message')
    const user = userEvent.setup()
    fireEvent.keyDown(textbox, { key: 'Enter' })
    expect(fetch).toHaveBeenCalledTimes(1)
    await user.type(textbox, 'Make')
    await user.keyboard('{Shift>}{Enter}{/Shift}a collage')
    expect(textbox).toHaveValue('Make\na collage')
    fireEvent.keyDown(textbox, { key: 'Enter', isComposing: true })
    fireEvent.keyDown(textbox, { key: 'Enter', repeat: true })
    expect(fetch).toHaveBeenCalledTimes(1)
    const pending = deferred()
    vi.mocked(fetch).mockReturnValueOnce(pending.promise)
    await user.keyboard('{Enter}')
    fireEvent.keyDown(textbox, { key: 'Enter' })
    expect(textbox).toHaveValue('')
    expect(textbox).toBeDisabled()
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(JSON.parse(vi.mocked(fetch).mock.calls[1][1]!.body as string).prompt).toBe('Make\na collage')
  })

  it('keeps preview loading visible until the matching image loads, including a changed proposal and reload', async () => {
    await open(conversation({ baseline: { proposal_id: 'P001' } }))
    expect(screen.getByText('Loading preview P001...')).toBeVisible()
    fireEvent.load(screen.getByAltText('Proposal P001'))
    expect(screen.queryByText('Loading preview P001...')).not.toBeInTheDocument()
    vi.mocked(fetch).mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P002' } })))
    fireEvent.click(screen.getByRole('button', { name: 'Refresh saved conversation and preview' }))
    await screen.findByAltText('Proposal P002')
    expect(screen.getByText('Loading preview P002...')).toBeVisible()
    fireEvent.error(screen.getByAltText('Proposal P002'))
    expect(screen.getByRole('alert')).toHaveTextContent('Preview P002 could not load')
    fireEvent.click(screen.getByRole('button', { name: 'Reload preview' }))
    expect(screen.getByText('Loading preview P002...')).toBeVisible()
    fireEvent.load(screen.getByAltText('Proposal P002'))
    expect(screen.queryByText('Loading preview P002...')).not.toBeInTheDocument()
  })

  it('keeps optional refresh in the fixed conversation heading and reads other-tab updates without submitting', async () => {
    await open()
    const refresh = screen.getByRole('button', { name: 'Refresh saved conversation and preview' })
    expect(refresh).toHaveAttribute('title', 'Refresh saved conversation and preview')
    expect(refresh.closest('.panel-heading')).toContainElement(screen.getByRole('heading', { name: 'Conversation' }))
    expect(refresh.closest('.composer')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Check status' })).not.toBeInTheDocument()
    const pending = deferred()
    vi.mocked(fetch).mockReturnValueOnce(pending.promise)
    fireEvent.click(refresh)
    expect(refresh).toBeDisabled()
    fireEvent.click(refresh)
    expect(fetch).toHaveBeenCalledTimes(2)
    await act(async () => { pending.resolve(json(conversation({
      baseline: { proposal_id: 'P002' }, messages: transcript(),
    }))) })
    expect(screen.getByAltText('Proposal P002')).toBeVisible()
    expect(within(screen.getByRole('log')).getByText('Created the layout.')).toBeVisible()
    expect(refresh).toBeEnabled()
    expect(vi.mocked(fetch).mock.calls.every(([, options]) => options?.method === 'GET')).toBe(true)
  })

  it('ignores a stale status response after a manual refresh publishes a newer baseline', async () => {
    vi.useFakeTimers()
    await open(conversation({ operation: operation({ status: 'generating', can_continue: false }) }))
    const stale = deferred()
    vi.mocked(fetch).mockReturnValueOnce(stale.promise)
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000) })
    const oldSignal = vi.mocked(fetch).mock.calls[1][1]?.signal
    vi.mocked(fetch).mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() })))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Check status' })) })
    expect(oldSignal?.aborted).toBe(true)
    await act(async () => { stale.resolve(json(conversation({ baseline: { proposal_id: 'P001' } }))) })
    expect(screen.getByAltText('Proposal P002')).toBeVisible()
    expect(screen.queryByAltText('Proposal P001')).not.toBeInTheDocument()
  })
})

describe('bounded real observation', () => {
  beforeEach(() => { vi.useFakeTimers() })

  it('preserves a confirmed completion when its status refresh times out and recovers without resending', async () => {
    await open(conversation({ baseline: { proposal_id: 'P001' } }))
    const refresh = deferred()
    vi.mocked(fetch).mockResolvedValueOnce(json(operation(), 201)).mockResolvedValueOnce(json(done()))
      .mockReturnValueOnce(refresh.promise)
    await act(async () => { send() })
    await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
    expect(screen.getByRole('status')).toHaveTextContent('Request completed. Saved conversation still needs refreshing.')
    expect(screen.getByRole('alert')).toHaveTextContent('Request completed as P002, but saved conversation could not refresh.')
    expect(screen.getByRole('alert')).not.toHaveTextContent('Outcome not confirmed')
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(screen.getByAltText('Proposal P001')).toBeVisible()
    vi.mocked(fetch).mockResolvedValueOnce(json(done()))
      .mockResolvedValueOnce(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() })))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Check status' })) })
    expect(screen.getByText('Original request completed as P002. Saved conversation refreshed.')).toBeVisible()
    expect(screen.getByAltText('Proposal P002')).toBeVisible()
    expect(screen.getByLabelText('Your message')).toBeEnabled()
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(2)
    await act(async () => { refresh.resolve(json(conversation({ baseline: { proposal_id: 'P001' } }))) })
    expect(screen.getByAltText('Proposal P002')).toBeVisible()
  })

  it('times out a lost response at 160 seconds without a silent retry', async () => {
    await open()
    vi.mocked(fetch).mockResolvedValueOnce({ status: 201, json: () => new Promise(() => {}) } as Response)
    await act(async () => { send() })
    await act(async () => { await vi.advanceTimersByTimeAsync(160_000) })
    expect(screen.getByRole('status')).toHaveTextContent('Outcome unknown')
    expect(screen.getByText(/Outcome not confirmed/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Check status' })).toBeEnabled()
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('restores active work and polls every two seconds without overlap, stopping on connectivity loss', async () => {
    const active = conversation({ operation: operation({ status: 'interpreting', can_continue: false }) })
    await open(active)
    const pending = deferred()
    vi.mocked(fetch).mockReturnValueOnce(pending.promise).mockRejectedValueOnce(new TypeError('offline'))
    await act(async () => { await vi.advanceTimersByTimeAsync(8_000) })
    expect(fetch).toHaveBeenCalledTimes(2)
    await act(async () => { pending.resolve(json(active)) })
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000) })
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(screen.getByText(/Could not reach/)).toBeVisible()
    await act(async () => { await vi.advanceTimersByTimeAsync(230_000) })
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })

  it('stops after 225 seconds, requires manual checking to observe again, and cleans timers on unmount', async () => {
    const active = conversation({ operation: operation({ status: 'generating', can_continue: false }) })
    const view = await open(active)
    vi.mocked(fetch).mockImplementation(async () => json(active))
    await act(async () => { await vi.advanceTimersByTimeAsync(225_000) })
    expect(screen.getByText(/Automatic status checks stopped after 225 seconds/)).toBeVisible()
    const count = vi.mocked(fetch).mock.calls.length
    expect(count).toBe(113)
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
    expect(fetch).toHaveBeenCalledTimes(count)
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Check status' })) })
    expect(screen.queryByText(/Automatic status checks stopped/)).not.toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000) })
    expect(fetch).toHaveBeenCalledTimes(count + 2)
    view.unmount()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('aborts an in-flight status read at the observation ceiling and ignores its late outcome', async () => {
    const active = conversation({ operation: operation({ status: 'generating', can_continue: false }) })
    await open(active)
    vi.mocked(fetch).mockImplementation(async () => json(active))
    await act(async () => { await vi.advanceTimersByTimeAsync(222_000) })
    const lastRead = deferred()
    vi.mocked(fetch).mockReturnValueOnce(lastRead.promise)
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000) })
    const signal = vi.mocked(fetch).mock.calls.at(-1)![1]?.signal
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000) })
    expect(signal?.aborted).toBe(true)
    expect(screen.getByText(/Automatic status checks stopped/)).toBeVisible()
    await act(async () => {
      lastRead.resolve(json(conversation({ baseline: { proposal_id: 'P002' }, messages: transcript() })))
    })
    expect(screen.queryByAltText('Proposal P002')).not.toBeInTheDocument()
    expect(vi.getTimerCount()).toBe(0)
  })

  it.each(['prepared', 'uncertain', 'terminal'] as const)('stops observation on %s and never auto-generates from a GET', async (next) => {
    await open(conversation({ operation: operation({
      status: next === 'prepared' ? 'interpreting' : 'generating', can_continue: false,
    }) }))
    vi.mocked(fetch).mockResolvedValueOnce(json(conversation({
      operation: next === 'terminal' ? null : operation({ status: next, can_continue: next === 'prepared' }),
      messages: next === 'terminal' ? transcript() : [],
    })))
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000) })
    await act(async () => { await vi.advanceTimersByTimeAsync(250_000) })
    expect(fetch).toHaveBeenCalledTimes(2)
    if (next === 'uncertain') expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    if (next === 'prepared') expect(screen.getByRole('button', { name: 'Continue generation' })).toBeEnabled()
    expect(vi.getTimerCount()).toBe(0)
  })
})

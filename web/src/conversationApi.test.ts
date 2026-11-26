import { beforeEach, describe, expect, it, vi } from 'vitest'
import { generateRequest, interpretRequest, loadConversation, loadOperation, previewUrl } from './conversationApi'
import { conversation, json, operation, preparedRevision, requestId, revision } from './test/conversation'

const signal = () => new AbortController().signal

beforeEach(() => { vi.useFakeTimers() })

describe('strict conversation API boundary', () => {
  it('sends one JSON interpretation and one generation with separate revisions and safe fetch policy', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(json(operation(), 201)).mockResolvedValueOnce(json(operation({
      status: 'completed', can_continue: false, result_kind: 'proposal', proposal_id: 'P002',
    })))
    await interpretRequest('trip', requestId, 'Make a collage', revision, signal())
    await generateRequest('trip', requestId, preparedRevision, signal())
    const calls = vi.mocked(fetch).mock.calls
    expect(calls.map(([url]) => url)).toEqual([
      `http://127.0.0.1:7071/api/projects/trip/conversation/requests`,
      `http://127.0.0.1:7071/api/projects/trip/conversation/requests/${requestId}/generate`,
    ])
    expect(JSON.parse(calls[0][1]!.body as string)).toEqual({ request_id: requestId, prompt: 'Make a collage', revision })
    expect(JSON.parse(calls[1][1]!.body as string)).toEqual({ revision: preparedRevision })
    for (const [, options] of calls) expect(options).toMatchObject({
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'omit', cache: 'no-store', redirect: 'error', mode: 'cors',
    })
    expect(vi.getTimerCount()).toBe(0)
  })

  it('accepts 200 duplicate interpretation, not arbitrary 2xx or a 201 generation response', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(json(operation()))
      .mockResolvedValueOnce(json(operation(), 202)).mockResolvedValueOnce(json(operation(), 201))
    await expect(interpretRequest('trip', requestId, 'hello', revision, signal())).resolves.toEqual(operation())
    await expect(interpretRequest('trip', requestId, 'hello', revision, signal())).rejects.toMatchObject({ status: 202, uncertain: true })
    await expect(generateRequest('trip', requestId, revision, signal())).rejects.toMatchObject({ status: 201, uncertain: true })
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it.each([
    ['interpretation', 160_000], ['generation', 220_000],
  ])('includes JSON body parsing in the %s deadline (%s ms)', async (stage, timeout) => {
    vi.mocked(fetch).mockResolvedValue({ status: 200, json: () => new Promise(() => {}) } as Response)
    const work = stage === 'interpretation'
      ? interpretRequest('trip', requestId, 'hello', revision, signal())
      : generateRequest('trip', requestId, revision, signal())
    const assertion = expect(work).rejects.toMatchObject({ message: 'Backend request timed out.', uncertain: true })
    await vi.advanceTimersByTimeAsync(Number(timeout) - 1)
    expect(vi.mocked(fetch).mock.calls[0][1]?.signal?.aborted).toBe(false)
    await vi.advanceTimersByTimeAsync(1)
    await assertion
    expect(vi.mocked(fetch).mock.calls[0][1]?.signal?.aborted).toBe(true)
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
  })

  it.each([409, 503, 504])('preserves structured HTTP %s errors without treating the outcome as safe to resend', async (status) => {
    vi.mocked(fetch).mockResolvedValueOnce(json({ error: { code: 'stage_error', message: 'Check saved status.' } }, status))
    await expect(interpretRequest('trip', requestId, 'hello', revision, signal())).rejects.toMatchObject({
      status, code: 'stage_error', message: 'Check saved status.', uncertain: true,
    })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('rejects unknown, missing, coerced, malformed and identity-mismatched conversation fields', async () => {
    const sample = conversation()
    const { pending: _pending, ...missing } = sample
    for (const value of [
      { ...sample, project_id: 'other' }, { ...sample, extra: true }, missing,
      { ...sample, live_enabled: 'true' }, { ...sample, revision: 'A'.repeat(64) },
      { ...sample, baseline: { proposal_id: '../../secret' } },
      { ...sample, pending: { kind: 'approval', message: 'yes?' } },
      { ...sample, messages: [{ id: 'a', role: 'system', text: 'hidden', kind: 'raw', proposal_id: null }] },
      { ...sample, messages: [1, 2].map(() => ({ id: 'a', role: 'user', text: 'hi', kind: 'request', proposal_id: null })) },
      { ...sample, operation: operation({ status: 'failed', can_continue: false }) },
      { ...sample, operation: operation({ error: { code: 'bad', message: 1 } as never }) },
    ]) {
      vi.mocked(fetch).mockResolvedValueOnce(json(value))
      await expect(loadConversation('trip', signal())).rejects.toThrow('Unexpected conversation response')
    }
  })

  it('validates operation identities and types before using success DTOs', async () => {
    for (const value of [
      { ...operation(), request_id: '12345678-1234-4234-8234-123456789ABC' },
      { ...operation(), request_id: '22345678-1234-4234-8234-123456789abc' },
      { ...operation(), can_continue: 'true' }, { ...operation(), status: 'queued' },
      { ...operation(), result_kind: 'raw_intent' }, { ...operation(), proposal_id: 'v0001' },
      { ...operation(), status: 'uncertain', can_continue: true }, { ...operation(), private_handoff: {} },
    ]) {
      vi.mocked(fetch).mockResolvedValueOnce(json(value, 201))
      await expect(interpretRequest('trip', requestId, 'hello', revision, signal())).rejects.toMatchObject({ uncertain: true })
    }
    vi.mocked(fetch).mockResolvedValueOnce(json(operation()))
    await expect(loadOperation('trip', requestId, signal())).resolves.toEqual(operation())
  })

  it('validates outgoing identities, prompt byte size and preview IDs without sending requests', async () => {
    expect(previewUrl('trip', 'P001')).toBe('http://127.0.0.1:7071/api/projects/trip/proposals/P001/preview')
    expect(() => previewUrl('trip', '../P001')).toThrow()
    expect(() => previewUrl('../trip', 'P001')).toThrow()
    await expect(interpretRequest('trip', requestId, ' ', revision, signal())).rejects.toThrow('nonempty')
    await expect(interpretRequest('trip', requestId, 'é'.repeat(131_073), revision, signal())).rejects.toThrow('256 KiB')
    await expect(interpretRequest('trip', 'not-a-uuid', 'hello', revision, signal())).rejects.toThrow('Invalid request ID')
    await expect(generateRequest('trip', requestId, 'old', signal())).rejects.toThrow('Invalid saved revision')
    expect(fetch).not.toHaveBeenCalled()
  })
})

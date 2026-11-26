import type { ConversationView, OperationView, SelectionView } from '../conversationApi'
import type { Project } from '../projects'

export const requestId = '12345678-1234-4234-8234-123456789abc'
export const revision = 'a'.repeat(64)
export const preparedRevision = 'b'.repeat(64)
export const savedProject: Project = {
  id: 'trip', canvas: { width: 1200, height: 1800 },
  photos: [{ number: 1, src: 'http://127.0.0.1:7071/api/projects/trip/photos/1' },
    { number: 2, src: 'http://127.0.0.1:7071/api/projects/trip/photos/2' }],
}

export function operation(patch: Partial<OperationView> = {}): OperationView {
  return {
    request_id: requestId, status: 'prepared', summary: 'Create a fresh layout using photos 1 and 2.',
    result_kind: null, message: null, proposal_id: null, error: null, can_continue: true,
    revision: preparedRevision, ...patch,
  }
}

export function selection(patch: Partial<SelectionView> = {}): SelectionView {
  return { action_id: requestId, proposal_id: 'P001', status: 'completed', revision, message: 'Collage selection saved.', ...patch }
}

export function conversation(patch: Partial<ConversationView> = {}): ConversationView {
  const ids = new Set([
    ...(patch.baseline ? [patch.baseline.proposal_id] : []),
    ...(patch.messages ?? []).flatMap((item) => item.proposal_id ? [item.proposal_id] : []),
  ])
  return {
    project_id: 'trip', revision, live_enabled: true, messages: [],
    baseline: null, pending: null, operation: null,
    proposals: [...ids].map((proposal_id) => ({ proposal_id, width: 1200, height: 1800 })),
    selection: { enabled: true, reason: '', confirmation: null, action: null }, ...patch,
  }
}

export function transcript(text = 'Created the layout.', proposalId: string | null = 'P002'): ConversationView['messages'] {
  return [
    { id: `${requestId}:user`, role: 'user', text: 'Make a collage', kind: 'request', proposal_id: null },
    { id: `${requestId}:assistant`, role: 'assistant', text, kind: proposalId ? 'proposal' : 'question', proposal_id: proposalId },
  ]
}

export function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
}

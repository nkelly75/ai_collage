import { ApiError, apiUrl, request } from './api'
import { projectIdError } from './projects'

export interface OperationView {
  request_id: string
  status: 'interpreting' | 'prepared' | 'generating' | 'completed' | 'failed' | 'uncertain'
  summary: string
  result_kind: 'proposal' | 'selection' | 'question' | 'name_confirmation' | 'acknowledgement' | null
  message: string | null
  proposal_id: string | null
  error: { code: string; message: string } | null
  can_continue: boolean
  revision: string
}

export interface ConversationView {
  project_id: string
  revision: string
  live_enabled: boolean
  messages: {
    id: string
    role: 'user' | 'assistant'
    text: string
    kind: string
    proposal_id: string | null
  }[]
  baseline: { proposal_id: string } | null
  pending: { kind: 'question' | 'name_confirmation'; message: string } | null
  operation: OperationView | null
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const revision = /^[0-9a-f]{64}$/
const proposal = /^P[0-9]{3,}$/
const statuses = ['interpreting', 'prepared', 'generating', 'completed', 'failed', 'uncertain']
const resultKinds = ['proposal', 'selection', 'question', 'name_confirmation', 'acknowledgement']

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function fields(value: unknown, names: string[]): value is Record<string, unknown> {
  return object(value) && Object.keys(value).length === names.length &&
    names.every((name) => Object.hasOwn(value, name))
}

function text(value: unknown): value is string { return typeof value === 'string' }
function nullableText(value: unknown) { return value === null || text(value) }
function proposalId(value: unknown): value is string {
  return text(value) && value.length <= 64 && proposal.test(value)
}
function nullableProposal(value: unknown) { return value === null || proposalId(value) }

function invalid(): never { throw new ApiError('Unexpected conversation response. Check saved status before continuing.', 0, '', true) }

function parseOperation(value: unknown): OperationView {
  if (!fields(value, ['request_id', 'status', 'summary', 'result_kind', 'message', 'proposal_id',
    'error', 'can_continue', 'revision']) ||
    !text(value.request_id) || !uuid.test(value.request_id) ||
    !text(value.revision) || !revision.test(value.revision) ||
    !text(value.status) || !statuses.includes(value.status) || !text(value.summary) ||
    !(value.result_kind === null || text(value.result_kind) && resultKinds.includes(value.result_kind)) ||
    !nullableText(value.message) || !nullableProposal(value.proposal_id) ||
    typeof value.can_continue !== 'boolean' || value.can_continue && value.status !== 'prepared' ||
    !(value.error === null || fields(value.error, ['code', 'message']) &&
      text(value.error.code) && text(value.error.message))) invalid()
  return value as unknown as OperationView
}

function projectPath(id: string) {
  if (projectIdError(id)) throw new ApiError('Invalid project ID.')
  return `api/projects/${id}`
}

function operationPath(id: string, requestId: string) {
  if (!uuid.test(requestId)) throw new ApiError('Invalid request ID.')
  return `${projectPath(id)}/conversation/requests/${requestId}`
}

function parseConversation(value: unknown, id: string): ConversationView {
  if (!fields(value, ['project_id', 'revision', 'live_enabled', 'messages', 'baseline', 'pending', 'operation']) ||
    value.project_id !== id || !text(value.revision) || !revision.test(value.revision) ||
    typeof value.live_enabled !== 'boolean' || !Array.isArray(value.messages) ||
    !(value.baseline === null || fields(value.baseline, ['proposal_id']) && proposalId(value.baseline.proposal_id)) ||
    !(value.pending === null || fields(value.pending, ['kind', 'message']) &&
      ['question', 'name_confirmation'].includes(value.pending.kind as string) && text(value.pending.message))) invalid()
  const ids = new Set<string>()
  for (const message of value.messages) {
    if (!fields(message, ['id', 'role', 'text', 'kind', 'proposal_id']) ||
      !text(message.id) || !message.id || ids.has(message.id) ||
      !['user', 'assistant'].includes(message.role as string) ||
      !text(message.text) || !text(message.kind) || !nullableProposal(message.proposal_id)) invalid()
    ids.add(message.id)
  }
  if (value.operation !== null) {
    const operation = parseOperation(value.operation)
    if (['completed', 'failed'].includes(operation.status)) invalid()
  }
  return value as unknown as ConversationView
}

export async function loadConversation(id: string, signal: AbortSignal): Promise<ConversationView> {
  return parseConversation(await request(`${projectPath(id)}/conversation`, signal), id)
}

export async function loadOperation(id: string, requestId: string, signal: AbortSignal): Promise<OperationView> {
  const operation = parseOperation(await request(operationPath(id, requestId), signal))
  if (operation.request_id !== requestId) invalid()
  return operation
}

export async function interpretRequest(id: string, requestId: string, prompt: string, expectedRevision: string,
  signal: AbortSignal): Promise<OperationView> {
  operationPath(id, requestId)
  if (!revision.test(expectedRevision) || !prompt.trim() || new TextEncoder().encode(prompt).length > 256 * 1024) {
    throw new ApiError('Enter a nonempty message of at most 256 KiB with a valid saved revision.')
  }
  const operation = parseOperation(await request(`${projectPath(id)}/conversation/requests`, signal, {
    body: JSON.stringify({ request_id: requestId, prompt, revision: expectedRevision }),
    json: true, timeout: 160_000, statuses: [200, 201],
  }))
  if (operation.request_id !== requestId) invalid()
  return operation
}

export async function generateRequest(id: string, requestId: string, expectedRevision: string,
  signal: AbortSignal): Promise<OperationView> {
  if (!revision.test(expectedRevision)) throw new ApiError('Invalid saved revision.')
  const operation = parseOperation(await request(`${operationPath(id, requestId)}/generate`, signal, {
    body: JSON.stringify({ revision: expectedRevision }), json: true, timeout: 220_000, statuses: [200],
  }))
  if (operation.request_id !== requestId) invalid()
  return operation
}

export function previewUrl(id: string, proposalIdValue: string): string {
  if (!proposalId(proposalIdValue)) throw new ApiError('Invalid proposal ID.')
  return apiUrl(`${projectPath(id)}/proposals/${proposalIdValue}/preview`)
}

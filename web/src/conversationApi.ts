import { ApiError, apiUrl, request } from './api'
import { projectIdError } from './projects'

export interface OperationView {
  request_id: string
  status: 'interpreting' | 'prepared' | 'generating' | 'completed' | 'failed' | 'uncertain' | 'abandoned'
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
    role: 'user' | 'assistant' | 'activity'
    text: string
    kind: string
    proposal_id: string | null
  }[]
  baseline: { proposal_id: string } | null
  pending: { kind: 'question' | 'name_confirmation'; message: string } | null
  operation: OperationView | null
  proposals: { proposal_id: string; width: number; height: number }[]
  selection: { enabled: boolean; reason: string; confirmation: string | null; action: SelectionView | null }
}

export interface SelectionView {
  action_id: string
  proposal_id: string
  status: 'saving' | 'completed' | 'uncertain'
  revision: string | null
  message: string
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const revision = /^[0-9a-f]{64}$/
const proposal = /^P[0-9]{3,}$/
const statuses = ['interpreting', 'prepared', 'generating', 'completed', 'failed', 'uncertain', 'abandoned']
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
  if (!fields(value, ['project_id', 'revision', 'live_enabled', 'messages', 'baseline', 'pending', 'operation', 'proposals', 'selection']) ||
    value.project_id !== id || !text(value.revision) || !revision.test(value.revision) ||
    typeof value.live_enabled !== 'boolean' || !Array.isArray(value.messages) ||
    !(value.baseline === null || fields(value.baseline, ['proposal_id']) && proposalId(value.baseline.proposal_id)) ||
    !(value.pending === null || fields(value.pending, ['kind', 'message']) &&
      ['question', 'name_confirmation'].includes(value.pending.kind as string) && text(value.pending.message))) invalid()
  const ids = new Set<string>()
  for (const message of value.messages) {
    if (!fields(message, ['id', 'role', 'text', 'kind', 'proposal_id']) ||
      !text(message.id) || !message.id || ids.has(message.id) ||
      !['user', 'assistant', 'activity'].includes(message.role as string) ||
      !text(message.text) || !text(message.kind) || !nullableProposal(message.proposal_id)) invalid()
    ids.add(message.id)
  }
  if (value.operation !== null) {
    const operation = parseOperation(value.operation)
    if (['completed', 'failed', 'abandoned'].includes(operation.status)) invalid()
  }
  if (!Array.isArray(value.proposals)) invalid()
  const proposalIds = new Set<string>()
  for (const item of value.proposals) {
    if (!fields(item, ['proposal_id', 'width', 'height']) || !proposalId(item.proposal_id) ||
      proposalIds.has(item.proposal_id) || !Number.isInteger(item.width) || !Number.isInteger(item.height) ||
      typeof item.width !== 'number' || item.width < 1 || item.width > 4096 ||
      typeof item.height !== 'number' || item.height < 1 || item.height > 4096) invalid()
    proposalIds.add(item.proposal_id)
  }
  if (!fields(value.selection, ['enabled', 'reason', 'confirmation', 'action']) ||
    typeof value.selection.enabled !== 'boolean' || !text(value.selection.reason) ||
    !nullableText(value.selection.confirmation)) invalid()
  if (value.selection.action !== null) parseSelection(value.selection.action)
  return value as unknown as ConversationView
}

function parseSelection(value: unknown): SelectionView {
  if (!fields(value, ['action_id', 'proposal_id', 'status', 'revision', 'message']) ||
    !text(value.action_id) || !uuid.test(value.action_id) || !proposalId(value.proposal_id) ||
    !text(value.status) || !['saving', 'completed', 'uncertain'].includes(value.status) ||
    !(value.revision === null || text(value.revision) && revision.test(value.revision)) ||
    !text(value.message) || value.status === 'completed' && value.revision === null) invalid()
  return value as unknown as SelectionView
}

export async function selectCollage(id: string, actionId: string, proposalIdValue: string, expectedRevision: string,
  abandonPending: boolean, signal: AbortSignal): Promise<SelectionView> {
  if (!uuid.test(actionId) || !proposalId(proposalIdValue) || !revision.test(expectedRevision)) {
    throw new ApiError('Invalid collage selection.')
  }
  const result = parseSelection(await request(`${projectPath(id)}/conversation/selections`, signal, {
    body: JSON.stringify({ action_id: actionId, proposal_id: proposalIdValue, revision: expectedRevision,
      abandon_pending: abandonPending }), json: true, timeout: 10_000, statuses: [200, 201],
  }))
  if (result.action_id !== actionId || result.proposal_id !== proposalIdValue) invalid()
  return result
}

export async function loadSelection(id: string, actionId: string, signal: AbortSignal): Promise<SelectionView> {
  if (!uuid.test(actionId)) throw new ApiError('Invalid action ID.')
  const result = parseSelection(await request(`${projectPath(id)}/conversation/selections/${actionId}`, signal))
  if (result.action_id !== actionId) invalid()
  return result
}

export async function downloadCollage(id: string, proposalIdValue: string, signal: AbortSignal) {
  previewUrl(id, proposalIdValue)
  const blob = await request(`${projectPath(id)}/proposals/${proposalIdValue}/preview`, signal, { binary: true })
  if (!(blob instanceof Blob)) throw new ApiError('No PNG was returned.')
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  try {
    anchor.href = url
    anchor.download = `${id}-${proposalIdValue}.png`
    document.body.append(anchor)
    anchor.click()
  } finally {
    anchor.remove()
    URL.revokeObjectURL(url)
  }
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

export function thumbnailUrl(id: string, proposalIdValue: string): string {
  if (!proposalId(proposalIdValue)) throw new ApiError('Invalid proposal ID.')
  return apiUrl(`${projectPath(id)}/proposals/${proposalIdValue}/thumbnail`)
}

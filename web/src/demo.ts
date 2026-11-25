const asset = (name: string) => `${import.meta.env.BASE_URL}demo/${name}`

export const photos = [1, 2, 3, 4]
  .map((number) => ({ number, src: asset(`photo-${number}.jpg`) }))

export type ProposalId = 'P001' | 'P002'

export interface Proposal {
  id: ProposalId
  image: string
}

export const proposals: Record<ProposalId, Proposal> = {
  P001: {
    id: 'P001',
    image: asset('london-cream.png'),
  },
  P002: {
    id: 'P002',
    image: asset('london-charcoal.png'),
  },
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  proposal?: ProposalId
}

export interface DemoStep {
  prompt: string
  response: Message
}

export const welcome: Message = {
  id: 'welcome',
  role: 'assistant',
  text: 'Use the suggested messages to try the sample conversation.',
}

export const steps: readonly DemoStep[] = [
  {
    prompt: 'Use all four photos with a cream background, white borders and gentle tilts.',
    response: {
      id: 'first-proposal',
      role: 'assistant',
      text: 'All four photos, with a cream background, white borders and gentle tilts.',
      proposal: 'P001',
    },
  },
  {
    prompt: 'Use a darker background.',
    response: {
      id: 'clarification',
      role: 'assistant',
      text: 'Change just the background to charcoal, keeping the arrangement unchanged?',
    },
  },
  {
    prompt: 'Yes, just change the background to charcoal.',
    response: {
      id: 'second-proposal',
      role: 'assistant',
      text: 'The background is now charcoal. Photo positions, sizes, borders and tilts are unchanged.',
      proposal: 'P002',
    },
  },
]

export function matchesPrompt(input: string, expected: string) {
  return input.trim().toLowerCase() === expected.toLowerCase()
}

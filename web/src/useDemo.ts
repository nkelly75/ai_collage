import { useEffect, useState } from 'react'
import { matchesPrompt, steps, welcome } from './demo'
import type { DemoStep, Message, ProposalId } from './demo'

interface Pending {
  step: DemoStep
  phase: 'intent' | 'layout'
}

export function useDemo() {
  const [messages, setMessages] = useState<Message[]>([welcome])
  const [stepIndex, setStepIndex] = useState(0)
  const [active, setActive] = useState<ProposalId | null>(null)
  const [accepted, setAccepted] = useState<ProposalId | null>(null)
  const [pending, setPending] = useState<Pending | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const next = steps[stepIndex]

  useEffect(() => {
    if (!pending) return
    const timer = window.setTimeout(() => {
      if (pending.phase === 'intent' && pending.step.response.proposal) {
        setPending({ ...pending, phase: 'layout' })
      } else {
        setMessages((previous) => [...previous, pending.step.response])
        if (pending.step.response.proposal) setActive(pending.step.response.proposal)
        setStepIndex((previous) => previous + 1)
        setPending(null)
      }
    }, 650)
    return () => window.clearTimeout(timer)
  }, [pending])

  function submit(input: string) {
    if (pending) return false
    if (!next || !matchesPrompt(input, next.prompt)) {
      setError(next
        ? 'Only the suggested sample message is supported. No AI request was made.'
        : 'The sample walkthrough is complete. Select a proposal or reset the prototype.')
      return false
    }
    setError('')
    setNotice('')
    setMessages((previous) => [...previous, {
      id: `user-${stepIndex}`, role: 'user', text: input.trim(),
    }])
    setPending({ step: next, phase: 'intent' })
    return true
  }

  function select(id: ProposalId) {
    if (pending) return
    setActive(id)
    setNotice('Baseline changed. Later history is retained.')
  }

  function accept() {
    if (pending || !active) return
    setAccepted(active)
    setNotice('Accepted in this tab only. No version was saved.')
  }

  return {
    messages, active, accepted, error, notice, next, submit, select, accept,
    busy: pending !== null,
    progress: pending
      ? pending.phase === 'intent' ? 'Understanding your request' : 'Creating your layout'
      : '',
  }
}

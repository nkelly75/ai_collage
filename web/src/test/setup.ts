import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

beforeEach(() => {
  const blocked = () => { throw new Error('Tests must explicitly mock backend requests.') }
  vi.stubGlobal('fetch', vi.fn(blocked))
  vi.stubGlobal('XMLHttpRequest', blocked)
  vi.stubGlobal('WebSocket', blocked)
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(blocked)
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(blocked)
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

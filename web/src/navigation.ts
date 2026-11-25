import { useSyncExternalStore } from 'react'

export function navigate(path: string) {
  if (location.pathname === path) return
  history.pushState(null, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

function subscribe(onChange: () => void) {
  window.addEventListener('popstate', onChange)
  return () => window.removeEventListener('popstate', onChange)
}

export function usePath() {
  return useSyncExternalStore(subscribe, () => location.pathname)
}

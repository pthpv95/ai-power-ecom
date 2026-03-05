const STORAGE_KEY = 'guest_user_id'

export function getUserId(): string {
  if (typeof window === 'undefined') {
    // SSR fallback — will be replaced on client hydration
    return 'guest_ssr'
  }

  let id = localStorage.getItem(STORAGE_KEY)
  if (!id) {
    id = `guest_${crypto.randomUUID()}`
    localStorage.setItem(STORAGE_KEY, id)
  }
  return id
}

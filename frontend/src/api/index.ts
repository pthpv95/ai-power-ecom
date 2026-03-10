import { getUserId } from '../lib/user'

export interface Product {
  id: number
  name: string
  description: string
  price: number
  category: string
  brand: string
  stock: number
  image_url: string | null
}

export interface CartItem {
  id: number
  user_id: string
  product_id: number
  quantity: number
  product: Product
}

export interface Cart {
  items: CartItem[]
  total: number
}

export async function fetchProducts(): Promise<Product[]> {
  const res = await fetch('/api/products')
  return res.json()
}

export async function fetchCart(): Promise<Cart> {
  const res = await fetch(`/api/cart/${getUserId()}`)
  return res.json()
}

export async function addToCart(product_id: number): Promise<CartItem> {
  const res = await fetch('/api/cart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: getUserId(), product_id, quantity: 1 }),
  })
  return res.json()
}

export async function removeFromCart(item_id: number): Promise<void> {
  await fetch(`/api/cart/${item_id}?user_id=${encodeURIComponent(getUserId())}`, { method: 'DELETE' })
}

export async function updateCartQuantity(item_id: number, quantity: number): Promise<void> {
  await fetch(`/api/cart/${item_id}?user_id=${encodeURIComponent(getUserId())}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity }),
  })
}

export interface ChatMessage {
  id: number
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export async function loadConversation(conversation_id: string): Promise<ChatMessage[]> {
  const res = await fetch(`/api/chat/${conversation_id}/messages?user_id=${encodeURIComponent(getUserId())}`)
  return res.json()
}

export interface ChatResponse {
  reply: string
  conversation_id: string
}

export async function sendChatMessage(
  message: string,
  conversation_id: string | null,
): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: getUserId(),
      message,
      conversation_id,
    }),
  })
  return res.json()
}

/**
 * Two-step SSE streaming:
 * 1. POST /api/chat/stream → enqueue agent task, get { conversation_id }
 * 2. GET  /api/chat/events/{conversation_id} → read SSE events via fetch+ReadableStream
 *
 * Same callback interface as before — ChatPanel.tsx stays unchanged.
 */
export async function streamChatMessage(
  message: string,
  conversation_id: string | null,
  callbacks: {
    onToken: (token: string) => void
    onStatus: (status: string) => void
    onDone: (conversation_id: string) => void
    onError: (error: string) => void
    onCartUpdated?: () => void
  },
): Promise<void> {
  // Step 1: Enqueue the agent task
  const enqueueRes = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: getUserId(),
      message,
      conversation_id,
    }),
  })

  if (!enqueueRes.ok) {
    callbacks.onError('Failed to enqueue chat message')
    return
  }

  const { request_id: reqId } = await enqueueRes.json()

  // Step 2: Open SSE connection keyed by request_id (unique per message)
  const eventsRes = await fetch(`/api/chat/events/${reqId}`)

  if (!eventsRes.ok || !eventsRes.body) {
    callbacks.onError('Failed to connect to event stream')
    return
  }

  const reader = eventsRes.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE events are separated by double newlines
    const events = buffer.split('\n\n')
    buffer = events.pop() || '' // last chunk might be incomplete

    for (const event of events) {
      const line = event.trim()
      if (!line.startsWith('data: ')) continue

      const data = JSON.parse(line.slice(6)) // strip "data: "

      switch (data.type) {
        case 'token':
          callbacks.onToken(data.content)
          break
        case 'status':
          callbacks.onStatus(data.content)
          break
        case 'cart_updated':
          callbacks.onCartUpdated?.()
          break
        case 'done':
          callbacks.onDone(data.conversation_id)
          break
        case 'error':
          callbacks.onError(data.content)
          break
      }
    }
  }
}

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

const USER_ID = 'user_abc' // hardcoded for now, will come from auth later

export async function fetchProducts(): Promise<Product[]> {
  const res = await fetch('/api/products')
  return res.json()
}

export async function fetchCart(): Promise<Cart> {
  const res = await fetch(`/api/cart/${USER_ID}`)
  return res.json()
}

export async function addToCart(product_id: number): Promise<CartItem> {
  const res = await fetch('/api/cart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: USER_ID, product_id, quantity: 1 }),
  })
  return res.json()
}

export async function removeFromCart(item_id: number): Promise<void> {
  await fetch(`/api/cart/${item_id}`, { method: 'DELETE' })
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
      user_id: USER_ID,
      message,
      conversation_id,
    }),
  })
  return res.json()
}

/**
 * SSE streaming version — reads tokens as they arrive.
 *
 * We use fetch() + ReadableStream instead of EventSource because:
 * 1. EventSource only supports GET requests (we need POST with a body)
 * 2. fetch gives us more control over error handling
 * 3. ReadableStream lets us process chunks as they arrive
 */
export async function streamChatMessage(
  message: string,
  conversation_id: string | null,
  callbacks: {
    onToken: (token: string) => void
    onStatus: (status: string) => void
    onDone: (conversation_id: string) => void
    onError: (error: string) => void
  },
): Promise<void> {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: USER_ID,
      message,
      conversation_id,
    }),
  })

  if (!res.ok || !res.body) {
    callbacks.onError('Failed to connect to chat stream')
    return
  }

  const reader = res.body.getReader()
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
        case 'done':
          callbacks.onDone(data.conversation_id)
          break
      }
    }
  }
}

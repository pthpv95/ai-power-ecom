import { useState, useEffect, useCallback } from 'react'
import ChatPanel from './components/ChatPanel'
import ProductGrid from './components/ProductGrid'
import CartDrawer from './components/CartDrawer'

function getConversationIdFromUrl(): string | null {
  const params = new URLSearchParams(window.location.search)
  return params.get('c')
}

function setConversationIdInUrl(id: string | null) {
  const url = new URL(window.location.href)
  if (id) {
    url.searchParams.set('c', id)
  } else {
    url.searchParams.delete('c')
  }
  window.history.replaceState({}, '', url.toString())
}

export default function App() {
  const [conversationId, setConversationId] = useState<string | null>(
    getConversationIdFromUrl,
  )
  const [cartVersion, setCartVersion] = useState(0)

  useEffect(() => {
    setConversationIdInUrl(conversationId)
  }, [conversationId])

  const refreshCart = useCallback(() => {
    setCartVersion((v) => v + 1)
  }, [])

  return (
    <div className="flex h-screen bg-white text-gray-900">
      <div className="w-[380px] border-r border-gray-200 flex flex-col shrink-0">
        <ChatPanel
          conversationId={conversationId}
          onConversationId={(id) => setConversationId(id || null)}
          onCartUpdated={refreshCart}
        />
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <ProductGrid />
      </div>

      <div className="w-[280px] border-l border-gray-200 flex flex-col shrink-0">
        <CartDrawer cartVersion={cartVersion} />
      </div>
    </div>
  )
}

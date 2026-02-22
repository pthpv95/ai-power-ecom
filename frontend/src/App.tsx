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
  const [isCartOpen, setIsCartOpen] = useState(false)
  const [cartItemCount, setCartItemCount] = useState(0)

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
        <ProductGrid onCartUpdated={refreshCart} />
      </div>

      {/* Floating cart icon button */}
      <button
        onClick={() => setIsCartOpen(true)}
        className="fixed top-4 right-4 z-40 bg-blue-600 hover:bg-blue-700 text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg transition-colors"
        aria-label="Open cart"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
        </svg>
        {cartItemCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
            {cartItemCount > 99 ? '99+' : cartItemCount}
          </span>
        )}
      </button>

      <CartDrawer
        cartVersion={cartVersion}
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        onItemCountChange={setCartItemCount}
      />
    </div>
  )
}

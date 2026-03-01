import { useEffect, useState } from 'react'
import { fetchCart, removeFromCart, addToCart, updateCartQuantity, type Cart } from '../api'

function getCategoryGradient(category: string): string {
  const cat = category.toLowerCase()
  if (cat.includes('jacket') || cat.includes('outerwear')) return 'from-blue-500 to-blue-700'
  if (cat.includes('footwear') || cat.includes('shoe') || cat.includes('boot')) return 'from-amber-500 to-orange-600'
  if (cat.includes('backpack') || cat.includes('bag')) return 'from-emerald-500 to-teal-600'
  if (cat.includes('tent') || cat.includes('shelter')) return 'from-violet-500 to-purple-700'
  if (cat.includes('sleeping')) return 'from-indigo-500 to-blue-600'
  return 'from-slate-500 to-slate-700'
}

interface CartDrawerProps {
  cartVersion: number
  isOpen: boolean
  onClose: () => void
  onItemCountChange: (count: number) => void
  onCartUpdated: () => void
}

export default function CartDrawer({ cartVersion, isOpen, onClose, onItemCountChange, onCartUpdated }: CartDrawerProps) {
  const [cart, setCart] = useState<Cart>({ items: [], total: 0 })

  async function loadCart() {
    const data = await fetchCart()
    setCart(data)
    onItemCountChange(data.items.reduce((sum, item) => sum + item.quantity, 0))
  }

  useEffect(() => {
    loadCart()
  }, [cartVersion])

  async function handleRemove(itemId: number) {
    await removeFromCart(itemId)
    loadCart()
    onCartUpdated()
  }

  async function handleIncrement(productId: number) {
    await addToCart(productId)
    loadCart()
    onCartUpdated()
  }

  async function handleDecrement(itemId: number, currentQty: number) {
    if (currentQty <= 1) {
      await removeFromCart(itemId)
    } else {
      await updateCartQuantity(itemId, currentQty - 1)
    }
    loadCart()
    onCartUpdated()
  }

  const totalItems = cart.items.reduce((sum, item) => sum + item.quantity, 0)

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 animate-fade-in"
          onClick={onClose}
        />
      )}

      {/* Drawer panel */}
      <div
        className={`fixed top-0 right-0 h-full w-[360px] bg-white shadow-2xl z-50 flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-text-primary">Shopping Cart</h2>
            <p className="text-xs text-text-muted mt-0.5">{totalItems} {totalItems === 1 ? 'item' : 'items'}</p>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary p-1.5 rounded-lg hover:bg-surface-secondary transition-colors"
            aria-label="Close cart"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin">
          {cart.items.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-full bg-surface-secondary flex items-center justify-center mb-3">
                <svg className="w-8 h-8 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-text-secondary">Your cart is empty</p>
              <p className="text-xs text-text-muted mt-1">Add items to get started</p>
            </div>
          )}

          {cart.items.map((item) => (
            <div key={item.id} className="bg-surface-secondary rounded-xl p-3 animate-fade-in">
              <div className="flex gap-3">
                {/* Mini gradient image */}
                <div className={`w-14 h-14 rounded-lg bg-gradient-to-br ${getCategoryGradient(item.product.category)} flex items-center justify-center shrink-0`}>
                  <svg className="w-6 h-6 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.41a2.25 2.25 0 013.182 0l2.909 2.91m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                  </svg>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-text-primary truncate">{item.product.name}</div>
                  <div className="text-xs text-text-muted">{item.product.category}</div>
                  <div className="flex items-center justify-between mt-2">
                    {/* Quantity controls */}
                    <div className="flex items-center gap-0">
                      <button
                        onClick={() => handleDecrement(item.id, item.quantity)}
                        className="w-7 h-7 rounded-l-lg border border-border bg-white hover:bg-surface-secondary flex items-center justify-center text-text-secondary transition-colors"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" d="M19.5 12h-15" />
                        </svg>
                      </button>
                      <div className="w-8 h-7 border-y border-border bg-white flex items-center justify-center text-xs font-medium text-text-primary">
                        {item.quantity}
                      </div>
                      <button
                        onClick={() => handleIncrement(item.product_id)}
                        className="w-7 h-7 rounded-r-lg border border-border bg-white hover:bg-surface-secondary flex items-center justify-center text-text-secondary transition-colors"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" d="M12 4.5v15m7.5-7.5h-15" />
                        </svg>
                      </button>
                    </div>

                    <span className="text-sm font-semibold text-text-primary">
                      ${(item.product.price * item.quantity).toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Remove button */}
                <button
                  onClick={() => handleRemove(item.id)}
                  className="text-text-muted hover:text-red-500 p-1 self-start transition-colors"
                  aria-label="Remove item"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        {cart.items.length > 0 && (
          <div className="p-4 border-t border-border space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-text-secondary">Total</span>
              <span className="text-lg font-semibold text-text-primary">${cart.total.toFixed(2)}</span>
            </div>
            <button className="w-full bg-primary hover:bg-primary-hover text-white py-2.5 rounded-xl text-sm font-medium transition-colors active:scale-[0.98]">
              Proceed to Checkout
            </button>
          </div>
        )}
      </div>
    </>
  )
}

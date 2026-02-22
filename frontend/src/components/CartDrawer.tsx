import { useEffect, useState } from 'react'
import { fetchCart, removeFromCart, type Cart } from '../api'

interface CartDrawerProps {
  cartVersion: number
  isOpen: boolean
  onClose: () => void
  onItemCountChange: (count: number) => void
}

export default function CartDrawer({ cartVersion, isOpen, onClose, onItemCountChange }: CartDrawerProps) {
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
  }

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Drawer panel */}
      <div
        className={`fixed top-0 right-0 h-full w-[320px] bg-white shadow-xl z-50 flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <span className="font-semibold text-gray-700">Cart ({cart.items.length})</span>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1"
            aria-label="Close cart"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {cart.items.length === 0 && (
            <p className="text-sm text-gray-400 text-center mt-8">Your cart is empty</p>
          )}
          {cart.items.map((item) => (
            <div key={item.id} className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-800">{item.product.name}</div>
                <div className="text-xs text-gray-400">Qty: {item.quantity}</div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <span className="text-sm font-semibold text-blue-600">
                  ${(item.product.price * item.quantity).toFixed(2)}
                </span>
                <button
                  onClick={() => handleRemove(item.id)}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Total */}
        {cart.items.length > 0 && (
          <div className="p-4 border-t border-gray-200">
            <div className="flex justify-between font-semibold text-gray-800">
              <span>Total</span>
              <span>${cart.total.toFixed(2)}</span>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

import { useEffect, useState } from 'react'
import { fetchCart, removeFromCart, type Cart } from '../api'

export default function CartDrawer({ cartVersion }: { cartVersion: number }) {
  const [cart, setCart] = useState<Cart>({ items: [], total: 0 })

  async function loadCart() {
    const data = await fetchCart()
    setCart(data)
  }

  useEffect(() => {
    loadCart()
  }, [cartVersion])

  async function handleRemove(itemId: number) {
    await removeFromCart(itemId)
    loadCart()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-200 font-semibold text-gray-700">
        Cart ({cart.items.length})
      </div>

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

      {cart.items.length > 0 && (
        <div className="p-4 border-t border-gray-200">
          <div className="flex justify-between font-semibold text-gray-800">
            <span>Total</span>
            <span>${cart.total.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { addToCart } from '../api'
import { useToast } from './Toast'

interface ProductCardProps {
  id: number
  name: string
  price: string
  onCartUpdated: () => void
}

export default function ProductCard({ id, name, price, onCartUpdated }: ProductCardProps) {
  const [added, setAdded] = useState(false)
  const { toast } = useToast()

  async function handleAdd() {
    await addToCart(id)
    onCartUpdated()
    setAdded(true)
    toast(`${name} added to cart!`)
    setTimeout(() => setAdded(false), 1500)
  }

  return (
    <div className="flex items-center justify-between gap-2 bg-sidebar-lighter/50 border border-border-sidebar rounded-xl px-3 py-2 my-1 hover:bg-sidebar-lighter transition-colors">
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-text-sidebar truncate">{name}</div>
        <div className="text-xs font-semibold text-primary">{price}</div>
      </div>
      <button
        onClick={handleAdd}
        disabled={added}
        className={`text-xs px-3 py-1 rounded-full shrink-0 transition-all duration-200 ${
          added
            ? 'bg-emerald-600 text-white'
            : 'bg-primary text-white hover:bg-primary-hover'
        }`}
      >
        {added ? (
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            Added
          </span>
        ) : (
          'Add'
        )}
      </button>
    </div>
  )
}

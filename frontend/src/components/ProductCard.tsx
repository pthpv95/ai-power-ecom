import { addToCart } from '../api'

interface ProductCardProps {
  id: number
  name: string
  price: string
  onCartUpdated: () => void
}

export default function ProductCard({ id, name, price, onCartUpdated }: ProductCardProps) {
  async function handleAdd() {
    await addToCart(id)
    onCartUpdated()
  }

  return (
    <div className="flex items-center justify-between gap-2 bg-white border border-gray-200 rounded-xl px-3 py-2 my-1">
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-800 truncate">{name}</div>
        <div className="text-xs font-semibold text-blue-600">{price}</div>
      </div>
      <button
        onClick={handleAdd}
        className="text-xs bg-blue-500 text-white px-3 py-1 rounded-full hover:bg-blue-600 shrink-0"
      >
        Add
      </button>
    </div>
  )
}

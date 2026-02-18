import { useEffect, useState } from 'react'
import { fetchProducts, addToCart, type Product } from '../api'

export default function ProductGrid() {
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => {
    fetchProducts().then(setProducts)
  }, [])

  async function handleAddToCart(productId: number) {
    await addToCart(productId)
    alert('Added to cart!')
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-200 font-semibold text-gray-700">
        Products ({products.length})
      </div>

      <div className="flex-1 overflow-y-auto p-4 grid grid-cols-2 gap-3 content-start">
        {products.map((p) => (
          <div key={p.id} className="border border-gray-200 rounded-xl p-3 flex flex-col gap-2">
            <div className="text-xs text-gray-400 uppercase tracking-wide">{p.category}</div>
            <div className="font-medium text-sm text-gray-800 leading-tight">{p.name}</div>
            <div className="text-xs text-gray-500 line-clamp-2">{p.description}</div>
            <div className="flex items-center justify-between mt-auto">
              <span className="font-semibold text-blue-600">${p.price}</span>
              <button
                onClick={() => handleAddToCart(p.id)}
                className="text-xs bg-blue-500 text-white px-3 py-1 rounded-full hover:bg-blue-600"
              >
                Add to cart
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

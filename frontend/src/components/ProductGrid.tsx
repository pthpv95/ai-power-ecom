import { useEffect, useState } from 'react'
import { fetchProducts, addToCart, type Product } from '../api'
import { useToast } from './Toast'

function getCategoryGradient(category: string): string {
  const cat = category.toLowerCase()
  if (cat.includes('jacket') || cat.includes('outerwear')) return 'from-blue-500 to-blue-700'
  if (cat.includes('footwear') || cat.includes('shoe') || cat.includes('boot')) return 'from-amber-500 to-orange-600'
  if (cat.includes('backpack') || cat.includes('bag')) return 'from-emerald-500 to-teal-600'
  if (cat.includes('tent') || cat.includes('shelter')) return 'from-violet-500 to-purple-700'
  if (cat.includes('sleeping')) return 'from-indigo-500 to-blue-600'
  return 'from-slate-500 to-slate-700'
}

function StockBadge({ stock }: { stock: number }) {
  if (stock === 0) {
    return <span className="text-[11px] font-medium text-red-500">Out of stock</span>
  }
  if (stock <= 5) {
    return <span className="text-[11px] font-medium text-amber-500">Low stock ({stock})</span>
  }
  return <span className="text-[11px] font-medium text-emerald-500">In stock</span>
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-border-light overflow-hidden">
      <div className="h-32 skeleton" />
      <div className="p-3 space-y-2">
        <div className="h-3 w-16 skeleton" />
        <div className="h-4 w-3/4 skeleton" />
        <div className="h-3 w-1/2 skeleton" />
        <div className="flex items-center justify-between pt-1">
          <div className="h-5 w-16 skeleton" />
          <div className="h-7 w-20 skeleton rounded-full" />
        </div>
      </div>
    </div>
  )
}

export default function ProductGrid({ onCartUpdated }: { onCartUpdated?: () => void }) {
  const [products, setProducts] = useState<Product[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [addedIds, setAddedIds] = useState<Set<number>>(new Set())
  const { toast } = useToast()

  useEffect(() => {
    fetchProducts().then((data) => {
      setProducts(data)
      setIsLoading(false)
    })
  }, [])

  async function handleAddToCart(product: Product) {
    if (product.stock === 0) return
    await addToCart(product.id)
    onCartUpdated?.()
    toast(`${product.name} added to cart!`)

    setAddedIds((prev) => new Set(prev).add(product.id))
    setTimeout(() => {
      setAddedIds((prev) => {
        const next = new Set(prev)
        next.delete(product.id)
        return next
      })
    }, 1500)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-text-primary">Products</h2>
          {!isLoading && (
            <p className="text-xs text-text-muted mt-0.5">{products.length} items</p>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 content-start">
            {products.map((p) => {
              const isAdded = addedIds.has(p.id)

              return (
                <div
                  key={p.id}
                  className="bg-white border border-border-light rounded-xl overflow-hidden shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200"
                >
                  {/* Image placeholder */}
                  <div className={`h-32 bg-gradient-to-br ${getCategoryGradient(p.category)} flex items-center justify-center`}>
                    <svg className="w-10 h-10 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.41a2.25 2.25 0 013.182 0l2.909 2.91m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                    </svg>
                  </div>

                  <div className="p-3 flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-text-muted uppercase tracking-wider font-medium">{p.category}</span>
                      <StockBadge stock={p.stock} />
                    </div>
                    <div className="font-medium text-sm text-text-primary leading-tight">{p.name}</div>
                    <div className="text-xs text-text-muted">{p.brand}</div>
                    <div className="text-xs text-text-secondary line-clamp-2">{p.description}</div>
                    <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-border-light">
                      <span className="font-semibold text-text-primary">${p.price}</span>
                      <button
                        onClick={() => handleAddToCart(p)}
                        disabled={p.stock === 0 || isAdded}
                        className={`text-xs px-3 py-1.5 rounded-full font-medium transition-all duration-200 ${
                          isAdded
                            ? 'bg-emerald-600 text-white'
                            : p.stock === 0
                              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                              : 'bg-primary text-white hover:bg-primary-hover active:scale-95'
                        }`}
                      >
                        {isAdded ? (
                          <span className="flex items-center gap-1">
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                            Added!
                          </span>
                        ) : p.stock === 0 ? (
                          'Out of stock'
                        ) : (
                          'Add to cart'
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

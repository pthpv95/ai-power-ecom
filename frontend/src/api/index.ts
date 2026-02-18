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

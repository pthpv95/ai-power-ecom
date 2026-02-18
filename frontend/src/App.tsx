import ChatPanel from './components/ChatPanel'
import ProductGrid from './components/ProductGrid'
import CartDrawer from './components/CartDrawer'

export default function App() {
  return (
    <div className="flex h-screen bg-white text-gray-900">
      {/* Chat — left panel */}
      <div className="w-[380px] border-r border-gray-200 flex flex-col shrink-0">
        <ChatPanel />
      </div>

      {/* Products — center */}
      <div className="flex-1 flex flex-col min-w-0">
        <ProductGrid />
      </div>

      {/* Cart — right panel */}
      <div className="w-[280px] border-l border-gray-200 flex flex-col shrink-0">
        <CartDrawer />
      </div>
    </div>
  )
}

import { useRef, useState, useEffect, useCallback } from 'react'
import { streamChatMessage, loadConversation } from '../api'
import ProductCard from './ProductCard'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatPanelProps {
  conversationId: string | null
  onConversationId: (id: string) => void
  onCartUpdated: () => void
}

/**
 * Parse product references from agent messages.
 * The agent outputs: [ID:7] Summit Pro Rain Jacket — $74.99
 * We extract these into structured data for rendering cards.
 */
const PRODUCT_RE = /\[ID:(\d+)\]\s*(.+?)\s*—\s*(\$[\d.]+)/g

interface ParsedProduct {
  id: number
  name: string
  price: string
}

function parseProducts(text: string): ParsedProduct[] {
  const products: ParsedProduct[] = []
  let match
  while ((match = PRODUCT_RE.exec(text)) !== null) {
    products.push({ id: parseInt(match[1]), name: match[2].trim(), price: match[3] })
  }
  PRODUCT_RE.lastIndex = 0 // reset regex state
  return products
}

/** Strip [ID:X] tags from display text */
function formatDisplay(text: string): string {
  return text.replace(/\[ID:\d+\]\s*/g, '')
}

const GREETING: Message = {
  role: 'assistant',
  content: 'Hi! I can help you find outdoor gear. What are you looking for?',
}

export default function ChatPanel({ conversationId, onConversationId, onCartUpdated }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  const loadChat = useCallback(async (id: string) => {
    const dbMessages = await loadConversation(id)
    if (dbMessages.length > 0) {
      setMessages([GREETING, ...dbMessages.map((m) => ({ role: m.role, content: m.content }))])
    }
  }, [])

  useEffect(() => {
    if (conversationId) {
      loadChat(conversationId)
    }
  }, [conversationId, loadChat])

  async function sendMessage() {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)
    setStatus('')

    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

    await streamChatMessage(userMessage, conversationId, {
      onCartUpdated,
      onToken: (token) => {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          updated[updated.length - 1] = { ...last, content: last.content + token }
          return updated
        })
        setStatus('')
      },
      onStatus: (statusText) => {
        setStatus(statusText)
      },
      onDone: (newConversationId) => {
        onConversationId(newConversationId)
        setLoading(false)
        setStatus('')
      },
      onError: (error) => {
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: error }
          return updated
        })
        setLoading(false)
        setStatus('')
      },
    })
  }

  function newChat() {
    onConversationId('')
    setMessages([GREETING])
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <span className="font-semibold text-gray-700">AI Shopping Assistant</span>
        <button
          onClick={newChat}
          className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
        >
          New chat
        </button>
      </div>

      <div data-testid="message-list" className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, i) => {
          const products = msg.role === 'assistant' ? parseProducts(msg.content) : []

          return (
            <div key={i} data-testid={`message-${msg.role}`}>
              <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {msg.role === 'assistant' ? formatDisplay(msg.content) : msg.content}
                </div>
              </div>

              {/* Product cards rendered below the message */}
              {products.length > 0 && (
                <div className="mt-2 ml-2 space-y-1">
                  {products.map((p) => (
                    <ProductCard
                      key={p.id}
                      id={p.id}
                      name={p.name}
                      price={p.price}
                      onCartUpdated={onCartUpdated}
                    />
                  ))}
                </div>
              )}
            </div>
          )
        })}

        {status && (
          <div className="flex justify-start">
            <div className="bg-amber-50 border border-amber-200 rounded-2xl px-4 py-2 text-sm text-amber-600">
              {status}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-gray-200 flex gap-2">
        <input
          data-testid="chat-input"
          className="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm outline-none focus:border-blue-400"
          placeholder="Ask me anything about gear..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          disabled={loading}
        />
        <button
          data-testid="send-button"
          onClick={sendMessage}
          disabled={loading}
          className="bg-blue-500 text-white px-4 py-2 rounded-full text-sm hover:bg-blue-600 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  )
}

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

  // Show typing indicator when loading and last assistant message is empty
  const lastMsg = messages[messages.length - 1]
  const showTyping = loading && lastMsg?.role === 'assistant' && lastMsg.content === ''

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border-sidebar flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
          </svg>
          <span className="font-semibold text-text-sidebar">AI Shopping Assistant</span>
        </div>
        <button
          onClick={newChat}
          className="flex items-center gap-1 text-xs text-text-sidebar-muted hover:text-text-sidebar px-2 py-1.5 rounded-lg hover:bg-sidebar-light transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New chat
        </button>
      </div>

      {/* Messages */}
      <div data-testid="message-list" className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-dark">
        {messages.map((msg, i) => {
          const products = msg.role === 'assistant' ? parseProducts(msg.content) : []
          // Don't render empty assistant messages (typing indicator handles that)
          if (msg.role === 'assistant' && msg.content === '' && i === messages.length - 1 && loading) {
            return null
          }

          return (
            <div key={i} data-testid={`message-${msg.role}`} className="animate-fade-in-up">
              <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center mr-2 mt-1 shrink-0">
                    <svg className="w-3.5 h-3.5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                    </svg>
                  </div>
                )}
                <div
                  className={`max-w-[85%] px-4 py-2.5 text-sm whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-primary text-white rounded-2xl rounded-br-md'
                      : 'bg-sidebar-light text-text-sidebar rounded-2xl rounded-bl-md'
                  }`}
                >
                  {msg.role === 'assistant' ? formatDisplay(msg.content) : msg.content}
                </div>
              </div>

              {/* Product cards rendered below the message */}
              {products.length > 0 && (
                <div className="mt-2 ml-8 space-y-1">
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

        {/* Typing indicator */}
        {showTyping && (
          <div className="flex justify-start animate-fade-in">
            <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center mr-2 mt-1 shrink-0">
              <svg className="w-3.5 h-3.5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <div className="bg-sidebar-light rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-1.5">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}

        {/* Status indicator */}
        {status && (
          <div className="flex justify-start animate-fade-in">
            <div className="ml-8 bg-sidebar-lighter/50 rounded-xl px-3 py-2 text-xs text-text-sidebar-muted flex items-center gap-2">
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {status}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-3">
        <div className="bg-sidebar-light rounded-xl flex items-center gap-2 px-4 py-2">
          <input
            data-testid="chat-input"
            className="flex-1 bg-transparent text-text-sidebar placeholder-text-sidebar-muted text-sm outline-none"
            placeholder="Ask me anything about gear..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            disabled={loading}
          />
          <button
            data-testid="send-button"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-primary hover:bg-primary-hover text-white p-2 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

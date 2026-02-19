import { useRef, useState, useEffect, useCallback } from 'react'
import { streamChatMessage, loadConversation } from '../api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatPanelProps {
  conversationId: string | null
  onConversationId: (id: string) => void
  onCartUpdated: () => void
}

export default function ChatPanel({ conversationId, onConversationId, onCartUpdated }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hi! I can help you find outdoor gear. What are you looking for?' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  // Load conversation from DB when conversationId changes
  const loadChat = useCallback(async (id: string) => {
    const dbMessages = await loadConversation(id)
    if (dbMessages.length > 0) {
      setMessages(dbMessages.map((m) => ({ role: m.role, content: m.content })))
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
    setMessages([
      { role: 'assistant', content: 'Hi! I can help you find outdoor gear. What are you looking for?' },
    ])
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

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

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
          className="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm outline-none focus:border-blue-400"
          placeholder="Ask me anything about gear..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          disabled={loading}
        />
        <button
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

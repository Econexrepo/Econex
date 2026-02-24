import { useState, useEffect, useRef } from 'react'
import api from '../api/axios'
import './Chat.css'
import { FaTrash } from "react-icons/fa";

// ── Utility ─────────────────────────────────────────────────────────────────────
function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60)    return `${Math.round(diff)}s ago`
  if (diff < 3600)  return `${Math.round(diff / 60)}m ago`
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`
  return `${Math.round(diff / 86400)}d ago`
}

// ── Render markdown-ish text (bold, bullets) ─────────────────────────────────
function RenderContent({ content }) {
  const lines = content.split('\n')
  return (
    <div className="message-content">
      {lines.map((line, i) => {
        // Bold: **text**
        const parts = line.split(/\*\*(.*?)\*\*/g)
        const rendered = parts.map((part, j) =>
          j % 2 === 1 ? <strong key={j}>{part}</strong> : part
        )
        // Bullet
        if (line.startsWith('- ') || line.startsWith('• ')) {
          return <li key={i} className="msg-bullet">{rendered}</li>
        }
        if (line === '') return <br key={i} />
        return <p key={i} className="msg-para">{rendered}</p>
      })}
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────────────────
function SessionItem({ session, active, onClick, onDelete }) {
  return (
    <button
      className={`session-item${active ? ' session-item--active' : ''}`}
      onClick={onClick}
    >
      <div className="session-header-row">
        <span className="session-title">{session.title}</span>
        <span className="session-time">{timeAgo(session.created_at)}</span>
        <button
          className="session-delete-btn"
          onClick={(e) => onDelete(session.id, e)}
          title="Delete conversation"
        >
          <FaTrash size={11} />
        </button>
      </div>
      <p className="session-preview">{session.preview}</p>
      {session.tag && <span className={`session-tag session-tag--${session.tag.toLowerCase()}`}>{session.tag}</span>}
    </button>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`message-row${isUser ? ' message-row--user' : ''}`}>
      {!isUser && <div className="msg-avatar msg-avatar--ai">AI</div>}
      <div className={`message-bubble${isUser ? ' message-bubble--user' : ''}`}>
        {isUser
          ? msg.content
          : <RenderContent content={msg.content} />
        }
      </div>
      {isUser && (
        <div className="msg-avatar msg-avatar--user">
          <span>ME</span>
        </div>
      )}
    </div>
  )
}

// ── Welcome screen shown when chat is empty ───────────────────────────────────
function WelcomeScreen({ onSuggest }) {
  const suggestions = [
    { icon: '🌾', text: 'Show agriculture sectors impact on RSUI' },
    { icon: '🏭', text: 'Show industry sector under GDP impact' },
    { icon: '💼', text: 'Show services sector under GDP impact' },
    { icon: '📊', text: 'Compare all sectors under Wages' },
    { icon: '⚡', text: 'Show short-run coefficients' },
    { icon: '📈', text: 'Show long-run effects' },
  ]
  return (
    <div className="welcome-screen">
      <div className="welcome-icon">🧠</div>
      <h2 className="welcome-title">Econex AI</h2>
      <p className="welcome-subtitle">
      
        Ask about Agriculture,Wages,GDP, PCE,Unemployment impact on Sri Lanka's RSUI.
      </p>
      <div className="suggestions-grid">
        {suggestions.map((s, i) => (
          <button key={i} className="suggestion-chip" onClick={() => onSuggest(s.text)}>
            <span className="suggestion-icon">{s.icon}</span>
            <span>{s.text}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Main Chat page ──────────────────────────────────────────────────────────────
export default function Chat() {
  const [sessions,  setSessions]  = useState([])
  const [activeId,  setActiveId]  = useState(null)
  const [messages,  setMessages]  = useState([])
  const [input,     setInput]     = useState('')
  const [sending,   setSending]   = useState(false)
  const [search,    setSearch]    = useState('')
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load sessions from API on mount
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        const { data } = await api.get('/api/chat/sessions')
        setSessions(data)
        if (data.length > 0) {
          setActiveId(data[0].id)
          // Load messages for first session
          const { data: sess } = await api.get(`/api/chat/sessions/${data[0].id}`)
          setMessages(sess.messages || [])
        }
      } catch (err) {
        setError('Could not connect to Econex backend. Make sure the server is running.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Load messages for selected session
  const selectSession = async (id) => {
    setActiveId(id)
    try {
      const { data } = await api.get(`/api/chat/sessions/${id}`)
      setMessages(data.messages || [])
    } catch {
      setMessages([])
    }
  }

  // New session
  const newSession = async () => {
    try {
      const { data } = await api.post('/api/chat/sessions')
      setSessions((prev) => [data, ...prev])
      setActiveId(data.id)
      setMessages([])
      inputRef.current?.focus()
    } catch (err) {
      console.error('Failed to create session', err)
    }
  }

  // Delete session
  const deleteSession = async (id, e) => {
    e.stopPropagation()
    try {
      await api.delete(`/api/chat/sessions/${id}`)
      setSessions((prev) => prev.filter((s) => s.id !== id))
      if (activeId === id) {
        const remaining = sessions.filter((s) => s.id !== id)
        if (remaining.length > 0) {
          selectSession(remaining[0].id)
        } else {
          setActiveId(null)
          setMessages([])
        }
      }
    } catch (err) {
      console.error('Failed to delete session', err)
    }
  }

  // Send message
  const sendMessage = async (overrideText) => {
    const text = (overrideText || input).trim()
    if (!text || sending) return
    setInput('')
    setSending(true)
    setError(null)

    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() }
    setMessages((prev) => [...prev, userMsg])

    try {
      const { data } = await api.post('/api/chat/message', {
        session_id: activeId,
        message: text,
      })
      const aiMsg = {
        role: 'assistant',
        content: data.content,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, aiMsg])

      // Refresh sessions list to update preview/title
      const { data: updatedSessions } = await api.get('/api/chat/sessions')
      setSessions(updatedSessions)
    } catch (err) {
      const errMsg = err?.response?.data?.detail || 'Error getting response. Please try again.'
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `⚠️ ${errMsg}`, timestamp: new Date().toISOString() },
      ])
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const filtered = sessions.filter((s) =>
    s.title.toLowerCase().includes(search.toLowerCase()) ||
    s.preview?.toLowerCase().includes(search.toLowerCase())
  )

  const activeSession = sessions.find((s) => s.id === activeId)

  if (loading) {
    return (
      <div className="chat-layout chat-loading">
        <div className="loading-spinner" />
        <p>Connecting to Econex AI…</p>
      </div>
    )
  }

  return (
    <div className="chat-layout">
      {/* ── Left panel: sessions list ── */}
      <aside className="chat-sidebar">
        <div className="chat-sidebar-header">
          <h2 className="chat-sidebar-title">Chat History</h2>
          <button className="new-chat-btn" onClick={newSession} title="New chat">＋ New</button>
        </div>

        <div className="chat-search-wrap">
          <input
            className="chat-search"
            type="text"
            placeholder="🔍 Search conversations…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="session-list">
          {filtered.length === 0 && (
            <p className="session-empty">No conversations yet.<br />Start a new chat!</p>
          )}
          {filtered.map((s) => (
            <SessionItem
              key={s.id}
              session={s}
              active={s.id === activeId}
              onClick={() => selectSession(s.id)}
              onDelete={deleteSession}
            />
          ))}
        </div>
      </aside>

      {/* ── Right panel: conversation ── */}
      <div className="chat-main">
        <div className="chat-main-header">
          <div className="chat-header-left">
            <h2 className="chat-conv-title">
              {activeSession?.title || 'Econex AI Assistant'}
            </h2>
            {activeSession?.tag && (
              <span className={`header-tag header-tag--${activeSession.tag.toLowerCase()}`}>
                {activeSession.tag}
              </span>
            )}
          </div>
          <div className="chat-header-right">
            <span className="header-model-badge">GPT-4o</span>
          </div>
        </div>

        {error && (
          <div className="chat-error-banner">
            ⚠️ {error}
          </div>
        )}

        <div className="messages-area">
          {messages.length === 0 && !sending ? (
            <WelcomeScreen onSuggest={(text) => { setInput(text); sendMessage(text) }} />
          ) : (
            messages.map((msg, i) => <Message key={i} msg={msg} />)
          )}
          {sending && (
            <div className="message-row">
              <div className="msg-avatar msg-avatar--ai">AI</div>
              <div className="message-bubble typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="chat-input-row">
          <textarea
            ref={inputRef}
            className="chat-input"
            rows={1}
            placeholder="Ask me anything — e.g. 'Predict RSUI if Agriculture increases by 5%'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="send-btn"
            onClick={() => sendMessage()}
            disabled={!input.trim() || sending}
            title="Send (Enter)"
          >
            {sending ? '…' : '➤'}
          </button>
        </div>
        <p className="chat-hint">Press Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}

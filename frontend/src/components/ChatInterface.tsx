import React, { useState, useEffect, useRef } from 'react'

// Chat message type
export interface ChatMessage {
  id: string;
  text: string;
  timestamp: string;
  sender: 'user' | 'system' | 'ai';
  avatar?: string;
}

interface ChatInterfaceProps {
  isConnected: boolean;
  onSendMessage: (message: string) => void;
  messages: ChatMessage[];
  isProcessingAI?: boolean;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ 
  isConnected, 
  onSendMessage, 
  messages,
  isProcessingAI = false
}) => {
  const [inputMessage, setInputMessage] = useState('')
  const [isMinimized, setIsMinimized] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when chat is opened
  useEffect(() => {
    if (!isMinimized && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isMinimized])

  const handleSendMessage = async () => {
    if (inputMessage.trim() && isConnected && !isProcessingAI) {
      await onSendMessage(inputMessage.trim())
      setInputMessage('')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  const getMessageAvatar = (sender: string) => {
    switch (sender) {
      case 'user':
        return '👤'
      case 'ai':
        return '🤖'
      case 'system':
        return '⚙️'
      default:
        return '💬'
    }
  }

  const getMessageClass = (sender: string) => {
    switch (sender) {
      case 'user':
        return 'chat-message-user'
      case 'ai':
        return 'chat-message-ai'
      case 'system':
        return 'chat-message-system'
      default:
        return 'chat-message-default'
    }
  }

  return (
    <div className={`chat-interface ${isMinimized ? 'minimized' : ''}`}>
      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-header-content">
          <div className="chat-title">
            <span className="chat-emoji">💬</span>
            <h3>Board Chat</h3>
          </div>
          <div className="chat-status">
            <div className={`status-dot ${isConnected ? 'status-connected' : 'status-disconnected'}`}></div>
            <span className="status-text">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        <button 
          className="chat-toggle-btn"
          onClick={() => setIsMinimized(!isMinimized)}
          title={isMinimized ? 'Expand chat' : 'Minimize chat'}
        >
          {isMinimized ? '📈' : '📉'}
        </button>
      </div>

      {/* Chat Content */}
      {!isMinimized && (
        <>
          {/* Messages Area */}
          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="chat-empty-state">
                <div className="chat-empty-emoji">🎨</div>
                <p>Welcome to Board Chat!</p>
                <p className="chat-empty-subtitle">
                  Chat with others while collaborating on the canvas
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className={`chat-message ${getMessageClass(message.sender)}`}>
                  <div className="chat-message-avatar">
                    {getMessageAvatar(message.sender)}
                  </div>
                  <div className="chat-message-content">
                    <div className="chat-message-header">
                      <span className="chat-message-sender">
                        {message.sender === 'user' ? 'You' : 
                         message.sender === 'ai' ? 'AI Assistant' : 
                         message.sender === 'system' ? 'System' : 'Unknown'}
                      </span>
                      <span className="chat-message-time">
                        {formatTime(message.timestamp)}
                      </span>
                    </div>
                    <div className="chat-message-text">
                      {message.text}
                    </div>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="chat-input-area">
            <div className="chat-input-container">
              <input
                ref={inputRef}
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={isConnected ? "Type a message..." : "Connecting..."}
                disabled={!isConnected}
                className="chat-input"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || !isConnected}
                className="chat-send-btn"
                title="Send message"
              >
                🚀
              </button>
            </div>
            <div className="chat-input-hint">
              Press Enter to send • Shift+Enter for new line
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default ChatInterface

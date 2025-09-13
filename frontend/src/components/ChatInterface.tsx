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
  onAddMessage?: (message: ChatMessage) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ 
  isConnected, 
  onSendMessage, 
  messages,
  isProcessingAI = false,
  onAddMessage
}) => {
  const [inputMessage, setInputMessage] = useState('')
  const [isMinimized, setIsMinimized] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [isProcessingAudio, setIsProcessingAudio] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null)

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

  // Cleanup recording on unmount
  useEffect(() => {
    return () => {
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current)
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
    }
  }, [])

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

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder

      const audioChunks: Blob[] = []
      
      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data)
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' })
        
        // Set processing state
        setIsProcessingAudio(true)
        
        try {
          // Send audio to Flask API (same way as recording_test.py)
          const formData = new FormData()
          formData.append('audio', audioBlob, 'recording.wav')
          
          console.log('📤 Sending audio to Flask API...')
          
          const response = await fetch('http://localhost:5000/process-audio-upload', {
            method: 'POST',
            body: formData,
            // Don't set Content-Type header, let browser set it with boundary
          })
          
          console.log(`📡 API Response Status: ${response.status}`)
          
          if (response.ok) {
            const result = await response.json()
            if (result.success) {
              console.log('✅ Audio processed successfully!')
              console.log(`🤖 Response: ${result.response}`)
              
              // Add the AI response as an AI message
              addAIMessage(result.response)
            } else {
              console.error(`❌ Processing failed: ${result.error}`)
              addAIMessage(`❌ Audio processing failed: ${result.error}`)
            }
          } else {
            const errorText = await response.text()
            console.error(`❌ API request failed with status: ${response.status}`)
            console.error(`Response: ${errorText}`)
            addAIMessage(`❌ Audio processing failed (HTTP ${response.status})`)
          }
        } catch (error) {
          console.error('❌ Error sending audio to API:', error)
          if (error.name === 'TypeError' && error.message.includes('fetch')) {
            addAIMessage('❌ Could not connect to audio processing server. Make sure Flask API is running on http://localhost:5000')
          } else {
            addAIMessage(`❌ Error processing audio: ${error.message}`)
          }
        } finally {
          // Clear processing state
          setIsProcessingAudio(false)
        }
        
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)

      // Start timer
      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)

    } catch (error) {
      console.error('Error starting recording:', error)
      alert('Could not access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    
    if (recordingIntervalRef.current) {
      clearInterval(recordingIntervalRef.current)
      recordingIntervalRef.current = null
    }
    
    setIsRecording(false)
    setRecordingTime(0)
  }

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const formatRecordingTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const generateChatId = (): string => {
    return Date.now().toString(36) + Math.random().toString(36).substring(2)
  }

  const addAIMessage = (text: string) => {
    if (onAddMessage) {
      const aiMessage: ChatMessage = {
        id: generateChatId(),
        text,
        timestamp: new Date().toISOString(),
        sender: 'ai'
      }
      onAddMessage(aiMessage)
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
              <button
                onClick={toggleRecording}
                disabled={!isConnected || isProcessingAI || isProcessingAudio}
                className={`chat-record-btn ${isRecording ? 'recording' : ''} ${isProcessingAudio ? 'processing' : ''}`}
                title={
                  isProcessingAudio ? 'Processing audio...' :
                  isRecording ? 'Stop recording' : 'Start recording'
                }
              >
                {isProcessingAudio ? (
                  <div className="processing-spinner"></div>
                ) : isRecording ? (
                  <div className="recording-icon">
                    <div className="recording-dot"></div>
                  </div>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 1C10.34 1 9 2.34 9 4V12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12V4C15 2.34 13.66 1 12 1Z" fill="currentColor"/>
                    <path d="M19 10V12C19 15.87 15.87 19 12 19C8.13 19 5 15.87 5 12V10H7V12C7 14.76 9.24 17 12 17C14.76 17 17 14.76 17 12V10H19Z" fill="currentColor"/>
                    <path d="M11 22H13V24H11V22Z" fill="currentColor"/>
                  </svg>
                )}
              </button>
              <input
                ref={inputRef}
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  isProcessingAudio ? "Processing audio..." :
                  isRecording ? "Recording..." :
                  isConnected ? "Type a message..." : "Connecting..."
                }
                disabled={!isConnected || isRecording || isProcessingAudio}
                className="chat-input"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || !isConnected || isRecording || isProcessingAudio}
                className="chat-send-btn"
                title="Send message"
              >
                🚀
              </button>
            </div>
            <div className="chat-input-hint">
              {isProcessingAudio ? (
                <span className="processing-timer">
                  ⏳ Processing audio...
                </span>
              ) : isRecording ? (
                <span className="recording-timer">
                  🔴 Recording: {formatRecordingTime(recordingTime)}
                </span>
              ) : (
                <>
                  Press Enter to send • Shift+Enter for new line • Click mic to record
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default ChatInterface

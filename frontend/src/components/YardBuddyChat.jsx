import React, { useState, useRef, useEffect } from 'react';
import './YardBuddyChat.css';

const YardBuddyChat = ({ userRole = 'yard-supervisor', yardContext = {}, currentPage = 'dashboard' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hey! I'm YardBuddy 🚛\nAsk me anything about the yard — trailer locations, pending moves, dock status, SLA rules, or how to use any feature in this app.",
      timestamp: new Date().toISOString()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('default');
  const messagesEndRef = useRef(null);

  // Context-aware quick actions based on current page
  const getQuickActions = () => {
    const actionsByPage = {
      gate: [
        "How to check in a trailer?",
        "Pending approvals",
        "Gate schedule today"
      ],
      trailers: [
        "Find trailer TRL-2087",
        "Trailers exceeding dwell time",
        "Zone capacity status"
      ],
      moves: [
        "Show pending moves",
        "Optimize move queue",
        "Jockey assignments"
      ],
      exceptions: [
        "Any SLA breaches?",
        "Critical exceptions",
        "Resolution workflows"
      ],
      dashboard: [
        "What's the current yard status?",
        "Show pending moves",
        "Any SLA breaches?",
        "Dock schedule now"
      ]
    };
    return actionsByPage[currentPage] || actionsByPage.dashboard;
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (messageText) => {
    if (!messageText.trim()) return;

    const userMsg = {
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: messageText,
          user_role: userRole,
          session_id: sessionId,
          yard_context: yardContext
        }),
      });

      const data = await response.json();
      
      // Debug log to see what backend returns
      console.log('API Response:', data);

      // Validate response has required fields
      if (!data || typeof data.response !== 'string') {
        console.error('Invalid API response structure:', data);
        throw new Error('Invalid response format from server');
      }

      const assistantMsg = {
        role: 'assistant',
        content: data.response,
        intent: data.intent,
        confidence: data.confidence,
        timestamp: data.timestamp || new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(inputMessage);
  };

  const clearChat = async () => {
    try {
      await fetch(`http://localhost:8000/api/ai/history/${sessionId}`, {
        method: 'DELETE',
      });
      setMessages([{
        role: 'assistant',
        content: "Hey! I'm YardBuddy 🚛\nAsk me anything about the yard — trailer locations, pending moves, dock status, SLA rules, or how to use any feature in this app.",
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      console.error('Error clearing chat:', error);
    }
  };

  const formatMessage = (content) => {
    // Guard against undefined, null, or non-string content
    if (content === undefined || content === null) {
      console.error('formatMessage received null/undefined:', content);
      return 'Sorry, I received an empty response.';
    }
    
    if (typeof content !== 'string') {
      console.error('formatMessage received non-string:', typeof content, content);
      return String(content);
    }
    
    if (content.trim() === '') {
      return 'Sorry, I received an empty response.';
    }
    
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="chat-link">$1 ↗</a>')
      .replace(/\n/g, '<br />');
  };

  const quickActions = getQuickActions();

  return (
    <div className="yardbuddy-container">
      {!isOpen && (
        <button 
          className="yardbuddy-fab"
          onClick={() => setIsOpen(true)}
          aria-label="Open YardBuddy"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>
      )}

      {isOpen && (
        <div className="yardbuddy-chat">
          <div className="yardbuddy-header">
            <div className="yardbuddy-header-info">
              <div className="yardbuddy-avatar">
                <span>🚛</span>
              </div>
              <div className="yardbuddy-title">
                <h3>YardBuddy</h3>
                <span className="yardbuddy-subtitle">AI Assistant · {userRole}</span>
              </div>
            </div>
            <div className="yardbuddy-header-actions">
              <button 
                className="yardbuddy-clear-btn"
                onClick={clearChat}
                title="Clear chat"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="23 4 23 10 17 10"></polyline>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
              </button>
              <button 
                className="yardbuddy-close-btn"
                onClick={() => setIsOpen(false)}
                aria-label="Close"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          </div>

          <div className="yardbuddy-messages">
            {messages.map((msg, index) => (
              <div 
                key={index} 
                className={`yardbuddy-message ${msg.role === 'user' ? 'user' : 'assistant'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="yardbuddy-message-avatar">
                    <span>🚛</span>
                  </div>
                )}
                <div className="yardbuddy-message-content">
                  <div 
                    className="yardbuddy-message-text"
                    dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }}
                  />
                  {msg.intent && (
                    <span className="yardbuddy-message-meta">
                      Intent: {msg.intent} ({(msg.confidence * 100).toFixed(0)}%)
                    </span>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="yardbuddy-message assistant">
                <div className="yardbuddy-message-avatar">
                  <span>🚛</span>
                </div>
                <div className="yardbuddy-message-content">
                  <div className="yardbuddy-typing">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {messages.length <= 2 && (
            <div className="yardbuddy-quick-actions">
              {quickActions.map((action, index) => (
                <button
                  key={index}
                  className="yardbuddy-quick-btn"
                  onClick={() => sendMessage(action)}
                >
                  {action}
                </button>
              ))}
            </div>
          )}

          <form className="yardbuddy-input-container" onSubmit={handleSubmit}>
            <input
              type="text"
              className="yardbuddy-input"
              placeholder="Ask anything about the yard..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={isLoading}
            />
            <button 
              type="submit" 
              className="yardbuddy-send-btn"
              disabled={!inputMessage.trim() || isLoading}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default YardBuddyChat;
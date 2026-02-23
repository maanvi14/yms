import React, { useState, useRef, useEffect } from 'react';
import './YardBuddyChat.css';

const YardBuddyChat = ({ userRole = 'yard-supervisor', yardContext = {}, currentPage = 'dashboard' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hey! I'm YardBuddy 🚛\nAsk me anything about the yard — trailer locations, pending moves, dock status, SLA rules, or how to use any feature in this app.",
      timestamp: new Date().toISOString(),
      toolContext: null
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
        "Which zone has highest risk?"
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

  // ✅ FIXED: Properly render all zones from tool_context
  const renderZoneStatus = (toolContext) => {
    if (!toolContext) {
      return null;
    }

    console.log('🔍 renderZoneStatus called with:', toolContext);

    // Navigate the nested structure: tool_context.predictions.congestion.predictions
    const predictions = toolContext.predictions || {};
    const congestion = predictions.congestion || {};
    const zonePredictions = congestion.predictions || {};
    
    const yardState = toolContext.yard_state || {};
    const zones = yardState.zones || {};

    console.log('📊 Zones from yard_state:', zones);
    console.log('🔮 Zone Predictions from congestion.predictions:', zonePredictions);

    // Use zonePredictions keys if zones is empty, or merge both
    const allZoneIds = new Set([
      ...Object.keys(zones),
      ...Object.keys(zonePredictions)
    ]);

    if (allZoneIds.size === 0) {
      console.log('❌ No zones found');
      return null;
    }

    // Calculate metrics
    const trailerCount = yardState.trailer_count || 0;
    const dockOccupancy = yardState.dock_occupancy || 0;
    const activeMoves = yardState.active_moves || 0;

    // Convert to array and sort
    const zoneEntries = Array.from(allZoneIds).sort();

    return (
      <div className="yardbuddy-zone-card">
        <div className="yard-metrics">
          <div className="metric">
            <span className="metric-label">Trailers</span>
            <span className="metric-value">{trailerCount}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Docks</span>
            <span className="metric-value">{dockOccupancy}/12</span>
          </div>
          <div className="metric">
            <span className="metric-label">Moves</span>
            <span className="metric-value">{activeMoves}</span>
          </div>
        </div>

        <h4>📊 Zone Status ({zoneEntries.length} zones)</h4>
        <div className="zone-grid">
          {zoneEntries.map((zone) => {
            // Get data from both sources
            const capacity = zones[zone] || 0;
            const pred = zonePredictions[zone] || {};
            
            const riskLevel = pred.risk_level || 'unknown';
            const isHighRisk = riskLevel === 'HIGH';
            const isCritical = riskLevel === 'CRITICAL';
            const isMedium = riskLevel === 'MEDIUM';
            
            console.log(`  ${zone}: ${capacity}% - ${riskLevel}`);
            
            return (
              <div 
                key={zone} 
                className={`zone-item ${isCritical ? 'critical-risk' : ''} ${isHighRisk ? 'high-risk' : ''} ${isMedium ? 'medium-risk' : ''}`}
              >
                <span className="zone-name">{zone}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="zone-capacity">{capacity}%</span>
                  {isCritical && <span className="zone-alert">🚨</span>}
                  {isHighRisk && <span className="zone-alert">⚠️</span>}
                  {riskLevel !== 'unknown' && (
                    <span className={`zone-risk ${riskLevel.toLowerCase()}`}>
                      {riskLevel}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {congestion.highest_risk_zone && (
          <div className="highest-risk">
            ⚠️ Highest Risk: <strong>{congestion.highest_risk_zone}</strong> ({congestion.highest_risk_level})
          </div>
        )}
      </div>
    );
  };

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
        // ✅ FIXED: Removed yard_context so backend fetches full yard state with all zones
        body: JSON.stringify({
          message: messageText,
          user_role: userRole,
          session_id: sessionId
        }),
      });

      const data = await response.json();
      
      console.log('✅ Full API Response:', JSON.stringify(data, null, 2));
      console.log('✅ Tool Context:', data.tool_context);

      if (!data || typeof data.response !== 'string') {
        console.error('❌ Invalid API response structure:', data);
        throw new Error('Invalid response format from server');
      }

      const assistantMsg = {
        role: 'assistant',
        content: data.response,
        intent: data.intent,
        confidence: data.confidence,
        toolContext: data.tool_context || null,
        timestamp: data.timestamp || new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      console.error('❌ Error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        toolContext: null
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
        timestamp: new Date().toISOString(),
        toolContext: null
      }]);
    } catch (error) {
      console.error('Error clearing chat:', error);
    }
  };

  const formatMessage = (content) => {
    if (content === undefined || content === null) {
      return 'Sorry, I received an empty response.';
    }
    
    if (typeof content !== 'string') {
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
                  {msg.role === 'assistant' && msg.toolContext && renderZoneStatus(msg.toolContext)}
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

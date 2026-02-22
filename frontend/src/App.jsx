import React, { useState } from 'react';
import YardBuddyChat from './components/YardBuddyChat';

// Mock YMS Dashboard Layout
function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');

  // Mock yard data - in real app, this comes from your API
  const yardContext = {
    trailer_count: 8,
    dock_occupancy: 7,
    active_moves: 4,
    sla_breaches: [
      { trailer_id: "TRL-2087", carrier: "Schneider", reason: "exceeding 12-hour dwell" }
    ],
    zones: { "Zone C": 87 }
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">KSAP OTMNow</div>
        <nav>
          <button className={currentPage === 'dashboard' ? 'active' : ''} onClick={() => setCurrentPage('dashboard')}>Dashboard</button>
          <button className={currentPage === 'gate' ? 'active' : ''} onClick={() => setCurrentPage('gate')}>Gate</button>
          <button className={currentPage === 'trailers' ? 'active' : ''} onClick={() => setCurrentPage('trailers')}>Trailers</button>
          <button className={currentPage === 'moves' ? 'active' : ''} onClick={() => setCurrentPage('moves')}>Moves</button>
          <button className={currentPage === 'exceptions' ? 'active' : ''} onClick={() => setCurrentPage('exceptions')}>Exceptions</button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="top-bar">
          <h1>{currentPage.charAt(0).toUpperCase() + currentPage.slice(1)}</h1>
          <div className="user-info">Yard Supervisor</div>
        </header>

        <div className="content-area">
          {/* Mock content based on page */}
          {currentPage === 'gate' && (
            <div className="gate-form">
              <h2>Vehicle Check-In</h2>
              <div className="form-group">
                <label>Tractor Number Plate</label>
                <input type="text" placeholder="e.g. TX-4829" />
              </div>
              <div className="form-group">
                <label>Trailer Number Plate</label>
                <input type="text" placeholder="e.g. TRL-1001" />
              </div>
              <button className="checkin-btn">Check In Vehicle</button>
            </div>
          )}

          {currentPage === 'dashboard' && (
            <div className="dashboard-stats">
              <div className="stat-card">
                <h3>Trailers On-Site</h3>
                <p className="stat-value">{yardContext.trailer_count}</p>
              </div>
              <div className="stat-card">
                <h3>Docks Occupied</h3>
                <p className="stat-value">{yardContext.dock_occupancy}/12</p>
              </div>
              <div className="stat-card alert">
                <h3>SLA Breaches</h3>
                <p className="stat-value">{yardContext.sla_breaches.length}</p>
              </div>
            </div>
          )}

          {currentPage !== 'gate' && currentPage !== 'dashboard' && (
            <div className="placeholder">
              <p>{currentPage} page content would go here...</p>
            </div>
          )}
        </div>
      </main>

      {/* YardBuddy Chat Widget */}
      <YardBuddyChat 
        userRole="yard-supervisor"
        yardContext={yardContext}
        currentPage={currentPage}
      />
    </div>
  );
}

export default App;
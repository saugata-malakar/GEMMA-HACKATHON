/**
 * RAKSHA AI — Core JavaScript
 * Handles offline detection, UI state, WebSocket, and API integration.
 */

const API_BASE = '/api/v1';
let ws = null;
let incidentMap = null;
let mapMarkers = {};
let currentChatSessionId = null;

// ── App Initialization ──
document.addEventListener('DOMContentLoaded', async () => {
  initServiceWorker();
  initUI();
  
  // Show splash screen for at least 1s
  const splashPromise = new Promise(resolve => setTimeout(resolve, 1000));
  
  try {
    await fetchInitialData();
    initWebSocket();
  } catch (error) {
    console.error('Startup error:', error);
    showToast('Starting in offline mode', 'warning');
  }

  await splashPromise;
  document.getElementById('splash').style.opacity = '0';
  setTimeout(() => {
    document.getElementById('splash').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    initMap(); // Leaflet map needs to be initialized after container is visible
  }, 500);
});

// ── Service Worker & Offline Support ──
function initServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then(() => console.log('Service Worker registered'))
      .catch(err => console.error('SW registration failed:', err));
  }

  window.addEventListener('online', () => {
    updateOnlineStatus(true);
    showToast('Connection restored. Syncing...', 'success');
    initWebSocket();
  });
  
  window.addEventListener('offline', () => {
    updateOnlineStatus(false);
    showToast('Offline mode active. Using local Gemma 4 model.', 'warning');
    if (ws) ws.close();
  });

  updateOnlineStatus(navigator.onLine);
}

function updateOnlineStatus(isOnline) {
  const dot = document.getElementById('statusDot');
  const label = document.getElementById('statusLabel');
  
  if (isOnline) {
    dot.className = 'status-dot online';
    label.textContent = 'Gemma 4 (Cloud 27B)';
  } else {
    dot.className = 'status-dot offline';
    label.textContent = 'Gemma 4 (Local 4B)';
  }
}

// ── UI Navigation & Modals ──
function initUI() {
  // Navigation
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
      
      const target = e.currentTarget;
      target.classList.add('active');
      const viewId = target.getAttribute('data-view');
      if (viewId) {
        const viewEl = document.getElementById(`view-${viewId}`);
        if (viewEl) viewEl.classList.add('active');
      }

      if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
      }

      if (viewId === 'dashboard' && incidentMap) {
        setTimeout(() => incidentMap.invalidateSize(), 100);
      }
    });
  });

  // Sidebar toggle
  const sidebar = document.getElementById('sidebar');
  document.getElementById('sidebarToggle')?.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  // Modals
  document.querySelectorAll('[data-modal]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const modalId = btn.getAttribute('data-modal');
      const modal = document.getElementById(modalId);
      if (modal.classList.contains('hidden')) {
        modal.classList.remove('hidden');
      } else {
        modal.classList.add('hidden');
      }
    });
  });

  // Time update
  setInterval(() => {
    document.getElementById('dashTimestamp').textContent = new Date().toLocaleString();
  }, 1000);
  document.getElementById('dashTimestamp').textContent = new Date().toLocaleString();

  // Form Submissions
  document.getElementById('incidentForm').addEventListener('submit', handleIncidentSubmit);
  document.getElementById('alertForm').addEventListener('submit', handleAlertSubmit);
  document.getElementById('responderForm')?.addEventListener('submit', handleResponderSubmit);
  
  // Chat setup
  setupChat();
  
  // Assess setup
  setupAssess();
  
  // Triage setup
  setupTriage();
}

// ── Map Initialization ──
function initMap() {
  if (incidentMap) return;
  
  // Default to central India if location unavailable
  incidentMap = L.map('incidentMap').setView([20.5937, 78.9629], 5);
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(incidentMap);

  // Try to get user location
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => {
        incidentMap.setView([pos.coords.latitude, pos.coords.longitude], 12);
        document.getElementById('incLat').value = pos.coords.latitude.toFixed(6);
        document.getElementById('incLng').value = pos.coords.longitude.toFixed(6);
      },
      () => console.log('Location access denied')
    );
  }
}

function updateMapMarkers(incidents) {
  if (!incidentMap) return;
  
  // Clear existing
  Object.values(mapMarkers).forEach(m => incidentMap.removeLayer(m));
  mapMarkers = {};
  
  incidents.forEach(inc => {
    if (!inc.coordinates) return;
    
    let color = '#00B0FF';
    if (inc.severity >= 8) color = '#FF1744';
    else if (inc.severity >= 5) color = '#FF6D00';
    
    const circle = L.circleMarker([inc.coordinates.lat, inc.coordinates.lng], {
      radius: 8,
      fillColor: color,
      color: '#fff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.8
    }).addTo(incidentMap);
    
    circle.bindPopup(`
      <b>${inc.type.toUpperCase()}</b><br>
      Severity: ${inc.severity}/10<br>
      Status: ${inc.status}
    `);
    
    mapMarkers[inc.id] = circle;
  });
}

// ── WebSocket ──
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  
  ws = new WebSocket(`${protocol}//${host}/ws/dashboard`);
  
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    switch (msg.type) {
      case 'initial_state':
        renderDashboard(msg.data);
        break;
      case 'incident_created':
        showToast('New incident reported', 'warning');
        fetchInitialData(); // Lazy refresh
        break;
      case 'new_alert':
        showToast(`ALERT: ${msg.data.title}`, 'error');
        fetchInitialData();
        break;
      case 'responder_dispatched':
        showToast(`${msg.data.responder.name} dispatched`, 'success');
        break;
      case 'triage_entry':
        updateTriageLog(msg.data);
        break;
      case 'resource_requested':
        showToast(`Requested resources: ${(msg.data.resources || []).join(', ')}`, 'info');
        break;
      case 'overwatch_action':
        showToast(`🤖 AI OVERWATCH: ${msg.data.action}`, 'warning');
        break;
      case 'mesh_sync':
        showToast(`📶 Mesh Sync: ${msg.data.merged_records} records merged from peer ${msg.data.peer.substring(0,6)}`, 'info');
        break;
    }
  };

  ws.onclose = () => {
    if (navigator.onLine) {
      setTimeout(initWebSocket, 5000); // Reconnect
    }
  };
}

// ── API & Data Fetching ──
async function fetchInitialData() {
  try {
    const [statusRes, incRes, respRes, alertRes] = await Promise.all([
      fetch(`${API_BASE}/status`),
      fetch(`${API_BASE}/incidents`),
      fetch(`${API_BASE}/responders`),
      fetch(`${API_BASE}/alerts`)
    ]);

    const status = await statusRes.json();
    const incidents = await incRes.json();
    const responders = await respRes.json();
    const alerts = await alertRes.json();

    renderDashboard({
      incidents: incidents.incidents,
      responders: responders.responders,
      alerts: alerts.alerts
    });
    
    // Update status bar
    updateOnlineStatus(status.online);

  } catch (err) {
    console.warn('API fetch failed, reading from cache if available');
  }
}

function renderDashboard(data) {
  const { incidents = [], responders = [], alerts = [] } = data;
  
  // Update badges & stats
  const activeIncidents = incidents.filter(i => i.status === 'active' || i.status === 'reported');
  document.getElementById('statActiveIncidents').textContent = activeIncidents.length;
  document.getElementById('incidentBadge').textContent = activeIncidents.length;
  
  const availableResponders = responders.filter(r => r.status === 'available');
  document.getElementById('statAvailableResponders').textContent = availableResponders.length;
  
  document.getElementById('statAlertCount').textContent = alerts.length;
  
  // Update Map
  updateMapMarkers(activeIncidents);
  
  // Update Recent Incidents List
  const recentList = document.getElementById('recentIncidents');
  if (incidents.length === 0) {
    recentList.innerHTML = '<div class="empty-state">No incidents reported</div>';
  } else {
    recentList.innerHTML = incidents.slice(0, 5).map(inc => `
      <div class="incident-card" onclick="document.getElementById('nav-incidents').click()">
        <div class="ic-header">
          <span class="ic-type">${getIncidentIcon(inc.type)} ${inc.type.replace('_', ' ').toUpperCase()}</span>
          <span class="ic-status status-${inc.status}">${inc.status}</span>
        </div>
        <p class="ic-desc">${inc.description}</p>
        <div class="ic-meta">
          <span>Sev: ${inc.severity}/10</span>
          <span>${new Date(inc.timestamp).toLocaleTimeString()}</span>
        </div>
      </div>
    `).join('');
  }

  // Update Dash Alerts List
  const dashAlerts = document.getElementById('dashAlerts');
  if (alerts.length === 0) {
    dashAlerts.innerHTML = '<div class="empty-state">All clear</div>';
  } else {
    dashAlerts.innerHTML = alerts.slice(0, 3).map(alt => `
      <div class="alert-card ${alt.severity}">
        <div class="alert-title">⚠️ ${alt.title}</div>
        <div class="alert-time">${new Date(alt.timestamp).toLocaleTimeString()}</div>
      </div>
    `).join('');
  }
  
  // Full incidents view
  renderFullIncidents(incidents);
  // Full responders view
  renderFullResponders(responders);
  // Full alerts view
  renderFullAlerts(alerts);
}

function getIncidentIcon(type) {
  const icons = {
    earthquake: '🌋', flood: '🌊', cyclone: '🌀', fire: '🔥',
    landslide: '⛰️', building_collapse: '🏚️', chemical: '☣️', tsunami: '🌊'
  };
  return icons[type] || '🚨';
}

function renderFullIncidents(incidents) {
  const grid = document.getElementById('incidentsGrid');
  if (incidents.length === 0) {
    grid.innerHTML = '<div class="empty-state">No incidents found in database.</div>';
    return;
  }
  
  grid.innerHTML = incidents.map(inc => `
    <div class="stat-card incident-card" style="padding: 1.5rem; display: flex; flex-direction: column;">
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-glass); padding-bottom: 1rem; margin-bottom: 1rem;">
        <span style="font-weight: 700; letter-spacing: 1px; color: var(--text-main); font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;">
          <span style="font-size: 1.25rem;">${getIncidentIcon(inc.type)}</span> 
          ${inc.type.replace('_', ' ').toUpperCase()}
        </span>
        <span style="background: rgba(99, 102, 241, 0.2); color: #818cf8; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; border: 1px solid rgba(99, 102, 241, 0.3);">
          ${inc.status}
        </span>
      </div>
      
      <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.5; margin-bottom: 1rem; flex-grow: 1;">
        ${!inc.description || inc.description.toLowerCase() === 'none' ? '<i style="opacity: 0.5;">No additional details provided.</i>' : inc.description}
      </p>
      
      ${inc.ai_assessment ? `
      <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.2); padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem; font-size: 0.85rem; color: #cbd5e1;">
        <strong style="color: #818cf8;">🤖 AI Assessment:</strong> Severity ${inc.ai_assessment.damage_severity}/10. 
        ${inc.ai_assessment.structural_integrity !== 'unknown' ? `Structure: ${inc.ai_assessment.structural_integrity}.` : ''}
      </div>
      ` : ''}
      
      <div style="display: flex; justify-content: space-between; color: rgba(255,255,255,0.4); font-size: 0.85rem; margin-bottom: 1.5rem; font-family: 'JetBrains Mono', monospace;">
        <span>📍 ${inc.coordinates ? `${inc.coordinates.lat.toFixed(4)}, ${inc.coordinates.lng.toFixed(4)}` : 'No location'}</span>
        <span>${new Date(inc.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
      </div>
      
      <div style="display:flex; gap:0.75rem; margin-top: auto;">
        <button class="btn btn-primary" style="flex:1; padding: 0.75rem; font-size: 0.85rem; text-align: center;" onclick="dispatchToIncident('${inc.id}')">DISPATCH TEAM</button>
        <button class="btn" style="flex:1; padding: 0.75rem; font-size: 0.85rem; text-align: center; background: rgba(255,255,255,0.05); color: white; border: 1px solid var(--border-glass);" onclick="viewDetails('${inc.id}')">VIEW DETAILS</button>
      </div>
    </div>
  `).join('');
}

function renderFullResponders(responders) {
  const grid = document.getElementById('respondersGrid');
  
  // Update top stats
  document.getElementById('rAvailable').textContent = responders.filter(r => r.status === 'available').length;
  document.getElementById('rDispatched').textContent = responders.filter(r => r.status === 'dispatched').length;
  document.getElementById('rOnScene').textContent = responders.filter(r => r.status === 'on_scene').length;
  
  if (responders.length === 0) {
    grid.innerHTML = '<div class="empty-state">No responders registered.</div>';
    return;
  }
  
  const getRoleIcon = (role) => {
    const roles = {
        'medic': '⚕️', 'search_rescue': '🦺', 'firefighter': '🚒', 
        'police': '🚓', 'engineer': '🏗️', 'commander': '⭐', 'drone_op': '🚁'
    };
    return roles[(role || '').toLowerCase()] || '👤';
  };
  
  grid.innerHTML = responders.map(r => `
    <div class="stat-card" style="padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem;">
      <div style="display: flex; align-items: center; gap: 1rem;">
        <div style="font-size: 2.2rem; background: rgba(255,255,255,0.05); width: 3.5rem; height: 3.5rem; display: flex; align-items: center; justify-content: center; border-radius: 12px; border: 1px solid var(--border-glass);">
          ${getRoleIcon(r.role)}
        </div>
        <div style="flex-grow: 1;">
          <h3 style="font-size: 1.15rem; font-weight: 700; margin: 0; color: var(--text-main);">${r.name}</h3>
          <p style="color: var(--primary); font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin: 0;">${r.team} • ${r.role}</p>
        </div>
        <span style="background: ${r.status === 'available' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)'}; color: ${r.status === 'available' ? '#34d399' : '#fbbf24'}; padding: 0.35rem 0.75rem; border-radius: 999px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; border: 1px solid ${r.status === 'available' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}; box-shadow: 0 0 10px ${r.status === 'available' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)'};">
          ${r.status}
        </span>
      </div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
        <div>
          <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.2rem;">Equipment</div>
          <div style="font-size: 0.85rem; color: #e2e8f0;">${r.equipment && r.equipment.length > 0 ? r.equipment.join(', ') : 'Standard Kit'}</div>
        </div>
        <div>
          <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.2rem;">Last Known Location</div>
          <div style="font-size: 0.85rem; color: #e2e8f0; font-family: 'JetBrains Mono', monospace;">${r.location ? `${r.location.lat.toFixed(4)}, ${r.location.lng.toFixed(4)}` : 'GPS Offline'}</div>
        </div>
      </div>
    
      <div>
        <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.5rem; letter-spacing: 0.5px;">Specializations</div>
        <div style="display: flex; flex-wrap: wrap; gap: 0.35rem;">
          ${(r.skills || ['General Response']).map(s => `<span style="background: rgba(99, 102, 241, 0.15); color: #818cf8; padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.75rem; border: 1px solid rgba(99, 102, 241, 0.3);">${s.replace('_', ' ')}</span>`).join('')}
        </div>
      </div>
    
      <button class="btn" style="width: 100%; margin-top: auto; padding: 0.75rem; background: rgba(255,255,255,0.05); color: white; border: 1px solid var(--border-glass); transition: all 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'">
        📞 SECURE CONTACT: ${r.phone || 'UNIT RADIO'}
      </button>
    </div>
  `).join('');
}

function renderFullAlerts(alerts) {
  const container = document.getElementById('alertsContainer');
  if (!container) return;
  
  if (!alerts || alerts.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="padding: 4rem 2rem; border-radius: 16px; border: 1px dashed var(--border-glass); text-align: center;">
        <div style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;">✅</div>
        <h3 style="margin-bottom: 0.5rem;">All Clear</h3>
        <p style="color: var(--text-muted);">No active emergency broadcasts at this time.</p>
      </div>`;
    return;
  }
  
  container.innerHTML = alerts.map(alt => {
    let icon = '📢';
    let color = 'var(--primary)';
    let bg = 'rgba(99, 102, 241, 0.1)';
    let border = 'rgba(99, 102, 241, 0.3)';
    
    if (alt.severity === 'critical') {
      icon = '🚨';
      color = '#ef4444';
      bg = 'rgba(239, 68, 68, 0.1)';
      border = 'rgba(239, 68, 68, 0.3)';
    } else if (alt.severity === 'high') {
      icon = '⚠️';
      color = '#f59e0b';
      bg = 'rgba(245, 158, 11, 0.1)';
      border = 'rgba(245, 158, 11, 0.3)';
    }
    
    return `
      <div class="stat-card" style="margin-bottom: 1rem; border-left: 4px solid ${color}; padding: 1.5rem;">
        <div style="display: flex; gap: 1.5rem; align-items: flex-start;">
          <div style="font-size: 2.5rem; background: ${bg}; border: 1px solid ${border}; width: 4rem; height: 4rem; display: flex; align-items: center; justify-content: center; border-radius: 12px; flex-shrink: 0;">
            ${icon}
          </div>
          <div style="flex-grow: 1;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
              <h3 style="font-size: 1.25rem; font-weight: 800; color: var(--text-main); margin: 0;">${alt.title}</h3>
              <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-muted); background: rgba(255,255,255,0.05); padding: 0.25rem 0.5rem; border-radius: 6px;">
                ${new Date(alt.timestamp).toLocaleString()}
              </span>
            </div>
            <p style="color: #cbd5e1; font-size: 1rem; line-height: 1.5; margin-bottom: 1rem;">
              ${alt.message}
            </p>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
              <span style="background: ${bg}; color: ${color}; border: 1px solid ${border}; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">
                ${alt.severity} SEVERITY
              </span>
              ${(alt.languages || ['en']).map(lang => `
                <span style="background: rgba(255,255,255,0.05); border: 1px solid var(--border-glass); padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;">
                  🌐 ${lang}
                </span>
              `).join('')}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ── AI Chat Support ──
let chatWs = null;

function setupChat() {
  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSend');
  const messages = document.getElementById('chatMessages');
  const imageInput = document.getElementById('chatImageInput');
  const attachPreview = document.getElementById('attachPreview');
  const attachThumb = document.getElementById('attachThumb');
  let currentImageBase64 = null;

  // Auto-resize input
  input.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
  });

  // Image attachment
  imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        currentImageBase64 = e.target.result.split(',')[1];
        attachThumb.src = e.target.result;
        attachPreview.classList.remove('hidden');
      };
      reader.readAsDataURL(file);
    }
  });

  document.getElementById('removeAttach').addEventListener('click', () => {
    currentImageBase64 = null;
    imageInput.value = '';
    attachPreview.classList.add('hidden');
  });

  // Connect Chat WebSocket
  function connectChatWs() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    chatWs = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);
    
    chatWs.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'thinking') {
        currentChatSessionId = data.session_id;
        // Remove old thinking if exists
        const oldTyping = document.getElementById('typingInd');
        if (oldTyping) oldTyping.remove();
        
        messages.insertAdjacentHTML('beforeend', `
          <div class="typing-indicator" id="typingInd">
            <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
          </div>
        `);
        messages.scrollTop = messages.scrollHeight;
      } 
      else if (data.type === 'response') {
        const typing = document.getElementById('typingInd');
        if (typing) typing.remove();
        
        let functionHTML = '';
        if (data.function_results && data.function_results.length > 0) {
          functionHTML = data.function_results.map(fr => `
            <div class="function-call">
              <div class="fc-name">⚙️ Function: ${fr.name}</div>
              <div class="fc-result">${fr.result.message || 'Executed successfully'}</div>
            </div>
          `).join('');
        }
        
        // Parse markdown lightly
        let text = data.content
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\n/g, '<br>');
        
        messages.insertAdjacentHTML('beforeend', `
          <div class="msg ai">
            <div class="msg-bubble">
              ${text}
              ${functionHTML}
            </div>
            <div class="msg-meta">${data.model_used} • ${new Date().toLocaleTimeString()}</div>
          </div>
        `);
        messages.scrollTop = messages.scrollHeight;
      }
    };
    
    chatWs.onclose = () => {
      document.getElementById('chatModelBadge').textContent = 'Offline (Reconnecting...)';
      setTimeout(connectChatWs, 3000);
    };
    
    chatWs.onopen = () => {
      document.getElementById('chatModelBadge').textContent = 'Connected (Gemma 4)';
    };
  }
  
  connectChatWs();

  // Send message
  const sendMessage = () => {
    const text = input.value.trim();
    if (!text && !currentImageBase64) return;
    
    // Hide welcome block if exists
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.style.display = 'none';
    
    const lang = document.getElementById('langSelect').value;
    
    // Add user message to UI
    let imgHTML = '';
    if (currentImageBase64) {
      imgHTML = `<img src="data:image/jpeg;base64,${currentImageBase64}" class="msg-img" />`;
    }
    
    messages.insertAdjacentHTML('beforeend', `
      <div class="msg user">
        <div class="msg-bubble">${imgHTML}${text}</div>
      </div>
    `);
    
    // Send to WS
    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
      chatWs.send(JSON.stringify({
        type: 'message',
        content: text,
        language: lang,
        image: currentImageBase64
      }));
    } else {
      // Fallback to REST API if WS fails
      fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          language: lang,
          image_base64: currentImageBase64,
          session_id: currentChatSessionId
        })
      }).then(res => res.json()).then(data => {
        // Add response UI
        // (Simplified here for fallback)
      });
    }
    
    // Cleanup input
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('removeAttach').click();
    messages.scrollTop = messages.scrollHeight;
  };

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Quick prompts
  document.querySelectorAll('.quick-prompt').forEach(btn => {
    btn.addEventListener('click', () => {
      input.value = btn.getAttribute('data-prompt');
      sendMessage();
    });
  });
}

// ── AI Image Assessment ──
function setupAssess() {
  const input = document.getElementById('imageInput');
  const uploadBtn = document.getElementById('uploadBtn');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const preview = document.getElementById('previewImage');
  const zone = document.getElementById('uploadZone');
  const resultsPanel = document.getElementById('assessResults');
  
  let currentBase64 = null;

  uploadBtn.addEventListener('click', () => input.click());
  
  input.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleImageFile(file);
  });

  // Drag & drop
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) handleImageFile(e.dataTransfer.files[0]);
  });

  function handleImageFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      preview.src = e.target.result;
      preview.classList.remove('hidden');
      zone.style.display = 'none';
      currentBase64 = e.target.result.split(',')[1];
      analyzeBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  analyzeBtn.addEventListener('click', async () => {
    if (!currentBase64) return;
    
    const originalText = analyzeBtn.innerHTML;
    analyzeBtn.innerHTML = '⚡ Scanning image...';
    analyzeBtn.disabled = true;
    
    // Add the scan animation overlay to the preview image
    const uploadPanel = document.querySelector('.assess-upload-panel');
    const scanOverlay = document.createElement('div');
    scanOverlay.className = 'ai-scan-animation';
    uploadPanel.appendChild(scanOverlay);
    
    resultsPanel.innerHTML = `
      <div class="results-placeholder">
        <div class="typing-indicator" style="align-self: center; margin-bottom: 1rem;">
          <div class="typing-dot" style="background: var(--primary);"></div>
          <div class="typing-dot" style="background: var(--primary);"></div>
          <div class="typing-dot" style="background: var(--primary);"></div>
        </div>
        <p style="color: var(--primary); font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 1px;">Processing Visual Data Pipeline...</p>
      </div>
    `;

    try {
      const res = await fetch(`${API_BASE}/assess/base64`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_base64: currentBase64,
          disaster_type: document.getElementById('disasterTypeSelect').value || null,
          building_type: document.getElementById('buildingTypeSelect').value || null,
          language: document.getElementById('langSelect').value
        })
      });
      
      const data = await res.json();
      
      let badgeStyle = 'background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.4);';
      if (data.damage_severity >= 8) badgeStyle = 'background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4);';
      else if (data.damage_severity <= 4) badgeStyle = 'background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4);';

      resultsPanel.innerHTML = `
        <div class="ai-report stat-card" style="padding: 2rem; border-radius: 16px; display: flex; flex-direction: column; gap: 1.5rem; height: 100%;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border-glass); padding-bottom: 1.5rem;">
            <div>
              <h2 style="font-size: 1.5rem; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 0.5rem;">Intelligence Report</h2>
              <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.5; font-style: italic;">"${data.summary || 'Analysis complete'}"</p>
            </div>
            <div style="text-align: center; ${badgeStyle} padding: 0.75rem 1.5rem; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
              <div style="font-size: 0.75rem; text-transform: uppercase; font-weight: 700; opacity: 0.8;">Severity</div>
              <div style="font-size: 2rem; font-weight: 900; line-height: 1;">${data.damage_severity}</div>
            </div>
          </div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 12px; border: 1px solid var(--border-glass);">
              <h3 style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 1px; margin-bottom: 0.5rem;">Structural Status</h3>
              <p style="font-size: 1.125rem; font-weight: 700; color: var(--text-main); text-transform: uppercase;">${data.structural_integrity || 'Unknown'}</p>
              ${data.estimated_trapped ? `<p style="color: #f87171; font-weight: 700; margin-top: 0.5rem; font-size: 0.9rem;">⚠️ Est. Trapped: ${data.estimated_trapped}</p>` : ''}
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 12px; border: 1px solid var(--border-glass);">
              <h3 style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 1px; margin-bottom: 0.5rem;">Required Resources</h3>
              <p style="font-size: 0.9rem; margin-bottom: 0.25rem;">Teams: <strong>${data.resource_requirements?.teams_required || 1}</strong></p>
              <p style="font-size: 0.9rem;">Medical: <strong>${data.resource_requirements?.medical_personnel || 0}</strong></p>
            </div>
          </div>
          
          <div>
            <h3 style="font-size: 0.85rem; text-transform: uppercase; color: #818cf8; letter-spacing: 1px; margin-bottom: 0.75rem;">Identified Hazards</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
              ${(data.hazards || []).map(h => `<span style="background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.3); padding: 0.35rem 0.75rem; border-radius: 6px; font-size: 0.85rem;">⚠️ ${h}</span>`).join('')}
              ${(!data.hazards || data.hazards.length === 0) ? '<span style="color:var(--text-muted)">No visible hazards identified</span>' : ''}
            </div>
          </div>
          
          <div>
            <h3 style="font-size: 0.85rem; text-transform: uppercase; color: #34d399; letter-spacing: 1px; margin-bottom: 0.75rem;">Recommended Actions</h3>
            <ul style="list-style-type: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.5rem;">
              ${(data.recommended_actions || []).map(a => `<li style="background: rgba(255,255,255,0.02); border-left: 3px solid #34d399; padding: 0.75rem 1rem; border-radius: 0 6px 6px 0; font-size: 0.9rem;">${a}</li>`).join('')}
            </ul>
          </div>
          
          <div style="margin-top: auto; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-glass); padding-top: 1rem; color: rgba(255,255,255,0.3); font-size: 0.75rem; font-family: 'JetBrains Mono', monospace;">
            <span>MODEL: ${data.model_used || 'raksha-vision-agent'}</span>
            <span>CONFIDENCE: ${data.confidence ? (data.confidence * 100).toFixed(0) : '95'}%</span>
          </div>
        </div>
      `;

      // Create an incident automatically from assessment
      showToast('Assessment complete. Saving to incident logs.', 'success');
      
    } catch (err) {
      console.error(err);
      showToast('Assessment failed.', 'error');
      resultsPanel.innerHTML = `<div class="results-placeholder"><p style="color: #f87171;">Assessment failed: ${err.message}</p></div>`;
    } finally {
      if (scanOverlay && scanOverlay.parentNode) scanOverlay.parentNode.removeChild(scanOverlay);
      analyzeBtn.innerHTML = originalText;
      analyzeBtn.disabled = false;
    }
  });
}

// ── Medical Triage ──
function setupTriage() {
  const chips = document.querySelectorAll('.chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('selected');
    });
  });

  // Auto-capture GPS location on page load for triage
  captureTriageLocation();

  document.getElementById('triageForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const btn = document.getElementById('triageSubmitBtn');
    btn.innerHTML = '⏳ Analyzing...';
    btn.disabled = true;

    // Collect symptoms
    const symptoms = Array.from(document.querySelectorAll('.chip.selected'))
      .map(c => c.getAttribute('data-symptom'));
    
    const custom = document.getElementById('customSymptom').value.trim();
    if (custom) symptoms.push(custom);
    
    if (symptoms.length === 0) {
      showToast('Please select at least one symptom', 'warning');
      btn.innerHTML = '🏥 Get AI Triage Assessment';
      btn.disabled = false;
      return;
    }

    // Get current GPS location for this patient
    const locationData = await getCurrentLocation();
    
    try {
      const res = await fetch(`${API_BASE}/triage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symptoms: symptoms,
          age_estimate: document.getElementById('triageAge').value || null,
          gender: document.getElementById('triageGender').value || null,
          location: locationData ? { lat: locationData.lat, lng: locationData.lng } : null,
          location_accuracy: locationData ? locationData.accuracy : null,
          additional_notes: document.getElementById('triageNotes')?.value || null,
          language: document.getElementById('langSelect').value
        })
      });

      const data = await res.json();
      const entry = data.entry;
      const ai = data.ai_guidance;

      // Reset form
      chips.forEach(c => c.classList.remove('selected'));
      document.getElementById('customSymptom').value = '';
      document.getElementById('triageAge').value = '';
      
      // Update result panel with enhanced display
      const resultPanel = document.getElementById('triageResult');
      
      // Color mapping for display
      const colorMap = {
        'red': { bg: '#ef4444', text: '#fff' },
        'yellow': { bg: '#f59e0b', text: '#000' },
        'green': { bg: '#10b981', text: '#fff' },
        'black': { bg: '#374151', text: '#fff' }
      };
      const colors = colorMap[ai.triage_color] || colorMap.yellow;
      
      resultPanel.innerHTML = `
        <div style="width:100%; text-align:left;">
          <h2 style="margin-bottom:1rem; border-bottom:1px solid var(--border); padding-bottom:0.5rem;">Triage Category Assigned</h2>
          <div style="display:flex; align-items:center; gap:1.5rem; margin-bottom:1.5rem;">
            <div style="width:100px; height:100px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:${colors.bg}; color:${colors.text}; font-size:2rem; font-weight:800; text-transform:uppercase;">
              ${ai.triage_color}
            </div>
            <div>
              <p style="font-family:'JetBrains Mono', monospace; color:var(--text-secondary);">ID: ${entry.patient_id}</p>
              <p style="font-weight:600; font-size:1.125rem;">${ai.triage_color === 'red' ? 'IMMEDIATE' : ai.triage_color === 'yellow' ? 'DELAYED' : ai.triage_color === 'green' ? 'MINIMAL' : 'EXPECTANT'}</p>
              ${data.location_captured ? `<p style="font-size: 0.8rem; color: var(--primary);">📍 GPS: ${data.gps_accuracy_meters?.toFixed(0) || '?'}m accuracy</p>` : ''}
            </div>
          </div>
          
          <h3 style="font-size:0.875rem; color:var(--text-muted); text-transform:uppercase;">AI Medical Reasoning</h3>
          <p style="margin-bottom:1rem;">${ai.medical_summary || entry.ai_notes}</p>
          
          ${ai.vital_status ? `
          <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <h4 style="font-size: 0.85rem; color: var(--primary); margin-bottom: 0.5rem;">Vital Assessment</h4>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; font-size: 0.85rem;">
              <div>Airway: <strong>${ai.airway_status || 'N/A'}</strong></div>
              <div>Breathing: <strong>${ai.breathing_status || 'N/A'}</strong></div>
              <div>Circulation: <strong>${ai.circulation_status || 'N/A'}</strong></div>
            </div>
          </div>
          ` : ''}
          
          <h3 style="font-size:0.875rem; color:var(--text-muted); text-transform:uppercase;">Immediate Interventions</h3>
          <ul style="padding-left:1.5rem;">
            ${(ai.immediate_remedy || []).map(i => `<li>${i}</li>`).join('')}
          </ul>
          
          ${ai.transport_priority ? `
          <div style="margin-top: 1rem; padding: 0.75rem; background: rgba(0,176,255,0.1); border-radius: 8px; border-left: 3px solid var(--primary);">
            <strong>Transport Priority:</strong> ${ai.transport_priority} | 
            <strong>Hospital:</strong> ${ai.hospital_type || 'General'} | 
            <strong>ETA:</strong> ~${ai.estimated_eta_to_hospital || '30'} min
          </div>
          ` : ''}
        </div>
      `;
      resultPanel.style.display = 'block';

      // Load into log
      fetchTriageLog();

      showToast('Triage entry saved with GPS location', 'success');

    } catch (err) {
      console.error(err);
      showToast('Failed to process triage. Use manual protocols.', 'error');
    } finally {
      btn.innerHTML = '🏥 Get AI Triage Assessment';
      btn.disabled = false;
    }
  });

  fetchTriageLog();
}

// GPS Location helper functions
let triageLocation = null;

async function captureTriageLocation() {
  const locationData = await getCurrentLocation();
  if (locationData) {
    triageLocation = locationData;
    console.log('Triage location captured:', locationData);
  }
}

async function getCurrentLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      console.warn('Geolocation not supported');
      resolve(null);
      return;
    }
    
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy
        });
      },
      (error) => {
        console.warn('Geolocation error:', error.message);
        resolve(null);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  });
}

async function fetchTriageLog() {
  try {
    const res = await fetch(`${API_BASE}/triage`);
    const data = await res.json();
    
    const log = document.getElementById('triageLog');
    if (data.entries.length === 0) {
      log.innerHTML = '<div class="empty-state">No entries yet</div>';
      return;
    }
    
    log.innerHTML = data.entries.map(e => `
      <div class="triage-card tc-${e.triage_color}">
        <div class="tc-header">
          <span class="tc-id">${e.patient_id}</span>
          <span class="tc-tag tag-${e.triage_color}">${e.triage_color}</span>
        </div>
        <div class="tc-notes">${e.symptoms.join(', ')}</div>
        <div class="tc-meta">${new Date(e.timestamp).toLocaleTimeString()} • ${e.age_estimate || 'Age unknown'}</div>
      </div>
    `).join('');
  } catch (e) {
    console.error('Failed fetching triage log', e);
  }
}

// ── Form Handlers ──
async function handleIncidentSubmit(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  const original = btn.textContent;
  btn.textContent = 'Saving...';
  btn.disabled = true;

  const data = {
    type: document.getElementById('incType').value,
    description: document.getElementById('incDesc').value,
    coordinates: {
      lat: parseFloat(document.getElementById('incLat').value) || 20.5937,
      lng: parseFloat(document.getElementById('incLng').value) || 78.9629
    },
    affected_count: parseInt(document.getElementById('incAffected').value) || null,
    reported_by: document.getElementById('incReporter').value || 'Unknown',
    language: document.getElementById('langSelect').value
  };

  try {
    await fetch(`${API_BASE}/incidents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    document.getElementById('incidentModal').classList.add('hidden');
    e.target.reset();
    showToast('Incident reported successfully', 'success');
    
  } catch (err) {
    showToast('Failed to report incident', 'error');
  } finally {
    btn.textContent = original;
    btn.disabled = false;
  }
}

async function handleResponderSubmit(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  const original = btn.textContent;
  btn.textContent = 'Saving...';
  btn.disabled = true;

  const skillsStr = document.getElementById('respSkills').value || '';
  const skills = skillsStr.split(',').map(s => s.trim().replace(' ', '_')).filter(s => s);

  const data = {
    name: document.getElementById('respName').value,
    role: document.getElementById('respRole').value,
    team: document.getElementById('respTeam').value,
    phone: document.getElementById('respPhone').value || null,
    skills: skills,
    status: 'available',
    current_location: null,
    equipment: []
  };

  try {
    const res = await fetch(`${API_BASE}/responders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    if (res.ok) {
      document.getElementById('responderModal').classList.add('hidden');
      e.target.reset();
      showToast('Responder added successfully', 'success');
      if (document.getElementById('view-responders').classList.contains('active')) {
        fetchResponders();
      }
    } else {
      throw new Error('Failed');
    }
  } catch (err) {
    showToast('Failed to add responder', 'error');
  } finally {
    btn.textContent = original;
    btn.disabled = false;
  }
}

async function handleAlertSubmit(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  const original = btn.textContent;
  btn.textContent = 'Broadcasting...';
  btn.disabled = true;

  const langs = Array.from(e.target.querySelectorAll('.lang-chips input:checked')).map(cb => cb.value);

  const data = {
    title: document.getElementById('alertTitle').value,
    message: document.getElementById('alertMessage').value,
    severity: document.getElementById('alertSeverity').value,
    languages: langs.length > 0 ? langs : ['en']
  };

  try {
    await fetch(`${API_BASE}/alerts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    document.getElementById('alertModal').classList.add('hidden');
    e.target.reset();
    
    // Toast handled via WS broadcast
  } catch (err) {
    showToast('Failed to broadcast alert', 'error');
  } finally {
    btn.textContent = original;
    btn.disabled = false;
  }
}

// ── Utilities ──
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div style="display:flex; align-items:center; gap:0.5rem; font-weight:500;">
      <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}</span>
      ${message}
    </div>
  `;
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.3s forwards';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Global dispatch helper
window.dispatchToIncident = async function(incidentId) {
  try {
    showToast('Requesting dispatch...', 'info');
    const res = await fetch(`${API_BASE}/dispatch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_id: incidentId, priority: 'high' })
    });
    const data = await res.json();
    if(data.success) {
      fetchInitialData(); // Refresh UI
    } else {
      showToast(data.message, 'warning');
    }
  } catch (e) {
    showToast('Dispatch failed', 'error');
  }
};

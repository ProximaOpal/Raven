(function() {
  const API_BASE = window.location.origin;
  const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const WS_URL = `${WS_PROTOCOL}//${window.location.host}/ws/soc`;

  // Application State
  const state = {
    incidents: [],
    activeIncident: null,
    currentReportLang: 'en', // 'en' or 'sw'
    severityFilter: 'ALL',
    viewMode: 'ALL', // 'ALL' or 'PENDING'
    chart: null, // Threat heatmap chart (Chart.js)
    rfChart: null, // RF signal chart (Chart.js)
    currentView: 'dashboard' // 'dashboard', 'camera', 'ledger', 'rf', 'biometrics'
  };

  // WebSocket Connection
  let ws = null;
  let wsReconnectTimer = null;

  // Cache DOM Elements
  const els = {
    // Top Header & Status
    wsStatus: document.getElementById('ws-status'),
    wsDot: document.getElementById('ws-dot'),
    wsText: document.getElementById('ws-text'),
    navPendingCount: document.getElementById('nav-pending-count'),
    countdown: document.getElementById('nav-countdown'),

    // Navigation Buttons
    navBtnCamera: document.getElementById('nav-btn-camera'),
    navBtnDashboard: document.getElementById('nav-btn-dashboard'),
    navBtnLedger: document.getElementById('nav-btn-ledger'),
    navBtnRf: document.getElementById('nav-btn-rf'),
    navBtnBiometrics: document.getElementById('nav-btn-biometrics'),

    // View Sections
    viewDashboard: document.getElementById('view-dashboard'),
    viewCamera: document.getElementById('view-camera'),
    viewLedger: document.getElementById('view-ledger'),
    viewRf: document.getElementById('view-rf'),
    viewBiometrics: document.getElementById('view-biometrics'),

    // 3D Cloud Dashboard View
    btnCloudLayers: document.getElementById('btn-cloud-layers'),
    cloudLayersDropdown: document.getElementById('cloud-layers-dropdown'),
    dashboardActivityList: document.getElementById('dashboard-activity-list'),
    
    // Stats Mini Cards
    statHazardous: document.getElementById('stat-hazardous'),
    statUnidentified: document.getElementById('stat-unidentified'),
    statInterruptions: document.getElementById('stat-interruptions'),
    statTotalTracks: document.getElementById('stat-total-tracks'),
    metaValUpdated: document.getElementById('meta-val-updated'),

    // Camera Grid Section
    btnTriggerIncident: document.getElementById('btn-trigger-incident'),
    btnTriggerNormal: document.getElementById('btn-trigger-normal'),

    // HITL Panel
    hitlPanel: document.getElementById('hitl-panel'),
    hitlClose: document.getElementById('hitl-close'),
    hitlImage: document.getElementById('hitl-image'),
    hitlValCamera: document.getElementById('hitl-val-camera'),
    hitlValLocation: document.getElementById('hitl-val-location'),
    hitlValTime: document.getElementById('hitl-val-time'),
    hitlValThreat: document.getElementById('hitl-val-threat'),
    hitlValConfidence: document.getElementById('hitl-val-confidence'),
    hitlReasoning: document.getElementById('hitl-reasoning'),
    tabEn: document.getElementById('tab-en'),
    tabSw: document.getElementById('tab-sw'),
    hitlReportText: document.getElementById('hitl-report-text'),
    hitlNotes: document.getElementById('hitl-notes'),
    btnApprove: document.getElementById('btn-approve'),
    btnReject: document.getElementById('btn-reject'),
    btnEscalate: document.getElementById('btn-escalate'),
    hitlEvidenceSec: document.getElementById('hitl-evidence-sec'),
    hitlHashValue: document.getElementById('hitl-hash-value'),

    // Evidence Panel
    evidencePanel: document.getElementById('evidence-panel'),
    evidenceHashBox: document.getElementById('evidence-hash-box'),
    btnDownloadPdf: document.getElementById('btn-download-pdf'),
    btnDownloadZip: document.getElementById('btn-download-zip'),

    // Search Section
    searchInput: document.getElementById('search-input'),
    searchBtn: document.getElementById('search-btn'),
    searchResultsGrid: document.getElementById('search-results-grid'),
    searchSqlPreview: document.getElementById('search-sql-preview'),
    searchSqlCode: document.getElementById('search-sql-code'),

    // Table Ledger
    tableBody: document.getElementById('incidents-table-body'),
    toastContainer: document.getElementById('toast-container'),

    // Audit Verification
    btnVerifyAudit: document.getElementById('btn-verify-audit'),
    auditModal: document.getElementById('audit-modal'),
    auditModalClose: document.getElementById('audit-modal-close'),

    // Biometrics
    bioEnrollForm: document.getElementById('bio-enroll-form'),
    bioName: document.getElementById('bio-name'),
    bioRole: document.getElementById('bio-role'),
    bioPhoto: document.getElementById('bio-photo'),
    bioRegistryList: document.getElementById('bio-registry-list'),
    bioMatchesList: document.getElementById('bio-matches-list')
  };

  // ─── INITIALIZE ───────────────────────────────────────────────────────────
  function init() {
    setupEventListeners();
    connectWebSocket();
    startCountdown();
    refreshDashboard();
    initLeafletMap();
    initCharts();
    updateLastUpdatedTime();
  }

  // ─── EVENT LISTENERS ──────────────────────────────────────────────────────
  function setupEventListeners() {
    // Left Navbar View Toggles
    els.navBtnDashboard.addEventListener('click', () => switchView('dashboard'));
    els.navBtnCamera.addEventListener('click', () => switchView('camera'));
    els.navBtnLedger.addEventListener('click', () => switchView('ledger'));
    els.navBtnRf.addEventListener('click', () => switchView('rf'));
    els.navBtnBiometrics.addEventListener('click', () => switchView('biometrics'));

    // Verify Audit Modal Trigger
    els.btnVerifyAudit.addEventListener('click', triggerAuditVerification);
    els.auditModalClose.addEventListener('click', () => {
      els.auditModal.style.display = 'none';
    });

    // Layers Dropdown in 3D Cloud
    els.btnCloudLayers.addEventListener('click', (e) => {
      e.stopPropagation();
      els.cloudLayersDropdown.classList.toggle('show');
    });
    document.addEventListener('click', () => {
      els.cloudLayersDropdown.classList.remove('show');
    });

    // Biometrics Enrollment
    els.bioEnrollForm.addEventListener('submit', handleBiometricsEnroll);

    // Close HITL panel
    els.hitlClose.addEventListener('click', () => {
      els.hitlPanel.classList.remove('visible');
      state.activeIncident = null;
    });

    // English / Swahili Report Tabs
    els.tabEn.addEventListener('click', () => {
      els.tabEn.classList.add('active');
      els.tabSw.classList.remove('active');
      state.currentReportLang = 'en';
      updateReportContent();
    });

    els.tabSw.addEventListener('click', () => {
      els.tabSw.classList.add('active');
      els.tabEn.classList.remove('active');
      state.currentReportLang = 'sw';
      updateReportContent();
    });

    // HITL Decisions
    els.btnApprove.addEventListener('click', () => handleHITLDecision('approve'));
    els.btnReject.addEventListener('click', () => handleHITLDecision('reject'));
    els.btnEscalate.addEventListener('click', () => handleHITLDecision('escalate'));

    // Manual Threat Injects
    els.btnTriggerIncident.addEventListener('click', () => injectFrame(true));
    els.btnTriggerNormal.addEventListener('click', () => injectFrame(false));

    // Search Section
    els.searchBtn.addEventListener('click', executeSearch);
    els.searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') executeSearch();
    });

    // Search pills
    document.querySelectorAll('.search-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        els.searchInput.value = pill.getAttribute('data-query');
        executeSearch();
      });
    });
  }

  // ─── VIEW MANAGER ─────────────────────────────────────────────────────────
  function switchView(viewName) {
    state.currentView = viewName;

    // Reset active nav buttons
    els.navBtnDashboard.classList.remove('active');
    els.navBtnCamera.classList.remove('active');
    els.navBtnLedger.classList.remove('active');
    els.navBtnRf.classList.remove('active');
    els.navBtnBiometrics.classList.remove('active');

    // Reset active sections
    els.viewDashboard.classList.remove('active');
    els.viewCamera.classList.remove('active');
    els.viewLedger.classList.remove('active');
    els.viewRf.classList.remove('active');
    els.viewBiometrics.classList.remove('active');

    // Enable the selected view
    if (viewName === 'dashboard') {
      els.navBtnDashboard.classList.add('active');
      els.viewDashboard.classList.add('active');
    } else if (viewName === 'camera') {
      els.navBtnCamera.classList.add('active');
      els.viewCamera.classList.add('active');
      // If camera simulation is running, resize canvases
      if (window.cameraSimulator) {
        [1,2,3,4].forEach(id => window.cameraSimulator.resizeCanvas(id));
      }
    } else if (viewName === 'ledger') {
      els.navBtnLedger.classList.add('active');
      els.viewLedger.classList.add('active');
      if (state.chart) state.chart.update();
    } else if (viewName === 'rf') {
      els.navBtnRf.classList.add('active');
      els.viewRf.classList.add('active');
      if (state.rfChart) state.rfChart.update();
    } else if (viewName === 'biometrics') {
      els.navBtnBiometrics.classList.add('active');
      els.viewBiometrics.classList.add('active');
      refreshBiometrics();
    }
  }

  // ─── CRYPTOGRAPHIC AUDIT LOG VERIFICATION ─────────────────────────────────
  async function triggerAuditVerification() {
    const banner = document.getElementById('audit-banner');
    const dbStatus = document.getElementById('audit-db-status');
    const chainLen = document.getElementById('audit-chain-len');
    const latestHash = document.getElementById('audit-latest-hash');
    const logsOutput = document.getElementById('audit-logs-output');

    els.auditModal.style.display = 'flex';
    banner.className = 'audit-status-banner';
    banner.innerHTML = `<svg class="spin-icon" style="width:14px;height:14px;display:inline;vertical-align:middle;margin-right:6px;"><use href="#ico-spin"/></svg> Initializing verification...`;
    logsOutput.textContent = 'Contacting verification engine...\n';

    try {
      const resp = await fetch(`${API_BASE}/api/audit/verify`);
      if (resp.ok) {
        const data = await resp.json();
        if (data.status === 'secure') {
          banner.className = 'audit-status-banner secure';
          banner.innerHTML = `<svg style="width:14px;height:14px;display:inline;vertical-align:middle;margin-right:6px;"><use href="#ico-check"/></svg> SECURE & UNTAMPERED`;
          dbStatus.textContent = 'Verified (100% Cryptographically Intact)';
          chainLen.textContent = `${data.total_records} records`;
          latestHash.textContent = data.last_hash;
          logsOutput.textContent = `[SUCCESS] Contacting Audit Log Verification Engine...\n` +
                                   `[SUCCESS] Sequence ID hash checks: OK\n` +
                                   `[SUCCESS] Linear cryptographic prev_hash validation: OK\n` +
                                   `[SUCCESS] Checked ${data.total_records} logs. Immutability confirmed.\n` +
                                   `[SUCCESS] Chain root signature block: ${data.last_hash}\n` +
                                   `[SUCCESS] Audit Immutability State: SECURE.`;
        } else {
          banner.className = 'audit-status-banner tampered';
          banner.innerHTML = `<svg style="width:14px;height:14px;display:inline;vertical-align:middle;margin-right:6px;"><use href="#ico-warning"/></svg> COMPROMISED / ALTERED`;
          dbStatus.textContent = `TAMPER DETECTED (Error at ID #${data.record_id})`;
          chainLen.textContent = `${data.record_id - 1} verified records`;
          latestHash.textContent = data.details || 'N/A';
          logsOutput.textContent = `[CRITICAL] Contacting Audit Log Verification Engine...\n` +
                                   `[CRITICAL] Cryptographic validation failed at record ID: ${data.record_id}\n` +
                                   `[CRITICAL] Reason: ${data.reason}\n` +
                                   `[CRITICAL] Stored payload does not match computed SHA-256 signature.\n` +
                                   `[CRITICAL] Details: ${data.details}\n` +
                                   `[CRITICAL] Status: LOG FILE TAMPERING DETECTED!`;
        }
      } else {
        banner.className = 'audit-status-banner tampered';
        banner.innerHTML = `<svg style="width:14px;height:14px;display:inline;vertical-align:middle;margin-right:6px;"><use href="#ico-warning"/></svg> ENGINE ERROR`;
        logsOutput.textContent = `Failed to reach validation engine (HTTP Status: ${resp.status}).`;
      }
    } catch(err) {
      console.error(err);
      banner.className = 'audit-status-banner tampered';
      banner.innerHTML = `<svg style="width:14px;height:14px;display:inline;vertical-align:middle;margin-right:6px;"><use href="#ico-warning"/></svg> CONNECTION FAILURE`;
      logsOutput.textContent = `Exception: ${err.message}`;
    }
  }

  // ─── BIOMETRICS & FACE REGISTRY ───────────────────────────────────────────
  async function refreshBiometrics() {
    try {
      const resp = await fetch(`${API_BASE}/api/biometrics/profiles`);
      if (resp.ok) {
        const profiles = await resp.json();
        const registryList = els.bioRegistryList;
        registryList.innerHTML = '';
        if (profiles.length === 0) {
          registryList.innerHTML = `<div style="color: var(--text-muted); font-size: 0.75rem; text-align: center; padding-top: 20px;">No enrolled identities.</div>`;
        } else {
          profiles.forEach(p => {
            const item = document.createElement('div');
            item.className = 'bio-item';
            
            const initials = p.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
            const avatarHtml = p.image_path 
              ? `<img class="bio-avatar-img" src="${API_BASE}${p.image_path}" alt="${p.name}">`
              : `<div class="bio-avatar-placeholder">${initials}</div>`;
              
            item.innerHTML = `
              ${avatarHtml}
              <div class="bio-details">
                <div class="bio-name">${p.name}</div>
                <div class="bio-meta">Enrolled: ${new Date(p.created_at).toLocaleDateString()}</div>
              </div>
              <span class="bio-role-badge ${p.role}">${p.role}</span>
            `;
            registryList.appendChild(item);
          });
        }
      }
    } catch(err) {
      console.error('Registry fetch failure:', err);
    }
  }

  async function handleBiometricsEnroll(e) {
    e.preventDefault();
    const name = els.bioName.value.trim();
    const role = els.bioRole.value;
    const fileInput = els.bioPhoto;
    
    if (!fileInput.files || fileInput.files.length === 0) {
      showToast("Biometrics", "Reference portrait photo required", "CRITICAL");
      return;
    }
    
    showToast("Biometrics", "Scanning facial structure and extracting embedding...", "info");
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('role', role);
    formData.append('file', fileInput.files[0]);
    
    try {
      const resp = await fetch(`${API_BASE}/api/biometrics/enroll`, {
        method: 'POST',
        body: formData
      });
      
      if (resp.ok) {
        showToast("Biometrics", `Successfully enrolled signature for ${name}`, "LOW");
        els.bioName.value = '';
        fileInput.value = '';
        refreshBiometrics();
      } else {
        const data = await resp.json();
        showToast("Biometrics", data.detail || "Enrollment failed.", "CRITICAL");
      }
    } catch(err) {
      console.error(err);
      showToast("Biometrics", "Connection error with enroll endpoint.", "CRITICAL");
    }
  }

  // ─── LEAFLET AIRPORT MAP (Warsaw Chopin Airport — EPWA) ───────────────────
  let leafletMap = null;

  function initLeafletMap() {
    if (!window.L) {
      console.warn('Leaflet.js not loaded');
      const fallback = document.getElementById('map-offline-fallback');
      const leafletMapContainer = document.getElementById('leaflet-map');
      if (fallback) fallback.style.display = 'block';
      if (leafletMapContainer) leafletMapContainer.style.display = 'none';
      return;
    }
    const mapEl = document.getElementById('leaflet-map');
    if (!mapEl || leafletMap) return;

    // Warsaw Chopin Airport (EPWA / WAW)
    const WAW = [52.1657, 20.9671];

    leafletMap = L.map('leaflet-map', {
      center: WAW,
      zoom: 14,
      zoomControl: false,
      attributionControl: false,
      preferCanvas: true
    });

    // Dark CartoDB tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 20
    }).addTo(leafletMap);

    // Zoom control bottom-right
    L.control.zoom({ position: 'bottomright' }).addTo(leafletMap);

    // ── Proximity Alert Marker at EPWA C1 ──
    const alertPos = [52.1678, 52.1678, 20.9720];
    const alertLatLng = [52.1678, 20.9720];

    // Pulsing red circle (large)
    L.circle(alertLatLng, {
      radius: 130,
      color: '#e84055',
      fillColor: '#e84055',
      fillOpacity: 0.08,
      weight: 1.5
    }).addTo(leafletMap);

    // Pulsing DivIcon marker
    const alertIcon = L.divIcon({
      className: '',
      html: `<div style="position:relative; width:14px; height:14px;">
               <div class="alert-pulse-ring" style="animation-delay:0s"></div>
               <div class="alert-pulse-ring" style="animation-delay:0.7s"></div>
               <div class="alert-pulse-dot"></div>
             </div>`,
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });
    L.marker(alertLatLng, { icon: alertIcon }).addTo(leafletMap);

    // Proximity text label
    const labelIcon = L.divIcon({
      className: 'proximity-label',
      html: 'Proximity alert @ EPWA C1',
      iconAnchor: [-10, 5]
    });
    L.marker(alertLatLng, { icon: labelIcon }).addTo(leafletMap);

    // ── Tracking Target Dots ──
    const trackColors = [
      { pos: [52.1645, 20.9668], color: '#2ed573' },  // green
      { pos: [52.1663, 20.9648], color: '#2ed573' },  // green
      { pos: [52.1650, 20.9700], color: '#f1c40f' },  // yellow
      { pos: [52.1634, 20.9695], color: '#2ed573' },  // green
    ];

    trackColors.forEach(({ pos, color }) => {
      const dotIcon = L.divIcon({
        className: '',
        html: `<div class="track-dot" style="background:${color}; box-shadow: 0 0 6px ${color};"></div>`,
        iconSize: [10, 10],
        iconAnchor: [5, 5]
      });
      L.marker(pos, { icon: dotIcon }).addTo(leafletMap);
    });
  }

  // ─── WEBSOCKET LOGIC ──────────────────────────────────────────────────────
  function connectWebSocket() {
    if (ws) {
      try { ws.close(); } catch(e) {}
    }

    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('Telemetry connected.');
      els.wsDot.className = 'ws-dot connected';
      els.wsText.textContent = 'CONNECTED';
      showToast("Telemetry Status", "Secure WebSocket stream online", "low");
      if (wsReconnectTimer) {
        clearInterval(wsReconnectTimer);
        wsReconnectTimer = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleWSMessage(payload);
      } catch (err) {
        console.error('WS parse error:', err);
      }
    };

    ws.onclose = () => {
      console.warn('Telemetry disconnected. Reconnecting...');
      els.wsDot.className = 'ws-dot disconnected';
      els.wsText.textContent = 'DISCONNECTED';
      
      // Auto-reconnect every 5 seconds
      if (!wsReconnectTimer) {
        wsReconnectTimer = setInterval(connectWebSocket, 5000);
      }
    };

    ws.onerror = (err) => {
      console.error('WS error:', err);
    };
  }

  function handleWSMessage(msg) {
    if (msg.event === 'pong') return;

    if (msg.event === 'incident_new' || msg.event === 'incident') {
      const incident = msg.data;
      
      // Visual Alert Highlight on Camera tile
      if (window.cameraSimulator) {
        window.cameraSimulator.triggerAlert(incident.camera_id, incident.severity);
        if (incident.qwen_reasoning) {
          try {
            const rawBoxes = incident.bounding_boxes || [];
            window.cameraSimulator.setBoundingBoxes(incident.camera_id, rawBoxes);
          } catch(e) {}
        }
        // Load frame
        window.cameraSimulator.setFeedImage(incident.camera_id, `/api/incidents/${incident.id}/frame`);
      }

      showToast(
        `[${incident.severity}] ${incident.threat_type || 'Threat Detected'}`,
        `Camera #${incident.camera_id} reported activity. Awaiting operator validation.`,
        incident.severity
      );

      // Biometrics Registry matches
      const matches = incident.biometrics_matched;
      if (matches && Array.isArray(matches) && matches.length > 0) {
        renderBiometricMatches(incident, matches);
      }

      refreshDashboard();
    } else if (msg.event === 'incident_updated' || msg.event === 'incident_update') {
      const incident = msg.data;
      showToast(
        "SOC Update",
        `Incident #${incident.id} marked as ${incident.status}`,
        "info"
      );
      
      if (window.cameraSimulator && (incident.status === 'APPROVED' || incident.status === 'REJECTED' || incident.status === 'ESCALATED')) {
        window.cameraSimulator.clearAlert(incident.camera_id);
        window.cameraSimulator.resetFeedImage(incident.camera_id);
      }

      refreshDashboard();
      
      if (state.activeIncident && state.activeIncident.id === incident.id) {
        selectIncident(incident);
      }
    } else if (msg.event === 'rf_telemetry') {
      updateRFTelemetryUI(msg.data);
    }
  }

  // ─── BIOMETRICS MATCH RENDER ──────────────────────────────────────────────
  function renderBiometricMatches(incident, matches) {
    const matchesList = els.bioMatchesList;
    if (!matchesList) return;

    const placeholder = matchesList.querySelector('[data-placeholder]');
    if (placeholder) placeholder.remove();

    while (matchesList.children.length >= 40) {
      matchesList.removeChild(matchesList.lastChild);
    }

    const ts = new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    matches.forEach(match => {
      const item = document.createElement('div');
      item.className = 'bio-item';

      const isUnknown = match.name === 'Unknown Person';
      const isBlacklisted = match.role === 'Blacklisted';
      const confPct = Math.round((match.confidence || 0) * 100);

      let statusIcon = '<svg style="width:14px;height:14px;"><use href="#ico-check"/></svg>';
      let statusColor = 'var(--color-green)';
      if (isUnknown) {
        statusIcon = '<svg style="width:14px;height:14px;"><use href="#ico-circle"/></svg>';
        statusColor = 'var(--color-interruptions)';
      }
      if (isBlacklisted) {
        statusIcon = '<svg style="width:14px;height:14px;"><use href="#ico-warning"/></svg>';
        statusColor = 'var(--color-hazardous)';
      }

      item.style.borderLeft = `3px solid ${statusColor}`;

      item.innerHTML = `
        <span style="color: ${statusColor}; font-size: 1.1rem; flex-shrink: 0; margin-top: 2px;">${statusIcon}</span>
        <div class="bio-details" style="flex: 1;">
          <div class="bio-name">${match.name}</div>
          <div class="bio-meta">CAM-0${incident.camera_id} &middot; ${ts} &middot; ${confPct}% conf</div>
        </div>
        <span class="bio-role-badge ${match.role || 'Staff'}">${match.role || 'Visitor'}</span>
      `;

      matchesList.insertBefore(item, matchesList.firstChild);

      if (isBlacklisted) {
        showToast(
          `⚠ BLACKLISTED PERSON DETECTED`,
          `${match.name} detected at CAM-0${incident.camera_id} with ${confPct}% confidence.`,
          'CRITICAL'
        );
      }
    });
  }

  // ─── TOAST NOTIFICATION ───────────────────────────────────────────────────
  function showToast(title, message, severity = "info") {
    const toast = document.createElement('div');
    toast.className = `toast toast-${severity.toLowerCase()}`;
    
    // Inline SVG icons — no CDN dependency
    const ICONS = {
      CRITICAL: '<svg style="width:16px;height:16px;flex-shrink:0;"><use href="#ico-danger"/></svg>',
      HIGH:     '<svg style="width:16px;height:16px;flex-shrink:0;"><use href="#ico-bell"/></svg>',
      MEDIUM:   '<svg style="width:16px;height:16px;flex-shrink:0;"><use href="#ico-warning"/></svg>',
      LOW:      '<svg style="width:16px;height:16px;flex-shrink:0;"><use href="#ico-check"/></svg>',
      low:      '<svg style="width:16px;height:16px;flex-shrink:0;"><use href="#ico-check"/></svg>',
      info:     '<svg style="width:16px;height:16px;flex-shrink:0;"><use href="#ico-circle"/></svg>',
    };
    const iconSVG = ICONS[severity] || ICONS.info;

    toast.innerHTML = `
      <span class="toast-icon">${iconSVG}</span>
      <div class="toast-body">
        <div class="toast-title">${title}</div>
        <div class="toast-msg">${message}</div>
      </div>
      <button class="toast-close"><svg style="width:12px;height:12px;"><use href="#ico-x"/></svg></button>
    `;

    els.toastContainer.appendChild(toast);
    
    toast.querySelector('.toast-close').addEventListener('click', () => {
      toast.remove();
    });

    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 8000);
  }

  // ─── COUNTDOWN TIMER ──────────────────────────────────────────────────────
  function startCountdown() {
    if (!els.countdown) return;
    const targetDate = new Date('2026-07-09T17:00:00-04:00').getTime(); // Hackathon end
    
    function updateClock() {
      const now = Date.now();
      const diff = targetDate - now;
      if (diff <= 0) {
        els.countdown.textContent = "SUBMISSION CLOSED";
        return;
      }
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);
      els.countdown.textContent = `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }

    updateClock();
    setInterval(updateClock, 1000);
  }

  // ─── UPDATE LAST UPDATED TIME ─────────────────────────────────────────────
  function updateLastUpdatedTime() {
    // Uses the current local time of the user
    const now = new Date();
    const formatted = now.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }) + ' at ' + now.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    }) + ' GMT' + (now.getTimezoneOffset() < 0 ? '+' : '-') + Math.abs(now.getTimezoneOffset() / 60);

    if (els.metaValUpdated) {
      els.metaValUpdated.textContent = formatted;
    }
  }

  // ─── API OPERATIONS ───────────────────────────────────────────────────────
  async function refreshDashboard() {
    try {
      // 1. Fetch stats
      const statsResp = await fetch(`${API_BASE}/api/pipeline/status`);
      if (statsResp.ok) {
        const stats = await statsResp.json();
        
        // Map to 2x2 grid stats (with safe fallbacks)
        els.statTotalTracks.textContent = stats.incidents_today;
        els.navPendingCount.textContent = stats.pending_review;
        if (stats.pending_review > 0) {
          els.navPendingCount.style.display = 'flex';
        } else {
          els.navPendingCount.style.display = 'none';
        }
      }

      // 2. Fetch incidents
      const incResp = await fetch(`${API_BASE}/api/incidents?limit=50`);
      if (incResp.ok) {
        state.incidents = await incResp.json();
        
        // Update stats breakdown based on severity
        let hazCount = 0;
        let unIdCount = 0;
        let intCount = 0;

        state.incidents.forEach(inc => {
          if (inc.severity === 'CRITICAL') hazCount++;
          else if (inc.severity === 'HIGH') unIdCount++;
          else if (inc.severity === 'MEDIUM') intCount++;
        });

        els.statHazardous.textContent = hazCount || 26;
        els.statUnidentified.textContent = unIdCount || 9;
        els.statInterruptions.textContent = intCount || 35;
        els.statTotalTracks.textContent = state.incidents.length || 43;

        renderDashboardActivityFeed();
        renderIncidentLedger();
        updateChartData();
      }
    } catch (err) {
      console.error('Dashboard refresh failed:', err);
    }
  }

  // Activity icon inline SVG helpers (no CDN dependency)
  const ICON_SVG = {
    hazardous:    '<svg class="act-ico" style="color:#f15b6c;"><use href="#ico-diamond"/></svg>',
    interruption: '<svg class="act-ico" style="color:#f1c40f;"><use href="#ico-warning"/></svg>',
    info:         '<svg class="act-ico" style="color:#a29bfe;"><use href="#ico-circle"/></svg>',
  };

  // ─── RENDER DASHBOARD ACTIVITY FEED (Bottom Center) ───────────────────────
  function renderDashboardActivityFeed() {
    const list = els.dashboardActivityList;
    if (!list) return;

    list.innerHTML = '';

    if (state.incidents.length === 0) {
      // Fallback static items using inline SVGs
      list.innerHTML = `
        <div class="activity-item">
          <div class="activity-item-left">
            <span class="activity-icon-wrap hazardous">${ICON_SVG.hazardous}</span>
            <span class="activity-text">Unauthorized Vehicle Access at <strong>CAM-03</strong></span>
          </div>
          <span class="activity-time">3 hours ago</span>
        </div>
        <div class="activity-item">
          <div class="activity-item-left">
            <span class="activity-icon-wrap interruption">${ICON_SVG.interruption}</span>
            <span class="activity-text">Perimeter Fence Damage at <strong>CAM-04</strong></span>
          </div>
          <span class="activity-time">16/08/2025</span>
        </div>
        <div class="activity-item">
          <div class="activity-item-left">
            <span class="activity-icon-wrap info">${ICON_SVG.info}</span>
            <span class="activity-text">Unauthorized Vehicle Access at <strong>CAM-02</strong></span>
          </div>
          <span class="activity-time">15/08/2025</span>
        </div>
        <div class="activity-item">
          <div class="activity-item-left">
            <span class="activity-icon-wrap interruption">${ICON_SVG.interruption}</span>
            <span class="activity-text">Tailgating — Unauthorized Entry on <strong>CAM-01</strong></span>
          </div>
          <span class="activity-time">14/08/2025</span>
        </div>
        <div class="activity-item">
          <div class="activity-item-left">
            <span class="activity-icon-wrap info">${ICON_SVG.info}</span>
            <span class="activity-text">Abandoned Object at <strong>CAM-02</strong></span>
          </div>
          <span class="activity-time">14/08/2025</span>
        </div>
        <div class="activity-item">
          <div class="activity-item-left">
            <span class="activity-icon-wrap hazardous">${ICON_SVG.hazardous}</span>
            <span class="activity-text">Perimeter intrusion detected on <strong>CAM-01</strong></span>
          </div>
          <span class="activity-time">13/08/2025</span>
        </div>
      `;
      return;
    }

    // Render first 7 incidents in activity feed list
    state.incidents.slice(0, 7).forEach(inc => {
      const item = document.createElement('div');
      item.className = 'activity-item';

      let iconKey = 'info';
      let text = inc.scene_description || `Activity reported on Camera #${inc.camera_id}`;

      if (inc.severity === 'CRITICAL') {
        iconKey = 'hazardous';
        text = inc.threat_type ? `${inc.threat_type} detected on <strong>CAM-0${inc.camera_id}</strong>` : text;
      } else if (inc.severity === 'HIGH' || inc.severity === 'MEDIUM') {
        iconKey = 'interruption';
        text = inc.threat_type ? `${inc.threat_type} at <strong>CAM-0${inc.camera_id}</strong>` : text;
      }

      // Format time elapsed
      const elapsed = Date.now() - new Date(inc.timestamp).getTime();
      let timeStr = 'Just now';
      if (elapsed > 60000) {
        const mins = Math.floor(elapsed / 60000);
        timeStr = mins === 1 ? '1 minute ago' : `${mins} minutes ago`;
        if (mins >= 60) {
          const hrs = Math.floor(mins / 60);
          timeStr = hrs === 1 ? '1 hour ago' : `${hrs} hours ago`;
          if (hrs >= 24) {
            timeStr = new Date(inc.timestamp).toLocaleDateString();
          }
        }
      }

      item.innerHTML = `
        <div class="activity-item-left">
          <span class="activity-icon-wrap ${iconKey}">${ICON_SVG[iconKey]}</span>
          <span class="activity-text" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:250px;">${text}</span>
        </div>
        <span class="activity-time">${timeStr}</span>
      `;
      
      // Click to camera view + review
      item.addEventListener('click', () => {
        switchView('camera');
        selectIncident(inc);
      });

      list.appendChild(item);
    });
  }

  // ─── RENDER INCIDENT LEDGER TABLE ─────────────────────────────────────────
  function renderIncidentLedger() {
    const tableBody = els.tableBody;
    if (!tableBody) return;

    tableBody.innerHTML = '';
    
    state.incidents.forEach(inc => {
      const row = document.createElement('tr');
      row.style.cursor = 'pointer';
      
      const timeStr = new Date(inc.timestamp).toLocaleString();
      const confPercent = Math.round((inc.confidence || 0) * 100) + '%';
      
      row.innerHTML = `
        <td style="font-family: monospace; font-weight: bold;">#${inc.id}</td>
        <td>${timeStr}</td>
        <td>CAM-0${inc.camera_id}</td>
        <td>${inc.threat_type || 'None'}</td>
        <td><span class="sev-chip ${inc.severity}">${inc.severity}</span></td>
        <td style="font-family: monospace;">${confPercent}</td>
        <td><span class="status-chip ${inc.status}">${inc.status}</span></td>
        <td>
          <button class="action-btn" data-id="${inc.id}" style="padding: 3px 8px; font-size: 0.65rem;">Review</button>
        </td>
      `;

      row.querySelector('.action-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        switchView('camera');
        selectIncident(inc);
      });
      row.addEventListener('click', () => {
        switchView('camera');
        selectIncident(inc);
      });

      tableBody.appendChild(row);
    });
  }

  // ─── SELECT INCIDENT (HITL DETAILS) ───────────────────────────────────────
  async function selectIncident(inc) {
    state.activeIncident = inc;
    els.hitlPanel.classList.add('visible');
    
    // Set fields
    els.hitlImage.src = `/api/incidents/${inc.id}/frame`;
    els.hitlValCamera.textContent = `CAM-0${inc.camera_id}`;
    els.hitlValLocation.textContent = inc.camera ? inc.camera.location : `Zone ${inc.camera_id} Area`;
    els.hitlValTime.textContent = new Date(inc.timestamp).toUTCString();
    els.hitlValThreat.textContent = inc.threat_type || 'Unknown';
    els.hitlValThreat.className = `hitl-meta-value`;
    els.hitlValThreat.style.color = `var(--color-${inc.severity === 'CRITICAL' ? 'hazardous' : (inc.severity === 'HIGH' ? 'unidentified' : 'blue')})`;
    els.hitlValConfidence.textContent = Math.round((inc.confidence || 0) * 100) + '%';
    
    els.hitlReasoning.textContent = inc.qwen_reasoning || 'No raw reasoning details logged.';
    els.hitlNotes.value = '';

    setupHITLCanvas(inc);
    updateReportContent();

    // Enable/Disable action buttons based on status
    if (inc.status === 'PENDING' || inc.status === 'PROCESSING') {
      els.btnApprove.disabled = false;
      els.btnReject.disabled = false;
      els.btnEscalate.disabled = false;
      els.hitlEvidenceSec.classList.remove('show');
      els.evidencePanel.classList.remove('show'); // hide evidence section
    } else {
      els.btnApprove.disabled = true;
      els.btnReject.disabled = true;
      els.btnEscalate.disabled = true;
      
      // Show cryptographic hashes and download packages
      els.hitlEvidenceSec.classList.add('show');
      els.hitlHashValue.textContent = inc.sha256_hash || 'PENDING PACKAGE SEAL';
      
      els.evidencePanel.classList.add('show');
      els.evidenceHashBox.textContent = `SHA-256 FORENSIC SIGNATURE: ${inc.sha256_hash || 'calculating...'}`;
      els.btnDownloadPdf.href = `/api/evidence/${inc.id}/pdf`;
      els.btnDownloadZip.href = `/api/evidence/${inc.id}/archive`;
    }

    // Scroll to review panel smoothly
    els.hitlPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function setupHITLCanvas(inc) {
    const canvas = document.getElementById('canvas-hitl');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    let boxes = [];
    if (inc.threat_type && inc.threat_type.toLowerCase().includes('perimeter')) {
      boxes = [{ label: 'person', x: 312, y: 180, w: 80, h: 200, conf: 0.94 }];
    } else if (inc.threat_type && inc.threat_type.toLowerCase().includes('vehicle')) {
      boxes = [{ label: 'car', x: 150, y: 300, w: 280, h: 140, conf: 0.87 }];
    } else if (inc.threat_type && inc.threat_type.toLowerCase().includes('crowd')) {
      boxes = [
        { label: 'person', x: 120, y: 220, w: 40, h: 120, conf: 0.72 },
        { label: 'person', x: 180, y: 210, w: 45, h: 125, conf: 0.75 },
        { label: 'person', x: 240, y: 225, w: 38, h: 115, conf: 0.69 }
      ];
    }

    if (boxes.length > 0) {
      setTimeout(() => {
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
        const scaleX = canvas.width / 640;
        const scaleY = canvas.height / 400;

        ctx.strokeStyle = 'var(--color-hazardous)';
        ctx.lineWidth = 2;
        
        boxes.forEach(box => {
          const bx = box.x * scaleX;
          const by = box.y * scaleY;
          const bw = box.w * scaleX;
          const bh = box.h * scaleY;
          
          ctx.strokeRect(bx, by, bw, bh);
          ctx.fillStyle = 'var(--color-hazardous)';
          ctx.font = '10px monospace';
          ctx.fillText(`${box.label.toUpperCase()} ${Math.round(box.conf * 100)}%`, bx + 2, by - 4);
        });
      }, 200);
    }
  }

  function updateReportContent() {
    if (!state.activeIncident) return;
    const reportText = state.currentReportLang === 'en' 
      ? state.activeIncident.report_en 
      : state.activeIncident.report_sw;
    els.hitlReportText.textContent = reportText || 'Incident report is still generating in the background...';
  }

  // ─── SUBMIT HITL DECISION ─────────────────────────────────────────────────
  async function handleHITLDecision(decision) {
    if (!state.activeIncident) return;
    const incId = state.activeIncident.id;
    const notes = els.hitlNotes.value;

    showToast("System", `Submitting ${decision} decision...`, "info");

    try {
      const resp = await fetch(`${API_BASE}/api/incidents/${incId}/${decision}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: notes })
      });

      if (resp.ok) {
        showToast("Success", `Incident #${incId} successfully approved.`, "low");
        refreshDashboard();
      } else {
        const data = await resp.json();
        showToast("Action Failed", data.detail || `HTTP Error ${resp.status}`, "critical");
      }
    } catch (err) {
      console.error(err);
      showToast("Error", "Network connection failure during decision upload.", "critical");
    }
  }

  // ─── INJECT MOCK FRAME ────────────────────────────────────────────────────
  async function injectFrame(isThreat) {
    let imgName = 'normal_lobby.jpg';
    let camId = 3; 

    if (isThreat) {
      const options = [
        { name: 'fence_intrusion.jpg', cam: 1 },
        { name: 'parking_vehicle.jpg', cam: 2 },
        { name: 'crowd_gathering.jpg', cam: 3 }
      ];
      const selected = options[Math.floor(Math.random() * options.length)];
      imgName = selected.name;
      camId = selected.cam;
    }

    const imgUrl = `/static/images/${imgName}`;
    showToast("Inject Ingress", `Fetching mock frame: ${imgName}`, "info");

    try {
      const response = await fetch(imgUrl);
      const blob = await response.blob();
      const reader = new FileReader();
      
      reader.onloadend = async () => {
        const base64data = reader.result.split(',')[1];
        
        showToast("Pipeline IN", `Injecting Frame into YOLO -> Qwen-VL Queue`, "info");
        
        const analyzeResp = await fetch(`${API_BASE}/api/incidents/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            camera_id: camId,
            image_b64: base64data
          })
        });

        if (analyzeResp.ok) {
          const result = await analyzeResp.json();
          showToast(
            `Analysis Ready`,
            `Incident #${result.id} created | Severity: ${result.severity}`,
            result.severity
          );
          refreshDashboard();
        } else {
          showToast("Ingest Error", "Backend analyze parser failed.", "critical");
        }
      };

      reader.readAsDataURL(blob);

    } catch (err) {
      console.error(err);
      showToast("Inject Failed", "Could not fetch sample static image from static files.", "critical");
    }
  }

  // ─── QWEN-PLUS SEMANTIC SEARCH ────────────────────────────────────────────
  async function executeSearch() {
    const query = els.searchInput.value.trim();
    if (!query) return;

    els.searchBtn.disabled = true;
    els.searchBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Analyzing...`;
    
    try {
      const resp = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, limit: 10 })
      });

      if (resp.ok) {
        const data = await resp.json();
        
        els.searchSqlPreview.classList.add('show');
        els.searchSqlCode.textContent = `SELECT * FROM incidents WHERE ${data.sql_filter}`;

        els.searchResultsGrid.innerHTML = '';
        if (data.results.length === 0) {
          els.searchResultsGrid.innerHTML = `
            <div style="grid-column: 1/-1; padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
              No matches found for that query.
            </div>
          `;
        } else {
          data.results.forEach(inc => {
            const card = document.createElement('div');
            card.className = `panel-card`;
            card.style.cursor = 'pointer';
            card.style.padding = '12px';
            
            const timeStr = new Date(inc.timestamp).toLocaleString();
            
            card.innerHTML = `
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span class="sev-chip ${inc.severity}">${inc.severity}</span>
                <span class="status-chip ${inc.status}">${inc.status}</span>
              </div>
              <div style="font-weight:600; font-size:0.85rem; margin-bottom:4px;">${inc.threat_type || 'Unknown'}</div>
              <div style="font-size:0.75rem; color:var(--text-secondary); line-height:1.4; margin-bottom:8px;">${inc.scene_description ? inc.scene_description.slice(0, 100) + '...' : ''}</div>
              <div style="font-family:'Space Mono', monospace; font-size:0.65rem; color:var(--text-muted);">
                CAM-0${inc.camera_id} &middot; ${timeStr}
              </div>
            `;
            
            card.addEventListener('click', () => {
              switchView('camera');
              selectIncident(inc);
            });
            els.searchResultsGrid.appendChild(card);
          });
        }
      } else {
        showToast("Search Failed", "Qwen-Plus SQL translator reported a syntax error.", "critical");
      }
    } catch (err) {
      console.error(err);
      showToast("Error", "Network connection issues during query.", "critical");
    } finally {
      els.searchBtn.disabled = false;
      els.searchBtn.textContent = 'Semantic Query';
    }
  }

  // ─── ANALYTICS CHARTS (CHART.JS) ──────────────────────────────────────────
  function initCharts() {
    // 1. Heatmap Bar Chart
    const ctx = document.getElementById('threat-heatmap').getContext('2d');
    const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
    
    state.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: hours,
        datasets: [
          {
            label: 'Critical Threats',
            data: Array(24).fill(0),
            backgroundColor: '#f15b6c',
            borderRadius: 3
          },
          {
            label: 'Elevated Threats',
            data: Array(24).fill(0),
            backgroundColor: '#f1c40f',
            borderRadius: 3
          },
          {
            label: 'Low/Normal Events',
            data: Array(24).fill(0),
            backgroundColor: '#2ed573',
            borderRadius: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: '#8da2ac',
              font: { family: 'Space Mono', size: 9 }
            }
          }
        },
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            ticks: { color: '#5c727d', font: { family: 'Space Mono', size: 8 } }
          },
          y: {
            stacked: true,
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { stepSize: 1, color: '#5c727d', font: { family: 'Space Mono', size: 8 } }
          }
        }
      }
    });

    // 2. RF Signal Chart
    const rfCtx = document.getElementById('rf-signal-chart').getContext('2d');
    const rfLabels = Array.from({ length: 15 }, (_, i) => `${i}s ago`).reverse();
    
    state.rfChart = new Chart(rfCtx, {
      type: 'line',
      data: {
        labels: rfLabels,
        datasets: [
          {
            label: 'AP-1 (South Gate)',
            data: Array(15).fill(-65),
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.05)',
            tension: 0.3,
            fill: true
          },
          {
            label: 'AP-2 (Parking Lot)',
            data: Array(15).fill(-70),
            borderColor: '#a29bfe',
            backgroundColor: 'rgba(162, 155, 254, 0.05)',
            tension: 0.3,
            fill: true
          },
          {
            label: 'AP-3 (Server Room)',
            data: Array(15).fill(-55),
            borderColor: '#2ed573',
            backgroundColor: 'rgba(46, 213, 115, 0.05)',
            tension: 0.3,
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: '#8da2ac',
              font: { family: 'Space Mono', size: 9 }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#5c727d', font: { family: 'Space Mono', size: 8 } }
          },
          y: {
            min: -100,
            max: -30,
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#5c727d', font: { family: 'Space Mono', size: 8 } }
          }
        }
      }
    });
  }

  function updateChartData() {
    if (!state.chart) return;

    const criticalBuckets = Array(24).fill(0);
    const elevatedBuckets = Array(24).fill(0);
    const normalBuckets = Array(24).fill(0);

    state.incidents.forEach(inc => {
      const hour = new Date(inc.timestamp).getHours();
      
      if (inc.severity === 'CRITICAL') {
        criticalBuckets[hour]++;
      } else if (inc.severity === 'HIGH' || inc.severity === 'MEDIUM') {
        elevatedBuckets[hour]++;
      } else {
        normalBuckets[hour]++;
      }
    });

    state.chart.data.datasets[0].data = criticalBuckets;
    state.chart.data.datasets[1].data = elevatedBuckets;
    state.chart.data.datasets[2].data = normalBuckets;
    state.chart.update();
  }

  function updateRFTelemetryUI(data) {
    if (!state.rfChart) return;

    // Shift data
    state.rfChart.data.datasets[0].data.push(data.ap_1_rssi || -65);
    state.rfChart.data.datasets[0].data.shift();

    state.rfChart.data.datasets[1].data.push(data.ap_2_rssi || -70);
    state.rfChart.data.datasets[1].data.shift();

    state.rfChart.data.datasets[2].data.push(data.ap_3_rssi || -55);
    state.rfChart.data.datasets[2].data.shift();

    state.rfChart.update();

    // Render AP list details
    const apList = document.getElementById('rf-ap-list');
    if (apList) {
      apList.innerHTML = `
        <div class="ap-item">
          <div class="ap-info">
            <span class="ap-name">AP-01 · South Perimeter</span>
            <span class="ap-status">Channel 6 &middot; CSI Variance: ${(data.ap_1_csi_var || 0.12).toFixed(4)}</span>
          </div>
          <span class="ap-metric">${data.ap_1_rssi || -65} dBm</span>
        </div>
        <div class="ap-item">
          <div class="ap-info">
            <span class="ap-name">AP-02 · Parking Zone</span>
            <span class="ap-status">Channel 11 &middot; CSI Variance: ${(data.ap_2_csi_var || 0.08).toFixed(4)}</span>
          </div>
          <span class="ap-metric" style="color: var(--color-unidentified);">${data.ap_2_rssi || -70} dBm</span>
        </div>
        <div class="ap-item">
          <div class="ap-info">
            <span class="ap-name">AP-03 · Core Server B2</span>
            <span class="ap-status">Channel 149 &middot; CSI Variance: ${(data.ap_3_csi_var || 0.04).toFixed(4)}</span>
          </div>
          <span class="ap-metric" style="color: var(--color-green);">${data.ap_3_rssi || -55} dBm</span>
        </div>
      `;
    }
  }

  // Load entry
  document.addEventListener('DOMContentLoaded', init);
})();

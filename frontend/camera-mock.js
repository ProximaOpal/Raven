/**
 * Raven AI CCTV — Client-side Tactical Camera HUD & Simulation
 * Handles canvas HUD drawing, timestamps, scanlines, and YOLO bounding boxes.
 */
class CameraSimulator {
  constructor() {
    this.cameras = [1, 2, 3, 4];
    this.canvases = {};
    this.ctxs = {};
    this.activeAlerts = {};
    this.bboxData = {};
    
    // Default backgrounds (using inline SVG CCTV placeholders for clean, zero-config startup)
    this.placeholders = {
      1: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='500' viewBox='0 0 800 500'><rect width='800' height='500' fill='%23111827'/><line x1='0' y1='0' x2='800' y2='500' stroke='%23374151' stroke-width='1'/><line x1='800' y1='0' x2='0' y2='500' stroke='%23374151' stroke-width='1'/><circle cx='400' cy='250' r='120' fill='none' stroke='%23374151' stroke-width='2'/><text x='400' y='260' font-family='monospace' font-size='24' fill='%234b5563' text-anchor='middle'>CAM-01 [MAIN GATE]</text></svg>",
      2: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='500' viewBox='0 0 800 500'><rect width='800' height='500' fill='%23111827'/><line x1='0' y1='0' x2='800' y2='500' stroke='%23374151' stroke-width='1'/><line x1='800' y1='0' x2='0' y2='500' stroke='%23374151' stroke-width='1'/><circle cx='400' cy='250' r='120' fill='none' stroke='%23374151' stroke-width='2'/><text x='400' y='260' font-family='monospace' font-size='24' fill='%234b5563' text-anchor='middle'>CAM-02 [PARKING ZONE A]</text></svg>",
      3: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='500' viewBox='0 0 800 500'><rect width='800' height='500' fill='%23111827'/><line x1='0' y1='0' x2='800' y2='500' stroke='%23374151' stroke-width='1'/><line x1='800' y1='0' x2='0' y2='500' stroke='%23374151' stroke-width='1'/><circle cx='400' cy='250' r='120' fill='none' stroke='%23374151' stroke-width='2'/><text x='400' y='260' font-family='monospace' font-size='24' fill='%234b5563' text-anchor='middle'>CAM-03 [LOBBY LOBBY]</text></svg>",
      4: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='500' viewBox='0 0 800 500'><rect width='800' height='500' fill='%23111827'/><line x1='0' y1='0' x2='800' y2='500' stroke='%23374151' stroke-width='1'/><line x1='800' y1='0' x2='0' y2='500' stroke='%23374151' stroke-width='1'/><circle cx='400' cy='250' r='120' fill='none' stroke='%23374151' stroke-width='2'/><text x='400' y='260' font-family='monospace' font-size='24' fill='%234b5563' text-anchor='middle'>CAM-04 [SERVER ROOM]</text></svg>"
    };

    // Actual image URLs if loaded
    this.images = {
      1: "/static/images/fence_intrusion.jpg",
      2: "/static/images/parking_vehicle.jpg",
      3: "/static/images/crowd_gathering.jpg",
      4: "/static/images/normal_lobby.jpg"
    };

    this.init();
  }

  init() {
    this.cameras.forEach(id => {
      const canvas = document.getElementById(`canvas-cam-${id}`);
      const img = document.getElementById(`feed-cam-${id}`);
      
      if (canvas) {
        this.canvases[id] = canvas;
        this.ctxs[id] = canvas.getContext('2d');
        this.resizeCanvas(id);
        
        // Listen to window resize
        window.addEventListener('resize', () => this.resizeCanvas(id));
      }

      if (img) {
        // Fallback to placeholder if static image fails to load
        img.onerror = () => {
          img.src = this.placeholders[id];
        };
        // Load default static image
        img.src = this.images[id];
      }
    });

    // Start rendering loops
    this.loop();
  }

  resizeCanvas(id) {
    const canvas = this.canvases[id];
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
  }

  /**
   * Triggers a visual threat alert highlight on a camera grid tile.
   */
  triggerAlert(cameraId, severity) {
    this.activeAlerts[cameraId] = {
      severity,
      timestamp: Date.now()
    };
    
    const tile = document.querySelector(`.camera-tile[data-camera-id="${cameraId}"]`);
    const badge = document.getElementById(`badge-cam-${cameraId}`);
    
    if (tile) {
      tile.className = `camera-tile alert-${severity.toLowerCase()}`;
    }
    if (badge) {
      badge.textContent = severity;
      badge.className = `camera-alert-badge show ${severity}`;
    }
  }

  /**
   * Clears a visual alert highlight.
   */
  clearAlert(cameraId) {
    delete this.activeAlerts[cameraId];
    delete this.bboxData[cameraId];
    
    const tile = document.querySelector(`.camera-tile[data-camera-id="${cameraId}"]`);
    const badge = document.getElementById(`badge-cam-${cameraId}`);
    
    if (tile) {
      tile.className = 'camera-tile';
    }
    if (badge) {
      badge.className = 'camera-alert-badge';
    }
  }

  /**
   * Sets object detection bounding boxes on a camera.
   * Format: list of {label, x, y, w, h, conf}
   */
  setBoundingBoxes(cameraId, boxes) {
    this.bboxData[cameraId] = boxes || [];
  }

  /**
   * Set actual feed image from backend
   */
  setFeedImage(cameraId, src) {
    const img = document.getElementById(`feed-cam-${cameraId}`);
    if (img) {
      img.src = src;
    }
  }

  /**
   * Reset feed image to default
   */
  resetFeedImage(cameraId) {
    const img = document.getElementById(`feed-cam-${cameraId}`);
    if (img) {
      img.src = this.images[cameraId];
    }
  }

  loop() {
    requestAnimationFrame(() => this.loop());
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-GB', { hour12: false }) + '.' + String(now.getMilliseconds()).padStart(3, '0').slice(0, 2);

    this.cameras.forEach(id => {
      const canvas = this.canvases[id];
      const ctx = this.ctxs[id];
      if (!canvas || !ctx) return;

      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // Update HTML HUD time tag (avoiding canvas text crispiness issues)
      const timeTag = document.getElementById(`time-cam-${id}`);
      if (timeTag) {
        timeTag.textContent = now.toLocaleDateString() + ' ' + timeStr;
      }

      // Draw active alert pulse overlays
      const alert = this.activeAlerts[id];
      if (alert) {
        // Red flashing screen vignette
        const pulse = Math.abs(Math.sin(Date.now() / 200));
        ctx.fillStyle = alert.severity === 'CRITICAL' 
          ? `rgba(220, 38, 38, ${pulse * 0.15})`
          : `rgba(234, 88, 12, ${pulse * 0.12})`;
        ctx.fillRect(0, 0, w, h);

        // Draw crosshairs
        ctx.strokeStyle = alert.severity === 'CRITICAL' ? 'rgba(220,38,38,0.4)' : 'rgba(234,88,12,0.4)';
        ctx.lineWidth = 1 * window.devicePixelRatio;
        ctx.beginPath();
        ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h);
        ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2);
        ctx.stroke();
      }

      // Draw static/noise simulation lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      ctx.lineWidth = 0.5 * window.devicePixelRatio;
      ctx.beginPath();
      // Scan line
      const scanY = (Date.now() / 20) % h;
      ctx.moveTo(0, scanY); ctx.lineTo(w, scanY);
      ctx.stroke();

      // Bounding boxes
      const boxes = this.bboxData[id];
      if (boxes && boxes.length > 0) {
        boxes.forEach(box => {
          // Normalize coordinates (input coordinates are assumed 640x400)
          const scaleX = w / 640;
          const scaleY = h / 400;

          const bx = box.x * scaleX;
          const by = box.y * scaleY;
          const bw = box.w * scaleX;
          const bh = box.h * scaleY;

          // Box color matching severity
          const color = alert && alert.severity === 'CRITICAL' ? '#dc2626' : '#ea580c';
          
          ctx.strokeStyle = color;
          ctx.lineWidth = 2 * window.devicePixelRatio;
          ctx.strokeRect(bx, by, bw, bh);

          // Box tag
          ctx.fillStyle = color;
          ctx.font = `bold ${10 * window.devicePixelRatio}px 'Space Mono', monospace`;
          const text = `${box.label.toUpperCase()} ${Math.round(box.conf * 100)}%`;
          const textWidth = ctx.measureText(text).width;
          ctx.fillRect(bx, by - 16 * window.devicePixelRatio, textWidth + 8 * window.devicePixelRatio, 16 * window.devicePixelRatio);
          
          ctx.fillStyle = '#ffffff';
          ctx.fillText(text, bx + 4 * window.devicePixelRatio, by - 4 * window.devicePixelRatio);
        });
      }
    });
  }
}

// Instantiate simulator once DOM loaded
document.addEventListener('DOMContentLoaded', () => {
  window.cameraSimulator = new CameraSimulator();
});

/* ============================================
   SILICA — Interactive Script
   ============================================ */

(function() {
  'use strict';

  const scrollContainer = document.getElementById('scroll-container');
  const fpsCount = document.getElementById('fps-count');
  const resolutionEl = document.getElementById('resolution');
  const timerEl = document.getElementById('timer');
  const scrollerCursor = document.getElementById('scroller-cursor');
  const scrollerPins = document.querySelectorAll('.scroll-pins .pin');

  // --- Telemetry ---
  let lastTime = performance.now();
  let frameCount = 0;
  let fps = 0;

  function updateResolution() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    resolutionEl.textContent = `${w}x${h}`;
  }

  function updateFPS() {
    frameCount++;
    const now = performance.now();
    if (now - lastTime >= 1000) {
      fps = Math.round(frameCount * 1000 / (now - lastTime));
      fpsCount.textContent = String(fps).padStart(2, '0') + 'fps';
      frameCount = 0;
      lastTime = now;
    }
    requestAnimationFrame(updateFPS);
  }

  const startTime = performance.now();
  function updateTimer() {
    const elapsed = (performance.now() - startTime) / 1000;
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = Math.floor(elapsed % 60);
    timerEl.textContent = 
      String(hours).padStart(2, '0') + ':' +
      String(minutes).padStart(2, '0') + ':' +
      String(seconds).padStart(2, '0');
    requestAnimationFrame(updateTimer);
  }

  updateResolution();
  window.addEventListener('resize', updateResolution);
  requestAnimationFrame(updateFPS);
  requestAnimationFrame(updateTimer);

  // --- Scroll indicator ---
  function updateScrollIndicator() {
    if (!scrollContainer) return;
    const scrollTop = scrollContainer.scrollTop;
    const scrollHeight = scrollContainer.scrollHeight - scrollContainer.clientHeight;
    const scrollPct = scrollHeight > 0 ? scrollTop / scrollHeight : 0;
    
    if (scrollerCursor) {
      scrollerCursor.style.left = (scrollPct * 100) + '%';
    }
    
    scrollerPins.forEach((pin, i) => {
      setTimeout(() => { pin.style.visibility = 'visible'; }, 1000 + i * 20);
    });
  }

  scrollContainer.addEventListener('scroll', updateScrollIndicator);
  setTimeout(updateScrollIndicator, 500);

  // --- Scroll Reveal Animation ---
  const revealElements = document.querySelectorAll('[data-reveal]');
  
  function checkReveal() {
    const containerRect = scrollContainer.getBoundingClientRect();
    const viewportHeight = containerRect.height;
    const threshold = viewportHeight * 0.85;
    
    revealElements.forEach(el => {
      const rect = el.getBoundingClientRect();
      const relativeTop = rect.top - containerRect.top;
      if (relativeTop < threshold) {
        el.classList.add('revealed');
      }
    });
  }

  scrollContainer.addEventListener('scroll', checkReveal);
  window.addEventListener('resize', checkReveal);
  setTimeout(checkReveal, 300);
  setTimeout(checkReveal, 1000);

  // --- Scroll-driven part labels ---
  const partLabels = document.querySelectorAll('.part-label-item');
  
  function updatePartLabels() {
    const scrollTop = scrollContainer.scrollTop;
    const scrollMax = scrollContainer.scrollHeight - scrollContainer.clientHeight;
    const scrollPct = scrollMax > 0 ? scrollTop / scrollMax : 0;
    
    partLabels.forEach((label, i) => {
      const triggerPct = 0.05 + (i * 0.08);
      if (scrollPct > triggerPct) {
        label.classList.add('visible');
      }
    });
  }

  scrollContainer.addEventListener('scroll', updatePartLabels);

  // --- Interactive Film Layer Exploration ---
  const filmLayerLabels = document.querySelectorAll('.layer-label-item');
  const filmImages = document.querySelectorAll('.film-image');

  filmLayerLabels.forEach(label => {
    const activateLayer = () => {
      const targetLayer = label.getAttribute('data-film-layer');
      filmLayerLabels.forEach(l => l.classList.remove('active'));
      label.classList.add('active');
      filmImages.forEach(img => {
        img.classList.toggle('active', img.getAttribute('data-film-image') === targetLayer);
      });
    };
    label.addEventListener('mouseenter', activateLayer);
    label.addEventListener('click', activateLayer);
    label.addEventListener('touchstart', (e) => { e.preventDefault(); activateLayer(); });
  });

  // --- Animated counters ---
  const metricNums = document.querySelectorAll('.metric-num[data-count]');
  
  function animateCounter(el) {
    const target = parseFloat(el.getAttribute('data-count'));
    const duration = 2000;
    const startTime = performance.now();
    const isDecimal = target % 1 !== 0;
    
    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;
      el.textContent = isDecimal ? current.toFixed(2) : Math.round(current).toLocaleString();
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  const metricCards = document.querySelectorAll('.metric-card');
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const numEl = entry.target.querySelector('.metric-num[data-count]');
        if (numEl && !numEl.dataset.animated) {
          numEl.dataset.animated = 'true';
          animateCounter(numEl);
        }
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3, root: scrollContainer });

  metricCards.forEach(card => counterObserver.observe(card));

  // Set progress bar target widths
  document.querySelectorAll('.metric-bar-fill').forEach(bar => {
    const w = bar.style.width;
    if (w) { bar.style.setProperty('--target-width', w); bar.style.width = '0'; }
  });
  document.querySelectorAll('.progress-fill').forEach(bar => {
    const style = bar.getAttribute('style');
    const match = style && style.match(/width:\s*([\d.]+%)/);
    if (match) { bar.style.setProperty('--target-width', match[1]); bar.style.width = '0'; }
  });

  // ============================================================
  // ============================================================
  //  EXTRAORDINARY 3D SEMICONDUCTOR CHIP ANIMATION
  //  Scroll-driven, canvas-transform-based, guaranteed visible
  // ============================================================
  
  const canvas = document.getElementById('silica-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let W, H, dpr;
    let heroScrollProgress = 0;
    let smoothScrollProgress = 0;

    function resizeCanvas() {
      dpr = window.devicePixelRatio || 1;
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.style.width = W + 'px';
      canvas.style.height = H + 'px';
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function easeInOutCubic(t) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }
    function lerp(a, b, t) { return a + (b - a) * t; }
    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

    // Animation timeline - matches reference camera choreography
    function getTransform(p) {
      let rotX, rotY, rotZ, scale, yShift, perspective;

      if (p < 0.15) {
        const t = p / 0.15, e = easeInOutCubic(t);
        rotX = lerp(-0.08, -0.04, e);
        rotY = lerp(-0.25, -0.12, e);
        rotZ = lerp(0, 0.04, e);
        scale = lerp(0.50, 0.58, e);
        yShift = lerp(0, 10, e);
      } else if (p < 0.35) {
        // Phase 2: SIGNATURE ROLL
        const t = (p - 0.15) / 0.20, e = easeInOutCubic(t);
        rotX = lerp(-0.04, 0.25, e);
        rotY = lerp(-0.12, 0.35, e);
        rotZ = lerp(0.04, 1.1, e);
        scale = lerp(0.58, 0.70, e);
        yShift = lerp(10, 30, e);
      } else if (p < 0.55) {
        // Phase 3: Tilt UP dramatically
        const t = (p - 0.35) / 0.20, e = easeInOutCubic(t);
        rotX = lerp(0.25, 0.8, e);
        rotY = lerp(0.35, 0.15, e);
        rotZ = lerp(1.1, 0.25, e);
        scale = lerp(0.70, 0.82, e);
        yShift = lerp(30, 50, e);
      } else if (p < 0.75) {
        // Phase 4: Rotate around
        const t = (p - 0.55) / 0.20, e = easeInOutCubic(t);
        rotX = lerp(0.8, 0.45, e);
        rotY = lerp(0.15, -0.7, e);
        rotZ = lerp(0.25, -0.15, e);
        scale = lerp(0.82, 0.75, e);
        yShift = lerp(50, 25, e);
      } else {
        // Phase 5: Settle
        const t = (p - 0.75) / 0.25, e = easeInOutCubic(t);
        rotX = lerp(0.45, 0.30, e);
        rotY = lerp(-0.7, -0.45, e);
        rotZ = lerp(-0.15, 0.06, e);
        scale = lerp(0.75, 0.68, e);
        yShift = lerp(25, 5, e);
      }

      return { rotX, rotY, rotZ, scale, yShift };
    }

    function getLayerReveal(p) {
      if (p < 0.35) return 0;
      if (p < 0.65) return easeInOutCubic((p - 0.35) / 0.30) * 0.6;
      if (p < 0.85) return 0.6 - easeInOutCubic((p - 0.65) / 0.20) * 0.35;
      return 0.25 - easeInOutCubic((p - 0.85) / 0.15) * 0.25;
    }

    // Draw the chip using canvas transforms for reliable 3D illusion
    function drawChip() {
      const cx = W / 2;
      const cy = H / 2;
      const tf = getTransform(smoothScrollProgress);
      const layerReveal = getLayerReveal(smoothScrollProgress);
      const baseSize = Math.min(W, H) * 0.32 * tf.scale;
      
      ctx.save();
      ctx.translate(cx, cy + tf.yShift);

      // Ambient glow
      const glowR = baseSize * (1.2 + smoothScrollProgress * 0.4);
      const glowAlpha = 0.18 + smoothScrollProgress * 0.22;
      const glow = ctx.createRadialGradient(0, 0, 0, 0, 0, glowR);
      glow.addColorStop(0, `rgba(191, 109, 21, ${glowAlpha})`);
      glow.addColorStop(0.35, `rgba(191, 109, 21, ${glowAlpha * 0.4})`);
      glow.addColorStop(1, 'rgba(191, 109, 21, 0)');
      ctx.fillStyle = glow;
      ctx.fillRect(-glowR, -glowR, glowR * 2, glowR * 2);

      // Apply 3D-like transforms using matrix
      // Simulate perspective: scale Y based on rotX, skew based on rotY
      const cosX = Math.cos(tf.rotX);
      const sinX = Math.sin(tf.rotX);
      const cosY = Math.cos(tf.rotY);
      const sinY = Math.sin(tf.rotY);
      const cosZ = Math.cos(tf.rotZ);
      const sinZ = Math.sin(tf.rotZ);

      // Combined transform matrix
      const perspective = 0.0015;
      const m11 = cosY * cosZ + sinY * sinX * sinZ;
      const m12 = -cosY * sinZ + sinY * sinX * cosZ;
      const m21 = cosX * sinZ;
      const m22 = cosX * cosZ;

      // Apply Z rotation first, then perspective skew
      ctx.transform(m11, m21 * cosX, m12, m22 * cosX, 0, 0);
      
      // Add horizontal skew for Y-rotation perspective
      const skewX = sinY * 0.35;
      ctx.transform(1, 0, skewX, 1, 0, 0);

      // --- Draw from back to front ---
      const halfW = baseSize;
      const halfH = baseSize;
      const thickness = baseSize * 0.18 * (1 + Math.abs(sinX) * 0.5);

      // --- BOTTOM FACE (substrate underside) ---
      if (sinX < 0) {
        ctx.save();
        ctx.translate(0, -thickness);
        ctx.fillStyle = '#2a3040';
        ctx.strokeStyle = '#3a4050';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.rect(-halfW, -halfH, halfW * 2, halfH * 2);
        ctx.fill();
        ctx.stroke();
        ctx.restore();
      }

      // --- SIDE FACES (exposed edges) ---
      // Right side face
      if (sinY > -0.1) {
        const sideGrad = ctx.createLinearGradient(halfW, 0, halfW + thickness * Math.abs(sinY + 0.3), 0);
        sideGrad.addColorStop(0, '#5a6070');
        sideGrad.addColorStop(0.5, '#8a90a0');
        sideGrad.addColorStop(1, '#4a5060');
        ctx.fillStyle = sideGrad;
        ctx.strokeStyle = '#3a4050';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(halfW, -halfH);
        ctx.lineTo(halfW + thickness * 0.4, -halfH - thickness * 0.3);
        ctx.lineTo(halfW + thickness * 0.4, halfH - thickness * 0.3);
        ctx.lineTo(halfW, halfH);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }

      // Left side face
      if (sinY < 0.1) {
        const sideGrad = ctx.createLinearGradient(-halfW, 0, -halfW - thickness * 0.4, 0);
        sideGrad.addColorStop(0, '#6a7080');
        sideGrad.addColorStop(0.5, '#4a5060');
        sideGrad.addColorStop(1, '#3a4050');
        ctx.fillStyle = sideGrad;
        ctx.strokeStyle = '#2a3040';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(-halfW, -halfH);
        ctx.lineTo(-halfW - thickness * 0.3, -halfH - thickness * 0.2);
        ctx.lineTo(-halfW - thickness * 0.3, halfH - thickness * 0.2);
        ctx.lineTo(-halfW, halfH);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }

      // Bottom edge face (visible when tilting up)
      if (sinX > 0.05) {
        const edgeH = thickness * Math.abs(sinX) * 1.5;
        const edgeGrad = ctx.createLinearGradient(0, halfH, 0, halfH + edgeH);
        edgeGrad.addColorStop(0, '#7a8090');
        edgeGrad.addColorStop(1, '#3a4050');
        ctx.fillStyle = edgeGrad;
        ctx.beginPath();
        ctx.moveTo(-halfW, halfH);
        ctx.lineTo(-halfW + thickness * 0.2, halfH + edgeH);
        ctx.lineTo(halfW + thickness * 0.2, halfH + edgeH);
        ctx.lineTo(halfW, halfH);
        ctx.closePath();
        ctx.fill();
      }

      // --- METAL LAYER STACK (exploded view) ---
      const metalLayerCount = 6;
      const metalColors = [
        '#b87333', '#c88340', '#d89350', 
        '#e0a060', '#e8ad70', '#f0bb80'
      ];
      
      for (let i = 0; i < metalLayerCount; i++) {
        const layerOffset = layerReveal * (i + 1) * 3;
        const layerAlpha = 0.3 + (i / metalLayerCount) * 0.5;
        const layerDepth = -thickness * 0.3 - layerOffset;
        
        ctx.save();
        ctx.translate(0, layerDepth * 0.3);
        
        const layerInset = 2 + i * 0.5;
        ctx.fillStyle = metalColors[i];
        ctx.globalAlpha = layerAlpha;
        ctx.beginPath();
        ctx.rect(-halfW + layerInset, -halfH + layerInset, (halfW - layerInset) * 2, (halfH - layerInset) * 2);
        ctx.fill();
        
        // Routing lines on each metal layer
        ctx.globalAlpha = layerAlpha * 0.8;
        ctx.strokeStyle = i % 2 === 0 ? '#f0c080' : '#d09050';
        ctx.lineWidth = Math.max(0.5, 1.5 - i * 0.15);
        ctx.beginPath();
        const lineCount = 6 + i * 2;
        if (i % 2 === 0) {
          // Horizontal lines
          for (let l = 0; l < lineCount; l++) {
            const y = -halfH + layerInset + ((l + 0.5) / lineCount) * (halfH * 2 - layerInset * 2);
            const segs = 3 + Math.floor(Math.sin(l * 1.5 + i) * 1.5 + 1.5);
            for (let s = 0; s < segs; s++) {
              const x1 = -halfW + layerInset + (s / segs) * (halfW * 2 - layerInset * 2) + 3;
              const x2 = -halfW + layerInset + ((s + 1) / segs) * (halfW * 2 - layerInset * 2) - 3;
              ctx.moveTo(x1, y);
              ctx.lineTo(x2, y);
            }
          }
        } else {
          // Vertical lines
          for (let l = 0; l < lineCount; l++) {
            const x = -halfW + layerInset + ((l + 0.5) / lineCount) * (halfW * 2 - layerInset * 2);
            const segs = 3 + Math.floor(Math.cos(l * 1.3 + i * 0.7) * 1.5 + 1.5);
            for (let s = 0; s < segs; s++) {
              const y1 = -halfH + layerInset + (s / segs) * (halfH * 2 - layerInset * 2) + 3;
              const y2 = -halfH + layerInset + ((s + 1) / segs) * (halfH * 2 - layerInset * 2) - 3;
              ctx.moveTo(x, y1);
              ctx.lineTo(x, y2);
            }
          }
        }
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.restore();
      }

      // --- TOP SURFACE (silicon die with transistors) ---
      ctx.save();
      
      // Base silicon
      const siliconGrad = ctx.createLinearGradient(-halfW, -halfH, halfW, halfH);
      siliconGrad.addColorStop(0, '#4a5265');
      siliconGrad.addColorStop(0.5, '#5a6275');
      siliconGrad.addColorStop(1, '#3a4255');
      ctx.fillStyle = siliconGrad;
      ctx.beginPath();
      ctx.rect(-halfW, -halfH, halfW * 2, halfH * 2);
      ctx.fill();

      // Metallic edge highlight
      ctx.strokeStyle = '#a0a8b8';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.strokeStyle = 'rgba(191, 109, 21, 0.5)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Transistor grid pattern
      const gridCols = 20, gridRows = 20;
      const cellW = (halfW * 2) / gridCols;
      const cellH = (halfH * 2) / gridRows;
      
      for (let r = 0; r < gridRows; r++) {
        for (let c = 0; c < gridCols; c++) {
          const seed = Math.sin(r * 12.9898 + c * 78.233) * 43758.5453;
          const rand = seed - Math.floor(seed);
          if (rand < 0.25) continue;
          
          const x = -halfW + c * cellW + cellW * 0.1;
          const y = -halfH + r * cellH + cellH * 0.1;
          const cw = cellW * 0.8;
          const ch = cellH * 0.8;
          
          if (rand > 0.75) {
            // Functional block - larger
            ctx.fillStyle = `rgba(191, 109, 21, ${0.25 + rand * 0.15})`;
            ctx.fillRect(x, y, cw, ch);
            ctx.strokeStyle = `rgba(191, 109, 21, ${0.3 + rand * 0.2})`;
            ctx.lineWidth = 0.5;
            ctx.strokeRect(x, y, cw, ch);
          } else if (rand > 0.5) {
            // Gate / standard cell
            ctx.fillStyle = `rgba(200, 150, 80, ${0.2 + rand * 0.2})`;
            ctx.fillRect(x + cw * 0.2, y, cw * 0.6, ch);
          }
        }
      }

      // Functional blocks (CPU cores, caches)
      const blocks = [
        { x: -halfW * 0.65, y: -halfH * 0.65, w: halfW * 0.5, h: halfH * 0.5, type: 'core' },
        { x: halfW * 0.15, y: -halfH * 0.65, w: halfW * 0.5, h: halfH * 0.5, type: 'core' },
        { x: -halfW * 0.65, y: halfH * 0.15, w: halfW * 0.5, h: halfH * 0.5, type: 'cache' },
        { x: halfW * 0.15, y: halfH * 0.15, w: halfW * 0.5, h: halfH * 0.5, type: 'cache' },
      ];

      blocks.forEach(block => {
        if (block.type === 'core') {
          ctx.fillStyle = 'rgba(191, 109, 21, 0.35)';
          ctx.strokeStyle = 'rgba(191, 109, 21, 0.7)';
        } else {
          ctx.fillStyle = 'rgba(150, 155, 170, 0.2)';
          ctx.strokeStyle = 'rgba(180, 185, 200, 0.4)';
        }
        ctx.lineWidth = 1;
        ctx.fillRect(block.x, block.y, block.w, block.h);
        ctx.strokeRect(block.x, block.y, block.w, block.h);
        
        // Internal grid
        ctx.strokeStyle = block.type === 'core' 
          ? 'rgba(191, 109, 21, 0.2)' 
          : 'rgba(150, 155, 170, 0.15)';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        for (let i = 1; i < 4; i++) {
          const f = i / 4;
          ctx.moveTo(block.x + block.w * f, block.y);
          ctx.lineTo(block.x + block.w * f, block.y + block.h);
          ctx.moveTo(block.x, block.y + block.h * f);
          ctx.lineTo(block.x + block.w, block.y + block.h * f);
        }
        ctx.stroke();
      });

      // Seal ring (dashed near edge)
      ctx.strokeStyle = 'rgba(191, 109, 21, 0.5)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(-halfW + 6, -halfH + 6, halfW * 2 - 12, halfH * 2 - 12);
      ctx.setLineDash([]);

      ctx.restore();

      // --- I/O PINS around perimeter ---
      const pinCount = 24;
      const pinLen = baseSize * 0.08;
      const pinInset = baseSize * 0.04;
      
      ctx.strokeStyle = '#d4a857';
      ctx.fillStyle = '#f0c878';
      ctx.lineWidth = Math.max(1, baseSize * 0.008);
      ctx.lineCap = 'round';

      for (let i = 0; i < pinCount; i++) {
        const f = (i + 0.5) / pinCount;
        const pos = -halfW + pinInset + f * (halfW * 2 - pinInset * 2);
        
        // Top pins
        ctx.beginPath();
        ctx.moveTo(pos, -halfH);
        ctx.lineTo(pos + pinLen * 0.2, -halfH - pinLen);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(pos + pinLen * 0.2, -halfH - pinLen, Math.max(1, baseSize * 0.006), 0, Math.PI * 2);
        ctx.fill();
        
        // Bottom pins
        ctx.beginPath();
        ctx.moveTo(pos, halfH);
        ctx.lineTo(pos + pinLen * 0.2, halfH + pinLen);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(pos + pinLen * 0.2, halfH + pinLen, Math.max(1, baseSize * 0.006), 0, Math.PI * 2);
        ctx.fill();
        
        // Left pins
        ctx.beginPath();
        ctx.moveTo(-halfW, pos);
        ctx.lineTo(-halfW - pinLen, pos + pinLen * 0.1);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(-halfW - pinLen, pos + pinLen * 0.1, Math.max(1, baseSize * 0.006), 0, Math.PI * 2);
        ctx.fill();
        
        // Right pins
        ctx.beginPath();
        ctx.moveTo(halfW, pos);
        ctx.lineTo(halfW + pinLen, pos + pinLen * 0.1);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(halfW + pinLen, pos + pinLen * 0.1, Math.max(1, baseSize * 0.006), 0, Math.PI * 2);
        ctx.fill();
      }

      // --- Wireframe outline on top ---
      ctx.strokeStyle = `rgba(191, 109, 21, ${0.4 + smoothScrollProgress * 0.4})`;
      ctx.lineWidth = 1.2;
      ctx.strokeRect(-halfW, -halfH, halfW * 2, halfH * 2);
      
      // Corner dots
      ctx.fillStyle = `rgba(220, 180, 120, ${0.6 + smoothScrollProgress * 0.3})`;
      [[-halfW, -halfH], [halfW, -halfH], [halfW, halfH], [-halfW, halfH]].forEach(([x, y]) => {
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, Math.PI * 2);
        ctx.fill();
      });

      ctx.restore();

      // --- Crosshair bracket overlay ---
      ctx.save();
      ctx.translate(cx, cy + tf.yShift);
      const bracketSize = (50 + smoothScrollProgress * 70) * Math.min(W, H) / 800;
      const b = bracketSize / 2;
      const bl = bracketSize * 0.2;
      const alpha = 0.12 + smoothScrollProgress * 0.1;
      ctx.strokeStyle = `rgba(191, 109, 21, ${alpha})`;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(-b, -b + bl); ctx.lineTo(-b, -b); ctx.lineTo(-b + bl, -b);
      ctx.moveTo(b - bl, -b); ctx.lineTo(b, -b); ctx.lineTo(b, -b + bl);
      ctx.moveTo(-b, b - bl); ctx.lineTo(-b, b); ctx.lineTo(-b + bl, b);
      ctx.moveTo(b - bl, b); ctx.lineTo(b, b); ctx.lineTo(b, b - bl);
      ctx.stroke();
      ctx.restore();
    }

    function renderBackground() {
      const grad = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, Math.max(W, H) * 0.7);
      grad.addColorStop(0, 'rgba(30, 30, 30, 1)');
      grad.addColorStop(1, 'rgba(14, 14, 14, 1)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);
    }

    function render() {
      const scrollTop = scrollContainer.scrollTop;
      const heroHeight = window.innerHeight * 7;
      heroScrollProgress = clamp(scrollTop / heroHeight, 0, 1);
      smoothScrollProgress += (heroScrollProgress - smoothScrollProgress) * 0.08;

      ctx.clearRect(0, 0, W, H);
      renderBackground();
      drawChip();

      requestAnimationFrame(render);
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    requestAnimationFrame(render);
  }
  // --- Smooth scroll for anchor links ---
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target && scrollContainer) {
        e.preventDefault();
        scrollContainer.scrollTo({ top: target.offsetTop, behavior: 'smooth' });
      }
    });
  });

  // --- Initial triggers ---
  setTimeout(() => {
    checkReveal();
    updatePartLabels();
    updateScrollIndicator();
  }, 200);

})();

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
  // ============================================================
  //  SEMICONDUCTOR CHIP ANIMATION
  //  Scroll-driven, canvas-based, white/silver metallic chip
  // ============================================================
  
  const chipCanvas = document.getElementById('chip-canvas');
  if (chipCanvas) {
    const chipCtx = chipCanvas.getContext('2d');
    let cw, ch, cdpr;
    let targetScroll = 0;
    let currentScroll = 0;
    let animFrame = 0;

    function resizeChipCanvas() {
      cdpr = Math.min(window.devicePixelRatio || 1, 2);
      const container = chipCanvas.parentElement;
      cw = container.clientWidth || window.innerWidth;
      ch = container.clientHeight || window.innerHeight;
      chipCanvas.width = cw * cdpr;
      chipCanvas.height = ch * cdpr;
      chipCanvas.style.width = cw + 'px';
      chipCanvas.style.height = ch + 'px';
      chipCtx.setTransform(cdpr, 0, 0, cdpr, 0, 0);
    }

    // Easing helpers
    function easeInOut(t) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }
    function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
    function lerp(a, b, t) { return a + (b - a) * t; }
    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

    // Get scroll progress through hero section (0 to 1)
    function getHeroScrollProgress() {
      const scrollTop = scrollContainer.scrollTop;
      const heroStart = 0;
      const heroHeight = window.innerHeight * 7; // 700vh
      const progress = (scrollTop - heroStart) / heroHeight;
      return clamp(progress, 0, 1);
    }

    // Get animation parameters from scroll progress
    function getAnimParams(p) {
      // Phase A: 0.00 - 0.15 → Reveal
      // Phase B: 0.15 - 0.40 → Rotation
      // Phase C: 0.40 - 0.65 → Circuit illumination
      // Phase D: 0.65 - 0.85 → Perspective transition
      // Phase E: 0.85 - 1.00 → Settle

      let rotY, rotX, scale, glowIntensity, circuitAlpha, revealAlpha;

      if (p < 0.15) {
        const t = easeOut(p / 0.15);
        rotY = lerp(-0.6, -0.4, t);
        rotX = lerp(0.25, 0.20, t);
        scale = lerp(0.55, 0.85, t);
        glowIntensity = lerp(0, 0.3, t);
        circuitAlpha = 0;
        revealAlpha = lerp(0, 1, t);
      } else if (p < 0.40) {
        const t = easeInOut((p - 0.15) / 0.25);
        rotY = lerp(-0.4, 0.5, t);
        rotX = lerp(0.20, 0.30, t);
        scale = lerp(0.85, 0.95, t);
        glowIntensity = lerp(0.3, 0.5, t);
        circuitAlpha = lerp(0, 0.15, t);
        revealAlpha = 1;
      } else if (p < 0.65) {
        const t = easeInOut((p - 0.40) / 0.25);
        rotY = lerp(0.5, 0.8, t);
        rotX = lerp(0.30, 0.15, t);
        scale = lerp(0.95, 1.0, t);
        glowIntensity = lerp(0.5, 0.7, t);
        circuitAlpha = lerp(0.15, 0.6, t);
        revealAlpha = 1;
      } else if (p < 0.85) {
        const t = easeInOut((p - 0.65) / 0.20);
        rotY = lerp(0.8, 0.3, t);
        rotX = lerp(0.15, 0.45, t);
        scale = lerp(1.0, 0.92, t);
        glowIntensity = lerp(0.7, 0.55, t);
        circuitAlpha = lerp(0.6, 0.4, t);
        revealAlpha = 1;
      } else {
        const t = easeInOut((p - 0.85) / 0.15);
        rotY = lerp(0.3, -0.2, t);
        rotX = lerp(0.45, 0.28, t);
        scale = lerp(0.92, 0.88, t);
        glowIntensity = lerp(0.55, 0.35, t);
        circuitAlpha = lerp(0.4, 0.2, t);
        revealAlpha = 1;
      }

      return { rotY, rotX, scale, glowIntensity, circuitAlpha, revealAlpha };
    }

    // Draw the semiconductor chip
    function drawSemiconductorChip(params) {
      const cx = cw / 2;
      const cy = ch / 2;
      const baseSize = Math.min(cw, ch) * 0.22 * params.scale;
      
      chipCtx.save();
      chipCtx.translate(cx, cy);
      chipCtx.globalAlpha = params.revealAlpha;

      // Ambient glow behind chip
      if (params.glowIntensity > 0) {
        const glowR = baseSize * 2.2;
        const glow = chipCtx.createRadialGradient(0, 0, 0, 0, 0, glowR);
        glow.addColorStop(0, `rgba(180, 180, 190, ${params.glowIntensity * 0.15})`);
        glow.addColorStop(0.4, `rgba(120, 120, 140, ${params.glowIntensity * 0.06})`);
        glow.addColorStop(1, 'rgba(0, 0, 0, 0)');
        chipCtx.fillStyle = glow;
        chipCtx.fillRect(-glowR, -glowR, glowR * 2, glowR * 2);
      }

      // Apply 3D perspective transform
      const cosY = Math.cos(params.rotY);
      const sinY = Math.sin(params.rotY);
      const cosX = Math.cos(params.rotX);
      const sinX = Math.sin(params.rotX);
      
      // Build transform matrix: rotate Y, then rotate X
      // m11 = cosY, m12 = sinX * sinY, m21 = 0, m22 = cosX
      const m11 = cosY;
      const m12 = sinX * sinY;
      const m21 = 0;
      const m22 = cosX;
      
      chipCtx.transform(m11, m21, m12, m22, 0, 0);

      // Horizontal skew for perspective depth effect
      const skew = sinY * 0.25;
      chipCtx.transform(1, 0, skew, 1, 0, 0);

      // ==========================================
      // DRAW CHIP — layered from back to front
      // ==========================================
      
      const dieW = baseSize * 1.5;
      const dieH = baseSize * 1.5;
      const packageMargin = baseSize * 0.18;
      const pkgW = dieW + packageMargin * 2;
      const pkgH = dieH + packageMargin * 2;
      const thickness = baseSize * 0.35 * Math.abs(sinY) + baseSize * 0.08;

      // --- Substrate / Package bottom (visible when rotated) ---
      if (Math.abs(sinY) > 0.05) {
        chipCtx.save();
        chipCtx.translate(thickness * 0.5 * Math.sign(sinY), thickness * 0.3);
        
        // Package body
        const pkgGrad = chipCtx.createLinearGradient(-pkgW/2, 0, pkgW/2, 0);
        pkgGrad.addColorStop(0, '#1a1a1a');
        pkgGrad.addColorStop(0.5, '#2a2a2a');
        pkgGrad.addColorStop(1, '#1a1a1a');
        chipCtx.fillStyle = pkgGrad;
        chipCtx.strokeStyle = '#0a0a0a';
        chipCtx.lineWidth = 1;
        chipCtx.beginPath();
        const r = baseSize * 0.06, rx = -pkgW/2, ry = -pkgH/2;
        chipCtx.moveTo(rx + r, ry);
        chipCtx.lineTo(rx + pkgW - r, ry);
        chipCtx.quadraticCurveTo(rx + pkgW, ry, rx + pkgW, ry + r);
        chipCtx.lineTo(rx + pkgW, ry + pkgH - r);
        chipCtx.quadraticCurveTo(rx + pkgW, ry + pkgH, rx + pkgW - r, ry + pkgH);
        chipCtx.lineTo(rx + r, ry + pkgH);
        chipCtx.quadraticCurveTo(rx, ry + pkgH, rx, ry + pkgH - r);
        chipCtx.lineTo(rx, ry + r);
        chipCtx.quadraticCurveTo(rx, ry, rx + r, ry);
        chipCtx.closePath();
        chipCtx.fill();
        chipCtx.stroke();

        // Package marker dots
        chipCtx.fillStyle = '#0a0a0a';
        for (let i = 0; i < 3; i++) {
          chipCtx.beginPath();
          chipCtx.arc(-pkgW/2 + baseSize * 0.08 + i * baseSize * 0.06, 
                     -pkgH/2 + baseSize * 0.08, baseSize * 0.012, 0, Math.PI * 2);
          chipCtx.fill();
        }
        
        chipCtx.restore();
      }

      // --- Die substrate (dark silicon) ---
      chipCtx.save();
      
      // Shadow under die
      chipCtx.shadowColor = 'rgba(0, 0, 0, 0.5)';
      chipCtx.shadowBlur = baseSize * 0.08;
      chipCtx.shadowOffsetY = baseSize * 0.02;

      // Silicon die base
      const dieGrad = chipCtx.createLinearGradient(-dieW/2, -dieH/2, dieW/2, dieH/2);
      dieGrad.addColorStop(0, '#2a2d35');
      dieGrad.addColorStop(0.4, '#3a3d45');
      dieGrad.addColorStop(0.7, '#32353d');
      dieGrad.addColorStop(1, '#252830');
      
      chipCtx.fillStyle = dieGrad;
      chipCtx.strokeStyle = '#4a4d55';
      chipCtx.lineWidth = 1.2;
      chipCtx.beginPath();
      chipCtx.rect(-dieW/2, -dieH/2, dieW, dieH);
      chipCtx.fill();
      chipCtx.stroke();

      chipCtx.shadowColor = 'transparent';

      // --- Die edge bevel highlight ---
      chipCtx.strokeStyle = 'rgba(200, 200, 210, 0.15)';
      chipCtx.lineWidth = 0.8;
      chipCtx.strokeRect(-dieW/2 + 2, -dieH/2 + 2, dieW - 4, dieH - 4);

      // --- Scribe lines (dicing marks) ---
      chipCtx.strokeStyle = 'rgba(150, 150, 160, 0.08)';
      chipCtx.lineWidth = 0.5;
      chipCtx.setLineDash([3, 3]);
      chipCtx.beginPath();
      chipCtx.moveTo(-dieW/2, -dieH/2 + dieH * 0.5);
      chipCtx.lineTo(dieW/2, -dieH/2 + dieH * 0.5);
      chipCtx.moveTo(-dieW/2 + dieW * 0.5, -dieH/2);
      chipCtx.lineTo(-dieW/2 + dieW * 0.5, dieH/2);
      chipCtx.stroke();
      chipCtx.setLineDash([]);

      // --- Seal ring ---
      const sealInset = baseSize * 0.04;
      chipCtx.strokeStyle = 'rgba(180, 160, 120, 0.35)';
      chipCtx.lineWidth = 1;
      chipCtx.setLineDash([4, 2]);
      chipCtx.strokeRect(-dieW/2 + sealInset, -dieH/2 + sealInset, 
                          dieW - sealInset * 2, dieH - sealInset * 2);
      chipCtx.setLineDash([]);

      // --- Power grid (horizontal + vertical lines) ---
      const gridAlpha = 0.12 + params.circuitAlpha * 0.2;
      chipCtx.strokeStyle = `rgba(190, 170, 130, ${gridAlpha})`;
      chipCtx.lineWidth = 0.6;
      chipCtx.beginPath();
      const gridLines = 8;
      for (let i = 1; i < gridLines; i++) {
        const f = i / gridLines;
        // Horizontal
        chipCtx.moveTo(-dieW/2 + sealInset * 2, -dieH/2 + f * dieH);
        chipCtx.lineTo(dieW/2 - sealInset * 2, -dieH/2 + f * dieH);
        // Vertical
        chipCtx.moveTo(-dieW/2 + f * dieW, -dieH/2 + sealInset * 2);
        chipCtx.lineTo(-dieW/2 + f * dieW, dieH/2 - sealInset * 2);
      }
      chipCtx.stroke();

      // --- Functional blocks (CPU cores, caches) ---
      const blocks = [
        { x: -dieW * 0.32, y: -dieH * 0.32, w: dieW * 0.28, h: dieH * 0.28, type: 'core', label: 'CORE 0' },
        { x:  dieW * 0.04, y: -dieH * 0.32, w: dieW * 0.28, h: dieH * 0.28, type: 'core', label: 'CORE 1' },
        { x: -dieW * 0.32, y:  dieH * 0.04, w: dieW * 0.28, h: dieH * 0.28, type: 'cache', label: 'L2$' },
        { x:  dieW * 0.04, y:  dieH * 0.04, w: dieW * 0.28, h: dieH * 0.28, type: 'cache', label: 'L2$' },
      ];

      blocks.forEach(block => {
        // Block background
        if (block.type === 'core') {
          chipCtx.fillStyle = 'rgba(180, 180, 190, 0.08)';
          chipCtx.strokeStyle = 'rgba(200, 200, 210, 0.2)';
        } else {
          chipCtx.fillStyle = 'rgba(160, 160, 175, 0.05)';
          chipCtx.strokeStyle = 'rgba(170, 170, 185, 0.12)';
        }
        chipCtx.lineWidth = 0.8;
        chipCtx.fillRect(block.x, block.y, block.w, block.h);
        chipCtx.strokeRect(block.x, block.y, block.w, block.h);

        // Internal grid in blocks
        chipCtx.strokeStyle = `rgba(190, 170, 130, ${0.08 + params.circuitAlpha * 0.15})`;
        chipCtx.lineWidth = 0.4;
        chipCtx.beginPath();
        const subGrid = 4;
        for (let i = 1; i < subGrid; i++) {
          const f = i / subGrid;
          chipCtx.moveTo(block.x + block.w * f, block.y);
          chipCtx.lineTo(block.x + block.w * f, block.y + block.h);
          chipCtx.moveTo(block.x, block.y + block.h * f);
          chipCtx.lineTo(block.x + block.w, block.y + block.h * f);
        }
        chipCtx.stroke();
      });

      // --- Peripheral / I/O ring area ---
      const ioWidth = dieW * 0.12;
      chipCtx.fillStyle = 'rgba(140, 140, 155, 0.04)';
      // Top IO strip
      chipCtx.fillRect(-dieW/2, -dieH/2, dieW, ioWidth);
      // Bottom IO strip
      chipCtx.fillRect(-dieW/2, dieH/2 - ioWidth, dieW, ioWidth);
      // Left IO strip
      chipCtx.fillRect(-dieW/2, -dieH/2, ioWidth, dieH);
      // Right IO strip
      chipCtx.fillRect(dieW/2 - ioWidth, -dieH/2, ioWidth, dieH);

      // --- Luminous circuit traces (Phase C) ---
      if (params.circuitAlpha > 0.02) {
        const alpha = params.circuitAlpha;
        
        // Main horizontal bus
        chipCtx.strokeStyle = `rgba(220, 200, 160, ${alpha * 0.8})`;
        chipCtx.lineWidth = 1.2;
        chipCtx.shadowColor = 'rgba(220, 180, 120, 0.5)';
        chipCtx.shadowBlur = baseSize * 0.03;
        chipCtx.beginPath();
        chipCtx.moveTo(-dieW * 0.45, 0);
        chipCtx.lineTo(dieW * 0.45, 0);
        chipCtx.stroke();

        // Vertical spines
        chipCtx.strokeStyle = `rgba(200, 180, 140, ${alpha * 0.6})`;
        chipCtx.lineWidth = 0.8;
        for (let s = -2; s <= 2; s++) {
          chipCtx.beginPath();
          chipCtx.moveTo(s * dieW * 0.18, -dieH * 0.42);
          chipCtx.lineTo(s * dieW * 0.18, dieH * 0.42);
          chipCtx.stroke();
        }

        // Connection stubs to cores
        chipCtx.strokeStyle = `rgba(230, 210, 170, ${alpha * 0.7})`;
        chipCtx.lineWidth = 0.6;
        blocks.forEach(block => {
          // Top connection
          chipCtx.beginPath();
          chipCtx.moveTo(block.x + block.w * 0.5, block.y);
          chipCtx.lineTo(block.x + block.w * 0.5, -dieH * 0.42);
          chipCtx.stroke();
          // Left connection
          chipCtx.beginPath();
          chipCtx.moveTo(block.x, block.y + block.h * 0.5);
          chipCtx.lineTo(-dieW * 0.45, block.y + block.h * 0.5);
          chipCtx.stroke();
        });

        chipCtx.shadowBlur = 0;

        // Bright signal nodes
        const nodeAlpha = alpha * 0.9;
        chipCtx.fillStyle = `rgba(255, 240, 200, ${nodeAlpha})`;
        chipCtx.shadowColor = 'rgba(255, 220, 150, 0.8)';
        chipCtx.shadowBlur = baseSize * 0.04;
        const nodeCount = Math.floor(6 + alpha * 10);
        for (let n = 0; n < nodeCount; n++) {
          const seed = Math.sin(n * 12.9898) * 43758.5453;
          const fr = seed - Math.floor(seed);
          const seed2 = Math.cos(n * 78.233) * 43758.5453;
          const fr2 = seed2 - Math.floor(seed2);
          const nx = lerp(-dieW * 0.42, dieW * 0.42, fr);
          const ny = lerp(-dieH * 0.42, dieH * 0.42, fr2);
          const pulse = 0.5 + 0.5 * Math.sin(animFrame * 0.03 + n * 1.5);
          chipCtx.globalAlpha = revealAlpha * nodeAlpha * (0.4 + pulse * 0.6);
          chipCtx.beginPath();
          chipCtx.arc(nx, ny, baseSize * 0.012, 0, Math.PI * 2);
          chipCtx.fill();
        }
        chipCtx.globalAlpha = revealAlpha;
        chipCtx.shadowBlur = 0;
      }

      // --- Bond pads around die perimeter ---
      chipCtx.fillStyle = 'rgba(210, 190, 150, 0.4)';
      chipCtx.strokeStyle = 'rgba(150, 130, 90, 0.3)';
      chipCtx.lineWidth = 0.4;
      const padCount = 14;
      const padSize = baseSize * 0.025;
      const padInset = baseSize * 0.015;
      for (let i = 0; i < padCount; i++) {
        const f = (i + 0.5) / padCount;
        // Top
        chipCtx.fillRect(-dieW/2 + padInset + f * (dieW - padInset * 2) - padSize/2, 
                        -dieH/2 + padInset, padSize, padSize * 0.6);
        // Bottom
        chipCtx.fillRect(-dieW/2 + padInset + f * (dieW - padInset * 2) - padSize/2, 
                        dieH/2 - padInset - padSize * 0.6, padSize, padSize * 0.6);
        // Left
        chipCtx.fillRect(-dieW/2 + padInset, 
                        -dieH/2 + padInset + f * (dieH - padInset * 2) - padSize/2, 
                        padSize * 0.6, padSize);
        // Right
        chipCtx.fillRect(dieW/2 - padInset - padSize * 0.6, 
                        -dieH/2 + padInset + f * (dieH - padInset * 2) - padSize/2, 
                        padSize * 0.6, padSize);
      }

      // --- Die corner fiducial marks ---
      chipCtx.strokeStyle = 'rgba(200, 200, 210, 0.25)';
      chipCtx.lineWidth = 0.8;
      const fidSize = baseSize * 0.04;
      const fidInset = baseSize * 0.06;
      [[-1,-1],[1,-1],[1,1],[-1,1]].forEach(([sx, sy]) => {
        chipCtx.beginPath();
        chipCtx.moveTo(sx * (dieW/2 - fidInset), sy * (dieH/2 - fidInset));
        chipCtx.lineTo(sx * (dieW/2 - fidInset - fidSize), sy * (dieH/2 - fidInset));
        chipCtx.moveTo(sx * (dieW/2 - fidInset), sy * (dieH/2 - fidInset));
        chipCtx.lineTo(sx * (dieW/2 - fidInset), sy * (dieH/2 - fidInset - fidSize));
        chipCtx.stroke();
      });

      chipCtx.restore(); // End of die drawing

      // --- Package pins (visible on sides when rotated) ---
      if (Math.abs(sinY) > 0.1) {
        const pinCount = 16;
        const pinLen = baseSize * 0.12 * Math.abs(sinY);
        const pinSpacing = pkgH / (pinCount + 1);
        const pinDir = Math.sign(sinY);
        
        chipCtx.strokeStyle = 'rgba(180, 180, 190, 0.6)';
        chipCtx.fillStyle = 'rgba(200, 200, 210, 0.7)';
        chipCtx.lineWidth = 1;
        
        for (let i = 0; i < pinCount; i++) {
          const py = -pkgH/2 + (i + 1) * pinSpacing;
          // Left side pins
          chipCtx.beginPath();
          chipCtx.moveTo(-pkgW/2, py);
          chipCtx.lineTo(-pkgW/2 - pinLen, py - pinLen * 0.2);
          chipCtx.stroke();
          // Pin tip
          chipCtx.beginPath();
          chipCtx.arc(-pkgW/2 - pinLen, py - pinLen * 0.2, baseSize * 0.012, 0, Math.PI * 2);
          chipCtx.fill();
          
          // Right side pins
          chipCtx.beginPath();
          chipCtx.moveTo(pkgW/2, py);
          chipCtx.lineTo(pkgW/2 + pinLen, py - pinLen * 0.2);
          chipCtx.stroke();
          chipCtx.beginPath();
          chipCtx.arc(pkgW/2 + pinLen, py - pinLen * 0.2, baseSize * 0.012, 0, Math.PI * 2);
          chipCtx.fill();
        }
      }

      // --- Specular highlight ---
      chipCtx.save();
      chipCtx.globalAlpha = 0.08 * params.revealAlpha;
      const highlight = chipCtx.createRadialGradient(
        -dieW * 0.25, -dieH * 0.3, 0,
        -dieW * 0.25, -dieH * 0.3, dieW * 0.6
      );
      highlight.addColorStop(0, 'rgba(255, 255, 255, 1)');
      highlight.addColorStop(1, 'rgba(255, 255, 255, 0)');
      chipCtx.fillStyle = highlight;
      chipCtx.fillRect(-dieW, -dieH, dieW * 2, dieH * 2);
      chipCtx.restore();

      chipCtx.restore(); // End of main transform
    }

    // Main render loop
    function renderChipAnimation() {
      animFrame++;
      
      // Smooth scroll interpolation
      targetScroll = getHeroScrollProgress();
      currentScroll += (targetScroll - currentScroll) * 0.08;
      
      const params = getAnimParams(currentScroll);
      
      chipCtx.clearRect(0, 0, cw, ch);
      drawSemiconductorChip(params);
      
      requestAnimationFrame(renderChipAnimation);
    }

    // Respect reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    resizeChipCanvas();
    window.addEventListener('resize', resizeChipCanvas);
    
    if (!prefersReducedMotion) {
      requestAnimationFrame(renderChipAnimation);
    } else {
      // Static frame for reduced motion
      currentScroll = 0.3;
      const params = getAnimParams(currentScroll);
      chipCtx.clearRect(0, 0, cw, ch);
      drawSemiconductorChip(params);
    }
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

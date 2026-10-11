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
  // ============================================================
  //  GLASS SEMICONDUCTOR CHIP ANIMATION
  //  Time-based floating, glass material, pink/coral illumination
  // ============================================================
  
  const chipCanvas = document.getElementById('chip-canvas');
  if (chipCanvas) {
    const chipCtx = chipCanvas.getContext('2d');
    let cw, ch, cdpr;
    let animTime = 0;
    let lastFrameTime = performance.now();
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function resizeChipCanvas() {
      cdpr = Math.min(window.devicePixelRatio || 1, 2);
      cw = window.innerWidth;
      ch = window.innerHeight;
      chipCanvas.style.width = cw + 'px';
      chipCanvas.style.height = ch + 'px';
      chipCanvas.width = cw * cdpr;
      chipCanvas.height = ch * cdpr;
      chipCtx.setTransform(cdpr, 0, 0, cdpr, 0, 0);
    }

    // --- Particle System ---
    class Particle {
      constructor() { this.reset(true); }
      reset(initial = false) {
        this.x = Math.random() * cw;
        this.y = Math.random() * ch;
        this.size = Math.random() * 1.5 + 0.3;
        this.baseAlpha = Math.random() * 0.4 + 0.1;
        this.alpha = this.baseAlpha;
        this.speedX = (Math.random() - 0.5) * 0.15;
        this.speedY = (Math.random() - 0.5) * 0.1 - 0.05;
        this.pulseSpeed = Math.random() * 0.02 + 0.005;
        this.pulseOffset = Math.random() * Math.PI * 2;
        this.tint = Math.random() > 0.85 ? 'pink' : 'white';
      }
      update(dt) {
        this.x += this.speedX * dt;
        this.y += this.speedY * dt;
        this.alpha = this.baseAlpha * (0.6 + 0.4 * Math.sin(animTime * this.pulseSpeed + this.pulseOffset));
        if (this.x < -10) this.x = cw + 10;
        if (this.x > cw + 10) this.x = -10;
        if (this.y < -10) this.y = ch + 10;
        if (this.y > ch + 10) this.y = -10;
      }
      draw() {
        chipCtx.beginPath();
        chipCtx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        if (this.tint === 'pink') {
          chipCtx.fillStyle = `rgba(245, 198, 208, ${this.alpha * 0.8})`;
        } else {
          chipCtx.fillStyle = `rgba(255, 245, 240, ${this.alpha})`;
        }
        chipCtx.fill();
      }
    }

    const particleCount = Math.min(120, Math.floor((cw * ch) / 15000));
    const particles = [];
    for (let i = 0; i < particleCount; i++) particles.push(new Particle());

    // --- Drawing helpers ---
    function lerp(a, b, t) { return a + (b - a) * t; }

    // Draw glass chip with all layers
    function drawGlassChip(cx, cy, baseSize, rotY, rotX, floatY) {
      chipCtx.save();
      chipCtx.translate(cx, cy + floatY);
      
      // 3D perspective transform
      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);
      
      const m11 = cosY;
      const m12 = sinX * sinY * 0.4;
      const m21 = 0;
      const m22 = cosX;
      
      chipCtx.transform(m11, m21, m12, m22, 0, 0);
      chipCtx.transform(1, 0, sinY * 0.15, 1, 0, 0);

      const scaleX = 0.85 + Math.abs(sinY) * 0.15;
      const chipW = baseSize * 1.4 * scaleX;
      const chipH = baseSize * 1.4;
      const hw = chipW / 2;
      const hh = chipH / 2;
      const edgeDepth = baseSize * 0.12 * Math.abs(sinY) + baseSize * 0.04;

      // --- Outer glow / aura ---
      const auraR = baseSize * 1.6;
      const aura = chipCtx.createRadialGradient(0, 0, 0, 0, 0, auraR);
      aura.addColorStop(0, 'rgba(232, 138, 154, 0.12)');
      aura.addColorStop(0.3, 'rgba(245, 198, 208, 0.05)');
      aura.addColorStop(1, 'rgba(232, 138, 154, 0)');
      chipCtx.fillStyle = aura;
      chipCtx.fillRect(-auraR, -auraR, auraR * 2, auraR * 2);

      // --- Package shadow ---
      chipCtx.save();
      chipCtx.translate(edgeDepth * 0.3, edgeDepth * 0.5);
      chipCtx.fillStyle = 'rgba(0, 0, 0, 0.35)';
      chipCtx.beginPath();
      chipCtx.roundRect ? chipCtx.roundRect(-hw - 4, -hh - 4, chipW + 8, chipH + 8, baseSize * 0.08) 
                        : chipCtx.rect(-hw - 4, -hh - 4, chipW + 8, chipH + 8);
      chipCtx.fill();
      chipCtx.restore();

      // --- Ceramic package body ---
      const pkgGrad = chipCtx.createLinearGradient(-hw, -hh, hw, hh);
      pkgGrad.addColorStop(0, 'rgba(28, 26, 32, 0.95)');
      pkgGrad.addColorStop(0.5, 'rgba(38, 35, 44, 0.95)');
      pkgGrad.addColorStop(1, 'rgba(22, 20, 26, 0.95)');
      chipCtx.fillStyle = pkgGrad;
      chipCtx.strokeStyle = 'rgba(200, 192, 200, 0.12)';
      chipCtx.lineWidth = 1;
      chipCtx.beginPath();
      if (chipCtx.roundRect) {
        chipCtx.roundRect(-hw, -hh, chipW, chipH, baseSize * 0.07);
      } else {
        chipCtx.rect(-hw, -hh, chipW, chipH);
      }
      chipCtx.fill();
      chipCtx.stroke();

      // Package edge highlight
      chipCtx.strokeStyle = 'rgba(245, 198, 208, 0.08)';
      chipCtx.lineWidth = 0.5;
      chipCtx.strokeRect(-hw + 2, -hh + 2, chipW - 4, chipH - 4);

      // --- Die cavity (recessed area) ---
      const cavityInset = baseSize * 0.12;
      const cgw = chipW - cavityInset * 2;
      const cgh = chipH - cavityInset * 2;
      const cgx = -hw + cavityInset;
      const cgy = -hh + cavityInset;

      // Cavity shadow
      chipCtx.fillStyle = 'rgba(0, 0, 0, 0.4)';
      chipCtx.beginPath();
      chipCtx.rect(cgx - 1, cgy - 1, cgw + 2, cgh + 2);
      chipCtx.fill();

      // --- Glass die (main transparent surface) ---
      // Multiple layered gradients for glass effect
      
      // Base glass layer (charcoal tinted)
      const glassBase = chipCtx.createLinearGradient(cgx, cgy, cgx + cgw, cgy + cgh);
      glassBase.addColorStop(0, 'rgba(50, 45, 58, 0.55)');
      glassBase.addColorStop(0.35, 'rgba(65, 58, 74, 0.45)');
      glassBase.addColorStop(0.65, 'rgba(55, 48, 64, 0.5)');
      glassBase.addColorStop(1, 'rgba(42, 38, 50, 0.6)');
      chipCtx.fillStyle = glassBase;
      chipCtx.fillRect(cgx, cgy, cgw, cgh);

      // Pink internal illumination (from within)
      const innerGlow = chipCtx.createRadialGradient(
        cgx + cgw * 0.35, cgy + cgh * 0.4, 0,
        cgx + cgw * 0.35, cgy + cgh * 0.4, cgw * 0.6
      );
      innerGlow.addColorStop(0, 'rgba(232, 138, 154, 0.22)');
      innerGlow.addColorStop(0.4, 'rgba(245, 198, 208, 0.10)');
      innerGlow.addColorStop(1, 'rgba(232, 138, 154, 0)');
      chipCtx.fillStyle = innerGlow;
      chipCtx.fillRect(cgx, cgy, cgw, cgh);

      // Secondary coral glow from corner
      const cornerGlow = chipCtx.createRadialGradient(
        cgx + cgw * 0.85, cgy + cgh * 0.75, 0,
        cgx + cgw * 0.85, cgy + cgh * 0.75, cgw * 0.5
      );
      cornerGlow.addColorStop(0, 'rgba(200, 100, 120, 0.18)');
      cornerGlow.addColorStop(1, 'rgba(200, 100, 120, 0)');
      chipCtx.fillStyle = cornerGlow;
      chipCtx.fillRect(cgx, cgy, cgw, cgh);

      // --- Circuit structures visible through glass ---
      chipCtx.save();
      chipCtx.globalAlpha = 0.35;
      
      // Main horizontal bus
      chipCtx.strokeStyle = 'rgba(245, 198, 208, 0.5)';
      chipCtx.lineWidth = Math.max(0.5, baseSize * 0.008);
      chipCtx.beginPath();
      chipCtx.moveTo(cgx + cgw * 0.1, cgy + cgh * 0.5);
      chipCtx.lineTo(cgx + cgw * 0.9, cgy + cgh * 0.5);
      chipCtx.stroke();

      // Vertical spines
      chipCtx.strokeStyle = 'rgba(232, 138, 154, 0.35)';
      chipCtx.lineWidth = Math.max(0.3, baseSize * 0.005);
      for (let s = 1; s <= 5; s++) {
        chipCtx.beginPath();
        chipCtx.moveTo(cgx + (s / 6) * cgw, cgy + cgh * 0.15);
        chipCtx.lineTo(cgx + (s / 6) * cgw, cgy + cgh * 0.85);
        chipCtx.stroke();
      }

      // Functional block outlines (CPU cores / memory)
      chipCtx.strokeStyle = 'rgba(255, 245, 240, 0.2)';
      chipCtx.lineWidth = Math.max(0.3, baseSize * 0.004);
      const blocks = [
        [0.12, 0.12, 0.32, 0.32],
        [0.56, 0.12, 0.32, 0.32],
        [0.12, 0.56, 0.32, 0.32],
        [0.56, 0.56, 0.32, 0.32],
      ];
      blocks.forEach(([bx, by, bw, bh]) => {
        chipCtx.strokeRect(cgx + cgw * bx, cgy + cgh * by, cgw * bw, cgh * bh);
        // Internal grid
        chipCtx.strokeStyle = 'rgba(245, 198, 208, 0.12)';
        for (let g = 1; g < 3; g++) {
          chipCtx.beginPath();
          chipCtx.moveTo(cgx + cgw * bx + (cgw * bw / 3) * g, cgy + cgh * by);
          chipCtx.lineTo(cgx + cgw * bx + (cgw * bw / 3) * g, cgy + cgh * by + cgh * bh);
          chipCtx.stroke();
          chipCtx.beginPath();
          chipCtx.moveTo(cgx + cgw * bx, cgy + cgh * by + (cgh * bh / 3) * g);
          chipCtx.lineTo(cgx + cgw * bx + cgw * bw, cgy + cgh * by + (cgh * bh / 3) * g);
          chipCtx.stroke();
        }
        chipCtx.strokeStyle = 'rgba(255, 245, 240, 0.2)';
      });

      // Connection dots at intersections
      chipCtx.fillStyle = 'rgba(255, 245, 240, 0.4)';
      for (let d = 0; d < 12; d++) {
        const seed = Math.sin(d * 12.9898) * 43758.5453;
        const fr = seed - Math.floor(seed);
        const seed2 = Math.cos(d * 78.233) * 43758.5453;
        const fr2 = seed2 - Math.floor(seed2);
        const pulse = 0.5 + 0.5 * Math.sin(animTime * 0.001 + d * 0.8);
        chipCtx.globalAlpha = 0.25 + pulse * 0.35;
        chipCtx.beginPath();
        chipCtx.arc(cgx + cgw * (0.15 + fr * 0.7), cgy + cgh * (0.15 + fr2 * 0.7), 
                  Math.max(0.5, baseSize * 0.006), 0, Math.PI * 2);
        chipCtx.fill();
      }
      chipCtx.globalAlpha = 1;
      chipCtx.restore();

      // --- Glass surface reflections (top layer) ---
      // Primary highlight (top-left)
      const topHighlight = chipCtx.createLinearGradient(cgx, cgy, cgx + cgw * 0.5, cgy + cgh * 0.5);
      topHighlight.addColorStop(0, 'rgba(255, 245, 240, 0.25)');
      topHighlight.addColorStop(0.5, 'rgba(255, 245, 240, 0.08)');
      topHighlight.addColorStop(1, 'rgba(255, 245, 240, 0)');
      chipCtx.fillStyle = topHighlight;
      chipCtx.beginPath();
      chipCtx.moveTo(cgx, cgy);
      chipCtx.lineTo(cgx + cgw * 0.6, cgy);
      chipCtx.lineTo(cgx, cgy + cgh * 0.6);
      chipCtx.closePath();
      chipCtx.fill();

      // Edge highlights (bright along edges)
      chipCtx.strokeStyle = 'rgba(255, 245, 240, 0.35)';
      chipCtx.lineWidth = 1.5;
      chipCtx.beginPath();
      chipCtx.moveTo(cgx, cgy + cgh - 2);
      chipCtx.lineTo(cgx, cgy + 2);
      chipCtx.lineTo(cgx + cgw * 0.4, cgy);
      chipCtx.stroke();

      // Right edge subtle highlight
      chipCtx.strokeStyle = 'rgba(245, 198, 208, 0.15)';
      chipCtx.lineWidth = 1;
      chipCtx.beginPath();
      chipCtx.moveTo(cgx + cgw, cgy + 2);
      chipCtx.lineTo(cgx + cgw, cgy + cgh - 2);
      chipCtx.stroke();

      // Bottom edge pink reflection
      chipCtx.strokeStyle = 'rgba(232, 138, 154, 0.2)';
      chipCtx.beginPath();
      chipCtx.moveTo(cgx + 2, cgy + cgh);
      chipCtx.lineTo(cgx + cgw - 2, cgy + cgh);
      chipCtx.stroke();

      // Die border (seal ring)
      chipCtx.strokeStyle = 'rgba(200, 192, 200, 0.25)';
      chipCtx.lineWidth = 0.8;
      chipCtx.strokeRect(cgx + 1, cgy + 1, cgw - 2, cgh - 2);

      // Inner seal ring
      chipCtx.strokeStyle = 'rgba(245, 198, 208, 0.15)';
      chipCtx.lineWidth = 0.5;
      chipCtx.setLineDash([3, 2]);
      chipCtx.strokeRect(cgx + 4, cgy + 4, cgw - 8, cgh - 8);
      chipCtx.setLineDash([]);

      // --- Package pins (fine metallic details) ---
      const pinCount = 16;
      const pinLen = baseSize * 0.06;
      chipCtx.strokeStyle = 'rgba(200, 192, 200, 0.5)';
      chipCtx.fillStyle = 'rgba(220, 212, 220, 0.6)';
      chipCtx.lineWidth = 0.8;
      
      for (let i = 0; i < pinCount; i++) {
        const f = (i + 0.5) / pinCount;
        const py = -hh + baseSize * 0.04 + f * (chipH - baseSize * 0.08);
        const pinDir = sinY > 0 ? 1 : -1;
        
        // Left pins
        chipCtx.beginPath();
        chipCtx.moveTo(-hw, py);
        chipCtx.lineTo(-hw - pinLen * (0.6 + Math.abs(sinY) * 0.4), py - pinLen * 0.15);
        chipCtx.stroke();
        chipCtx.beginPath();
        chipCtx.arc(-hw - pinLen * (0.6 + Math.abs(sinY) * 0.4), py - pinLen * 0.15, 
                  Math.max(0.5, baseSize * 0.008), 0, Math.PI * 2);
        chipCtx.fill();
        
        // Right pins
        chipCtx.beginPath();
        chipCtx.moveTo(hw, py);
        chipCtx.lineTo(hw + pinLen * (0.6 + Math.abs(sinY) * 0.4), py - pinLen * 0.15);
        chipCtx.stroke();
        chipCtx.beginPath();
        chipCtx.arc(hw + pinLen * (0.6 + Math.abs(sinY) * 0.4), py - pinLen * 0.15,
                  Math.max(0.5, baseSize * 0.008), 0, Math.PI * 2);
        chipCtx.fill();
      }

      // Package marker dots
      chipCtx.fillStyle = 'rgba(20, 18, 24, 0.9)';
      for (let m = 0; m < 3; m++) {
        chipCtx.beginPath();
        chipCtx.arc(-hw + baseSize * 0.04 + m * baseSize * 0.025, 
                   -hh + baseSize * 0.035, baseSize * 0.006, 0, Math.PI * 2);
        chipCtx.fill();
      }

      // One pink marker dot (pin 1 indicator)
      chipCtx.fillStyle = 'rgba(232, 138, 154, 0.6)';
      chipCtx.beginPath();
      chipCtx.arc(-hw + baseSize * 0.04, -hh + baseSize * 0.035, baseSize * 0.007, 0, Math.PI * 2);
      chipCtx.fill();

      chipCtx.restore();
    }

    // --- Main render loop ---
    function renderGlassChip() {
      const now = performance.now();
      const dt = Math.min(32, now - lastFrameTime);
      lastFrameTime = now;
      animTime += dt;

      // Clear
      chipCtx.clearRect(0, 0, cw, ch);

      // Update and draw particles
      particles.forEach(p => {
        if (!prefersReducedMotion) p.update(dt * 0.06);
        p.draw();
      });

      // Chip animation parameters
      const cx = cw / 2;
      const cy = ch / 2;
      const baseSize = Math.min(cw, ch) * 0.18;
      
      let rotY, rotX, floatY;
      if (prefersReducedMotion) {
        rotY = 0.25;
        rotX = 0.08;
        floatY = 0;
      } else {
        rotY = Math.sin(animTime * 0.00015) * 0.4 + 0.1;
        rotX = Math.sin(animTime * 0.00012) * 0.12 + 0.05;
        floatY = Math.sin(animTime * 0.0004) * baseSize * 0.08;
      }

      // Draw the glass chip
      drawGlassChip(cx, cy, baseSize, rotY, rotX, floatY);

      requestAnimationFrame(renderGlassChip);
    }

    // --- Init ---
    resizeChipCanvas();
    window.addEventListener('resize', () => {
      resizeChipCanvas();
      // Re-optimize particle count for new size
      const newCount = Math.min(120, Math.floor((cw * ch) / 15000));
      while (particles.length < newCount) particles.push(new Particle());
      while (particles.length > newCount) particles.pop();
    });
    
    requestAnimationFrame(renderGlassChip);
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

/* ============================================
   SILICA — Interactive Script
   Glass semiconductor chip animation + scroll UX
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

  // ============================================================
  //  GLASS SEMICONDUCTOR CHIP ANIMATION
  //  Matches bottle reference: glass material, pink/coral 
  //  internal illumination, floating in dark particle space
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

    // --- Particle System (starfield like bottle reference) ---
    class Particle {
      constructor() { this.reset(true); }
      reset(initial = false) {
        this.x = Math.random() * cw;
        this.y = Math.random() * ch;
        this.size = Math.random() * 1.2 + 0.2;
        this.baseAlpha = Math.random() * 0.5 + 0.08;
        this.alpha = this.baseAlpha;
        this.speedX = (Math.random() - 0.5) * 0.08;
        this.speedY = (Math.random() - 0.5) * 0.06 - 0.02;
        this.pulseSpeed = Math.random() * 0.015 + 0.003;
        this.pulseOffset = Math.random() * Math.PI * 2;
        this.tint = Math.random() > 0.88 ? 'pink' : (Math.random() > 0.5 ? 'warm' : 'white');
      }
      update(dt) {
        this.x += this.speedX * dt;
        this.y += this.speedY * dt;
        this.alpha = this.baseAlpha * (0.5 + 0.5 * Math.sin(animTime * this.pulseSpeed + this.pulseOffset));
        if (this.x < -10) this.x = cw + 10;
        if (this.x > cw + 10) this.x = -10;
        if (this.y < -10) this.y = ch + 10;
        if (this.y > ch + 10) this.y = -10;
      }
      draw() {
        chipCtx.beginPath();
        chipCtx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        if (this.tint === 'pink') {
          chipCtx.fillStyle = `rgba(245, 198, 208, ${this.alpha * 0.9})`;
        } else if (this.tint === 'warm') {
          chipCtx.fillStyle = `rgba(255, 235, 225, ${this.alpha * 0.8})`;
        } else {
          chipCtx.fillStyle = `rgba(255, 250, 248, ${this.alpha})`;
        }
        chipCtx.fill();
      }
    }

    resizeChipCanvas();
    const particleCount = Math.min(150, Math.floor((cw * ch) / 12000));
    const particles = [];
    for (let i = 0; i < particleCount; i++) particles.push(new Particle());

    window.addEventListener('resize', () => {
      resizeChipCanvas();
      const newCount = Math.min(150, Math.floor((cw * ch) / 12000));
      while (particles.length < newCount) particles.push(new Particle());
      while (particles.length > newCount) particles.pop();
    });

    // --- Drawing helpers ---
    function lerp(a, b, t) { return a + (b - a) * t; }

    // Draw the glass chip with bottle-inspired lighting
    function drawGlassChip(cx, cy, baseSize, rotY, rotX, floatY, bobPhase) {
      chipCtx.save();
      chipCtx.translate(cx, cy + floatY);

      // 3D perspective simulation
      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);

      const m11 = cosY;
      const m12 = sinX * sinY * 0.35;
      const m21 = 0;
      const m22 = cosX;

      chipCtx.transform(m11, m21, m12, m22, 0, 0);
      chipCtx.transform(1, 0, sinY * 0.12, 1, 0, 0);

      const scaleX = 0.82 + Math.abs(sinY) * 0.18;
      const chipW = baseSize * 1.5 * scaleX;
      const chipH = baseSize * 1.5;
      const hw = chipW / 2;
      const hh = chipH / 2;
      const edgeDepth = baseSize * 0.1 * Math.abs(sinY) + baseSize * 0.05;

      // ==========================================
      // 1. OUTER AURA / BLOOM (like bottle glow)
      // ==========================================
      const auraR = baseSize * 2.2;
      const aura = chipCtx.createRadialGradient(0, -baseSize * 0.1, 0, 0, 0, auraR);
      aura.addColorStop(0, 'rgba(232, 138, 154, 0.18)');
      aura.addColorStop(0.25, 'rgba(245, 198, 208, 0.08)');
      aura.addColorStop(0.5, 'rgba(232, 138, 154, 0.03)');
      aura.addColorStop(1, 'rgba(232, 138, 154, 0)');
      chipCtx.fillStyle = aura;
      chipCtx.fillRect(-auraR, -auraR, auraR * 2, auraR * 2);

      // Secondary warm glow from below
      const aura2 = chipCtx.createRadialGradient(0, baseSize * 0.3, 0, 0, baseSize * 0.3, baseSize * 1.5);
      aura2.addColorStop(0, 'rgba(200, 100, 120, 0.12)');
      aura2.addColorStop(1, 'rgba(200, 100, 120, 0)');
      chipCtx.fillStyle = aura2;
      chipCtx.fillRect(-auraR, -auraR, auraR * 2, auraR * 2);

      // ==========================================
      // 2. DROP SHADOW
      // ==========================================
      chipCtx.save();
      chipCtx.translate(edgeDepth * 0.4, edgeDepth * 0.6);
      chipCtx.filter = 'blur(8px)';
      chipCtx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      chipCtx.beginPath();
      if (chipCtx.roundRect) {
        chipCtx.roundRect(-hw - 2, -hh - 2, chipW + 4, chipH + 4, baseSize * 0.08);
      } else {
        chipCtx.rect(-hw - 2, -hh - 2, chipW + 4, chipH + 4);
      }
      chipCtx.fill();
      chipCtx.restore();

      // ==========================================
      // 3. CERAMIC PACKAGE BODY
      // ==========================================
      const pkgGrad = chipCtx.createLinearGradient(-hw, -hh, hw, hh);
      pkgGrad.addColorStop(0, 'rgba(26, 24, 30, 0.96)');
      pkgGrad.addColorStop(0.4, 'rgba(36, 32, 42, 0.96)');
      pkgGrad.addColorStop(0.7, 'rgba(32, 28, 38, 0.96)');
      pkgGrad.addColorStop(1, 'rgba(20, 18, 24, 0.96)');
      chipCtx.fillStyle = pkgGrad;
      chipCtx.beginPath();
      if (chipCtx.roundRect) {
        chipCtx.roundRect(-hw, -hh, chipW, chipH, baseSize * 0.07);
      } else {
        chipCtx.rect(-hw, -hh, chipW, chipH);
      }
      chipCtx.fill();

      // Package edge highlight (top)
      chipCtx.strokeStyle = 'rgba(255, 245, 240, 0.12)';
      chipCtx.lineWidth = 1;
      chipCtx.beginPath();
      if (chipCtx.roundRect) {
        chipCtx.roundRect(-hw, -hh, chipW, chipH, baseSize * 0.07);
      } else {
        chipCtx.rect(-hw, -hh, chipW, chipH);
      }
      chipCtx.stroke();

      // ==========================================
      // 4. DIE CAVITY (recessed)
      // ==========================================
      const cavityInset = baseSize * 0.1;
      const cgw = chipW - cavityInset * 2;
      const cgh = chipH - cavityInset * 2;
      const cgx = -hw + cavityInset;
      const cgy = -hh + cavityInset;

      // Cavity shadow
      chipCtx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      chipCtx.fillRect(cgx - 1, cgy - 1, cgw + 2, cgh + 2);

      // ==========================================
      // 5. GLASS DIE — MAIN TRANSPARENT SURFACE
      // ==========================================
      
      // Base glass layer (charcoal tinted, transparent)
      const glassBase = chipCtx.createLinearGradient(cgx, cgy, cgx + cgw, cgy + cgh);
      glassBase.addColorStop(0, 'rgba(55, 50, 65, 0.5)');
      glassBase.addColorStop(0.3, 'rgba(70, 62, 80, 0.38)');
      glassBase.addColorStop(0.55, 'rgba(60, 52, 70, 0.42)');
      glassBase.addColorStop(0.8, 'rgba(48, 42, 58, 0.48)');
      glassBase.addColorStop(1, 'rgba(38, 34, 46, 0.55)');
      chipCtx.fillStyle = glassBase;
      chipCtx.fillRect(cgx, cgy, cgw, cgh);

      // ==========================================
      // 6. INTERNAL ILLUMINATION (pink/coral glow)
      //    Like the glowing liquid in the bottle
      // ==========================================
      
      // Main pink internal glow (center-left)
      const innerGlow = chipCtx.createRadialGradient(
        cgx + cgw * 0.32, cgy + cgh * 0.38, 0,
        cgx + cgw * 0.32, cgy + cgh * 0.38, cgw * 0.7
      );
      innerGlow.addColorStop(0, 'rgba(232, 138, 154, 0.35)');
      innerGlow.addColorStop(0.3, 'rgba(245, 198, 208, 0.18)');
      innerGlow.addColorStop(0.6, 'rgba(232, 138, 154, 0.06)');
      innerGlow.addColorStop(1, 'rgba(232, 138, 154, 0)');
      chipCtx.fillStyle = innerGlow;
      chipCtx.fillRect(cgx, cgy, cgw, cgh);

      // Secondary coral glow from bottom-right
      const cornerGlow = chipCtx.createRadialGradient(
        cgx + cgw * 0.82, cgy + cgh * 0.78, 0,
        cgx + cgw * 0.82, cgy + cgh * 0.78, cgw * 0.55
      );
      cornerGlow.addColorStop(0, 'rgba(200, 100, 120, 0.28)');
      cornerGlow.addColorStop(0.4, 'rgba(232, 138, 154, 0.1)');
      cornerGlow.addColorStop(1, 'rgba(200, 100, 120, 0)');
      chipCtx.fillStyle = cornerGlow;
      chipCtx.fillRect(cgx, cgy, cgw, cgh);

      // Subtle bottom glow (like light through glass)
      const bottomGlow = chipCtx.createLinearGradient(cgx, cgy + cgh * 0.5, cgx, cgy + cgh);
      bottomGlow.addColorStop(0, 'rgba(245, 198, 208, 0)');
      bottomGlow.addColorStop(1, 'rgba(232, 138, 154, 0.15)');
      chipCtx.fillStyle = bottomGlow;
      chipCtx.fillRect(cgx, cgy, cgw, cgh);

      // ==========================================
      // 7. CIRCUIT STRUCTURES (visible through glass)
      // ==========================================
      chipCtx.save();
      chipCtx.globalAlpha = 0.4;

      // Main horizontal bus
      chipCtx.strokeStyle = 'rgba(245, 198, 208, 0.55)';
      chipCtx.lineWidth = Math.max(0.6, baseSize * 0.01);
      chipCtx.beginPath();
      chipCtx.moveTo(cgx + cgw * 0.08, cgy + cgh * 0.5);
      chipCtx.lineTo(cgx + cgw * 0.92, cgy + cgh * 0.5);
      chipCtx.stroke();

      // Vertical spines
      chipCtx.strokeStyle = 'rgba(232, 138, 154, 0.4)';
      chipCtx.lineWidth = Math.max(0.4, baseSize * 0.006);
      for (let s = 1; s <= 6; s++) {
        chipCtx.beginPath();
        chipCtx.moveTo(cgx + (s / 7) * cgw, cgy + cgh * 0.12);
        chipCtx.lineTo(cgx + (s / 7) * cgw, cgy + cgh * 0.88);
        chipCtx.stroke();
      }

      // Functional blocks (CPU cores / memory arrays)
      chipCtx.strokeStyle = 'rgba(255, 245, 240, 0.22)';
      chipCtx.lineWidth = Math.max(0.4, baseSize * 0.005);
      const blocks = [
        [0.10, 0.10, 0.34, 0.32],
        [0.56, 0.10, 0.34, 0.32],
        [0.10, 0.58, 0.34, 0.32],
        [0.56, 0.58, 0.34, 0.32],
      ];
      blocks.forEach(([bx, by, bw, bh]) => {
        chipCtx.strokeRect(cgx + cgw * bx, cgy + cgh * by, cgw * bw, cgh * bh);
        // Internal grid within blocks
        chipCtx.strokeStyle = 'rgba(245, 198, 208, 0.14)';
        for (let g = 1; g < 4; g++) {
          chipCtx.beginPath();
          chipCtx.moveTo(cgx + cgw * bx + (cgw * bw / 4) * g, cgy + cgh * by);
          chipCtx.lineTo(cgx + cgw * bx + (cgw * bw / 4) * g, cgy + cgh * by + cgh * bh);
          chipCtx.stroke();
          chipCtx.beginPath();
          chipCtx.moveTo(cgx + cgw * bx, cgy + cgh * by + (cgh * bh / 4) * g);
          chipCtx.lineTo(cgx + cgw * bx + cgw * bw, cgy + cgh * by + (cgh * bh / 4) * g);
          chipCtx.stroke();
        }
        chipCtx.strokeStyle = 'rgba(255, 245, 240, 0.22)';
      });

      // Connection / activity dots (pulsing)
      chipCtx.fillStyle = 'rgba(255, 245, 240, 0.5)';
      for (let d = 0; d < 16; d++) {
        const seed = Math.sin(d * 12.9898) * 43758.5453;
        const fr = seed - Math.floor(seed);
        const seed2 = Math.cos(d * 78.233) * 43758.5453;
        const fr2 = seed2 - Math.floor(seed2);
        const pulse = 0.4 + 0.6 * Math.sin(animTime * 0.0008 + d * 0.7);
        chipCtx.globalAlpha = 0.2 + pulse * 0.5;
        chipCtx.beginPath();
        chipCtx.arc(cgx + cgw * (0.12 + fr * 0.76), cgy + cgh * (0.12 + fr2 * 0.76), 
                  Math.max(0.6, baseSize * 0.007), 0, Math.PI * 2);
        chipCtx.fill();
      }
      chipCtx.globalAlpha = 1;
      chipCtx.restore();

      // ==========================================
      // 8. GLASS SURFACE REFLECTIONS
      //    Bright highlights like on the bottle
      // ==========================================

      // Primary top-left highlight (large, soft)
      const topHighlight = chipCtx.createLinearGradient(cgx, cgy, cgx + cgw * 0.55, cgy + cgh * 0.55);
      topHighlight.addColorStop(0, 'rgba(255, 250, 245, 0.32)');
      topHighlight.addColorStop(0.4, 'rgba(255, 245, 240, 0.12)');
      topHighlight.addColorStop(1, 'rgba(255, 245, 240, 0)');
      chipCtx.fillStyle = topHighlight;
      chipCtx.beginPath();
      chipCtx.moveTo(cgx, cgy);
      chipCtx.lineTo(cgx + cgw * 0.65, cgy);
      chipCtx.lineTo(cgx, cgy + cgh * 0.65);
      chipCtx.closePath();
      chipCtx.fill();

      // Sharp specular highlight (top edge)
      const specular = chipCtx.createLinearGradient(cgx, cgy, cgx, cgy + cgh * 0.15);
      specular.addColorStop(0, 'rgba(255, 255, 255, 0.45)');
      specular.addColorStop(1, 'rgba(255, 255, 255, 0)');
      chipCtx.fillStyle = specular;
      chipCtx.fillRect(cgx + 2, cgy + 1, cgw - 4, cgh * 0.12);

      // Left edge bright line
      chipCtx.strokeStyle = 'rgba(255, 250, 245, 0.45)';
      chipCtx.lineWidth = 1.8;
      chipCtx.beginPath();
      chipCtx.moveTo(cgx + 0.5, cgy + cgh - 3);
      chipCtx.lineTo(cgx + 0.5, cgy + 2);
      chipCtx.lineTo(cgx + cgw * 0.35, cgy + 0.5);
      chipCtx.stroke();

      // Right edge subtle pink reflection
      chipCtx.strokeStyle = 'rgba(245, 198, 208, 0.25)';
      chipCtx.lineWidth = 1.2;
      chipCtx.beginPath();
      chipCtx.moveTo(cgx + cgw - 0.5, cgy + 3);
      chipCtx.lineTo(cgx + cgw - 0.5, cgy + cgh - 3);
      chipCtx.stroke();

      // Bottom edge pink glow line
      chipCtx.strokeStyle = 'rgba(232, 138, 154, 0.35)';
      chipCtx.lineWidth = 1.2;
      chipCtx.beginPath();
      chipCtx.moveTo(cgx + 3, cgy + cgh - 0.5);
      chipCtx.lineTo(cgx + cgw - 3, cgy + cgh - 0.5);
      chipCtx.stroke();

      // ==========================================
      // 9. DIE BORDERS / SEAL RINGS
      // ==========================================
      
      // Outer die border
      chipCtx.strokeStyle = 'rgba(200, 192, 200, 0.3)';
      chipCtx.lineWidth = 0.8;
      chipCtx.strokeRect(cgx + 0.5, cgy + 0.5, cgw - 1, cgh - 1);

      // Inner seal ring (dashed pink)
      chipCtx.strokeStyle = 'rgba(245, 198, 208, 0.2)';
      chipCtx.lineWidth = 0.5;
      chipCtx.setLineDash([4, 3]);
      chipCtx.strokeRect(cgx + 5, cgy + 5, cgw - 10, cgh - 10);
      chipCtx.setLineDash([]);

      // ==========================================
      // 10. PACKAGE PINS (metallic details)
      // ==========================================
      const pinCount = 18;
      const pinLen = baseSize * 0.07;
      chipCtx.lineWidth = 0.9;

      for (let i = 0; i < pinCount; i++) {
        const f = (i + 0.5) / pinCount;
        const py = -hh + baseSize * 0.05 + f * (chipH - baseSize * 0.1);
        const perspective = 0.6 + Math.abs(sinY) * 0.4;

        // Left pins
        const leftPinX = -hw - pinLen * perspective;
        const leftPinY = py - pinLen * 0.12;
        
        // Pin gradient
        const pinGradL = chipCtx.createLinearGradient(-hw, py, leftPinX, leftPinY);
        pinGradL.addColorStop(0, 'rgba(220, 212, 220, 0.7)');
        pinGradL.addColorStop(1, 'rgba(180, 170, 180, 0.3)');
        chipCtx.strokeStyle = pinGradL;
        chipCtx.beginPath();
        chipCtx.moveTo(-hw, py);
        chipCtx.lineTo(leftPinX, leftPinY);
        chipCtx.stroke();

        // Pin tip ball
        chipCtx.fillStyle = 'rgba(240, 232, 240, 0.8)';
        chipCtx.beginPath();
        chipCtx.arc(leftPinX, leftPinY, Math.max(0.6, baseSize * 0.01), 0, Math.PI * 2);
        chipCtx.fill();

        // Right pins
        const rightPinX = hw + pinLen * perspective;
        const rightPinY = py - pinLen * 0.12;
        
        const pinGradR = chipCtx.createLinearGradient(hw, py, rightPinX, rightPinY);
        pinGradR.addColorStop(0, 'rgba(220, 212, 220, 0.7)');
        pinGradR.addColorStop(1, 'rgba(180, 170, 180, 0.3)');
        chipCtx.strokeStyle = pinGradR;
        chipCtx.beginPath();
        chipCtx.moveTo(hw, py);
        chipCtx.lineTo(rightPinX, rightPinY);
        chipCtx.stroke();

        chipCtx.fillStyle = 'rgba(240, 232, 240, 0.8)';
        chipCtx.beginPath();
        chipCtx.arc(rightPinX, rightPinY, Math.max(0.6, baseSize * 0.01), 0, Math.PI * 2);
        chipCtx.fill();
      }

      // ==========================================
      // 11. PIN 1 INDICATOR (pink marker dot)
      // ==========================================
      chipCtx.fillStyle = 'rgba(232, 138, 154, 0.85)';
      chipCtx.beginPath();
      chipCtx.arc(-hw + baseSize * 0.045, -hh + baseSize * 0.04, baseSize * 0.01, 0, Math.PI * 2);
      chipCtx.fill();

      // Pin 1 glow
      const pin1Glow = chipCtx.createRadialGradient(
        -hw + baseSize * 0.045, -hh + baseSize * 0.04, 0,
        -hw + baseSize * 0.045, -hh + baseSize * 0.04, baseSize * 0.06
      );
      pin1Glow.addColorStop(0, 'rgba(232, 138, 154, 0.4)');
      pin1Glow.addColorStop(1, 'rgba(232, 138, 154, 0)');
      chipCtx.fillStyle = pin1Glow;
      chipCtx.beginPath();
      chipCtx.arc(-hw + baseSize * 0.045, -hh + baseSize * 0.04, baseSize * 0.06, 0, Math.PI * 2);
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

      // Subtle background vignette (dark edges)
      const bgVignette = chipCtx.createRadialGradient(
        cw / 2, ch * 0.45, ch * 0.1,
        cw / 2, ch * 0.45, ch * 0.9
      );
      bgVignette.addColorStop(0, 'rgba(232, 138, 154, 0.03)');
      bgVignette.addColorStop(0.5, 'rgba(8, 8, 10, 0)');
      bgVignette.addColorStop(1, 'rgba(0, 0, 0, 0.35)');
      chipCtx.fillStyle = bgVignette;
      chipCtx.fillRect(0, 0, cw, ch);

      // Draw particles
      particles.forEach(p => {
        if (!prefersReducedMotion) p.update(dt * 0.06);
        p.draw();
      });

      // Chip animation parameters
      // Position: slightly above center, more prominent
      const cx = cw / 2;
      const cy = ch * 0.52;
      const baseSize = Math.min(cw, ch) * 0.22;

      let rotY, rotX, floatY, bobPhase;
      if (prefersReducedMotion) {
        rotY = 0.3;
        rotX = 0.1;
        floatY = 0;
        bobPhase = 0;
      } else {
        // Slow continuous rotation around vertical axis
        rotY = Math.sin(animTime * 0.00012) * 0.5 + 0.15;
        // Gentle tilt
        rotX = Math.sin(animTime * 0.00009 + 1.2) * 0.15 + 0.06;
        // Smooth floating up and down
        floatY = Math.sin(animTime * 0.00035) * baseSize * 0.1;
        bobPhase = animTime * 0.00035;
      }

      // Draw the glass chip
      drawGlassChip(cx, cy, baseSize, rotY, rotX, floatY, bobPhase);

      requestAnimationFrame(renderGlassChip);
    }

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
    updateScrollIndicator();
  }, 200);

})();

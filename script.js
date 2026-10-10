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
  //  EXTRAORDINARY 3D SEMICONDUCTOR CHIP ANIMATION
  //  Scroll-driven, perspective-projected, physically-inspired
  // ============================================================
  
  const canvas = document.getElementById('silica-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let W, H, dpr;
    let heroScrollProgress = 0; // 0 to 1 through the hero section
    let smoothScrollProgress = 0;
    let animTime = 0;

    function resizeCanvas() {
      dpr = window.devicePixelRatio || 1;
      W = canvas.clientWidth = window.innerWidth;
      H = canvas.clientHeight = window.innerHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // ---------- 3D Math Utilities ----------
    function rotateX(p, a) {
      const c = Math.cos(a), s = Math.sin(a);
      return { x: p.x, y: p.y * c - p.z * s, z: p.y * s + p.z * c };
    }
    function rotateY(p, a) {
      const c = Math.cos(a), s = Math.sin(a);
      return { x: p.x * c + p.z * s, y: p.y, z: -p.x * s + p.z * c };
    }
    function rotateZ(p, a) {
      const c = Math.cos(a), s = Math.sin(a);
      return { x: p.x * c - p.y * s, y: p.x * s + p.y * c, z: p.z };
    }
    function project(p, cx, cy, scale, perspective) {
      const f = perspective / (perspective + p.z);
      return {
        x: cx + p.x * scale * f,
        y: cy + p.y * scale * f,
        z: p.z,
        scale: f
      };
    }

    // Easing
    function easeInOutCubic(t) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }
    function lerp(a, b, t) { return a + (b - a) * t; }
    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

    // ---------- Animation Timeline ----------
    // Maps hero scroll progress (0-1) to 3D rotation angles
    // This choreography matches the reference camera's distinctive movement:
    // Phase 1 (0.00-0.15): Establish presence, gentle rotation
    // Phase 2 (0.15-0.35): SIGNATURE ROLL - dramatic Z-axis rotation
    // Phase 3 (0.35-0.55): Tilt toward viewer, perspective shift
    // Phase 4 (0.55-0.75): Y-axis rotation, reveal different faces
    // Phase 5 (0.75-1.00): Settle into composed final angle
    function getRotationAngles(p) {
      let rotX, rotY, rotZ, chipScale, zOffset;

      if (p < 0.15) {
        // Phase 1: Gentle establishment
        const t = p / 0.15;
        const e = easeInOutCubic(t);
        rotX = lerp(-0.1, -0.05, e);
        rotY = lerp(-0.3, -0.15, e);
        rotZ = lerp(0, 0.05, e);
        chipScale = lerp(0.55, 0.62, e);
        zOffset = lerp(0, -20, e);
      } else if (p < 0.35) {
        // Phase 2: SIGNATURE ROLL - the camera's distinctive rolling motion
        const t = (p - 0.15) / 0.20;
        const e = easeInOutCubic(t);
        rotX = lerp(-0.05, 0.3, e);
        rotY = lerp(-0.15, 0.4, e);
        rotZ = lerp(0.05, 1.2, e); // Full roll!
        chipScale = lerp(0.62, 0.72, e);
        zOffset = lerp(-20, -60, e);
      } else if (p < 0.55) {
        // Phase 3: Tilt toward viewer, dramatic perspective
        const t = (p - 0.35) / 0.20;
        const e = easeInOutCubic(t);
        rotX = lerp(0.3, 0.9, e); // Tilt UP dramatically
        rotY = lerp(0.4, 0.2, e);
        rotZ = lerp(1.2, 0.3, e);
        chipScale = lerp(0.72, 0.85, e);
        zOffset = lerp(-60, -100, e);
      } else if (p < 0.75) {
        // Phase 4: Rotate to reveal underside and layers
        const t = (p - 0.55) / 0.20;
        const e = easeInOutCubic(t);
        rotX = lerp(0.9, 0.5, e);
        rotY = lerp(0.2, -0.8, e); // Swing around
        rotZ = lerp(0.3, -0.2, e);
        chipScale = lerp(0.85, 0.78, e);
        zOffset = lerp(-100, -70, e);
      } else {
        // Phase 5: Settle into composed final angle
        const t = (p - 0.75) / 0.25;
        const e = easeInOutCubic(t);
        rotX = lerp(0.5, 0.35, e);
        rotY = lerp(-0.8, -0.5, e);
        rotZ = lerp(-0.2, 0.08, e);
        chipScale = lerp(0.78, 0.7, e);
        zOffset = lerp(-70, -30, e);
      }

      return { rotX, rotY, rotZ, chipScale, zOffset };
    }

    // How much internal structure to reveal (0 = closed, 1 = fully exploded)
    function getLayerReveal(p) {
      if (p < 0.35) return 0;
      if (p < 0.65) {
        const t = (p - 0.35) / 0.30;
        return easeInOutCubic(t) * 0.7;
      }
      if (p < 0.85) {
        const t = (p - 0.65) / 0.20;
        return 0.7 - easeInOutCubic(t) * 0.4;
      }
      const t = (p - 0.85) / 0.15;
      return 0.3 - easeInOutCubic(t) * 0.3;
    }

    // ---------- Chip Model ----------
    const CHIP = {
      w: 200, h: 200, // Top face dimensions
      thickness: 35,  // Total thickness
      substrateH: 22, // Silicon substrate thickness
      metalLayers: 8, // Metal interconnect layers
      metalSpacing: 1.2,
      passivationH: 2
    };

    // Generate a detailed transistor grid pattern
    function generateTransistorPattern() {
      const cells = [];
      const cols = 24, rows = 24;
      const cellW = CHIP.w / cols;
      const cellH = CHIP.h / rows;
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const seed = Math.sin(r * 12.9898 + c * 78.233) * 43758.5453;
          const rand = seed - Math.floor(seed);
          cells.push({
            x: -CHIP.w/2 + c * cellW,
            y: -CHIP.h/2 + r * cellH,
            w: cellW * 0.85,
            h: cellH * 0.85,
            density: rand,
            type: rand > 0.7 ? 'block' : (rand > 0.3 ? 'gate' : 'empty')
          });
        }
      }
      return cells;
    }

    // Generate I/O pin positions
    function generateIOPins() {
      const pins = [];
      const count = 28;
      const inset = 8;
      const usableW = CHIP.w - inset * 2;
      const usableH = CHIP.h - inset * 2;
      const spacingW = usableW / (count - 1);
      const spacingH = usableH / (count - 1);
      for (let i = 0; i < count; i++) {
        pins.push({ side: 'top', x: -CHIP.w/2 + inset + i * spacingW, y: -CHIP.h/2 });
        pins.push({ side: 'bottom', x: -CHIP.w/2 + inset + i * spacingW, y: CHIP.h/2 });
        pins.push({ side: 'left', x: -CHIP.w/2, y: -CHIP.h/2 + inset + i * spacingH });
        pins.push({ side: 'right', x: CHIP.w/2, y: -CHIP.h/2 + inset + i * spacingH });
      }
      return pins;
    }

    // Generate functional blocks (CPU, cache, etc.)
    function generateBlocks() {
      return [
        { x: -70, y: -70, w: 55, h: 55, type: 'core', label: 'CORE' },
        { x: 15, y: -70, w: 55, h: 55, type: 'core', label: 'CORE' },
        { x: -70, y: 15, w: 55, h: 55, type: 'cache', label: 'CACHE' },
        { x: 15, y: 15, w: 55, h: 55, type: 'cache', label: 'CACHE' },
        { x: -70, y: -5, w: 140, h: 10, type: 'bus', label: '' },
      ];
    }

    const transistorPattern = generateTransistorPattern();
    const ioPins = generateIOPins();
    const functionalBlocks = generateBlocks();

    // ---------- Rendering ----------
    function transformPoint(x, y, z, angles, cx, cy, scale, perspective, zOff) {
      let p = { x, y, z: z + zOff };
      p = rotateX(p, angles.rotX);
      p = rotateY(p, angles.rotY);
      p = rotateZ(p, angles.rotZ);
      return project(p, cx, cy, scale, perspective);
    }

    // Draw a filled quad with 4 3D points
    function drawQuad(p1, p2, p3, p4, fillStyle, strokeStyle, lineWidth) {
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.lineTo(p3.x, p3.y);
      ctx.lineTo(p4.x, p4.y);
      ctx.closePath();
      if (fillStyle) { ctx.fillStyle = fillStyle; ctx.fill(); }
      if (strokeStyle) { ctx.strokeStyle = strokeStyle; ctx.lineWidth = lineWidth || 0.5; ctx.stroke(); }
    }

    // Calculate face normal for backface culling and lighting
    function faceNormal(p1, p2, p3) {
      const ax = p2.x - p1.x, ay = p2.y - p1.y, az = p2.z - p1.z;
      const bx = p3.x - p1.x, by = p3.y - p1.y, bz = p3.z - p1.z;
      return {
        x: ay * bz - az * by,
        y: az * bx - ax * bz,
        z: ax * by - ay * bx
      };
    }

    function isFrontFacing(normal) {
      return normal.z > 0;
    }

    // Lighting based on face normal
    function calcLighting(normal, baseLight) {
      const lightDir = { x: -0.4, y: -0.6, z: -0.7 };
      const len = Math.sqrt(normal.x*normal.x + normal.y*normal.y + normal.z*normal.z);
      const ldir = { x: lightDir.x, y: lightDir.y, z: lightDir.z };
      const llen = Math.sqrt(ldir.x*ldir.x + ldir.y*ldir.y + ldir.z*ldir.z);
      const dot = (normal.x/len * ldir.x/llen + normal.y/len * ldir.y/llen + normal.z/len * ldir.z/llen);
      return clamp(baseLight + dot * 0.5, 0.35, 1.15);
    }

    function shadeColor(r, g, b, intensity) {
      return `rgb(${Math.floor(r * intensity)}, ${Math.floor(g * intensity)}, ${Math.floor(b * intensity)})`;
    }

    function shadeRGBA(r, g, b, a, intensity) {
      return `rgba(${Math.floor(r * intensity)}, ${Math.floor(g * intensity)}, ${Math.floor(b * intensity)}, ${a})`;
    }

    // Main render function
    function renderChip() {
      const cx = W / 2;
      const cy = H / 2;
      const perspective = 600;
      const angles = getRotationAngles(smoothScrollProgress);
      const layerReveal = getLayerReveal(smoothScrollProgress);
      const baseScale = Math.min(W, H) * 0.0055 * angles.chipScale;
      const zOff = angles.zOffset;

      // Collect all faces with depth for painter's algorithm
      const faces = [];

      const hw = CHIP.w / 2;
      const hh = CHIP.h / 2;
      const t = CHIP.thickness;
      const subH = CHIP.substrateH;
      const passH = CHIP.passivationH;

      // --- SUBSTRATE (bottom bulk silicon) ---
      const subTop = -t/2;
      const subBot = -t/2 + subH;
      const subColor = { r: 70, g: 78, b: 95 };
      
      // Substrate bottom face
      {
        const p1 = transformPoint(-hw, -hh, subBot, angles, cx, cy, baseScale, perspective, zOff);
        const p2 = transformPoint( hw, -hh, subBot, angles, cx, cy, baseScale, perspective, zOff);
        const p3 = transformPoint( hw,  hh, subBot, angles, cx, cy, baseScale, perspective, zOff);
        const p4 = transformPoint(-hw,  hh, subBot, angles, cx, cy, baseScale, perspective, zOff);
        const n = faceNormal(p1, p2, p3);
        if (isFrontFacing(n)) {
          const l = calcLighting(n, 0.6);
          faces.push({ depth: (p1.z+p2.z+p3.z+p4.z)/4, draw: () => {
            drawQuad(p1, p2, p3, p4, shadeColor(subColor.r, subColor.g, subColor.b, l), shadeColor(50, 58, 75, l * 0.9), 0.8);
          }});
        }
      }

      // Substrate side faces
      const subSides = [
        { a: {x:-hw,y:-hh,z:subBot}, b:{x:hw,y:-hh,z:subBot}, c:{x:hw,y:-hh,z:subTop}, d:{x:-hw,y:-hh,z:subTop} },
        { a: {x:hw,y:-hh,z:subBot}, b:{x:hw,y:hh,z:subBot}, c:{x:hw,y:hh,z:subTop}, d:{x:hw,y:-hh,z:subTop} },
        { a: {x:hw,y:hh,z:subBot}, b:{x:-hw,y:hh,z:subBot}, c:{x:-hw,y:hh,z:subTop}, d:{x:hw,y:hh,z:subTop} },
        { a: {x:-hw,y:hh,z:subBot}, b:{x:-hw,y:-hh,z:subBot}, c:{x:-hw,y:-hh,z:subTop}, d:{x:-hw,y:hh,z:subTop} },
      ];
      subSides.forEach(side => {
        const p1 = transformPoint(side.a.x, side.a.y, side.a.z, angles, cx, cy, baseScale, perspective, zOff);
        const p2 = transformPoint(side.b.x, side.b.y, side.b.z, angles, cx, cy, baseScale, perspective, zOff);
        const p3 = transformPoint(side.c.x, side.c.y, side.c.z, angles, cx, cy, baseScale, perspective, zOff);
        const p4 = transformPoint(side.d.x, side.d.y, side.d.z, angles, cx, cy, baseScale, perspective, zOff);
        const n = faceNormal(p1, p2, p3);
        if (isFrontFacing(n)) {
          const l = calcLighting(n, 0.7);
          faces.push({ depth: (p1.z+p2.z+p3.z+p4.z)/4, draw: () => {
            drawQuad(p1, p2, p3, p4, shadeColor(subColor.r+15, subColor.g+15, subColor.b+20, l), shadeColor(60, 68, 85, l * 0.7), 0.5);
            // Subtle horizontal striations on substrate edge
            ctx.strokeStyle = shadeColor(subColor.r+20, subColor.g+25, subColor.b+35, l * 0.3);
            ctx.lineWidth = 0.3;
            for (let i = 1; i < 4; i++) {
              const frac = i / 4;
              ctx.beginPath();
              ctx.moveTo(lerp(p1.x, p4.x, frac), lerp(p1.y, p4.y, frac));
              ctx.lineTo(lerp(p2.x, p3.x, frac), lerp(p2.y, p3.y, frac));
              ctx.stroke();
            }
          }});
        }
      });

      // --- METAL LAYERS (stacked above substrate) ---
      const metalBaseZ = subTop;
      const metalColors = [
        { r: 200, g: 140, b: 60 },   // M1
        { r: 210, g: 150, b: 65 },   // M2
        { r: 215, g: 155, b: 70 },   // M3
        { r: 220, g: 160, b: 75 },   // M4
        { r: 225, g: 165, b: 80 },   // M5
        { r: 230, g: 170, b: 85 },   // M6
        { r: 235, g: 175, b: 90 },   // M7
        { r: 240, g: 185, b: 100 },  // M8 - top metal, brightest
      ];

      for (let layer = 0; layer < CHIP.metalLayers; layer++) {
        const layerFrac = layer / (CHIP.metalLayers - 1);
        const revealOffset = layerReveal * layer * 1.5;
        const layerZ = metalBaseZ + layer * CHIP.metalSpacing - revealOffset;
        const layerThickness = 0.6 + layerFrac * 0.8;
        const color = metalColors[layer];
        const isHorizontal = layer % 2 === 0;

        // Metal layer top face with routing lines
        {
          const p1 = transformPoint(-hw, -hh, layerZ, angles, cx, cy, baseScale, perspective, zOff);
          const p2 = transformPoint( hw, -hh, layerZ, angles, cx, cy, baseScale, perspective, zOff);
          const p3 = transformPoint( hw,  hh, layerZ, angles, cx, cy, baseScale, perspective, zOff);
          const p4 = transformPoint(-hw,  hh, layerZ, angles, cx, cy, baseScale, perspective, zOff);
          const n = faceNormal(p1, p2, p3);
          if (isFrontFacing(n)) {
            const l = calcLighting(n, 0.55);
            const alpha = 0.55 + layerFrac * 0.35;
            faces.push({ depth: (p1.z+p2.z+p3.z+p4.z)/4, draw: () => {
              // Dielectric base
              drawQuad(p1, p2, p3, p4, shadeRGBA(50, 55, 70, alpha * 0.15, l), null);
              
              // Metal routing lines
              ctx.strokeStyle = shadeRGBA(color.r, color.g, color.b, alpha, l);
              ctx.lineWidth = Math.max(0.4, 1.2 - layerFrac * 0.7) * p1.scale;
              ctx.lineCap = 'square';
              ctx.beginPath();
              
              const lineCount = 8 + Math.floor(layerFrac * 12);
              if (isHorizontal) {
                for (let i = 0; i < lineCount; i++) {
                  const yFrac = (i + 0.5) / lineCount;
                  const y = -hh + yFrac * CHIP.h;
                  // Add some breaks to look like real routing
                  const segments = 3 + Math.floor(Math.sin(i * 2.5) * 1.5 + 1.5);
                  for (let s = 0; s < segments; s++) {
                    const x1 = -hw + (s / segments) * CHIP.w + 2;
                    const x2 = -hw + ((s + 1) / segments) * CHIP.w - 2;
                    const gap = Math.sin(i * 1.7 + s) > 0.3 ? 0 : 0;
                    if (!gap) {
                      const sp = transformPoint(x1, y, layerZ + 0.05, angles, cx, cy, baseScale, perspective, zOff);
                      const ep = transformPoint(x2, y, layerZ + 0.05, angles, cx, cy, baseScale, perspective, zOff);
                      ctx.moveTo(sp.x, sp.y);
                      ctx.lineTo(ep.x, ep.y);
                    }
                  }
                }
              } else {
                for (let i = 0; i < lineCount; i++) {
                  const xFrac = (i + 0.5) / lineCount;
                  const x = -hw + xFrac * CHIP.w;
                  const segments = 3 + Math.floor(Math.cos(i * 1.9) * 1.5 + 1.5);
                  for (let s = 0; s < segments; s++) {
                    const y1 = -hh + (s / segments) * CHIP.h + 2;
                    const y2 = -hh + ((s + 1) / segments) * CHIP.h - 2;
                    const gap = Math.cos(i * 2.1 + s * 0.7) > 0.3 ? 0 : 0;
                    if (!gap) {
                      const sp = transformPoint(x, y1, layerZ + 0.05, angles, cx, cy, baseScale, perspective, zOff);
                      const ep = transformPoint(x, y2, layerZ + 0.05, angles, cx, cy, baseScale, perspective, zOff);
                      ctx.moveTo(sp.x, sp.y);
                      ctx.lineTo(ep.x, ep.y);
                    }
                  }
                }
              }
              ctx.stroke();
            }});
          }
        }

        // Metal layer edge (visible when tilted)
        if (layerReveal > 0.05 || Math.abs(angles.rotX) > 0.3 || Math.abs(angles.rotY) > 0.3) {
          const edgeAlpha = clamp(0.3 + layerReveal * 0.7 + Math.abs(angles.rotX) * 0.5, 0.2, 1);
          const edgeSides = [
            { x1: -hw, y1: -hh, x2: hw, y2: -hh, nz: layerZ + layerThickness },
            { x1: hw, y1: -hh, x2: hw, y2: hh, nz: layerZ + layerThickness },
            { x1: hw, y1: hh, x2: -hw, y2: hh, nz: layerZ + layerThickness },
            { x1: -hw, y1: hh, x2: -hw, y2: -hh, nz: layerZ + layerThickness },
          ];
          
          edgeSides.forEach((side, si) => {
            const p1 = transformPoint(side.x1, side.y1, layerZ, angles, cx, cy, baseScale, perspective, zOff);
            const p2 = transformPoint(side.x2, side.y2, layerZ, angles, cx, cy, baseScale, perspective, zOff);
            const p3 = transformPoint(side.x2, side.y2, layerZ + layerThickness, angles, cx, cy, baseScale, perspective, zOff);
            const p4 = transformPoint(side.x1, side.y1, layerZ + layerThickness, angles, cx, cy, baseScale, perspective, zOff);
            const n = faceNormal(p1, p2, p3);
            if (isFrontFacing(n)) {
              const l = calcLighting(n, 0.5);
              faces.push({ depth: (p1.z+p2.z+p3.z+p4.z)/4 + 0.1, draw: () => {
                drawQuad(p1, p2, p3, p4, shadeRGBA(color.r, color.g, color.b, edgeAlpha * 0.8, l), shadeRGBA(color.r-30, color.g-30, color.b-20, edgeAlpha * 0.4, l), 0.2);
              }});
            }
          });
        }
      }

      // --- TOP SURFACE: Transistor plane + functional blocks + passivation ---
      const topZ = metalBaseZ + (CHIP.metalLayers - 1) * CHIP.metalSpacing + passH;
      
      // Passivation / top dielectric
      {
        const p1 = transformPoint(-hw, -hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const p2 = transformPoint( hw, -hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const p3 = transformPoint( hw,  hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const p4 = transformPoint(-hw,  hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const n = faceNormal(p1, p2, p3);
        if (isFrontFacing(n)) {
          const l = calcLighting(n, 0.75);
          faces.push({ depth: (p1.z+p2.z+p3.z+p4.z)/4, draw: () => {
            // Base silicon tone
            drawQuad(p1, p2, p3, p4, shadeColor(75, 82, 98, l * 0.95), shadeColor(120, 128, 145, l * 0.7), 1.0);
            
            // Transistor grid pattern
            ctx.save();
            // Build transform for pattern space
            const patternAlpha = clamp(l * 0.8, 0.2, 0.9);
            
            transistorPattern.forEach(cell => {
              if (cell.type === 'empty') return;
              const cp1 = transformPoint(cell.x, cell.y, topZ + 0.02, angles, cx, cy, baseScale, perspective, zOff);
              const cp2 = transformPoint(cell.x + cell.w, cell.y, topZ + 0.02, angles, cx, cy, baseScale, perspective, zOff);
              const cp3 = transformPoint(cell.x + cell.w, cell.y + cell.h, topZ + 0.02, angles, cx, cy, baseScale, perspective, zOff);
              const cp4 = transformPoint(cell.x, cell.y + cell.h, topZ + 0.02, angles, cx, cy, baseScale, perspective, zOff);
              
              if (cell.type === 'gate') {
                ctx.fillStyle = shadeRGBA(210, 150, 70, patternAlpha * cell.density * 0.8, l);
                ctx.beginPath();
                ctx.moveTo(cp1.x, cp1.y);
                ctx.lineTo(cp2.x, cp2.y);
                ctx.lineTo(cp3.x, cp3.y);
                ctx.lineTo(cp4.x, cp4.y);
                ctx.closePath();
                ctx.fill();
              } else if (cell.type === 'block') {
                ctx.fillStyle = shadeRGBA(180, 185, 195, patternAlpha * 0.5, l);
                ctx.strokeStyle = shadeRGBA(210, 150, 70, patternAlpha * 0.6, l);
                ctx.lineWidth = 0.5 * cp1.scale;
                ctx.beginPath();
                ctx.moveTo(cp1.x, cp1.y);
                ctx.lineTo(cp2.x, cp2.y);
                ctx.lineTo(cp3.x, cp3.y);
                ctx.lineTo(cp4.x, cp4.y);
                ctx.closePath();
                ctx.fill();
                ctx.stroke();
              }
            });
            ctx.restore();
          }});
        }
      }

      // Functional blocks on top
      {
        const p1 = transformPoint(-hw, -hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const p2 = transformPoint( hw, -hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const p3 = transformPoint( hw,  hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const p4 = transformPoint(-hw,  hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const n = faceNormal(p1, p2, p3);
        if (isFrontFacing(n)) {
          const l = calcLighting(n, 0.65);
          faces.push({ depth: (p1.z+p2.z+p3.z+p4.z)/4 - 0.5, draw: () => {
            functionalBlocks.forEach(block => {
              const bp1 = transformPoint(block.x, block.y, topZ + 0.1, angles, cx, cy, baseScale, perspective, zOff);
              const bp2 = transformPoint(block.x + block.w, block.y, topZ + 0.1, angles, cx, cy, baseScale, perspective, zOff);
              const bp3 = transformPoint(block.x + block.w, block.y + block.h, topZ + 0.1, angles, cx, cy, baseScale, perspective, zOff);
              const bp4 = transformPoint(block.x, block.y + block.h, topZ + 0.1, angles, cx, cy, baseScale, perspective, zOff);
              
              if (block.type === 'core') {
                ctx.fillStyle = shadeRGBA(191, 109, 21, 0.35, l);
                ctx.strokeStyle = shadeRGBA(191, 109, 21, 0.7, l);
              } else if (block.type === 'cache') {
                ctx.fillStyle = shadeRGBA(150, 155, 165, 0.2, l);
                ctx.strokeStyle = shadeRGBA(180, 185, 195, 0.4, l);
              } else {
                ctx.fillStyle = shadeRGBA(100, 105, 115, 0.15, l);
                ctx.strokeStyle = shadeRGBA(140, 145, 155, 0.3, l);
              }
              ctx.lineWidth = 0.6 * bp1.scale;
              ctx.beginPath();
              ctx.moveTo(bp1.x, bp1.y);
              ctx.lineTo(bp2.x, bp2.y);
              ctx.lineTo(bp3.x, bp3.y);
              ctx.lineTo(bp4.x, bp4.y);
              ctx.closePath();
              ctx.fill();
              ctx.stroke();
              
              // Internal grid for blocks
              if (block.type !== 'bus') {
                ctx.strokeStyle = shadeRGBA(191, 109, 21, 0.15, l);
                ctx.lineWidth = 0.2 * bp1.scale;
                ctx.beginPath();
                for (let i = 1; i < 4; i++) {
                  const f = i / 4;
                  const lp1 = transformPoint(block.x + block.w * f, block.y, topZ + 0.12, angles, cx, cy, baseScale, perspective, zOff);
                  const lp2 = transformPoint(block.x + block.w * f, block.y + block.h, topZ + 0.12, angles, cx, cy, baseScale, perspective, zOff);
                  ctx.moveTo(lp1.x, lp1.y);
                  ctx.lineTo(lp2.x, lp2.y);
                  const lp3 = transformPoint(block.x, block.y + block.h * f, topZ + 0.12, angles, cx, cy, baseScale, perspective, zOff);
                  const lp4 = transformPoint(block.x + block.w, block.y + block.h * f, topZ + 0.12, angles, cx, cy, baseScale, perspective, zOff);
                  ctx.moveTo(lp3.x, lp3.y);
                  ctx.lineTo(lp4.x, lp4.y);
                }
                ctx.stroke();
              }
            });
          }});
        }
      }

      // --- TOP EDGE (chip boundary, metallic) ---
      const edgeFaces = [
        { a: {x:-hw,y:-hh,z:subTop}, b:{x:hw,y:-hh,z:subTop}, c:{x:hw,y:-hh,z:topZ}, d:{x:-hw,y:-hh,z:topZ} },
        { a: {x:hw,y:-hh,z:subTop}, b:{x:hw,y:hh,z:subTop}, c:{x:hw,y:hh,z:topZ}, d:{x:hw,y:-hh,z:topZ} },
        { a: {x:hw,y:hh,z:subTop}, b:{x:-hw,y:hh,z:subTop}, c:{x:-hw,y:hh,z:topZ}, d:{x:hw,y:hh,z:topZ} },
        { a: {x:-hw,y:hh,z:subTop}, b:{x:-hw,y:-hh,z:subTop}, c:{x:-hw,y:-hh,z:topZ}, d:{x:-hw,y:hh,z:topZ} },
      ];
      
      edgeFaces.forEach(side => {
        const p1 = transformPoint(side.a.x, side.a.y, side.a.z, angles, cx, cy, baseScale, perspective, zOff);
        const p2 = transformPoint(side.b.x, side.b.y, side.b.z, angles, cx, cy, baseScale, perspective, zOff);
        const p3 = transformPoint(side.c.x, side.c.y, side.c.z, angles, cx, cy, baseScale, perspective, zOff);
        const p4 = transformPoint(side.d.x, side.d.y, side.d.z, angles, cx, cy, baseScale, perspective, zOff);
        const n = faceNormal(p1, p2, p3);
        if (isFrontFacing(n)) {
          const l = calcLighting(n, 0.7);
          faces.push({ depth: (p1.z+p2.z+p3.z+p4.z)/4 - 0.2, draw: () => {
            // Metallic edge
            const grad = ctx.createLinearGradient(p1.x, p1.y, p4.x, p4.y);
            grad.addColorStop(0, shadeColor(170, 175, 185, l * 0.95));
            grad.addColorStop(0.5, shadeColor(210, 215, 225, l));
            grad.addColorStop(1, shadeColor(150, 155, 165, l * 0.85));
            drawQuad(p1, p2, p3, p4, grad, shadeColor(120, 125, 135, l * 0.7), 0.6);
            
            // Edge highlight line
            ctx.strokeStyle = shadeRGBA(240, 245, 255, 0.6 * l, 1);
            ctx.lineWidth = 1.0;
            ctx.beginPath();
            ctx.moveTo(p4.x, p4.y);
            ctx.lineTo(p3.x, p3.y);
            ctx.stroke();
          }});
        }
      });

      // --- I/O PINS ---
      ioPins.forEach(pin => {
        const pinLen = 10;
        const pinW = 2.5;
        let px, py, pz, dx, dy;
        
        if (pin.side === 'top') { px = pin.x; py = pin.y; dx = 0; dy = -1; pz = subTop + 5; }
        else if (pin.side === 'bottom') { px = pin.x; py = pin.y; dx = 0; dy = 1; pz = subTop + 5; }
        else if (pin.side === 'left') { px = pin.x; py = pin.y; dx = -1; dy = 0; pz = subTop + 5; }
        else { px = pin.x; py = pin.y; dx = 1; dy = 0; pz = subTop + 5; }
        
        const inner = transformPoint(px, py, pz, angles, cx, cy, baseScale, perspective, zOff);
        const outer = transformPoint(px + dx * pinLen, py + dy * pinLen, pz - 2, angles, cx, cy, baseScale, perspective, zOff);
        const n = { x: dx, y: dy, z: 0 };
        const l = calcLighting(n, 0.8);
        
        faces.push({ depth: (inner.z + outer.z) / 2 - 1, draw: () => {
          ctx.strokeStyle = shadeColor(210, 175, 100, l);
          ctx.lineWidth = Math.max(1.2, 2.5 * inner.scale);
          ctx.lineCap = 'round';
          ctx.beginPath();
          ctx.moveTo(inner.x, inner.y);
          ctx.lineTo(outer.x, outer.y);
          ctx.stroke();
          
          // Pin tip highlight
          ctx.fillStyle = shadeRGBA(255, 230, 170, 0.95, l);
          ctx.beginPath();
          ctx.arc(outer.x, outer.y, Math.max(1.2, 2 * outer.scale), 0, Math.PI * 2);
          ctx.fill();
        }});
      });

      // --- Seal ring (on top surface, near edge) ---
      {
        const inset = 5;
        const ringZ = topZ + 0.05;
        const corners = [
          transformPoint(-hw + inset, -hh + inset, ringZ, angles, cx, cy, baseScale, perspective, zOff),
          transformPoint( hw - inset, -hh + inset, ringZ, angles, cx, cy, baseScale, perspective, zOff),
          transformPoint( hw - inset,  hh - inset, ringZ, angles, cx, cy, baseScale, perspective, zOff),
          transformPoint(-hw + inset,  hh - inset, ringZ, angles, cx, cy, baseScale, perspective, zOff),
        ];
        const n = faceNormal(corners[0], corners[1], corners[2]);
        if (isFrontFacing(n)) {
          const l = calcLighting(n, 0.7);
          faces.push({ depth: corners[0].z - 0.8, draw: () => {
            ctx.strokeStyle = shadeRGBA(191, 109, 21, 0.5, l);
            ctx.lineWidth = 0.8 * corners[0].scale;
            ctx.setLineDash([3, 2]);
            ctx.beginPath();
            ctx.moveTo(corners[0].x, corners[0].y);
            ctx.lineTo(corners[1].x, corners[1].y);
            ctx.lineTo(corners[2].x, corners[2].y);
            ctx.lineTo(corners[3].x, corners[3].y);
            ctx.closePath();
            ctx.stroke();
            ctx.setLineDash([]);
          }});
        }
      }

      // --- Strong ambient glow behind chip ---
      {
        faces.push({ depth: 9999, draw: () => {
          const glowR = Math.min(W, H) * (0.3 + smoothScrollProgress * 0.2);
          const glowAlpha = 0.2 + smoothScrollProgress * 0.2;
          const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, glowR);
          grad.addColorStop(0, `rgba(191, 109, 21, ${glowAlpha})`);
          grad.addColorStop(0.3, `rgba(191, 109, 21, ${glowAlpha * 0.5})`);
          grad.addColorStop(1, 'rgba(191, 109, 21, 0)');
          ctx.fillStyle = grad;
          ctx.fillRect(0, 0, W, H);
        }});
      }

      // --- Subtle specular reflection on top surface ---
      {
        const p1 = transformPoint(-hw, -hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const p2 = transformPoint( hw, -hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const p3 = transformPoint( hw,  hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const p4 = transformPoint(-hw,  hh, topZ, angles, cx, cy, baseScale, perspective, zOff);
        const n = faceNormal(p1, p2, p3);
        if (isFrontFacing(n)) {
          const l = calcLighting(n, 0.5);
          faces.push({ depth: p1.z - 2, draw: () => {
            // Specular highlight
            const hx = lerp(p1.x, p3.x, 0.3);
            const hy = lerp(p1.y, p3.y, 0.25);
            const hr = Math.min(W, H) * 0.15 * baseScale;
            const grad = ctx.createRadialGradient(hx, hy, 0, hx, hy, hr);
            grad.addColorStop(0, shadeRGBA(255, 245, 225, 0.15 * l, 1));
            grad.addColorStop(1, shadeRGBA(255, 245, 225, 0, 1));
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, W, H);
          }});
        }
      }

      // --- Strong wireframe outline on top of everything ---
      {
        const hw = CHIP.w / 2, hh = CHIP.h / 2, t = CHIP.thickness;
        const outlineAlpha = 0.5 + smoothScrollProgress * 0.4;
        
        // Get all 8 corners
        const corners = [
          transformPoint(-hw, -hh, -t/2, angles, cx, cy, baseScale, perspective, zOff), // 0: BLB
          transformPoint( hw, -hh, -t/2, angles, cx, cy, baseScale, perspective, zOff), // 1: BRB
          transformPoint( hw,  hh, -t/2, angles, cx, cy, baseScale, perspective, zOff), // 2: FRB
          transformPoint(-hw,  hh, -t/2, angles, cx, cy, baseScale, perspective, zOff), // 3: FLB
          transformPoint(-hw, -hh,  t/2, angles, cx, cy, baseScale, perspective, zOff), // 4: BLT
          transformPoint( hw, -hh,  t/2, angles, cx, cy, baseScale, perspective, zOff), // 5: BRT
          transformPoint( hw,  hh,  t/2, angles, cx, cy, baseScale, perspective, zOff), // 6: FRT
          transformPoint(-hw,  hh,  t/2, angles, cx, cy, baseScale, perspective, zOff), // 7: FLT
        ];
        
        const edges = [
          [0,1],[1,2],[2,3],[3,0], // bottom
          [4,5],[5,6],[6,7],[7,4], // top
          [0,4],[1,5],[2,6],[3,7], // vertical
        ];
        
        faces.push({ depth: -100, draw: () => {
          ctx.strokeStyle = `rgba(191, 109, 21, ${outlineAlpha})`;
          ctx.lineWidth = 1.2;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          ctx.beginPath();
          edges.forEach(([a, b]) => {
            ctx.moveTo(corners[a].x, corners[a].y);
            ctx.lineTo(corners[b].x, corners[b].y);
          });
          ctx.stroke();
          
          // Corner dots
          ctx.fillStyle = `rgba(220, 180, 120, ${outlineAlpha})`;
          corners.forEach(c => {
            ctx.beginPath();
            ctx.arc(c.x, c.y, 1.8, 0, Math.PI * 2);
            ctx.fill();
          });
        }});
      }

      // --- Sort by depth (painter's algorithm) and draw ---
      faces.sort((a, b) => b.depth - a.depth);
      faces.forEach(f => f.draw());
    }

    // Background subtle grid
    function renderBackground() {
      // Subtle vignette
      const grad = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, Math.max(W, H) * 0.7);
      grad.addColorStop(0, 'rgba(30, 30, 30, 1)');
      grad.addColorStop(1, 'rgba(14, 14, 14, 1)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);
    }

    // Crosshair bracket overlay that scales with scroll
    function renderCrosshairOverlay() {
      const cx = W / 2;
      const cy = H / 2;
      const size = (60 + smoothScrollProgress * 80) * Math.min(W, H) / 800;
      const b = size / 2;
      const bracketLen = size * 0.2;
      const alpha = 0.15 + smoothScrollProgress * 0.12;
      
      ctx.strokeStyle = `rgba(191, 109, 21, ${alpha})`;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(cx - b, cy - b + bracketLen);
      ctx.lineTo(cx - b, cy - b);
      ctx.lineTo(cx - b + bracketLen, cy - b);
      ctx.moveTo(cx + b - bracketLen, cy - b);
      ctx.lineTo(cx + b, cy - b);
      ctx.lineTo(cx + b, cy - b + bracketLen);
      ctx.moveTo(cx - b, cy + b - bracketLen);
      ctx.lineTo(cx - b, cy + b);
      ctx.lineTo(cx - b + bracketLen, cy + b);
      ctx.moveTo(cx + b - bracketLen, cy + b);
      ctx.lineTo(cx + b, cy + b);
      ctx.lineTo(cx + b, cy + b - bracketLen);
      ctx.stroke();
    }

    // Main animation loop
    function render() {
      animTime++;
      
      // Calculate hero scroll progress (0 to 1 through the hero section)
      const scrollTop = scrollContainer.scrollTop;
      const heroHeight = window.innerHeight * 7; // 700vh
      heroScrollProgress = clamp(scrollTop / heroHeight, 0, 1);
      
      // Smooth interpolation for fluid motion
      smoothScrollProgress += (heroScrollProgress - smoothScrollProgress) * 0.08;
      
      ctx.clearRect(0, 0, W, H);
      renderBackground();
      renderChip();
      renderCrosshairOverlay();
      
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

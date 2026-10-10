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
  const scrollerEl = document.getElementById('scroller');

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

  // Timer
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
      scrollerCursor.style.visibility = 'visible';
    }
    
    scrollerPins.forEach((pin, i) => {
      setTimeout(() => {
        pin.style.visibility = 'visible';
      }, 1000 + i * 20);
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
  const partTexts = document.querySelectorAll('.part-text');
  
  function updatePartLabels() {
    const scrollTop = scrollContainer.scrollTop;
    const viewportHeight = scrollContainer.clientHeight;
    const scrollMax = scrollContainer.scrollHeight - viewportHeight;
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
      
      // Update label active state
      filmLayerLabels.forEach(l => l.classList.remove('active'));
      label.classList.add('active');
      
      // Update image visibility
      filmImages.forEach(img => {
        if (img.getAttribute('data-film-image') === targetLayer) {
          img.classList.add('active');
        } else {
          img.classList.remove('active');
        }
      });
    };

    label.addEventListener('mouseenter', activateLayer);
    label.addEventListener('click', activateLayer);
    label.addEventListener('touchstart', (e) => {
      e.preventDefault();
      activateLayer();
    });
  });

  // --- Animated counters for metrics ---
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
      
      if (isDecimal) {
        el.textContent = current.toFixed(2);
      } else {
        el.textContent = Math.round(current).toLocaleString();
      }
      
      if (progress < 1) {
        requestAnimationFrame(update);
      }
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

  // --- Set progress bar target widths ---
  document.querySelectorAll('.metric-bar-fill').forEach(bar => {
    const width = bar.style.width;
    if (width) {
      bar.style.setProperty('--target-width', width);
      bar.style.width = '0';
    }
  });

  document.querySelectorAll('.progress-fill').forEach(bar => {
    const style = bar.getAttribute('style');
    const match = style && style.match(/width:\s*([\d.]+%)/);
    if (match) {
      bar.style.setProperty('--target-width', match[1]);
      bar.style.width = '0';
    }
  });

  // --- Enhanced Canvas: Semiconductor Die Visualization ---
  const canvas = document.getElementById('silica-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let canvasWidth, canvasHeight;
    let scrollProgress = 0;
    let rotation = 0;
    let particles = [];
    let time = 0;

    function resizeCanvas() {
      canvasWidth = canvas.clientWidth = window.innerWidth;
      canvasHeight = canvas.clientHeight = window.innerHeight;
      canvas.width = canvasWidth * window.devicePixelRatio;
      canvas.height = canvasHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      initParticles();
    }

    function initParticles() {
      particles = [];
      const count = 100;
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * canvasWidth,
          y: Math.random() * canvasHeight,
          baseX: Math.random() * canvasWidth,
          baseY: Math.random() * canvasHeight,
          size: Math.random() * 1.5 + 0.5,
          speed: Math.random() * 0.0005 + 0.0002,
          phase: Math.random() * Math.PI * 2,
          opacity: Math.random() * 0.3 + 0.1
        });
      }
    }

    function drawDie(cx, cy, size, rot, alpha, stage) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rot);
      
      const half = size / 2;
      
      // Outer glow based on scroll progress
      if (scrollProgress > 0.1) {
        ctx.shadowColor = `rgba(191, 109, 21, ${0.15 * scrollProgress})`;
        ctx.shadowBlur = 40 * scrollProgress;
      }
      
      // Die outline
      ctx.strokeStyle = `rgba(200, 200, 200, ${0.25 * alpha})`;
      ctx.lineWidth = 1;
      ctx.strokeRect(-half, -half, size, size);
      
      ctx.shadowBlur = 0;
      
      const inner = size * 0.88;
      const innerHalf = inner / 2;
      
      // Scribe lines
      ctx.strokeStyle = `rgba(85, 85, 85, ${0.15 * alpha})`;
      ctx.lineWidth = 0.5;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(-half * 0.95, -half * 0.95, size * 0.95, size * 0.95);
      ctx.setLineDash([]);
      
      // Grid pattern - density increases with scroll
      const gridDivisions = Math.floor(4 + scrollProgress * 16);
      const gridSize = inner / gridDivisions;
      ctx.strokeStyle = `rgba(85, 85, 85, ${0.08 + scrollProgress * 0.08})`;
      ctx.lineWidth = 0.3;
      ctx.beginPath();
      for (let i = 1; i < gridDivisions; i++) {
        const pos = -innerHalf + i * gridSize;
        ctx.moveTo(pos, -innerHalf);
        ctx.lineTo(pos, innerHalf);
        ctx.moveTo(-innerHalf, pos);
        ctx.lineTo(innerHalf, pos);
      }
      ctx.stroke();
      
      // Core blocks - appear progressively
      if (scrollProgress > 0.15) {
        const blockAlpha = Math.min((scrollProgress - 0.15) * 2, 1) * alpha;
        
        // CPU blocks
        ctx.fillStyle = `rgba(191, 109, 21, ${0.22 * blockAlpha})`;
        ctx.strokeStyle = `rgba(191, 109, 21, ${0.4 * blockAlpha})`;
        ctx.lineWidth = 0.5;
        
        const bw = inner * 0.28;
        const bh = inner * 0.22;
        
        ctx.fillRect(-innerHalf * 0.8, -innerHalf * 0.7, bw, bh);
        ctx.strokeRect(-innerHalf * 0.8, -innerHalf * 0.7, bw, bh);
        
        ctx.fillRect(-innerHalf * 0.1, -innerHalf * 0.7, bw, bh);
        ctx.strokeRect(-innerHalf * 0.1, -innerHalf * 0.7, bw, bh);
        
        // Cache block
        ctx.fillStyle = `rgba(200, 200, 200, ${0.08 * blockAlpha})`;
        ctx.strokeStyle = `rgba(200, 200, 200, ${0.2 * blockAlpha})`;
        ctx.fillRect(innerHalf * 0.2, -innerHalf * 0.7, bw * 0.9, bh);
        ctx.strokeRect(innerHalf * 0.2, -innerHalf * 0.7, bw * 0.9, bh);
        
        // Memory array
        if (scrollProgress > 0.3) {
          const memAlpha = Math.min((scrollProgress - 0.3) * 2.5, 1) * alpha;
          ctx.fillStyle = `rgba(200, 200, 200, ${0.05 * memAlpha})`;
          ctx.strokeStyle = `rgba(200, 200, 200, ${0.12 * memAlpha})`;
          ctx.lineWidth = 0.3;
          
          const memSize = inner * 0.12;
          const gap = inner * 0.015;
          for (let row = 0; row < 2; row++) {
            for (let col = 0; col < 6; col++) {
              const mx = -innerHalf * 0.8 + col * (memSize + gap);
              const my = -innerHalf * 0.1 + row * (memSize + gap);
              ctx.fillRect(mx, my, memSize, memSize);
              ctx.strokeRect(mx, my, memSize, memSize);
            }
          }
        }
        
        // Peripheral blocks
        if (scrollProgress > 0.45) {
          const periAlpha = Math.min((scrollProgress - 0.45) * 2, 1) * alpha;
          ctx.fillStyle = `rgba(191, 109, 21, ${0.06 * periAlpha})`;
          ctx.strokeStyle = `rgba(191, 109, 21, ${0.18 * periAlpha})`;
          ctx.fillRect(-innerHalf * 0.8, innerHalf * 0.25, inner * 0.75, inner * 0.22);
          ctx.strokeRect(-innerHalf * 0.8, innerHalf * 0.25, inner * 0.75, inner * 0.22);
          
          ctx.fillRect(innerHalf * 0.05, innerHalf * 0.25, inner * 0.75, inner * 0.22);
          ctx.strokeRect(innerHalf * 0.05, innerHalf * 0.25, inner * 0.75, inner * 0.22);
        }
      }
      
      // Connection routing network - increases with scroll
      if (scrollProgress > 0.25) {
        const routeAlpha = Math.min((scrollProgress - 0.25) * 1.5, 1) * alpha;
        ctx.strokeStyle = `rgba(191, 109, 21, ${0.25 * routeAlpha})`;
        ctx.lineWidth = 0.4;
        ctx.beginPath();
        
        const routeCount = Math.floor(scrollProgress * 60);
        for (let i = 0; i < routeCount; i++) {
          const seed = i * 137.5;
          const x1 = -innerHalf + (Math.sin(seed) * 0.5 + 0.5) * inner;
          const y1 = -innerHalf + (Math.cos(seed * 1.3) * 0.5 + 0.5) * inner;
          const x2 = -innerHalf + (Math.sin(seed * 2.1) * 0.5 + 0.5) * inner;
          const y2 = -innerHalf + (Math.cos(seed * 0.7) * 0.5 + 0.5) * inner;
          
          // Manhattan routing
          const midX = (x1 + x2) / 2;
          ctx.moveTo(x1, y1);
          ctx.lineTo(midX, y1);
          ctx.lineTo(midX, y2);
          ctx.lineTo(x2, y2);
        }
        ctx.stroke();
      }
      
      // I/O pins around perimeter
      if (scrollProgress > 0.35) {
        const ioAlpha = Math.min((scrollProgress - 0.35) * 2, 1) * alpha;
        ctx.fillStyle = `rgba(200, 200, 200, ${0.3 * ioAlpha})`;
        const pinCount = 20;
        const pinSize = size * 0.012;
        const pinGap = (size * 0.9) / pinCount;
        
        for (let i = 0; i < pinCount; i++) {
          const pos = -half * 0.9 + i * pinGap + pinGap / 2;
          // Top
          ctx.fillRect(pos - pinSize/2, -half - pinSize, pinSize, pinSize * 0.8);
          // Bottom
          ctx.fillRect(pos - pinSize/2, half + pinSize * 0.2, pinSize, pinSize * 0.8);
        }
      }
      
      // Seal ring
      ctx.strokeStyle = `rgba(191, 109, 21, ${0.25 * alpha})`;
      ctx.lineWidth = 0.5;
      ctx.setLineDash([2, 2]);
      ctx.strokeRect(-half * 0.97, -half * 0.97, size * 0.97, size * 0.97);
      ctx.setLineDash([]);
      
      ctx.restore();
    }

    function drawOrbitingDice(cx, cy, baseSize, alpha) {
      if (scrollProgress < 0.4) return;
      
      const orbitAlpha = Math.min((scrollProgress - 0.4) * 1.8, 0.7) * alpha;
      const orbitRadius = baseSize * 0.75;
      const smallSize = baseSize * 0.18;
      const count = 3;
      
      for (let i = 0; i < count; i++) {
        const angle = rotation * (0.3 + i * 0.15) + (i * Math.PI * 2 / count);
        const wobble = Math.sin(time * 0.001 + i) * baseSize * 0.03;
        const ox = cx + Math.cos(angle) * (orbitRadius + wobble);
        const oy = cy + Math.sin(angle) * (orbitRadius + wobble);
        
        ctx.save();
        ctx.translate(ox, oy);
        ctx.rotate(-rotation * 0.2 + i);
        
        ctx.fillStyle = `rgba(191, 109, 21, ${0.1 * orbitAlpha})`;
        ctx.strokeStyle = `rgba(191, 109, 21, ${0.3 * orbitAlpha})`;
        ctx.lineWidth = 0.5;
        ctx.fillRect(-smallSize/2, -smallSize/2, smallSize, smallSize);
        ctx.strokeRect(-smallSize/2, -smallSize/2, smallSize, smallSize);
        
        // Mini grid
        ctx.strokeStyle = `rgba(85, 85, 85, ${0.2 * orbitAlpha})`;
        ctx.lineWidth = 0.2;
        ctx.beginPath();
        ctx.moveTo(-smallSize/4, -smallSize/2);
        ctx.lineTo(-smallSize/4, smallSize/2);
        ctx.moveTo(smallSize/4, -smallSize/2);
        ctx.lineTo(smallSize/4, smallSize/2);
        ctx.moveTo(-smallSize/2, 0);
        ctx.lineTo(smallSize/2, 0);
        ctx.stroke();
        
        ctx.restore();
      }
      
      // Orbit paths
      ctx.strokeStyle = `rgba(85, 85, 85, ${0.08 * orbitAlpha})`;
      ctx.lineWidth = 0.5;
      ctx.setLineDash([2, 4]);
      ctx.beginPath();
      ctx.arc(cx, cy, orbitRadius, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    function drawParticles() {
      particles.forEach(p => {
        // Orbit around center with scroll influence
        const radius = Math.sqrt(
          Math.pow(p.baseX - canvasWidth/2, 2) + 
          Math.pow(p.baseY - canvasHeight/2, 2)
        );
        const baseAngle = Math.atan2(p.baseY - canvasHeight/2, p.baseX - canvasWidth/2);
        const scrollAngle = scrollProgress * Math.PI * 2 * p.speed * 1000;
        
        p.x = canvasWidth/2 + Math.cos(baseAngle + scrollAngle + p.phase) * radius * (0.5 + scrollProgress * 0.5);
        p.y = canvasHeight/2 + Math.sin(baseAngle + scrollAngle + p.phase) * radius * (0.5 + scrollProgress * 0.5);
        
        ctx.fillStyle = `rgba(191, 109, 21, ${p.opacity * (0.2 + scrollProgress * 0.8)})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (0.5 + scrollProgress * 0.5), 0, Math.PI * 2);
        ctx.fill();
      });
      
      // Connection lines between nearby particles
      if (scrollProgress > 0.2) {
        ctx.strokeStyle = `rgba(85, 85, 85, ${0.08 * scrollProgress})`;
        ctx.lineWidth = 0.3;
        const maxDist = 80 + scrollProgress * 40;
        for (let i = 0; i < particles.length; i++) {
          for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < maxDist) {
              ctx.beginPath();
              ctx.moveTo(particles[i].x, particles[i].y);
              ctx.lineTo(particles[j].x, particles[j].y);
              ctx.stroke();
            }
          }
        }
      }
    }

    function drawCrosshairOverlay() {
      const cx = canvasWidth / 2;
      const cy = canvasHeight / 2;
      const size = 60 + scrollProgress * 80;
      
      ctx.strokeStyle = `rgba(191, 109, 21, ${0.1 + scrollProgress * 0.1})`;
      ctx.lineWidth = 0.5;
      
      const b = size / 2;
      const bracketLen = size * 0.2;
      
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

    function render() {
      time++;
      ctx.clearRect(0, 0, canvasWidth, canvasHeight);
      
      // Update scroll progress
      const scrollTop = scrollContainer.scrollTop;
      const scrollMax = scrollContainer.scrollHeight - scrollContainer.clientHeight;
      scrollProgress = Math.min(scrollTop / (scrollMax * 0.45), 1);
      
      rotation += 0.0015 + scrollProgress * 0.004;
      
      // Draw particles first (background)
      drawParticles();
      
      // Main die
      const cx = canvasWidth / 2;
      const cy = canvasHeight / 2;
      const baseSize = Math.min(canvasWidth, canvasHeight) * 0.4;
      const size = baseSize * (0.55 + scrollProgress * 0.45);
      const alpha = 0.25 + scrollProgress * 0.75;
      
      // Determine stage based on scroll progress
      const stage = scrollProgress < 0.2 ? 0 : 
                  scrollProgress < 0.4 ? 1 : 
                  scrollProgress < 0.6 ? 2 : 
                  scrollProgress < 0.8 ? 3 : 4;
      
      drawDie(cx, cy, size, rotation * 0.08, alpha, stage);
      
      // Orbiting secondary dice
      drawOrbitingDice(cx, cy, baseSize, alpha);
      
      drawCrosshairOverlay();
      
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
        scrollContainer.scrollTo({
          top: target.offsetTop,
          behavior: 'smooth'
        });
      }
    });
  });

  // --- Initial triggers ---
  setTimeout(() => {
    checkReveal();
    updatePartLabels();
    updateScrollIndicator();
  }, 200);

  if (scrollerEl) {
    setTimeout(() => {
      scrollerEl.style.opacity = '1';
    }, 1500);
  }

})();

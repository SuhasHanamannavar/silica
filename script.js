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
  const scrollerPins = document.querySelectorAll('[data-scroller-pin], .scroll-pins .pin');
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
    
    // Show scroller pins after a delay
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

  // --- Part labels visibility based on scroll ---
  const partLabels = document.querySelectorAll('.part-label-item');
  const partTexts = document.querySelectorAll('.part-text');
  
  function updatePartLabels() {
    const scrollTop = scrollContainer.scrollTop;
    const viewportHeight = scrollContainer.clientHeight;
    const scrollPct = scrollTop / (scrollContainer.scrollHeight - viewportHeight);
    
    // Show part labels progressively as user scrolls through hero section
    partLabels.forEach((label, i) => {
      const triggerPct = 0.05 + (i * 0.08);
      if (scrollPct > triggerPct) {
        label.classList.add('visible');
      }
    });
  }

  scrollContainer.addEventListener('scroll', updatePartLabels);

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

  // Observe metric cards and trigger counter animation
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

  // --- Set progress bar target widths from inline style ---
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

  // --- Canvas: Semiconductor Die Visualization ---
  const canvas = document.getElementById('silica-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let canvasWidth, canvasHeight;
    let scrollProgress = 0;
    let rotation = 0;
    let particles = [];

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
      const count = 80;
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * canvasWidth,
          y: Math.random() * canvasHeight,
          size: Math.random() * 2 + 0.5,
          speedX: (Math.random() - 0.5) * 0.15,
          speedY: (Math.random() - 0.5) * 0.15,
          opacity: Math.random() * 0.3 + 0.1
        });
      }
    }

    function drawDie(cx, cy, size, rot, alpha) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rot);
      
      const half = size / 2;
      
      // Outer die shadow/glow
      ctx.shadowColor = 'rgba(191, 109, 21, 0.2)';
      ctx.shadowBlur = 30 * scrollProgress;
      
      // Die outline
      ctx.strokeStyle = `rgba(200, 200, 200, ${0.3 * alpha})`;
      ctx.lineWidth = 1;
      ctx.strokeRect(-half, -half, size, size);
      
      ctx.shadowBlur = 0;
      
      // Inner die area
      const inner = size * 0.85;
      const innerHalf = inner / 2;
      
      // Grid pattern inside die
      ctx.strokeStyle = `rgba(85, 85, 85, ${0.15 * alpha})`;
      ctx.lineWidth = 0.5;
      const gridSize = size / 12;
      ctx.beginPath();
      for (let i = -5; i <= 5; i++) {
        ctx.moveTo(i * gridSize, -innerHalf);
        ctx.lineTo(i * gridSize, innerHalf);
        ctx.moveTo(-innerHalf, i * gridSize);
        ctx.lineTo(innerHalf, i * gridSize);
      }
      ctx.stroke();
      
      // Core blocks
      const blocks = [
        { x: -innerHalf * 0.6, y: -innerHalf * 0.5, w: inner * 0.35, h: inner * 0.3, color: 'rgba(191, 109, 21, 0.25)' },
        { x: innerHalf * 0.05, y: -innerHalf * 0.5, w: inner * 0.35, h: inner * 0.3, color: 'rgba(191, 109, 21, 0.2)' },
        { x: -innerHalf * 0.6, y: innerHalf * 0.05, w: inner * 0.35, h: inner * 0.3, color: 'rgba(200, 200, 200, 0.1)' },
        { x: innerHalf * 0.05, y: innerHalf * 0.05, w: inner * 0.35, h: inner * 0.3, color: 'rgba(200, 200, 200, 0.08)' },
      ];
      
      blocks.forEach(block => {
        ctx.fillStyle = block.color.replace(')', `, ${alpha})`).replace('rgba', 'rgba').replace(/,\s*[\d.]+\)/, `, ${parseFloat(block.color.match(/[\d.]+\)/)[0]) * alpha})`);
        // Simpler approach:
        const baseColor = block.color;
        const colorMatch = baseColor.match(/rgba?\(([^)]+)\)/);
        if (colorMatch) {
          const parts = colorMatch[1].split(',').map(s => s.trim());
          ctx.fillStyle = `rgba(${parts[0]}, ${parts[1]}, ${parts[2]}, ${parseFloat(parts[3]) * alpha})`;
        }
        ctx.fillRect(block.x, block.y, block.w, block.h);
        ctx.strokeStyle = `rgba(191, 109, 21, ${0.3 * alpha})`;
        ctx.lineWidth = 0.5;
        ctx.strokeRect(block.x, block.y, block.w, block.h);
      });
      
      // Connection lines between blocks (increases with scroll)
      const connectionCount = Math.floor(scrollProgress * 20);
      ctx.strokeStyle = `rgba(191, 109, 21, ${0.4 * alpha})`;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      for (let i = 0; i < connectionCount; i++) {
        const x1 = -innerHalf + Math.random() * inner;
        const y1 = -innerHalf + Math.random() * inner;
        const x2 = -innerHalf + Math.random() * inner;
        const y2 = -innerHalf + Math.random() * inner;
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
      }
      ctx.stroke();
      
      // Seal ring
      ctx.strokeStyle = `rgba(191, 109, 21, ${0.3 * alpha})`;
      ctx.lineWidth = 0.5;
      ctx.setLineDash([3, 3]);
      ctx.strokeRect(-half * 0.95, -half * 0.95, size * 0.95, size * 0.95);
      ctx.setLineDash([]);
      
      ctx.restore();
    }

    function drawParticles() {
      particles.forEach(p => {
        p.x += p.speedX;
        p.y += p.speedY;
        
        if (p.x < 0) p.x = canvasWidth;
        if (p.x > canvasWidth) p.x = 0;
        if (p.y < 0) p.y = canvasHeight;
        if (p.y > canvasHeight) p.y = 0;
        
        ctx.fillStyle = `rgba(191, 109, 21, ${p.opacity * (0.3 + scrollProgress * 0.7)})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      });
      
      // Draw connection lines between nearby particles
      ctx.strokeStyle = `rgba(85, 85, 85, ${0.1 * scrollProgress})`;
      ctx.lineWidth = 0.3;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }
    }

    function drawCrosshairOverlay() {
      const cx = canvasWidth / 2;
      const cy = canvasHeight / 2;
      const size = 60 + scrollProgress * 40;
      
      ctx.strokeStyle = `rgba(191, 109, 21, ${0.15 + scrollProgress * 0.1})`;
      ctx.lineWidth = 0.5;
      
      // Corner brackets around center
      const b = size / 2;
      const bracketLen = size * 0.2;
      
      ctx.beginPath();
      // TL
      ctx.moveTo(cx - b, cy - b + bracketLen);
      ctx.lineTo(cx - b, cy - b);
      ctx.lineTo(cx - b + bracketLen, cy - b);
      // TR
      ctx.moveTo(cx + b - bracketLen, cy - b);
      ctx.lineTo(cx + b, cy - b);
      ctx.lineTo(cx + b, cy - b + bracketLen);
      // BL
      ctx.moveTo(cx - b, cy + b - bracketLen);
      ctx.lineTo(cx - b, cy + b);
      ctx.lineTo(cx - b + bracketLen, cy + b);
      // BR
      ctx.moveTo(cx + b - bracketLen, cy + b);
      ctx.lineTo(cx + b, cy + b);
      ctx.lineTo(cx + b, cy + b - bracketLen);
      ctx.stroke();
    }

    function render() {
      ctx.clearRect(0, 0, canvasWidth, canvasHeight);
      
      // Update scroll progress
      const scrollTop = scrollContainer.scrollTop;
      const scrollMax = scrollContainer.scrollHeight - scrollContainer.clientHeight;
      scrollProgress = Math.min(scrollTop / (scrollMax * 0.4), 1); // Most action in first 40% of scroll
      
      rotation += 0.001 + scrollProgress * 0.003;
      
      // Draw particles
      drawParticles();
      
      // Draw die - scales in with scroll
      const cx = canvasWidth / 2;
      const cy = canvasHeight / 2;
      const baseSize = Math.min(canvasWidth, canvasHeight) * 0.35;
      const size = baseSize * (0.6 + scrollProgress * 0.4);
      const alpha = 0.3 + scrollProgress * 0.7;
      
      drawDie(cx, cy, size, rotation * 0.1, alpha);
      
      // Draw secondary smaller dice orbiting
      if (scrollProgress > 0.3) {
        const orbitAlpha = Math.min((scrollProgress - 0.3) * 2, 0.6);
        const orbitRadius = baseSize * 0.8;
        const smallSize = baseSize * 0.2;
        
        for (let i = 0; i < 3; i++) {
          const angle = rotation * (0.5 + i * 0.2) + (i * Math.PI * 2 / 3);
          const ox = cx + Math.cos(angle) * orbitRadius;
          const oy = cy + Math.sin(angle) * orbitRadius;
          drawDie(ox, oy, smallSize, -rotation * 0.3, orbitAlpha);
        }
      }
      
      drawCrosshairOverlay();
      
      requestAnimationFrame(render);
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    requestAnimationFrame(render);
  }

  // --- Layer interaction in anatomy section ---
  const layers = document.querySelectorAll('.layer');
  layers.forEach(layer => {
    layer.addEventListener('mouseenter', () => {
      layers.forEach(l => {
        if (l !== layer) {
          l.style.opacity = '0.4';
        }
      });
      layer.style.transform = 'scale(1.01)';
      layer.style.zIndex = '10';
    });
    
    layer.addEventListener('mouseleave', () => {
      layers.forEach(l => {
        l.style.opacity = '1';
        l.style.transform = 'none';
        l.style.zIndex = 'auto';
      });
    });
  });

  // --- Smooth scroll for any anchor links ---
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

  // --- Initial reveal for elements already in view ---
  setTimeout(() => {
    checkReveal();
    updatePartLabels();
    updateScrollIndicator();
  }, 200);

  // Show scroller after initial load
  setTimeout(() => {
    if (scrollerEl) {
      scrollerEl.style.opacity = '1';
    }
  }, 1500);

})();

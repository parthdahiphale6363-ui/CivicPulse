/* ============================================================
   CIVICPULSE — PREMIUM ANIMATIONS ENGINE
   ============================================================ */

/**
 * 3D Mouse Tracker for Cards
 * Fixed bug where event object was missing in update method
 */
class MouseTracker {
    constructor() {
        this.cards = [];
    }

    init() {
        this.cards = document.querySelectorAll('.card-3d');
        if (this.cards.length === 0) return;

        /* Disabled per user request 
        document.addEventListener('mousemove', (e) => {
            this.update3dCards(e);
        });
        */
    }

    update3dCards(e) {
        this.cards.forEach(card => {
            const rect = card.getBoundingClientRect();
            const cardCenterX = rect.left + rect.width / 2;
            const cardCenterY = rect.top + rect.height / 2;

            // Sensitivity adjustment based on distance from object
            const rotateX = (e.clientY - cardCenterY) * 0.02;
            const rotateY = (cardCenterX - e.clientX) * 0.02;

            card.style.transform = `
                perspective(1000px)
                rotateX(${rotateX}deg) 
                rotateY(${rotateY}deg) 
                translateZ(10px)
            `;
        });
    }
}

/**
 * Magnetic Attraction for Primary Buttons
 */
class MagneticInteraction {
    constructor() {
        this.buttons = [];
    }

    init() {
        this.buttons = document.querySelectorAll('.btn-primary, .btn-nav-register, .ai-fab');
        this.buttons.forEach(btn => {
            btn.addEventListener('mousemove', (e) => this.move(e, btn));
            btn.addEventListener('mouseleave', () => this.reset(btn));
        });
    }

    move(e, btn) {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;

        // Move button 30% towards the mouse
        btn.style.transform = `translate(${x * 0.3}px, ${y * 0.3}px)`;
        
        // Move icon slightly more for "organic" feel
        const icon = btn.querySelector('i');
        if (icon) {
            icon.style.transform = `translate(${x * 0.15}px, ${y * 0.15}px)`;
            icon.style.transition = 'none';
        }
    }

    reset(btn) {
        btn.style.transform = 'translate(0, 0)';
        btn.style.transition = 'transform 0.5s cubic-bezier(0.23, 1, 0.32, 1)';
        const icon = btn.querySelector('i');
        if (icon) {
            icon.style.transform = 'translate(0, 0)';
            icon.style.transition = 'transform 0.5s cubic-bezier(0.23, 1, 0.32, 1)';
        }
    }
}

const mouseTracker = new MouseTracker();
const magneticInteraction = new MagneticInteraction();

document.addEventListener('DOMContentLoaded', () => {
    mouseTracker.init();
    magneticInteraction.init();
});

// ============================================================
// PARALLAX SCROLLING
// ============================================================

class ParallaxScroll {
    constructor() {
        this.elements = [];
        this.scrollProgress = 0;
    }

    init() {
        this.elements = document.querySelectorAll('[data-parallax]');
        if (this.elements.length === 0) return;

        window.addEventListener('scroll', () => this.update());
        this.update();
    }

    update() {
        this.scrollProgress = window.scrollY;

        this.elements.forEach(el => {
            const speed = parseFloat(el.dataset.parallax) || 0.5;
            const yPos = -this.scrollProgress * speed;
            el.style.transform = `translateY(${yPos}px)`;
        });
    }
}

const parallax = new ParallaxScroll();
document.addEventListener('DOMContentLoaded', () => parallax.init());


// ============================================================
// ADVANCED SCROLL REVEAL & TEXT EFFECTS
// ============================================================

class ScrollReveal {
    constructor() {
        this.observer = null;
    }

    init() {
        const observerOptions = {
            threshold: [0, 0.2, 0.4, 0.6, 0.8, 1],
            rootMargin: '0px 0px -10% 0px'
        };

        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                }
            });
        }, observerOptions);

        this.observeElements();
    }

    observeElements() {
        const selectors = [
            '.reveal', '.reveal-left', '.reveal-right', '.reveal-scale', 
            '.reveal-bounce', '.reveal-flip', '.reveal-zoom-rotate', 
            '.reveal-slide-left', '.reveal-slide-right', '.reveal-blur',
            '.stagger-item', '.text-reveal', '.stat-number'
        ];
        
        document.querySelectorAll(selectors.join(',')).forEach(el => {
            this.observer.observe(el);
        });
    }
}

const scrollReveal = new ScrollReveal();
document.addEventListener('DOMContentLoaded', () => scrollReveal.init());


// ============================================================
// GLOBAL UI COMPONENTS (Back to Top, Progress Bar)
// ============================================================

function initGlobalUI() {
    // 1. Create Top Progress Bar
    const progressBar = document.createElement('div');
    progressBar.id = 'topProgressBar';
    document.body.appendChild(progressBar);

    // 2. Create Back to Top Button
    const backToTop = document.createElement('div');
    backToTop.className = 'back-to-top';
    backToTop.innerHTML = '<i class="fas fa-chevron-up"></i>';
    document.body.appendChild(backToTop);

    backToTop.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // 3. Scroll Events
    window.addEventListener('scroll', () => {
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrollPercent = (window.scrollY / docHeight) * 100;
        
        // Update progress bar
        progressBar.style.width = scrollPercent + '%';

        // Update back to top visibility
        if (window.scrollY > 500) {
            backToTop.classList.add('visible');
        } else {
            backToTop.classList.remove('visible');
        }
        
        // Update Navbar transparency
        const navbar = document.getElementById('navbar');
        if (navbar) {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }
    });

    // 4. Skeleton Loader Simulation (Remove after actual content loads)
    const skeletons = document.querySelectorAll('.skeleton');
    if (skeletons.length > 0) {
        window.addEventListener('load', () => {
            setTimeout(() => {
                skeletons.forEach(s => s.classList.add('skeleton-hidden'));
            }, 1500);
        });
    }
}

document.addEventListener('DOMContentLoaded', initGlobalUI);


// ============================================================
// STAT COUNTER ANIMATION
// ============================================================

function initCounterAnimation() {
    const counters = document.querySelectorAll('.stat-number');
    
    const countObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.dataset.counted) {
                entry.target.dataset.counted = 'true';
                animateValue(entry.target);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(c => countObserver.observe(c));
}

function animateValue(obj) {
    const target = parseInt(obj.innerText.replace(/,/g, ''));
    let current = 0;
    const duration = 2000;
    const start = performance.now();

    function step(timestamp) {
        const progress = Math.min((timestamp - start) / duration, 1);
        const value = Math.floor(progress * target);
        obj.innerText = value.toLocaleString();
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            obj.innerText = target.toLocaleString();
        }
    }
    window.requestAnimationFrame(step);
}

document.addEventListener('DOMContentLoaded', initCounterAnimation);


// ============================================================
// OPTIMIZATIONS & UTILS
// ============================================================

function debounce(func, wait) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Handle visibility change to save CPU
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        document.body.classList.add('animations-paused');
    } else {
        document.body.classList.remove('animations-paused');
    }
});

// Expose utils
window.animationUtils = {
    debounce,
    mouseTracker,
    magneticInteraction,
    scrollReveal
};
/* ============================================================
   CIVICPULSE — Main JavaScript
   ============================================================ */

// ---------- Page Loader ----------
window.addEventListener('load', () => {
    const loader = document.getElementById('pageLoader');
    if (loader) {
        setTimeout(() => {
            loader.classList.add('hidden');
        }, 2000);
    }
});

// ---------- Navbar Scroll Effect ----------
const navbar = document.getElementById('navbar');
if (navbar) {
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    });
}

// ---------- Mobile Nav Toggle ----------
const navToggle = document.getElementById('navToggle');
const navMenu = document.getElementById('navMenu');
if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        navToggle.classList.toggle('active');
    });

    // Close menu on link click
    document.querySelectorAll('.nav-link:not(.nav-dropdown-toggle)').forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            navToggle.classList.remove('active');
        });
    });
}

// ---------- Nav Dropdown Toggle (for touch / mobile) ----------
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-dropdown-toggle').forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const dropdown = toggle.closest('.nav-dropdown');
            // Close other dropdowns
            document.querySelectorAll('.nav-dropdown.active').forEach(d => {
                if (d !== dropdown) d.classList.remove('active');
            });
            dropdown.classList.toggle('active');
        });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.nav-dropdown')) {
            document.querySelectorAll('.nav-dropdown.active').forEach(d => {
                d.classList.remove('active');
            });
        }
    });
});

// ---------- Scroll Reveal Animations ----------
function initScrollReveal() {
    const reveals = document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    reveals.forEach(el => observer.observe(el));
}

document.addEventListener('DOMContentLoaded', initScrollReveal);

// ---------- Flash Messages Auto-dismiss ----------
document.addEventListener('DOMContentLoaded', () => {
    const flashes = document.querySelectorAll('.flash-message');
    flashes.forEach((flash, index) => {
        setTimeout(() => {
            flash.style.animation = 'flashSlideIn 0.4s ease-out reverse';
            setTimeout(() => flash.remove(), 400);
        }, 4000 + (index * 500));
    });
});

// ---------- Counter Animation ----------
function animateCounters() {
    const counters = document.querySelectorAll('.stat-number, .dash-stat-value');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = entry.target;
                const finalValue = parseInt(target.textContent) || 0;

                if (target.dataset.animated) return;
                target.dataset.animated = 'true';

                let current = 0;
                const duration = 1500;
                const step = finalValue / (duration / 16);

                const timer = setInterval(() => {
                    current += step;
                    if (current >= finalValue) {
                        current = finalValue;
                        clearInterval(timer);
                    }
                    target.textContent = Math.floor(current);
                }, 16);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(counter => observer.observe(counter));
}

document.addEventListener('DOMContentLoaded', animateCounters);

// ---------- Upvote Handler (1 member can upvote only once) ----------
function upvoteComplaint(id, btn) {
    if (!btn || btn.disabled) return;
    
    fetch(`/upvote/${id}`)
        .then(res => res.json().then(data => ({ status: res.status, data })))
        .then(({ status, data }) => {
            const countEl = btn.querySelector('.upvote-count');
            const labelEl = btn.querySelector('.upvote-label');
            
            if (data.success) {
                if (countEl) {
                    countEl.textContent = data.upvotes !== undefined ? data.upvotes : (parseInt(countEl.textContent || '0') + 1);
                }
                if (labelEl) {
                    labelEl.textContent = 'Upvoted';
                }
                btn.classList.add('upvoted');
                btn.disabled = true;
                btn.title = "You have already upvoted this complaint";
            } else if (data.requires_login || status === 401) {
                alert("Please log in to upvote complaints.");
                window.location.href = "/login";
            } else if (data.already_upvoted) {
                alert(data.message || "You have already upvoted this complaint.");
                if (countEl && data.upvotes !== undefined) {
                    countEl.textContent = data.upvotes;
                }
                if (labelEl) {
                    labelEl.textContent = 'Upvoted';
                }
                btn.classList.add('upvoted');
                btn.disabled = true;
                btn.title = "You have already upvoted this complaint";
            } else {
                alert(data.message || "Could not process upvote.");
            }
        })
        .catch(err => {
            console.error('Upvote failed:', err);
            alert("Network error while upvoting. Please try again.");
        });
}

// ---------- Smooth Scroll for Anchor Links ----------
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// ---------- AI Chat Functions ----------
let chatInput, chatMessages, chatSendBtn;

function initChat() {
    chatInput = document.getElementById('chatInput');
    chatMessages = document.getElementById('chatMessages');
    chatSendBtn = document.getElementById('chatSendBtn');

    if (!chatInput || !chatMessages) return;

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });

    if (chatSendBtn) {
        chatSendBtn.addEventListener('click', sendChatMessage);
    }

    // Suggestion clicks
    document.querySelectorAll('.chat-suggestion').forEach(btn => {
        btn.addEventListener('click', () => {
            chatInput.value = btn.textContent;
            sendChatMessage();
        });
    });
}

function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // Add user message
    addChatMessage(message, 'user');
    chatInput.value = '';
    chatSendBtn.disabled = true;

    // Show typing indicator
    const typingId = showTypingIndicator();

    // Send to API
    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
    })
        .then(res => res.json())
        .then(data => {
            removeTypingIndicator(typingId);
            addChatMessage(data.response, 'ai', data.sources);
            chatSendBtn.disabled = false;

            // Hide suggestions after first message
            const suggestions = document.querySelector('.chat-suggestions');
            if (suggestions) suggestions.style.display = 'none';
        })
        .catch(err => {
            removeTypingIndicator(typingId);
            addChatMessage('Sorry, I encountered an error. Please try again.', 'ai');
            chatSendBtn.disabled = false;
        });
}

function addChatMessage(text, type, sources) {
    const div = document.createElement('div');
    div.className = `chat-message ${type}`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.innerHTML = type === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';

    // Format AI response with line breaks
    if (type === 'ai') {
        bubble.innerHTML = formatAIResponse(text);
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'chat-sources';
            sourcesDiv.style.marginTop = '12px';
            sourcesDiv.style.padding = '8px 12px';
            sourcesDiv.style.background = 'rgba(16, 185, 129, 0.12)';
            sourcesDiv.style.border = '1px solid rgba(16, 185, 129, 0.35)';
            sourcesDiv.style.borderRadius = '8px';
            sourcesDiv.style.fontSize = '11.5px';
            sourcesDiv.style.color = '#e2e8f0';
            sourcesDiv.style.display = 'flex';
            sourcesDiv.style.flexWrap = 'wrap';
            sourcesDiv.style.alignItems = 'center';
            sourcesDiv.style.gap = '6px';
            
            const titleSpan = document.createElement('span');
            titleSpan.innerHTML = '<strong style="color:#34d399; display:inline-flex; align-items:center; gap:4px;"><i class="fas fa-certificate"></i> Verified Knowledge:</strong>';
            sourcesDiv.appendChild(titleSpan);

            sources.forEach((s) => {
                const sName = s.title || s.source || 'Civic Knowledge';
                if (s.source_url) {
                    const a = document.createElement('a');
                    a.href = s.source_url;
                    a.target = '_blank';
                    a.rel = 'noopener noreferrer';
                    a.innerHTML = `<i class="fas fa-external-link-alt" style="font-size:10px; margin-right:3px;"></i>${escapeHTML(sName)}`;
                    a.style.cssText = 'color:#38bdf8; background:rgba(56,189,248,0.12); border:1px solid rgba(56,189,248,0.25); padding:2px 8px; border-radius:12px; text-decoration:none; display:inline-flex; align-items:center;';
                    sourcesDiv.appendChild(a);
                } else {
                    const span = document.createElement('span');
                    span.textContent = sName;
                    span.style.cssText = 'color:#cbd5e1; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); padding:2px 8px; border-radius:12px;';
                    sourcesDiv.appendChild(span);
                }
            });
            bubble.appendChild(sourcesDiv);
        }
    } else {
        bubble.textContent = text;
    }

    div.appendChild(avatar);
    div.appendChild(bubble);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHTML(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatAIResponse(text) {
    if (!text) return '';
    // HTML-escape text first before converting markdown-like formatting to HTML
    let escaped = escapeHTML(text);
    return escaped
        .replace(/\[(.*?)\]\(((?:https?:\/\/|\/)[^\s"'>]+)\)/g, '<a href="$2" class="chat-link" target="_blank" rel="noopener noreferrer">$1</a>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n- /g, '<br>• ')
        .replace(/\n\d+\. /g, (match) => '<br>' + match.trim() + ' ')
        .replace(/\n/g, '<br>');
}

function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.className = 'chat-message ai';
    div.id = id;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';
    avatar.innerHTML = '<i class="fas fa-robot"></i>';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble typing-indicator';
    bubble.innerHTML = '<span></span><span></span><span></span>';

    div.appendChild(avatar);
    div.appendChild(bubble);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

document.addEventListener('DOMContentLoaded', initChat);

// ---------- Dashboard AI Summary ----------
function loadDashboardSummary() {
    const container = document.getElementById('aiSummaryContent');
    if (!container) return;

    fetch('/api/dashboard-summary')
        .then(res => res.json())
        .then(data => {
            container.innerHTML = formatAIResponse(data.summary);
        })
        .catch(() => {
            container.innerHTML = '<span style="color: var(--text-muted);">Unable to load AI summary.</span>';
        });
}

document.addEventListener('DOMContentLoaded', loadDashboardSummary);

// ---------- AI Analyze Complaint ----------
function analyzeComplaint(id) {
    const container = document.getElementById('aiAnalysis');
    if (!container) return;

    container.innerHTML = '<div class="ai-summary-loading"><div class="dot-pulse"><span></span><span></span><span></span></div> Analyzing complaint...</div>';

    fetch(`/api/analyze/${id}`)
        .then(res => res.json())
        .then(data => {
            container.innerHTML = formatAIResponse(data.analysis);
        })
        .catch(() => {
            container.innerHTML = 'Unable to analyze complaint.';
        });
}

// ---------- Dashboard Charts ----------
function initDashboardCharts() {
    if (typeof Chart === 'undefined') return;

    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            // Priority Distribution Chart
            const priorityCtx = document.getElementById('priorityChart');
            if (priorityCtx) {
                new Chart(priorityCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['High', 'Medium', 'Low'],
                        datasets: [{
                            data: [data.high, data.medium, data.low],
                            backgroundColor: [
                                'rgba(239, 68, 68, 0.8)',
                                'rgba(245, 158, 11, 0.8)',
                                'rgba(16, 185, 129, 0.8)'
                            ],
                            borderColor: [
                                'rgba(239, 68, 68, 1)',
                                'rgba(245, 158, 11, 1)',
                                'rgba(16, 185, 129, 1)'
                            ],
                            borderWidth: 2,
                            hoverOffset: 8
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: { color: '#94a3b8', padding: 16, font: { family: 'Inter' } }
                            }
                        },
                        cutout: '65%'
                    }
                });
            }

            // Status Chart
            const statusCtx = document.getElementById('statusChart');
            if (statusCtx) {
                new Chart(statusCtx, {
                    type: 'bar',
                    data: {
                        labels: ['Pending', 'Resolved'],
                        datasets: [{
                            label: 'Complaints',
                            data: [data.pending, data.resolved],
                            backgroundColor: [
                                'rgba(245, 158, 11, 0.6)',
                                'rgba(16, 185, 129, 0.6)'
                            ],
                            borderColor: [
                                'rgba(245, 158, 11, 1)',
                                'rgba(16, 185, 129, 1)'
                            ],
                            borderWidth: 2,
                            borderRadius: 8,
                            barThickness: 60
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: { color: 'rgba(148, 163, 184, 0.05)' },
                                ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                            },
                            x: {
                                grid: { display: false },
                                ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                            }
                        }
                    }
                });
            }

            // Category Chart
            const categoryCtx = document.getElementById('categoryChart');
            if (categoryCtx && data.categories.length > 0) {
                const colors = [
                    'rgba(99, 102, 241, 0.7)',
                    'rgba(6, 182, 212, 0.7)',
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(245, 158, 11, 0.7)',
                    'rgba(16, 185, 129, 0.7)',
                    'rgba(168, 85, 247, 0.7)',
                    'rgba(236, 72, 153, 0.7)'
                ];
                new Chart(categoryCtx, {
                    type: 'polarArea',
                    data: {
                        labels: data.categories.map(c => c.name),
                        datasets: [{
                            data: data.categories.map(c => c.count),
                            backgroundColor: colors.slice(0, data.categories.length),
                            borderWidth: 2,
                            borderColor: 'rgba(15, 23, 42, 0.5)'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: { color: '#94a3b8', padding: 12, font: { family: 'Inter', size: 11 } }
                            }
                        },
                        scales: {
                            r: {
                                grid: { color: 'rgba(148, 163, 184, 0.07)' },
                                ticks: { display: false }
                            }
                        }
                    }
                });
            }
        })
        .catch(err => console.error('Failed to load chart data:', err));
}

document.addEventListener('DOMContentLoaded', initDashboardCharts);

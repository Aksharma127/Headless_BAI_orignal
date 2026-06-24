/**
 * BAI Ghost User Visualizer (ghost-overlay.js)
 * Premium, interactive simulation engine for visualizing ML cohort behaviors.
 * 
 * Injects a sleek glassmorphism floating control panel allowing evaluators to 
 * spawn simulated "Ghost Users" (Bargain Hunters, Feature Researchers, Proof Seekers).
 * Replays realistic Bezier-curved pointer movements and clicks with custom ripple 
 * animations, directly triggering the BAI FLIP Actuator to showcase live layout adaptation.
 */

(function() {
    // Prevent duplicate injection
    if (window.BAIGhostVisualizer) return;

    // Define simulated cohort personas and their target section preferences
    const COHORTS = {
        bargain_hunter: {
            name: "🛍️ Bargain Hunter",
            desc: "Focuses heavily on pricing tiers and discount callouts.",
            color: "#10b981", // Emerald green
            targetSections: ['pricing', 'cta', 'hero'],
            optimizedOrder: ['pricing', 'cta', 'hero', 'features', 'testimonials']
        },
        feature_researcher: {
            name: "🔬 Feature Researcher",
            desc: "Thoroughly inspects technical feature grids and capabilities.",
            color: "#3b82f6", // Blue
            targetSections: ['features', 'hero', 'pricing'],
            optimizedOrder: ['features', 'hero', 'pricing', 'testimonials', 'cta']
        },
        proof_seeker: {
            name: "⭐ Proof Seeker",
            desc: "Seeks social proof, user testimonials, and validation.",
            color: "#8b5cf6", // Purple
            targetSections: ['testimonials', 'hero', 'cta'],
            optimizedOrder: ['testimonials', 'hero', 'features', 'pricing', 'cta']
        }
    };

    class GhostVisualizer {
        constructor() {
            this.activeGhost = null;
            this.isSimulating = false;
            this.init();
        }

        init() {
            this.injectStyles();
            this.injectControlPanel();
            this.createGhostCursor();
            this.setupEventListeners();
        }

        injectStyles() {
            const styleId = 'bai-ghost-styles';
            if (document.getElementById(styleId)) return;

            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
                /* Floating Glassmorphism Panel */
                #bai-ghost-panel {
                    position: fixed;
                    bottom: 24px;
                    right: 24px;
                    width: 340px;
                    background: rgba(17, 24, 39, 0.85);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05);
                    color: #f3f4f6;
                    font-family: 'Inter', system-ui, -apple-system, sans-serif;
                    z-index: 999999;
                    overflow: hidden;
                    transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.4s ease;
                }

                #bai-ghost-panel.minimized {
                    transform: translateY(calc(100% - 64px));
                }

                .bai-panel-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 16px 20px;
                    background: rgba(255, 255, 255, 0.05);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    cursor: pointer;
                    user-select: none;
                }

                .bai-panel-title {
                    font-size: 0.95rem;
                    font-weight: 700;
                    letter-spacing: -0.025em;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .bai-badge {
                    background: #3b82f6;
                    color: #ffffff;
                    font-size: 0.65rem;
                    font-weight: 800;
                    padding: 2px 6px;
                    border-radius: 8px;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }

                .bai-toggle-btn {
                    background: none;
                    border: none;
                    color: #9ca3af;
                    cursor: pointer;
                    transition: color 0.2s;
                }

                .bai-toggle-btn:hover {
                    color: #f3f4f6;
                }

                .bai-panel-body {
                    padding: 20px;
                }

                .bai-section-title {
                    font-size: 0.75rem;
                    font-weight: 600;
                    color: #9ca3af;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: 12px;
                }

                .bai-cohort-list {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }

                .bai-cohort-card {
                    display: flex;
                    flex-direction: column;
                    padding: 12px 14px;
                    background: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .bai-cohort-card:hover {
                    background: rgba(255, 255, 255, 0.08);
                    border-color: rgba(255, 255, 255, 0.2);
                    transform: translateY(-2px);
                }

                .bai-cohort-card.active {
                    border-color: #3b82f6;
                    background: rgba(59, 130, 246, 0.15);
                    box-shadow: 0 0 15px rgba(59, 130, 246, 0.3);
                }

                .bai-cohort-name {
                    font-size: 0.85rem;
                    font-weight: 600;
                    color: #ffffff;
                }

                .bai-cohort-desc {
                    font-size: 0.75rem;
                    color: #9ca3af;
                    margin-top: 4px;
                    line-height: 1.4;
                }

                .bai-status-box {
                    margin-top: 16px;
                    padding: 12px;
                    background: rgba(0, 0, 0, 0.25);
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    font-size: 0.8rem;
                }

                .bai-status-row {
                    display: flex;
                    justify_content: space-between;
                    align-items: center;
                    margin-bottom: 6px;
                }
                .bai-status-row:last-child { margin-bottom: 0; }

                .bai-status-label { color: #9ca3af; }
                .bai-status-value { font-weight: 600; font-family: monospace; }

                /* Ghost Cursor Element */
                #bai-ghost-cursor {
                    position: fixed;
                    top: 0;
                    left: 0;
                    pointer-events: none;
                    z-index: 9999999;
                    opacity: 0;
                    transition: opacity 0.3s ease;
                }

                .bai-cursor-svg {
                    width: 28px;
                    height: 28px;
                    filter: drop-shadow(0 4px 8px rgba(0,0,0,0.5));
                    transform: rotate(-15deg);
                }

                .bai-cursor-label {
                    position: absolute;
                    left: 24px;
                    top: 16px;
                    background: rgba(17, 24, 39, 0.9);
                    backdrop-filter: blur(8px);
                    border: 1px solid #3b82f6;
                    color: #ffffff;
                    font-size: 0.65rem;
                    font-weight: 700;
                    padding: 4px 8px;
                    border-radius: 12px;
                    white-space: nowrap;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                }

                /* Click Ripple Effect */
                .bai-ripple {
                    position: fixed;
                    pointer-events: none;
                    width: 40px;
                    height: 40px;
                    margin-left: -20px;
                    margin-top: -20px;
                    border: 2px solid #3b82f6;
                    border-radius: 50%;
                    z-index: 9999998;
                    animation: bai-ripple-anim 0.6s cubic-bezier(0.1, 0.8, 0.3, 1) forwards;
                }

                @keyframes bai-ripple-anim {
                    0% { transform: scale(0.1); opacity: 1; }
                    100% { transform: scale(2); opacity: 0; }
                }

                /* Section Highlight during simulation */
                .bai-simulated-focus {
                    position: relative;
                }
                .bai-simulated-focus::after {
                    content: '';
                    position: absolute;
                    top: 0; left: 0; right: 0; bottom: 0;
                    border: 2px dashed #3b82f6;
                    background: rgba(59, 130, 246, 0.05);
                    pointer-events: none;
                    animation: bai-pulse 1.5s infinite;
                    z-index: 9999;
                }

                @keyframes bai-pulse {
                    0% { opacity: 0.3; }
                    50% { opacity: 0.8; }
                    100% { opacity: 0.3; }
                }
            `;
            document.head.appendChild(style);
        }

        injectControlPanel() {
            const panel = document.createElement('div');
            panel.id = 'bai-ghost-panel';
            panel.innerHTML = `
                <div class="bai-panel-header" id="bai-panel-header">
                    <div class="bai-panel-title">
                        <span>👻 Ghost User ML Sim</span>
                        <span class="bai-badge">Live</span>
                    </div>
                    <button class="bai-toggle-btn" id="bai-toggle-btn">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                </div>
                <div class="bai-panel-body">
                    <div class="bai-section-title">Select Persona Cohort</div>
                    <div class="bai-cohort-list">
                        ${Object.entries(COHORTS).map(([id, c]) => `
                            <div class="bai-cohort-card" data-cohort="${id}">
                                <div class="bai-cohort-name">${c.name}</div>
                                <div class="bai-cohort-desc">${c.desc}</div>
                            </div>
                        `).join('')}
                    </div>
                    <div class="bai-status-box">
                        <div class="bai-status-row">
                            <span class="bai-status-label">Engine State</span>
                            <span class="bai-status-value" id="bai-sim-state" style="color: #10b981;">Ready</span>
                        </div>
                        <div class="bai-status-row">
                            <span class="bai-status-label">Simulated Clicks</span>
                            <span class="bai-status-value" id="bai-sim-clicks">0</span>
                        </div>
                        <div class="bai-status-row">
                            <span class="bai-status-label">Layout Status</span>
                            <span class="bai-status-value" id="bai-sim-layout">Default</span>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }

        createGhostCursor() {
            const cursor = document.createElement('div');
            cursor.id = 'bai-ghost-cursor';
            cursor.innerHTML = `
                <svg class="bai-cursor-svg" viewBox="0 0 24 24" fill="#3b82f6" xmlns="http://www.w3.org/2000/svg">
                    <path d="M3 3L10 21L13 14L20 11L3 3Z" stroke="#ffffff" stroke-width="2" stroke-linejoin="round"/>
                </svg>
                <div class="bai-cursor-label" id="bai-cursor-label">Ghost Persona</div>
            `;
            document.body.appendChild(cursor);
            this.ghostCursor = cursor;
            this.cursorLabel = cursor.querySelector('#bai-cursor-label');
            this.cursorSvg = cursor.querySelector('.bai-cursor-svg');
        }

        setupEventListeners() {
            const panelHeader = document.getElementById('bai-panel-header');
            const panel = document.getElementById('bai-ghost-panel');
            panelHeader.addEventListener('click', () => {
                panel.classList.toggle('minimized');
                const btn = document.getElementById('bai-toggle-btn');
                btn.style.transform = panel.classList.contains('minimized') ? 'rotate(180deg)' : 'rotate(0deg)';
            });

            document.querySelectorAll('.bai-cohort-card').forEach(card => {
                card.addEventListener('click', () => {
                    if (this.isSimulating) return;
                    const cohortId = card.getAttribute('data-cohort');
                    this.startSimulation(cohortId, card);
                });
            });

            // Listen for Actuator updates
            window.addEventListener('bai-layout-updated', (e) => {
                const layoutEl = document.getElementById('bai-sim-layout');
                if (layoutEl) layoutEl.textContent = "Optimized (FLIP)";
            });
        }

        async startSimulation(cohortId, cardElement) {
            if (this.isSimulating) return;
            this.isSimulating = true;

            // Update UI state
            document.querySelectorAll('.bai-cohort-card').forEach(c => c.classList.remove('active'));
            cardElement.classList.add('active');
            document.getElementById('bai-sim-state').textContent = "Simulating...";
            document.getElementById('bai-sim-state').style.color = "#3b82f6";
            document.getElementById('bai-sim-clicks').textContent = "0";
            document.getElementById('bai-sim-layout').textContent = "Pending Reorder...";

            const cohort = COHORTS[cohortId];
            this.cursorLabel.textContent = cohort.name;
            this.cursorLabel.style.borderColor = cohort.color;
            this.cursorSvg.setAttribute('fill', cohort.color);

            this.ghostCursor.style.opacity = "1";

            // Execute simulated click tour across preferred sections
            let clickCount = 0;
            for (const sectionId of cohort.targetSections) {
                const section = document.getElementById(sectionId);
                if (!section) continue;

                // Scroll section into view gracefully
                section.scrollIntoView({ behavior: 'smooth', block: 'center' });
                await this.sleep(600); // Wait for scroll to settle

                const rect = section.getBoundingClientRect();
                // Pick a random interactive target position inside the section
                const targetX = rect.left + (rect.width * (0.2 + Math.random() * 0.6));
                const targetY = rect.top + (rect.height * (0.3 + Math.random() * 0.4));

                // Smooth Bezier movement to target
                await this.moveCursorTo(targetX, targetY, 800);
                
                // Highlight section
                section.classList.add('bai-simulated-focus');

                // Perform 2 rapid exploratory clicks in the section
                for (let i = 0; i < 2; i++) {
                    const clickX = targetX + (Math.random() * 40 - 20);
                    const clickY = targetY + (Math.random() * 40 - 20);
                    await this.moveCursorTo(clickX, clickY, 300);
                    this.createRipple(clickX, clickY, cohort.color);

                    // Dispatch simulated pointerdown event for sensor.js to capture
                    const event = new PointerEvent('pointerdown', {
                        clientX: clickX, clientY: clickY,
                        bubbles: true, cancelable: true, pointerType: 'mouse'
                    });
                    document.dispatchEvent(event);

                    clickCount++;
                    document.getElementById('bai-sim-clicks').textContent = clickCount;
                    await this.sleep(300);
                }

                await this.sleep(400);
                section.classList.remove('bai-simulated-focus');
            }

            // Hide ghost cursor
            this.ghostCursor.style.opacity = "0";
            await this.sleep(500);

            // Trigger BAI Actuator to execute FLIP reorder with the cohort's optimized order
            if (window.BAIActuator && typeof window.BAIActuator.reorder === 'function') {
                console.log(`[BAI Ghost Sim] Triggering Actuator for ${cohort.name}`);
                await window.BAIActuator.reorder(cohort.optimizedOrder);
            } else {
                console.warn("[BAI Ghost Sim] window.BAIActuator not found; ensure actuator.js is loaded.");
                document.getElementById('bai-sim-layout').textContent = "Actuator Missing";
            }

            // Reset simulation state
            document.getElementById('bai-sim-state').textContent = "Complete";
            document.getElementById('bai-sim-state').style.color = "#10b981";
            this.isSimulating = false;
        }

        moveCursorTo(targetX, targetY, duration) {
            return new Promise(resolve => {
                const startX = parseFloat(this.ghostCursor.style.left || window.innerWidth / 2);
                const startY = parseFloat(this.ghostCursor.style.top || window.innerHeight / 2);
                const deltaX = targetX - startX;
                const deltaY = targetY - startY;
                const startTime = performance.now();

                const animate = (currentTime) => {
                    const elapsed = currentTime - startTime;
                    const progress = Math.min(elapsed / duration, 1);

                    // Cubic Bezier Easing (EaseInOut)
                    const ease = progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;

                    const currentX = startX + (deltaX * ease);
                    const currentY = startY + (deltaY * ease);

                    this.ghostCursor.style.left = `${currentX}px`;
                    this.ghostCursor.style.top = `${currentY}px`;

                    if (progress < 1) {
                        requestAnimationFrame(animate);
                    } else {
                        resolve();
                    }
                };
                requestAnimationFrame(animate);
            });
        }

        createRipple(x, y, color) {
            const ripple = document.createElement('div');
            ripple.className = 'bai-ripple';
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            ripple.style.borderColor = color;
            document.body.appendChild(ripple);
            setTimeout(() => ripple.remove(), 700);
        }

        sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    }

    // Initialize and expose globally
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.BAIGhostVisualizer = new GhostVisualizer(), { once: true });
    } else {
        window.BAIGhostVisualizer = new GhostVisualizer();
    }
})();

/**
 * BAI FLIP Actuator (actuator.js)
 * High-performance, visually spectacular DOM layout reordering engine.
 * 
 * Uses the FLIP (First, Last, Invert, Play) animation technique to smoothly 
 * transition page sections to their ML-optimized order without layout thrashing.
 * 
 * Capabilities:
 * - Real-time FLIP animation with smooth cubic-bezier easing
 * - Prefers-reduced-motion compliance (instant reorder fallback)
 * - Auto-fetches from FastAPI /api/layout or static cache fallback
 * - Exposes window.BAIActuator for manual triggering and demo visualizers
 */

(function() {
    const config = window.BAI_CONFIG || {};
    const MAIN_CONTAINER_ID = config.mainContainerId || 'main';
    
    // Default to localhost API, fallback to static cache file if offline
    const defaultLayoutEndpoint = window.location.protocol.startsWith('http')
        ? `${window.location.protocol}//${window.location.hostname}:8000/api/layout`
        : 'http://127.0.0.1:8000/api/layout';
    const LAYOUT_ENDPOINT = config.layoutEndpoint || defaultLayoutEndpoint;
    const FALLBACK_CACHE_URL = config.fallbackCacheUrl || '../cache/layout_order.json';

    // Check if user prefers reduced motion (Accessibility compliance)
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    class FLIPActuator {
        constructor(containerId) {
            this.containerId = containerId;
            this.isAnimating = false;
        }

        getContainer() {
            return document.getElementById(this.containerId);
        }

        /**
         * Fetch the latest layout order from the backend API.
         * Gracefully degrades to static cache file if the live API is unreachable.
         */
        async fetchLayoutOrder() {
            try {
                const res = await fetch(LAYOUT_ENDPOINT, {
                    headers: { 'Accept': 'application/json' },
                    cache: 'no-store'
                });
                if (!res.ok) throw new Error(`API returned ${res.status}`);
                const data = await res.json();
                
                // If API returned the full schema object, extract layout_order
                if (data && Array.isArray(data.layout_order)) {
                    console.log(`[BAI Actuator] Fetched layout order (source: ${data.source})`);
                    return data.layout_order;
                }
                if (Array.isArray(data)) {
                    return data;
                }
                throw new Error("Invalid layout format returned from API");
            } catch (err) {
                console.warn(`[BAI Actuator] Live API unreachable (${err.message}), attempting fallback cache...`);
                try {
                    const fallbackRes = await fetch(FALLBACK_CACHE_URL, { cache: 'no-store' });
                    const fallbackData = await fallbackRes.json();
                    if (Array.isArray(fallbackData)) {
                        console.log("[BAI Actuator] Fetched layout order from fallback cache.");
                        return fallbackData;
                    }
                    if (fallbackData && Array.isArray(fallbackData.layout_order)) {
                        return fallbackData.layout_order;
                    }
                } catch (fallbackErr) {
                    console.error("[BAI Actuator] All layout order fetches failed:", fallbackErr);
                }
                return null;
            }
        }

        /**
         * Execute the FLIP animation to reorder sections in the DOM.
         * @param {string[]} newOrder - Array of section IDs in the target order
         */
        async reorder(newOrder) {
            if (!newOrder || !Array.isArray(newOrder) || newOrder.length === 0) return;
            if (this.isAnimating) {
                console.warn("[BAI Actuator] Reorder requested while animation in progress; skipping.");
                return;
            }

            const container = this.getContainer();
            if (!container) {
                console.error(`[BAI Actuator] Container #${this.containerId} not found.`);
                return;
            }

            // Filter out valid child elements present in the DOM
            const childElements = Array.from(container.children).filter(el => el.id);
            if (childElements.length === 0) return;

            // Check if DOM is already in the target order
            const currentOrder = childElements.map(el => el.id);
            let isAlreadyOrdered = true;
            let targetIndex = 0;
            for (const id of newOrder) {
                const el = document.getElementById(id);
                if (el && el.parentElement === container) {
                    if (currentOrder[targetIndex] !== id) {
                        isAlreadyOrdered = false;
                        break;
                    }
                    targetIndex++;
                }
            }
            if (isAlreadyOrdered) {
                console.log("[BAI Actuator] DOM is already in optimized order.");
                return;
            }

            // ACCESSIBILITY & SAFETY: If reduced motion is requested, reorder instantly without FLIP
            if (prefersReducedMotion) {
                newOrder.forEach(id => {
                    const el = document.getElementById(id);
                    if (el && el.parentElement === container) container.appendChild(el);
                });
                console.log("[BAI Actuator] Reordered instantly (prefers-reduced-motion).");
                return;
            }

            this.isAnimating = true;

            // ============================================================
            // 1. FIRST: Measure initial bounding boxes
            // ============================================================
            const firstRects = new Map();
            childElements.forEach(el => {
                firstRects.set(el.id, el.getBoundingClientRect());
            });

            // ============================================================
            // 2. LAST: Move elements to their new DOM positions
            // ============================================================
            newOrder.forEach(id => {
                const el = document.getElementById(id);
                if (el && el.parentElement === container) {
                    container.appendChild(el);
                }
            });

            // Ensure footer remains at the very bottom if present
            const footer = document.getElementById('footer');
            if (footer && footer.parentElement === container) {
                container.appendChild(footer);
            }

            // Read new bounding boxes
            const lastRects = new Map();
            childElements.forEach(el => {
                lastRects.set(el.id, el.getBoundingClientRect());
            });

            // ============================================================
            // 3. INVERT: Calculate delta and apply instant transforms
            // ============================================================
            childElements.forEach(el => {
                const first = firstRects.get(el.id);
                const last = lastRects.get(el.id);
                if (!first || !last) return;

                const deltaX = first.left - last.left;
                const deltaY = first.top - last.top;

                // Instantly warp element back to initial position
                el.style.transition = 'none';
                el.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
            });

            // Force reflow so the browser commits the inverted positions
            container.getBoundingClientRect();

            // ============================================================
            // 4. PLAY: Enable transitions and snap to 0,0
            // ============================================================
            requestAnimationFrame(() => {
                childElements.forEach(el => {
                    // Smooth, premium easing curve (Expo / Deceleration)
                    el.style.transition = 'transform 0.65s cubic-bezier(0.22, 1, 0.36, 1)';
                    el.style.transform = 'translate(0, 0)';

                    // Optional visual highlight during transition
                    el.classList.add('bai-animating');
                });

                // Cleanup styles after animation finishes
                setTimeout(() => {
                    childElements.forEach(el => {
                        el.style.transition = '';
                        el.style.transform = '';
                        el.classList.remove('bai-animating');
                    });
                    this.isAnimating = false;
                    console.log("[BAI Actuator] FLIP animation complete.");
                    
                    // Dispatch custom event for visualizers/overlays
                    window.dispatchEvent(new CustomEvent('bai-layout-updated', {
                        detail: { layoutOrder: newOrder }
                    }));
                }, 700); // Slightly longer than transition duration
            });
        }

        async fetchAndReorder() {
            const order = await this.fetchLayoutOrder();
            if (order) {
                await this.reorder(order);
            }
        }
    }

    // Initialize and expose globally
    const actuator = new FLIPActuator(MAIN_CONTAINER_ID);
    window.BAIActuator = actuator;

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => actuator.fetchAndReorder(), { once: true });
    } else {
        actuator.fetchAndReorder();
    }
})();

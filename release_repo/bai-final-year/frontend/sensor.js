(function() {
    const config = window.BAI_CONFIG || {};
    const API_ENDPOINT = config.endpoint || 'http://127.0.0.1:8000/api/sync';
    const FLUSH_INTERVAL_MS = Number(config.flushIntervalMs || 5000);
    const MAX_BUFFERED_EVENTS = Number(config.maxBufferedEvents || 500);
    
    let clickBuffer = [];

    // STRICT PRIVACY SURVIVAL (Ad-blocker / Incognito Fallback)
    // If localStorage is blocked, the try/catch falls back to a temporary memory variable 
    // so the script doesn't crash the host website.
    let sessionId;
    try {
        sessionId = localStorage.getItem('bai_session');
        if (!sessionId) {
            sessionId = crypto.randomUUID();
            localStorage.setItem('bai_session', sessionId);
        }
    } catch (e) {
        if (!window.bai_temp_session) {
            window.bai_temp_session = crypto.randomUUID();
        }
        sessionId = window.bai_temp_session;
    }

    // FIX 3: TOUCHSCREEN BLINDSPOT
    // 'pointerdown' natively captures mouse, touch, and stylus events.
    document.addEventListener('pointerdown', (e) => {
        if (clickBuffer.length >= MAX_BUFFERED_EVENTS) {
            clickBuffer.shift();
        }
        clickBuffer.push({
            x: Math.round(e.clientX),
            y: Math.round(e.clientY),
            t: Date.now()
        });
    }, { passive: true }); // passive: true ensures we never block the UI scrolling thread

    function flushTelemetry() {
        if (clickBuffer.length === 0) return;

        // NETWORK RETRY LOGIC (Data Preservation)
        // Make a copy of the array before clearing it to prevent data loss if the network drops.
        const payloadData = [...clickBuffer];
        clickBuffer = []; 

        const payload = {
            session_id: sessionId,
            // FIX 4: LOCAL FILE PROTOCOL
            // If opened via file:///, hostname is blank. This fallback prevents FastAPI Pydantic crashes.
            domain: window.location.hostname || "local_file_test", 
            viewport: {
                w: window.innerWidth,
                h: window.innerHeight
            },
            interactions: payloadData
        };

        const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });

        // FIX 2: sendBeacon PAYLOAD LIMITS
        // sendBeacon returns 'false' if the browser blocks it due to payload size limits.
        if (navigator.sendBeacon && navigator.sendBeacon(API_ENDPOINT, blob)) {
            return; 
        }

        // Fallback to standard fetch if beacon fails or payload is too large
        fetch(API_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            keepalive: true // Tells the browser to finish the request even if the tab closes
        }).catch(() => {
            // THE CRITICAL FAILSAFE: 
            // If the user's WiFi drops, the fetch fails. We push the lost data 
            // back to the front of the queue to try again in 5 seconds.
            clickBuffer = [...payloadData, ...clickBuffer].slice(-MAX_BUFFERED_EVENTS);
        });
    }

    // Triggers
    setInterval(flushTelemetry, FLUSH_INTERVAL_MS);
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') flushTelemetry();
    });
})();

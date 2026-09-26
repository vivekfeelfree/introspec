document.addEventListener('DOMContentLoaded', () => {
    const backendSelect = document.getElementById('backendSelect');
    const apiKeyGroup = document.getElementById('apiKeyGroup');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const initialSpeakerSelect = document.getElementById('initialSpeakerSelect');
    const iterationsInput = document.getElementById('iterationsInput');
    const iterVal = document.getElementById('iterVal');

    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const welcomeStartBtn = document.getElementById('welcomeStartBtn');

    const pauseBtn = document.getElementById('pauseBtn');
    const targetPersonaSelect = document.getElementById('targetPersonaSelect');
    const interruptionInput = document.getElementById('interruptionInput');
    const sendInterruptionBtn = document.getElementById('sendInterruptionBtn');

    const menuToggleBtn = document.getElementById('menuToggleBtn');
    const closeSidebarBtn = document.getElementById('closeSidebarBtn');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const metricTurns = document.getElementById('metricTurns');
    const metricDepth = document.getElementById('metricDepth');
    const metricWords = document.getElementById('metricWords');

    const chatContainer = document.getElementById('chatContainer');
    const reportStatus = document.getElementById('reportStatus');
    const downloadGroup = document.getElementById('downloadGroup');

    const btnMd = document.getElementById('btnMd');
    const btnJson = document.getElementById('btnJson');
    const btnHtml = document.getElementById('btnHtml');

    let pollInterval = null;
    let renderedTurnCount = 0;
    let activeThinkingCard = null;
    let isPaused = false;

    // Mobile Drawer Handlers
    function openSidebar() {
        sidebar.classList.add('open');
        sidebarOverlay.classList.add('active');
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    }

    if (menuToggleBtn) menuToggleBtn.addEventListener('click', openSidebar);
    if (closeSidebarBtn) closeSidebarBtn.addEventListener('click', closeSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

    // Toggle API Key input display
    backendSelect.addEventListener('change', () => {
        const val = backendSelect.value;
        if (['gemini', 'openai', 'anthropic'].includes(val)) {
            apiKeyGroup.style.display = 'block';
        } else {
            apiKeyGroup.style.display = 'none';
        }
    });

    // Range slider label
    iterationsInput.addEventListener('input', () => {
        const val = parseInt(iterationsInput.value);
        iterVal.textContent = val === 0 ? 'Unlimited' : `${val} turns`;
    });

    // Launch Session Trigger Function
    async function launchSession() {
        closeSidebar();
        const maxIters = parseInt(iterationsInput.value);
        const payload = {
            max_iterations: maxIters === 0 ? null : maxIters,
            time_limit: null,
            initial_speaker: initialSpeakerSelect.value,
            backend_provider: backendSelect.value,
            gemini_api_key: apiKeyInput.value,
            openai_api_key: apiKeyInput.value,
            anthropic_api_key: apiKeyInput.value,
        };

        startBtn.disabled = true;
        stopBtn.disabled = false;
        renderedTurnCount = 0;
        downloadGroup.style.display = 'none';
        reportStatus.textContent = 'Session starting...';

        chatContainer.innerHTML = '';
        showThinkingIndicator('Initializing Indra & Ilavarasan human dialogue...');

        try {
            const resp = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (data.error) {
                showErrorCard(data.error);
                startBtn.disabled = false;
                stopBtn.disabled = true;
                return;
            }

            startPolling();
        } catch (err) {
            showErrorCard('Failed to connect to Introspec server: ' + err.message);
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }

    startBtn.addEventListener('click', launchSession);
    if (welcomeStartBtn) welcomeStartBtn.addEventListener('click', launchSession);

    // Stop Orchestration
    stopBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/stop', { method: 'POST' });
            reportStatus.textContent = 'Stop requested... completing active turn.';
        } catch (err) {
            console.error(err);
        }
    });

    // Pause / Resume Controls
    pauseBtn.addEventListener('click', async () => {
        try {
            const endpoint = isPaused ? '/api/resume' : '/api/pause';
            const resp = await fetch(endpoint, { method: 'POST' });
            const data = await resp.json();
            if (data.is_paused !== undefined) {
                isPaused = data.is_paused;
                updatePauseButtonState(isPaused);
            }
        } catch (err) {
            console.error(err);
        }
    });

    function updatePauseButtonState(paused) {
        isPaused = paused;
        if (isPaused) {
            pauseBtn.textContent = '▶️ Resume Auto';
            pauseBtn.classList.remove('btn-outline');
            pauseBtn.classList.add('btn-accent');
        } else {
            pauseBtn.textContent = '⏸️ Pause';
            pauseBtn.classList.remove('btn-accent');
            pauseBtn.classList.add('btn-outline');
        }
    }

    // Interruption / Message Injection
    async function sendInterruption() {
        const msg = interruptionInput.value.trim();
        if (!msg) return;

        const target = targetPersonaSelect.value;
        sendInterruptionBtn.disabled = true;

        try {
            const resp = await fetch('/api/inject', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target: target, message: msg })
            });
            const data = await resp.json();
            if (data.error) {
                alert(data.error);
            } else {
                interruptionInput.value = '';
            }
        } catch (err) {
            alert('Failed to send message: ' + err.message);
        } finally {
            sendInterruptionBtn.disabled = false;
        }
    }

    sendInterruptionBtn.addEventListener('click', sendInterruption);
    interruptionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendInterruption();
        }
    });

    function startPolling() {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(checkStatus, 600);
    }

    async function checkStatus() {
        try {
            const resp = await fetch('/api/status');
            const state = await resp.json();

            // Update UI status bar & pause state
            updateStatusBar(state.status, state.progress_turn, state.is_paused);
            updatePauseButtonState(state.is_paused || false);

            // Render new turns
            if (state.turns && state.turns.length > renderedTurnCount) {
                removeThinkingIndicator();
                const newTurns = state.turns.slice(renderedTurnCount);
                newTurns.forEach(t => renderTurn(t));
                renderedTurnCount = state.turns.length;

                // Update metrics
                updateMetrics(state.turns);

                // Show thinking indicator for NEXT turn if running and not paused
                if (state.status === 'running' && !state.is_paused) {
                    showThinkingIndicator('Translating human thought & generating next response...');
                }
            } else if (state.status === 'running' && renderedTurnCount === 0) {
                showThinkingIndicator('Waiting for initial dialogue utterance...');
            } else if (state.status === 'running' && state.is_paused) {
                removeThinkingIndicator();
            }

            // Handle completion or error
            if (state.status === 'completed') {
                clearInterval(pollInterval);
                removeThinkingIndicator();
                startBtn.disabled = false;
                stopBtn.disabled = true;
                reportStatus.textContent = '✅ Session completed. Reports ready!';
                showDownloadLinks(state.generated_files);
            } else if (state.status === 'error') {
                clearInterval(pollInterval);
                removeThinkingIndicator();
                startBtn.disabled = false;
                stopBtn.disabled = true;
                const errorMsg = state.error_message || 'Session failed to execute';
                reportStatus.textContent = '❌ Error: ' + errorMsg;
                showErrorCard(errorMsg);
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }

    function updateStatusBar(status, turnNum, paused) {
        statusDot.className = 'status-dot status-' + (paused ? 'paused' : status);
        const displayStatus = paused ? 'Paused' : (status.charAt(0).toUpperCase() + status.slice(1));
        statusText.textContent = displayStatus;
    }

    function updateMetrics(turns) {
        metricTurns.textContent = `${turns.length} Turns`;
        const totalWords = turns.reduce((acc, t) => acc + t.word_count, 0);
        metricWords.textContent = `${totalWords}w`;

        if (turns.length > 0) {
            const avgDepth = (turns.reduce((acc, t) => acc + t.depth_score, 0) / turns.length).toFixed(1);
            metricDepth.textContent = `Depth: ${avgDepth}`;
        }
    }

    function renderTurn(turn) {
        const turnDiv = document.createElement('div');
        const isIndra = turn.speaker_id === 1;
        
        let cardClass = `turn-item turn-speaker-${turn.speaker_id} `;
        cardClass += isIndra ? 'turn-indra' : 'turn-ilavarasan';
        if (turn.is_user_injection) cardClass += ' turn-user-injection';
        turnDiv.className = cardClass;

        const topics = (turn.detected_topics || []).map(tp => `<span class="topic-chip">${escapeHtml(tp)}</span>`).join('');

        let speakerBadge = escapeHtml(turn.speaker_name);
        if (turn.is_user_injection) {
            speakerBadge += ' 👤 [User Interruption]';
        }

        turnDiv.innerHTML = `
            <div class="turn-meta">
                <span class="turn-speaker-badge">${speakerBadge} (#${turn.turn_number})</span>
                <div class="turn-pills">
                    <span class="pill-tag">⏱️ ${turn.elapsed_seconds.toFixed(1)}s</span>
                    <span class="pill-tag">🧠 ${turn.depth_score}/10</span>
                    <span class="pill-tag">📝 ${turn.word_count}w</span>
                </div>
            </div>
            <div class="turn-topics-bar">${topics}</div>
            <div class="turn-text">${escapeHtml(turn.content).replace(/\n/g, '<br>')}</div>
        `;

        chatContainer.appendChild(turnDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function showThinkingIndicator(message) {
        if (!activeThinkingCard) {
            activeThinkingCard = document.createElement('div');
            activeThinkingCard.className = 'thinking-card';
            chatContainer.appendChild(activeThinkingCard);
        }
        activeThinkingCard.innerHTML = `
            <div class="thinking-spinner"></div>
            <span class="thinking-text">${escapeHtml(message)}</span>
        `;
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function removeThinkingIndicator() {
        if (activeThinkingCard) {
            activeThinkingCard.remove();
            activeThinkingCard = null;
        }
    }

    function showErrorCard(message) {
        removeThinkingIndicator();
        const errDiv = document.createElement('div');
        errDiv.className = 'error-card';
        errDiv.innerHTML = `
            <div class="error-header">⚠️ Session Notice</div>
            <div class="error-body">${escapeHtml(message)}</div>
            <button class="btn btn-primary error-retry-btn">Try Again</button>
        `;
        errDiv.querySelector('.error-retry-btn').addEventListener('click', launchSession);
        chatContainer.appendChild(errDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function showDownloadLinks(files) {
        if (!files) return;
        if (files.markdown) {
            const name = files.markdown.split('/').pop().split('\\').pop();
            btnMd.href = '/reports/' + name;
        }
        if (files.json) {
            const name = files.json.split('/').pop().split('\\').pop();
            btnJson.href = '/reports/' + name;
        }
        if (files.html) {
            const name = files.html.split('/').pop().split('\\').pop();
            btnHtml.href = '/reports/' + name;
        }
        downloadGroup.style.display = 'flex';
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
});

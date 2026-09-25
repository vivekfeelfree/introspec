document.addEventListener('DOMContentLoaded', () => {
    const backendSelect = document.getElementById('backendSelect');
    const apiKeyGroup = document.getElementById('apiKeyGroup');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const iterationsInput = document.getElementById('iterationsInput');
    const iterVal = document.getElementById('iterVal');
    const timeLimitInput = document.getElementById('timeLimitInput');
    const timeVal = document.getElementById('timeVal');

    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const welcomeStartBtn = document.getElementById('welcomeStartBtn');

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

    // Toggle API Key input display based on provider
    backendSelect.addEventListener('change', () => {
        const val = backendSelect.value;
        if (['gemini', 'openai', 'anthropic'].includes(val)) {
            apiKeyGroup.style.display = 'block';
        } else {
            apiKeyGroup.style.display = 'none';
        }
    });

    // Range slider labels
    iterationsInput.addEventListener('input', () => {
        iterVal.textContent = iterationsInput.value;
    });

    timeLimitInput.addEventListener('input', () => {
        timeVal.textContent = timeLimitInput.value;
    });

    // Launch Trial Trigger Function
    async function launchTrial() {
        closeSidebar();
        const payload = {
            max_iterations: parseInt(iterationsInput.value),
            time_limit: parseFloat(timeLimitInput.value),
            backend_provider: backendSelect.value,
            gemini_api_key: apiKeyInput.value,
            openai_api_key: apiKeyInput.value,
            anthropic_api_key: apiKeyInput.value,
        };

        startBtn.disabled = true;
        stopBtn.disabled = false;
        renderedTurnCount = 0;
        downloadGroup.style.display = 'none';
        reportStatus.textContent = 'Orchestration starting...';

        // Clear chat and show initial loading card
        chatContainer.innerHTML = '';
        showThinkingIndicator('Starting dual-agent orchestration session...');

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

    startBtn.addEventListener('click', launchTrial);
    if (welcomeStartBtn) welcomeStartBtn.addEventListener('click', launchTrial);

    // Stop Orchestration
    stopBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/stop', { method: 'POST' });
            reportStatus.textContent = 'Stop requested... finishing active turn.';
        } catch (err) {
            console.error(err);
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

            // Update UI status bar
            updateStatusBar(state.status, state.progress_turn, state.max_iterations);

            // Render new turns
            if (state.turns && state.turns.length > renderedTurnCount) {
                removeThinkingIndicator();
                const newTurns = state.turns.slice(renderedTurnCount);
                newTurns.forEach(t => renderTurn(t));
                renderedTurnCount = state.turns.length;

                // Update metrics
                updateMetrics(state.turns, state.max_iterations);

                // Show thinking indicator for NEXT turn if trial still running
                if (state.status === 'running' && renderedTurnCount < state.max_iterations) {
                    const nextSpeaker = (renderedTurnCount % 2 === 0) ? 'Agent 2 (Human Inquirer)' : 'Agent 1 (Transparent AI)';
                    showThinkingIndicator(`${nextSpeaker} is reasoning & generating response...`);
                }
            } else if (state.status === 'running' && renderedTurnCount === 0) {
                const initialSpeaker = 'Agent 2 (Human Inquirer)';
                showThinkingIndicator(`${initialSpeaker} is generating opening question...`);
            }

            // Handle completion or error
            if (state.status === 'completed') {
                clearInterval(pollInterval);
                removeThinkingIndicator();
                startBtn.disabled = false;
                stopBtn.disabled = true;
                reportStatus.textContent = '✅ Trial completed. Reports ready!';
                showDownloadLinks(state.generated_files);
            } else if (state.status === 'error') {
                clearInterval(pollInterval);
                removeThinkingIndicator();
                startBtn.disabled = false;
                stopBtn.disabled = true;
                const errorMsg = state.error_message || 'Trial failed to execute';
                reportStatus.textContent = '❌ Error: ' + errorMsg;
                showErrorCard(errorMsg);
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }

    function updateStatusBar(status, turnNum, maxTurns) {
        statusDot.className = 'status-dot status-' + status;
        statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }

    function updateMetrics(turns, maxTurns) {
        metricTurns.textContent = `${turns.length}/${maxTurns}`;
        const totalWords = turns.reduce((acc, t) => acc + t.word_count, 0);
        metricWords.textContent = `${totalWords}w`;

        if (turns.length > 0) {
            const avgDepth = (turns.reduce((acc, t) => acc + t.depth_score, 0) / turns.length).toFixed(1);
            metricDepth.textContent = `Depth: ${avgDepth}`;
        }
    }

    function renderTurn(turn) {
        const turnDiv = document.createElement('div');
        const isAgent1 = turn.speaker_id === 1;
        turnDiv.className = `turn-item turn-speaker-${turn.speaker_id} turn-agent${turn.speaker_id}`;

        const topics = (turn.detected_topics || []).map(tp => `<span class="topic-chip">${escapeHtml(tp)}</span>`).join('');

        turnDiv.innerHTML = `
            <div class="turn-meta">
                <span class="turn-speaker-badge">${escapeHtml(turn.speaker_name)} (#${turn.turn_number})</span>
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
            <div class="error-header">⚠️ Trial Execution Notice</div>
            <div class="error-body">${escapeHtml(message)}</div>
            <button class="btn btn-primary error-retry-btn">Try Again</button>
        `;
        errDiv.querySelector('.error-retry-btn').addEventListener('click', launchTrial);
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

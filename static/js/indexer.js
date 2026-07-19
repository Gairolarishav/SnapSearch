(() => {
  const folderPathInput  = document.getElementById('folderPath');
  const forceReindex     = document.getElementById('forceReindex');
  const startBtn         = document.getElementById('startBtn');
  const progressSection  = document.getElementById('progressSection');
  const progressBar      = document.getElementById('progressBar');
  const currentFile      = document.getElementById('currentFile');
  const counterBadge     = document.getElementById('counterBadge');
  const summaryCard      = document.getElementById('summaryCard');
  const errorAlert       = document.getElementById('errorAlert');
  const errorMsg         = document.getElementById('errorMsg');
  const sumAdded         = document.getElementById('sumAdded');
  const sumSkipped       = document.getElementById('sumSkipped');
  const sumFailed        = document.getElementById('sumFailed');
  const stageBadges      = document.querySelectorAll('.stage-badge');

  const STAGES = ['ocr', 'caption', 'embed', 'clip', 'done'];

  let sse = null;
  let pollTimer = null;

  startBtn.addEventListener('click', startIndexing);

  function startIndexing() {
    const folder = folderPathInput.value.trim();
    if (!folder) {
      folderPathInput.classList.add('is-invalid');
      return;
    }
    folderPathInput.classList.remove('is-invalid');

    hideAll();
    progressSection.style.display = 'block';
    startBtn.disabled = true;
    resetStages();
    setProgress(0, '—', 0, 0);

    fetch('/api/index/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: folder, force_reindex: forceReindex.checked })
    })
    .then(res => {
      if (!res.ok) return res.json().then(d => { throw new Error(d.detail || 'Failed to start'); });
      connectSSE();
    })
    .catch(err => showError(err.message));
  }

  function connectSSE() {
    if (typeof EventSource === 'undefined') {
      // Polling fallback
      pollTimer = setInterval(pollStatus, 1000);
      return;
    }

    sse = new EventSource('/api/index/progress');

    sse.onmessage = event => {
      const data = JSON.parse(event.data);
      handleUpdate(data);
      if (!data.running && (data.stage === 'done' || data.stage === 'error')) {
        sse.close();
        sse = null;
      }
    };

    sse.onerror = () => {
      sse.close();
      sse = null;
      // Fall back to polling if SSE breaks unexpectedly
      if (!pollTimer) {
        pollTimer = setInterval(pollStatus, 1500);
      }
    };
  }

  async function pollStatus() {
    try {
      const res = await fetch('/api/index/status');
      const data = await res.json();
      handleUpdate(data);
      if (!data.running && (data.stage === 'done' || data.stage === 'error')) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    } catch (_) {}
  }

  function handleUpdate(data) {
    if (data.stage === 'error') {
      showError(data.error || 'Unknown error');
      startBtn.disabled = false;
      return;
    }

    setProgress(data.percent, data.filename, data.current, data.total);
    highlightStage(data.stage);

    if (!data.running && data.stage === 'done' && data.result) {
      showSummary(data.result);
      startBtn.disabled = false;
    }
  }

  function setProgress(percent, filename, current, total) {
    progressBar.style.width = percent + '%';
    progressBar.setAttribute('aria-valuenow', percent);
    currentFile.textContent = filename || '—';
    counterBadge.textContent = `${current} / ${total}`;
  }

  function highlightStage(activeStage) {
    const activeIdx = STAGES.indexOf(activeStage);
    stageBadges.forEach(badge => {
      const s = badge.dataset.stage;
      const idx = STAGES.indexOf(s);
      badge.classList.remove('active', 'completed');
      if (idx < activeIdx) badge.classList.add('completed');
      else if (s === activeStage) badge.classList.add('active');
    });
  }

  function resetStages() {
    stageBadges.forEach(b => b.classList.remove('active', 'completed'));
  }

  function showSummary(result) {
    summaryCard.style.display = 'block';
    sumAdded.textContent   = result.added;
    sumSkipped.textContent = result.skipped;
    sumFailed.textContent  = result.failed;
  }

  function showError(msg) {
    errorAlert.style.display = 'flex';
    errorMsg.textContent = msg;
    progressSection.style.display = 'none';
  }

  function hideAll() {
    summaryCard.style.display  = 'none';
    errorAlert.style.display   = 'none';
  }
})();

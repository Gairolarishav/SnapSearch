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
  const failedFilesList  = document.getElementById('failedFilesList');
  const failedFilesSection = document.getElementById('failedFilesSection');
  const skippedNote      = document.getElementById('skippedNote');
  const stageBadges      = document.querySelectorAll('.stage-badge');

  const STAGES = ['ocr', 'caption', 'embed', 'clip', 'done'];

  let sse = null;
  let pollTimer = null;
  let activeRunId = null;

  startBtn.addEventListener('click', startIndexing);

  resumeIfRunning();

  async function resumeIfRunning() {
    try {
      const res = await fetch('/api/index/status');
      const data = await res.json();
      if (data.running || data.stage === 'done' || data.stage === 'error') {
        activeRunId = data.run_id;
        progressSection.style.display = 'block';
        startBtn.disabled = data.running;
        handleUpdate(data);
        if (data.running) connectSSE();
      }
    } catch (_) {}
  }

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
      return res.json();
    })
    .then(data => {
      activeRunId = data.run_id;
      connectSSE();
    })
    .catch(err => showError(err.message));
  }

  function connectSSE() {
    if (sse) { sse.close(); sse = null; }
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }

    if (typeof EventSource === 'undefined') {
      pollTimer = setInterval(pollStatus, 1000);
      return;
    }

    sse = new EventSource('/api/index/progress');

    sse.onmessage = event => {
      const data = JSON.parse(event.data);
      if (activeRunId !== null && data.run_id !== activeRunId) return;
      handleUpdate(data);
      if (!data.running && (data.stage === 'done' || data.stage === 'error')) {
        sse.close();
        sse = null;
      }
    };

    sse.onerror = () => {
      sse.close();
      sse = null;
      if (!pollTimer) {
        pollTimer = setInterval(pollStatus, 1500);
      }
    };
  }

  async function pollStatus() {
    try {
      const res = await fetch('/api/index/status');
      const data = await res.json();
      if (activeRunId !== null && data.run_id !== activeRunId) return;
      handleUpdate(data);
      if (!data.running && (data.stage === 'done' || data.stage === 'error')) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    } catch (_) {}
  }

  function handleUpdate(data) {
    if (data.stage === 'error') {
      showError(data.error || 'Unknown error occurred. Check the server logs for details.');
      startBtn.disabled = false;
      return;
    }

    if (data.stage === 'loading') {
      currentFile.textContent = data.filename || 'Loading AI models…';
      counterBadge.textContent = '—';
      progressBar.style.width = '0%';
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

    // Skipped note
    if (result.skipped > 0 && result.added === 0 && result.failed === 0) {
      skippedNote.textContent = 'All images were already indexed. Enable "Force re-index" to re-process them.';
      skippedNote.style.display = 'block';
    } else if (result.skipped > 0) {
      skippedNote.textContent = `${result.skipped} image(s) were already indexed and skipped.`;
      skippedNote.style.display = 'block';
    } else {
      skippedNote.style.display = 'none';
    }

    // Failed files list
    const files = result.failed_files || [];
    if (files.length > 0) {
      failedFilesSection.style.display = 'block';
      failedFilesList.innerHTML = files.map(f =>
        `<li class="list-group-item list-group-item-danger py-1 px-2 small">
          <span class="fw-medium font-mono">${escapeHtml(f.filename)}</span>
          <span class="text-muted ms-2">${escapeHtml(f.error)}</span>
        </li>`
      ).join('');
    } else {
      failedFilesSection.style.display = 'none';
      failedFilesList.innerHTML = '';
    }
  }

  function showError(msg) {
    errorAlert.classList.remove('d-none');
    errorMsg.textContent = msg;
    progressSection.style.display = 'none';
  }

  function hideAll() {
    summaryCard.style.display = 'none';
    errorAlert.classList.add('d-none');
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
})();

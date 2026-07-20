(() => {
  const searchInput = document.getElementById('searchInput');
  const searchBtn   = document.getElementById('searchBtn');
  const spinner     = document.getElementById('spinner');
  const emptyState  = document.getElementById('emptyState');
  const noIndexState= document.getElementById('noIndexState');
  const resultsGrid = document.getElementById('resultsGrid');
  const topK        = document.getElementById('topK');
  const topKVal     = document.getElementById('topKVal');
  const textWeight  = document.getElementById('textWeight');
  const weightLabel = document.getElementById('weightLabel');
  const advToggle   = document.getElementById('advancedToggle');
  const advPanel    = document.getElementById('advancedPanel');
  const statsCount  = document.getElementById('statsCount');
  const pathModal     = new bootstrap.Modal(document.getElementById('pathModal'));
  const modalPath     = document.getElementById('modalPath');
  const lightboxModal = new bootstrap.Modal(document.getElementById('lightboxModal'));
  const lightboxImg   = document.getElementById('lightboxImg');
  const lightboxFilename = document.getElementById('lightboxFilename');

  // Sliders
  topK.addEventListener('input', () => { topKVal.textContent = topK.value; });
  textWeight.addEventListener('input', () => {
    const tw = parseInt(textWeight.value);
    weightLabel.textContent = `Text ${tw}% / CLIP ${100 - tw}%`;
  });
  advToggle.addEventListener('click', () => {
    const visible = advPanel.style.display !== 'none';
    advPanel.style.display = visible ? 'none' : 'block';
  });

  // Search triggers
  searchBtn.addEventListener('click', doSearch);
  searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

  // Load stats on page load
  loadStats();

  async function loadStats() {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) return;
      const data = await res.json();
      statsCount.textContent = data.total_indexed.toLocaleString();
      if (data.total_indexed > 0) {
        noIndexState.style.display = 'none';
      }
    } catch (_) {}
  }

  async function doSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    setUIState('loading');

    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          top_k: parseInt(topK.value),
          text_weight: parseInt(textWeight.value) / 100,
        })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (!data.results || data.results.length === 0) {
        setUIState('empty');
      } else {
        renderResults(data.results);
        setUIState('results');
      }
    } catch (err) {
      console.error('Search failed:', err);
      setUIState('empty');
    }
  }

  function setUIState(state) {
    spinner.style.display     = state === 'loading'  ? 'block' : 'none';
    emptyState.style.display  = state === 'empty'    ? 'block' : 'none';
    noIndexState.style.display= state === 'noidx'    ? 'block' : 'none';
    resultsGrid.style.display = state === 'results'  ? '' : 'none';
  }

  function renderResults(results) {
    resultsGrid.innerHTML = '';
    for (const r of results) {
      const col = document.createElement('div');
      col.className = 'col-12 col-md-6 col-lg-4';
      col.innerHTML = buildCard(r);
      col.querySelector('.open-path-btn').addEventListener('click', e => {
        e.stopPropagation();
        modalPath.textContent = r.path;
        pathModal.show();
      });
      col.querySelector('.result-thumb-wrap').addEventListener('click', () => {
        lightboxImg.src = `/api/image?path=${encodeURIComponent(r.path)}&size=1600`;
        lightboxFilename.textContent = r.filename;
        lightboxModal.show();
      });
      resultsGrid.appendChild(col);
    }
  }

  function buildCard(r) {
    const scoreClass = r.score >= 0.8 ? 'score-high' : r.score >= 0.6 ? 'score-mid' : 'score-low';
    const scorePct   = Math.round(r.score * 100);
    const sourceBadge = sourceColor(r.match_source);
    const thumbUrl   = `/api/image?path=${encodeURIComponent(r.path)}&size=400`;
    const caption    = (r.caption || r.ocr_text || '').substring(0, 140);

    const fileType = (r.image_type && r.image_type !== 'unknown') ? r.image_type : r.filename.split('.').pop().toUpperCase();

    return `
      <div class="result-card h-100">
        <div class="result-thumb-wrap" style="cursor:pointer" title="Click to enlarge">
          <img
            class="result-thumb"
            src="${thumbUrl}"
            alt="${escHtml(r.filename)}"
            loading="lazy"
            onerror="this.parentElement.innerHTML='<div class=\\'result-thumb-placeholder\\'><i class=\\'fa-solid fa-image\\'></i></div>'"
          >
        </div>
        <div class="result-body">
          <div class="result-badges">
            <span class="badge ${scoreClass}">${scorePct}%</span>
            <span class="badge ${sourceBadge}">${escHtml(r.match_source)}</span>
          </div>
          <div class="result-caption">${escHtml(caption)}</div>
          <div class="result-filename" title="${escHtml(r.path)}">${escHtml(r.filename)}</div>
        </div>
        <div class="result-footer">
          <span class="text-muted" style="font-size:0.72rem">${escHtml(fileType)}</span>
          <button class="btn btn-sm btn-outline-secondary open-path-btn" style="font-size:0.72rem; padding:2px 8px">
            <i class="fa-solid fa-folder-open me-1"></i>Location
          </button>
        </div>
      </div>`;
  }

  function sourceColor(source) {
    if (source === 'Both')  return 'bg-primary';
    if (source === 'Text')  return 'bg-info';
    return 'bg-purple';
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
})();

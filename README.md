# SnapSearch

> Find any screenshot or image instantly by describing it in plain English.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.2-7952B3?logo=bootstrap&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-IndexFlatIP-FF6F00)
![License](https://img.shields.io/badge/License-MIT-green)

SnapSearch is an AI-powered image search engine that lets you find any screenshot or photo by describing what you remember about it — no file naming, tagging, or folder organization required. Point it at a folder, let it build a search index in the background, then type queries like *"error message in VS Code"* or *"blue chart from the sales report"* to surface the right image in seconds.

It uses a dual-index pipeline: EasyOCR extracts text embedded in images, while GPT-4o-mini generates a natural-language caption for every image regardless of whether it contains text. Both signals are embedded into separate vector spaces (MiniLM for text semantics, CLIP for visual semantics) and fused at query time for maximum recall.

---

## Key Features

- **Natural language search** over any image — screenshots, photos
- **Dual-index hybrid search** — text embeddings (MiniLM all-MiniLM-L6-v2, 384-dim) fused with visual embeddings (CLIP ViT-B/32, 512-dim)
- **GPT-4o-mini vision captions** every image, making even photo-only images searchable by description
- **EasyOCR** extracts embedded text from screenshots, invoices, code editors, and chat windows
- **Real-time 5-stage indexing pipeline** progress via Server-Sent Events (OCR → Caption → Embed → CLIP → Done)
- **Configurable text/CLIP weight blend** (default 40% text / 60% CLIP) via the Advanced panel
- **Score-based result cards** with color-coded confidence (green ≥80%, orange 60–80%, red <60%) and a match-source label (Text / CLIP / Both)
- **Lightbox full-size viewer** and file-location modal
- **Incremental indexing** — already-indexed images are skipped automatically; `force_reindex` flag available
- **Dark mode** support via CSS custom properties and `prefers-color-scheme`
- Supports **PNG, JPG, JPEG, GIF, BMP, WEBP**

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async HTTP server, SSE streaming |
| Frontend | Bootstrap 5.3.2, Vanilla JS, Jinja2 | Responsive UI, templating |
| OCR | EasyOCR | CPU-based text extraction from images |
| Vision AI | OpenAI GPT-4o-mini | Image captioning via base64 vision API |
| Text Embeddings | Sentence Transformers all-MiniLM-L6-v2 | 384-dim semantic text vectors |
| Visual Embeddings | CLIP ViT-B/32 (via sentence-transformers) | 512-dim visual vectors |
| Vector Search | FAISS IndexFlatIP | Cosine similarity via L2-normalized inner product |
| Metadata | SQLite | Image records (path, OCR text, caption, type) |
| Persistence | .index + .pkl files | FAISS index and ID map on disk |

---

## Prerequisites

- Python 3.10 or higher
- An OpenAI API key (used only for captioning — roughly $0.001–$0.002 per image with gpt-4o-mini)
- ~650 MB free disk space on first run for automatic model downloads (MiniLM + CLIP)

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Gairolarishav/SnapSearch.git
cd SnapSearch
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your OpenAI API key

```bash
cp .env.example .env
# Edit .env and paste your key:
# OPENAI_API_KEY=sk-...
```

### 5. Start the server

```bash
uvicorn app:app --reload
```

Open **http://localhost:8000** in your browser.

> **Note:** On first run, MiniLM (~90 MB) and CLIP (~560 MB) models will be downloaded automatically. This is a one-time operation.

---

## Usage

### Indexing Images

1. Navigate to **http://localhost:8000/indexer**
2. Enter the absolute path to your images folder (e.g. `C:\Users\you\Screenshots` or `/Users/you/Pictures`)
3. Optionally check **Force re-index** to reprocess already-indexed images from scratch
4. Click **Start Indexing**
5. Watch the live 5-stage pipeline: **OCR → Caption → Embed → CLIP → Done**
6. When complete, a summary card shows how many images were Added / Skipped / Failed

### Searching

1. Navigate to **http://localhost:8000**
2. Type a natural language description in the search bar
   - Examples: `"login page with red error"`, `"python stack trace"`, `"blue bar chart"`
3. Press **Enter** or click **Search**
4. Results appear as cards — click any thumbnail to open the fullscreen lightbox viewer
5. Click **Location** on a card to reveal the full file path on disk

---

## Configuration Options

| Parameter | Where to Set | Default | Effect |
|---|---|---|---|
| `top_k` | Search UI slider ("Results") | 9 | Number of results returned (3–30) |
| `text_weight` | Advanced panel slider | 0.40 (40%) | Weight for text embedding scores; CLIP weight = 1 − text_weight |
| `force_reindex` | Indexer UI checkbox | false | Clears all existing data and reprocesses every image when true |
| `OPENAI_API_KEY` | `.env` file | — | Required for GPT-4o-mini captioning |

---

## Architecture Overview

SnapSearch uses two parallel FAISS indices backed by a single SQLite metadata store:

**Indexing path:** For each image, EasyOCR extracts embedded text and GPT-4o-mini generates a natural-language caption. The combined string `"<caption> <ocr_text>"` is encoded by all-MiniLM-L6-v2 into a 384-dim text vector. Separately, the raw image pixels are encoded by CLIP ViT-B/32 into a 512-dim visual vector. Both vectors are L2-normalized and inserted into their respective FAISS IndexFlatIP indices. Metadata (path, filename, OCR text, caption, image type) is stored in SQLite.

**Search path:** The query string is encoded by both models simultaneously. Each FAISS index returns up to `top_k × 2` candidate IDs with raw inner-product scores. Scores are per-set max-normalized then combined as `final_score = text_weight × norm_text_score + clip_weight × norm_clip_score`. The top-k fused results are enriched with SQLite metadata and returned as JSON.

**Real-time progress:** Indexing runs in a thread pool executor; a thread-safe state dict is updated at each pipeline stage. The `/api/index/progress` endpoint streams this state as Server-Sent Events at 500ms intervals, with an automatic polling fallback for older browsers.

---

## Project Structure

```
ai_screenshot_search/
├── app.py              # FastAPI app, all endpoints, fuse_scores logic
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── src/
│   ├── indexer.py      # Pipeline orchestrator (OCR → Caption → Embed → CLIP → Save)
│   ├── ocr_engine.py   # EasyOCR singleton wrapper
│   ├── captioning.py   # GPT-4o-mini vision API wrapper
│   ├── embedder.py     # MiniLM text embedder with L2 normalization
│   ├── clip_embedder.py # CLIP image + text embedder with L2 normalization
│   ├── database.py     # SQLite CRUD (init, insert, get, count, clear)
│   └── vector_store.py # FAISS build/add/search/save/load wrappers
├── templates/
│   ├── base.html       # Shared layout (navbar, footer, Bootstrap/FA CDN links)
│   ├── index.html      # Search UI with lightbox and path modal
│   └── indexer.html    # Indexing UI with SSE progress pipeline
├── static/
│   ├── css/style.css   # CSS custom properties, dark mode, card and badge styles
│   └── js/
│       ├── search.js   # Search fetch, result rendering, lightbox logic
│       └── indexer.js  # SSE client, polling fallback, stage highlighting
└── index_store/        # Runtime-generated: text.index, clip.index, *.pkl, images.db
```

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Open a Pull Request

Please ensure any new dependencies are added to `requirements.txt`.

---

## License

This project is released under the MIT License.

## About the Maintainer

This project is maintained by Nascenture, a software development company specializing in Django development, custom software solutions, web applications, and cloud-based platforms, AI applications.

- Company Website: https://www.nascenture.com

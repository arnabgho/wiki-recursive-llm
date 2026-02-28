"""Lightweight web viewer for RLM wiki state."""

import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import RLM

logger = logging.getLogger(__name__)

_HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RLM Wiki Viewer</title>
<style>
:root {
  --bg: #1e1e2e;
  --bg2: #181825;
  --surface: #313244;
  --overlay: #45475a;
  --text: #cdd6f4;
  --subtext: #a6adc8;
  --blue: #89b4fa;
  --green: #a6e3a1;
  --peach: #fab387;
  --red: #f38ba8;
  --mauve: #cba6f7;
  --teal: #94e2d5;
  --yellow: #f9e2af;
  --border: #585b70;
  --font-mono: 'SF Mono', 'Cascadia Code', 'Fira Code', Consolas, monospace;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: var(--font-mono);
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* Stats bar */
.stats-bar {
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  padding: 6px 16px;
  display: flex;
  gap: 24px;
  font-size: 12px;
  color: var(--subtext);
  align-items: center;
  flex-shrink: 0;
}
.stats-bar .label { color: var(--overlay); }
.stats-bar .value { color: var(--blue); font-weight: 600; }
.stats-bar .updated { margin-left: auto; color: var(--overlay); font-size: 11px; }
/* Layout */
.main {
  display: flex;
  flex: 1;
  overflow: hidden;
}
/* Sidebar */
.sidebar {
  width: 280px;
  min-width: 200px;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-header {
  padding: 12px;
  border-bottom: 1px solid var(--border);
}
.sidebar-header input {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 10px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 12px;
  outline: none;
}
.sidebar-header input:focus { border-color: var(--blue); }
.page-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.group-label {
  padding: 4px 12px;
  font-size: 11px;
  color: var(--overlay);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  user-select: none;
}
.group-label:hover { color: var(--subtext); }
.page-item {
  padding: 6px 12px 6px 20px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  border-left: 2px solid transparent;
}
.page-item:hover { background: var(--surface); }
.page-item.active {
  background: var(--surface);
  border-left-color: var(--blue);
  color: var(--blue);
}
.page-item .title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tag-chip {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
}
.tag-finding { background: var(--green); color: var(--bg); }
.tag-todo { background: var(--yellow); color: var(--bg); }
.tag-done { background: var(--blue); color: var(--bg); }
.tag-question { background: var(--peach); color: var(--bg); }
.tag-default { background: var(--overlay); color: var(--text); }
/* Tabs */
.tab-bar {
  display: flex;
  border-bottom: 1px solid var(--border);
  background: var(--bg2);
  flex-shrink: 0;
}
.tab {
  padding: 8px 20px;
  cursor: pointer;
  font-size: 12px;
  color: var(--subtext);
  border-bottom: 2px solid transparent;
  user-select: none;
}
.tab:hover { color: var(--text); }
.tab.active { color: var(--blue); border-bottom-color: var(--blue); }
/* Content panel */
.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.page-view {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
.page-title {
  font-size: 20px;
  color: var(--blue);
  margin-bottom: 8px;
}
.page-meta {
  font-size: 11px;
  color: var(--overlay);
  margin-bottom: 16px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.page-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.page-content {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
  background: var(--surface);
  padding: 16px;
  border-radius: 6px;
}
.page-links {
  margin-top: 16px;
  font-size: 12px;
}
.page-links .link-section { margin-bottom: 8px; }
.page-links .link-label { color: var(--overlay); }
.page-links a {
  color: var(--teal);
  cursor: pointer;
  text-decoration: none;
}
.page-links a:hover { text-decoration: underline; }
/* Graph tab */
.graph-container {
  flex: 1;
  overflow: hidden;
  position: relative;
}
.graph-container canvas {
  width: 100%;
  height: 100%;
  display: block;
}
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--overlay);
  font-size: 14px;
}
</style>
</head>
<body>

<div class="stats-bar">
  <span><span class="label">Iterations:</span> <span class="value" id="stat-iter">-</span></span>
  <span><span class="label">LLM Calls:</span> <span class="value" id="stat-llm">-</span></span>
  <span><span class="label">Depth:</span> <span class="value" id="stat-depth">-</span></span>
  <span><span class="label">Pages:</span> <span class="value" id="stat-pages">-</span></span>
  <span class="updated" id="last-updated">—</span>
</div>

<div class="main">
  <div class="sidebar">
    <div class="sidebar-header">
      <input type="text" id="search-box" placeholder="Filter pages...">
    </div>
    <div class="page-list" id="page-list"></div>
  </div>
  <div class="content">
    <div class="tab-bar">
      <div class="tab active" data-tab="page">Page</div>
      <div class="tab" data-tab="graph">Graph</div>
    </div>
    <div id="tab-page" class="page-view">
      <div class="empty-state">No page selected</div>
    </div>
    <div id="tab-graph" class="graph-container" style="display:none">
      <canvas id="graph-canvas"></canvas>
    </div>
  </div>
</div>

<script>
(function() {
  let wikiData = null;
  let selectedPage = null;
  let activeTab = 'page';
  // Graph state
  let graphNodes = [];
  let graphEdges = [];
  let graphDrag = null;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  function tagClass(tag) {
    const map = {finding:'tag-finding', todo:'tag-todo', done:'tag-done', question:'tag-question'};
    return map[tag] || 'tag-default';
  }

  function renderSidebar(filter) {
    const list = $('#page-list');
    if (!wikiData || !wikiData.pages) { list.innerHTML = '<div class="empty-state">Wiki is empty</div>'; return; }
    const pages = Object.values(wikiData.pages);
    const filtered = filter
      ? pages.filter(p => p.title.toLowerCase().includes(filter) || p.tags.some(t => t.includes(filter)))
      : pages;

    // Group by prefix
    const groups = {};
    filtered.forEach(p => {
      const slash = p.title.indexOf('/');
      const group = slash > 0 ? p.title.substring(0, slash) : '(root)';
      (groups[group] = groups[group] || []).push(p);
    });

    let html = '';
    Object.keys(groups).sort().forEach(g => {
      html += `<div class="group-label">${esc(g)}</div>`;
      groups[g].sort((a,b) => a.title.localeCompare(b.title)).forEach(p => {
        const active = selectedPage === p.title ? ' active' : '';
        const tags = p.tags.map(t => `<span class="tag-chip ${tagClass(t)}">${esc(t)}</span>`).join('');
        html += `<div class="page-item${active}" data-title="${esc(p.title)}">
          <span class="title">${esc(p.title)}</span>${tags}</div>`;
      });
    });
    list.innerHTML = html || '<div class="empty-state">No matching pages</div>';

    list.querySelectorAll('.page-item').forEach(el => {
      el.addEventListener('click', () => { selectPage(el.dataset.title); });
    });
  }

  function selectPage(title) {
    selectedPage = title;
    renderSidebar($('#search-box').value.toLowerCase());
    renderPage();
  }

  function renderPage() {
    const view = $('#tab-page');
    if (!wikiData || !selectedPage || !wikiData.pages[selectedPage]) {
      view.innerHTML = '<div class="empty-state">No page selected</div>';
      return;
    }
    const p = wikiData.pages[selectedPage];
    const tags = p.tags.map(t => `<span class="tag-chip ${tagClass(t)}">${esc(t)}</span>`).join(' ');
    const links = p.links.map(l => `<a onclick="window._selectPage('${esc(l)}')">${esc(l)}</a>`).join(', ');
    // Find backlinks
    const backlinks = Object.values(wikiData.pages)
      .filter(op => op.links.includes(p.title))
      .map(op => `<a onclick="window._selectPage('${esc(op.title)}')">${esc(op.title)}</a>`)
      .join(', ');

    view.innerHTML = `
      <div class="page-title">${esc(p.title)}</div>
      <div class="page-meta">
        <span>created: iter ${p.created_at}</span>
        <span>updated: iter ${p.updated_at}</span>
        <div class="page-tags">${tags}</div>
      </div>
      <div class="page-content">${esc(p.content)}</div>
      <div class="page-links">
        ${links ? `<div class="link-section"><span class="link-label">Links: </span>${links}</div>` : ''}
        ${backlinks ? `<div class="link-section"><span class="link-label">Backlinks: </span>${backlinks}</div>` : ''}
      </div>`;
  }

  window._selectPage = selectPage;

  function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  // --- Tabs ---
  $$('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeTab = tab.dataset.tab;
      $('#tab-page').style.display = activeTab === 'page' ? '' : 'none';
      $('#tab-graph').style.display = activeTab === 'graph' ? '' : 'none';
      if (activeTab === 'graph') initGraph();
    });
  });

  // --- Graph ---
  function initGraph() {
    if (!wikiData || !wikiData.pages) return;
    const canvas = $('#graph-canvas');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * devicePixelRatio;
    canvas.height = rect.height * devicePixelRatio;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';

    const pages = Object.values(wikiData.pages);
    const titleSet = new Set(pages.map(p => p.title));

    graphNodes = pages.map((p, i) => ({
      title: p.title,
      x: rect.width/2 + (Math.random()-0.5) * rect.width * 0.6,
      y: rect.height/2 + (Math.random()-0.5) * rect.height * 0.6,
      vx: 0, vy: 0
    }));
    const nodeMap = {};
    graphNodes.forEach((n, i) => nodeMap[n.title] = i);

    graphEdges = [];
    pages.forEach(p => {
      p.links.forEach(l => {
        if (titleSet.has(l)) graphEdges.push([nodeMap[p.title], nodeMap[l]]);
      });
    });

    animateGraph(canvas, rect.width, rect.height);
  }

  function animateGraph(canvas, w, h) {
    const ctx = canvas.getContext('2d');
    const dpr = devicePixelRatio;
    let frame = 0;
    const maxFrames = 200;

    function tick() {
      if (activeTab !== 'graph') return;
      frame++;
      // Force-directed layout
      const nodes = graphNodes;
      const k = 80;
      // Repulsion
      for (let i = 0; i < nodes.length; i++) {
        nodes[i].vx = 0; nodes[i].vy = 0;
        for (let j = 0; j < nodes.length; j++) {
          if (i === j) continue;
          let dx = nodes[i].x - nodes[j].x;
          let dy = nodes[i].y - nodes[j].y;
          let dist = Math.sqrt(dx*dx + dy*dy) || 1;
          let force = k * k / dist;
          nodes[i].vx += dx/dist * force * 0.05;
          nodes[i].vy += dy/dist * force * 0.05;
        }
      }
      // Attraction along edges
      graphEdges.forEach(([a, b]) => {
        let dx = nodes[b].x - nodes[a].x;
        let dy = nodes[b].y - nodes[a].y;
        let dist = Math.sqrt(dx*dx + dy*dy) || 1;
        let force = (dist - k) * 0.01;
        nodes[a].vx += dx/dist * force;
        nodes[a].vy += dy/dist * force;
        nodes[b].vx -= dx/dist * force;
        nodes[b].vy -= dy/dist * force;
      });
      // Center gravity
      nodes.forEach(n => {
        n.vx += (w/2 - n.x) * 0.001;
        n.vy += (h/2 - n.y) * 0.001;
      });
      // Apply
      const damping = Math.max(0.1, 1 - frame/maxFrames);
      nodes.forEach(n => {
        if (graphDrag && graphDrag.node === n) return;
        n.x += n.vx * damping;
        n.y += n.vy * damping;
        n.x = Math.max(40, Math.min(w-40, n.x));
        n.y = Math.max(40, Math.min(h-40, n.y));
      });

      // Draw
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.scale(dpr, dpr);
      // Edges
      ctx.strokeStyle = '#585b70';
      ctx.lineWidth = 1;
      graphEdges.forEach(([a, b]) => {
        ctx.beginPath();
        ctx.moveTo(nodes[a].x, nodes[a].y);
        ctx.lineTo(nodes[b].x, nodes[b].y);
        ctx.stroke();
        // Arrowhead
        let dx = nodes[b].x - nodes[a].x;
        let dy = nodes[b].y - nodes[a].y;
        let dist = Math.sqrt(dx*dx+dy*dy) || 1;
        let ux = dx/dist, uy = dy/dist;
        let ax = nodes[b].x - ux*12, ay = nodes[b].y - uy*12;
        ctx.beginPath();
        ctx.moveTo(ax - uy*4 - ux*6, ay + ux*4 - uy*6);
        ctx.lineTo(nodes[b].x - ux*8, nodes[b].y - uy*8);
        ctx.lineTo(ax + uy*4 - ux*6, ay - ux*4 - uy*6);
        ctx.stroke();
      });
      // Nodes
      nodes.forEach(n => {
        const isSelected = n.title === selectedPage;
        ctx.beginPath();
        ctx.arc(n.x, n.y, isSelected ? 7 : 5, 0, Math.PI*2);
        ctx.fillStyle = isSelected ? '#89b4fa' : '#a6adc8';
        ctx.fill();
        ctx.font = '10px monospace';
        ctx.fillStyle = isSelected ? '#89b4fa' : '#a6adc8';
        ctx.textAlign = 'center';
        ctx.fillText(n.title, n.x, n.y - 10);
      });
      ctx.restore();

      if (frame < maxFrames) requestAnimationFrame(tick);
    }
    tick();

    // Drag support
    canvas.onmousedown = (e) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      for (const n of graphNodes) {
        if (Math.hypot(n.x-mx, n.y-my) < 12) {
          graphDrag = {node: n, ox: n.x-mx, oy: n.y-my};
          selectPage(n.title);
          break;
        }
      }
    };
    canvas.onmousemove = (e) => {
      if (!graphDrag) return;
      const rect = canvas.getBoundingClientRect();
      graphDrag.node.x = e.clientX - rect.left + graphDrag.ox;
      graphDrag.node.y = e.clientY - rect.top + graphDrag.oy;
      frame = 0; animateGraph(canvas, w, h);
    };
    canvas.onmouseup = () => { graphDrag = null; };

    // Click to select
    canvas.addEventListener('click', (e) => {
      if (graphDrag) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      for (const n of graphNodes) {
        if (Math.hypot(n.x-mx, n.y-my) < 12) { selectPage(n.title); return; }
      }
    });
  }

  // --- Search filter ---
  $('#search-box').addEventListener('input', (e) => {
    renderSidebar(e.target.value.toLowerCase());
  });

  // --- Polling ---
  async function poll() {
    try {
      const [wikiRes, statsRes] = await Promise.all([
        fetch('/api/wiki'), fetch('/api/stats')
      ]);
      const wiki = await wikiRes.json();
      const stats = await statsRes.json();

      wikiData = wiki;
      $('#stat-iter').textContent = stats.iterations;
      $('#stat-llm').textContent = stats.llm_calls;
      $('#stat-depth').textContent = stats.depth;
      $('#stat-pages').textContent = wiki.page_count;
      $('#last-updated').textContent = 'updated ' + new Date().toLocaleTimeString();

      renderSidebar($('#search-box').value.toLowerCase());
      if (activeTab === 'page') renderPage();
    } catch(e) {}
  }

  poll();
  setInterval(poll, 2000);
})();
</script>
</body>
</html>"""


def _make_handler(rlm: "RLM"):
    """Create a request handler class bound to the given RLM instance."""

    class WikiHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._serve_html()
            elif self.path == "/api/wiki":
                self._serve_json(rlm.wiki.export() if rlm.wiki else {"pages": {}, "page_count": 0})
            elif self.path == "/api/stats":
                self._serve_json(rlm.stats)
            else:
                self.send_error(404)

        def _serve_html(self) -> None:
            body = _HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_json(self, data: dict) -> None:
            body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            # Suppress default stderr logging; use our logger
            logger.debug("HTTP %s", args[0] if args else "")

    return WikiHandler


def serve_wiki(rlm: "RLM", port: int = 8787) -> HTTPServer:
    """Start a background HTTP server to browse wiki state.

    Args:
        rlm: RLM instance whose wiki and stats to serve.
        port: Port to listen on (default 8787).

    Returns:
        The HTTPServer instance (already running in a daemon thread).
    """
    handler = _make_handler(rlm)
    server = HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Wiki viewer running at http://127.0.0.1:%d", port)
    return server

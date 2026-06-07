let _ngNodes = []
let _ngEdges = []
let _ngCurLayout = "d3-force"
let _ngGraph = null
const _NG_LAYOUTS = {
  "d3-force": { type: "d3-force", linkDistance: 80, nodeStrength: -3000, edgeStrength: 1.2, preventOverlap: true, alpha: 0.5, alphaMin: 0.001, alphaDecay: 0.01, velocityDecay: 0.2 },
  concentric: { type: "concentric", minNodeSpacing: 60, preventOverlap: true, equidistant: false, startAngle: 0 },
  circular: { type: "circular", radius: 200, divisions: 1, ordering: "degree", angleRatio: 1 },
  radial: { type: "radial", unitRadius: 100, preventOverlap: true, maxPreventOverlapIteration: 200 },
  grid: { type: "grid", preventOverlap: true, sortBy: "degree" },
}
const _NG_LAYOUT_PARAMS = {
  "d3-force": { linkDistance: [20, 400, 80, 1], nodeStrength: [-8000, -100, -3000, 100], edgeStrength: [0, 5, 1.2, 0.1], alphaDecay: [0.001, 0.5, 0.01, 0.001] },
  concentric: { minNodeSpacing: [10, 200, 60, 5] },
  circular: { radius: [50, 600, 200, 10] },
  radial: { unitRadius: [30, 300, 100, 5] },
  grid: {},
}

const _NG_PALETTE = ["#2a3a5a","#2a4a3a","#4a3a2a","#3a2a4a","#4a3a3a","#3a4a4a","#3a3a2a","#4a2a3a","#2a3a4a","#3a4a2a"]
function _ngColor(s) {
  let h = 0; for (let i = 0; i < (s||"").length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0
  return _NG_PALETTE[Math.abs(h) % _NG_PALETTE.length]
}
function _ngShortLabel(raw) {
  const parts = (raw || "").split("\n")
  const first = parts[0] || ""
  const rest = parts.slice(1).join(" ").replace(/["']/g, "").trim()
  return first + " " + (rest.length > 28 ? rest.slice(0, 26) + ".." : rest)
}

async function _ngBuildGraph() {
  const container = document.getElementById("ngMemGraph")
  if (!container || _ngNodes.length < 2) return
  if (_ngGraph) { try { _ngGraph.destroy() } catch (e) {}; _ngGraph = null }
  container.textContent = ""

  const W = container.clientWidth || 800
  const layout = { type: _ngCurLayout }
  const base = _NG_LAYOUTS[_ngCurLayout] || {}
  const sliders = document.querySelectorAll("._ngpslider")
  for (const s of sliders) {
    const key = s.dataset.param
    if (key in base) layout[key] = Number(s.value)
  }
  for (const k of Object.keys(base)) {
    if (!(k in layout)) layout[k] = base[k]
  }

  const g6nodes = _ngNodes.map(n => ({ id: n.id, data: { label: n.label || n.id }, style: { fill: _ngColor(n.path || n.id) } }))
  const g6edges = _ngEdges.map(e => ({
    id: e.from + ">" + e.to, source: e.from, target: e.to,
    data: { type: e.label || "FOLLOWS", count: e.total_count || 1 },
    style: { lineWidth: Math.min(e.total_count || 1, 5) },
  }))

  _ngGraph = new G6.Graph({
    container, width: W, height: Math.max(window.innerHeight - 220, 400), autoFit: "view",
    data: { nodes: g6nodes, edges: g6edges },
    layout,
    node: {
      type: "rect",
      style: {
        size: [180, 40], fill: "#2a2a3a", stroke: "#555", lineWidth: 1, radius: 6,
        labelText: d => _ngShortLabel(d.data.label), labelFontSize: 10, labelFill: "#e0e0e0",
        labelFontFamily: "monospace", labelWordWrap: true, labelMaxWidth: 160,
        labelPlacement: "center", labelTextBaseline: "middle",
      },
      state: { selected: { fill: "#3a4a6a", stroke: "#7dd3fc", lineWidth: 2 }, hover: { fill: "#3a4a5a" } },
    },
    edge: {
      type: "line",
      style: {
        stroke: d => ({ FOLLOWS: "#555", APPROVED: "#4ade80", REJECTED: "#f87171", PENDING: "#facc15" }[d.data.type] || "#555"),
        lineWidth: 2, endArrow: true,
        labelText: d => d.data.type, labelFontSize: 9, labelFill: "#999",
        labelFontFamily: "monospace", labelBackgroundFill: "#0c0f14",
        labelBackgroundOpacity: 0.8, labelBackgroundPadding: [2, 4], labelPlacement: "center",
      },
    },
    behaviors: ["drag-canvas", "zoom-canvas", "drag-element", "click-select", "brush-select"],
    plugins: [
      {
        type: "tooltip",
        trigger: "hover",
        getContent: (e, items) => {
          if (!items || !items.length) return
          const d = items[0]
          const raw = d.data?.label || d.id || ""
          return `<div style="font:10px monospace;color:#e0e0e0;max-width:360px;word-break:break-all;padding:4px 6px">${raw.replace(/\n/g, "<br>")}</div>`
        },
      },
    ],
  })
  _ngGraph.on("node:dblclick", ({ target }) => {
    const id = target.id
    if (!id) return
    const label = _ngGraph.getNodeData(id).data?.label || id
    const next = prompt("编辑节点标签：", label)
    if (next && next !== label) {
      _ngGraph.updateNodeData([{ id, data: { label: next } }])
      _ngGraph.render()
    }
  })
  _ngGraph.on("afterlayout", () => {
    setTimeout(() => {
      if (_ngGraph && !_ngGraph.destroyed) _ngGraph.layout()
    }, 5000)
  })
  await _ngGraph.render()
}

function _ngBuildToolbar() {
  const tb = document.getElementById("ngToolbar")
  if (!tb) return
  tb.textContent = ""

  const s = document.createElement("span")
  s.textContent = "布局："
  s.style.cssText = "font-size:11px;color:var(--muted);line-height:26px"
  tb.appendChild(s)

  for (const name of Object.keys(_NG_LAYOUTS)) {
    const b = document.createElement("button")
    b.textContent = name
    b.style.cssText = "font-size:11px;padding:2px 10px;border-radius:6px;border:1px solid var(--border);background:" + (name === _ngCurLayout ? "var(--brand)" : "transparent") + ";color:var(--text);cursor:pointer"
    b.onclick = () => { _ngCurLayout = name; _ngBuildToolbar(); _ngBuildGraph() }
    tb.appendChild(b)
  }

  const r = document.createElement("button")
  r.textContent = "⇱ 复位"
  r.style.cssText = "font-size:11px;padding:2px 10px;border-radius:6px;border:1px solid var(--border);background:transparent;color:var(--text);cursor:pointer"
  r.onclick = () => _ngGraph?.fitView(50)
  tb.appendChild(r)

  const oldParams = document.querySelector("._ngParams")
  if (oldParams) oldParams.remove()
  const params = _NG_LAYOUT_PARAMS[_ngCurLayout] || {}
  const keys = Object.keys(params)
  if (keys.length) {
    const pw = document.createElement("div")
    pw.className = "_ngParams"
    pw.style.cssText = "display:flex;gap:10px;flex-wrap:wrap;width:100%;margin-top:4px"
    for (const key of keys) {
      const [min, max, def, step] = params[key]
      const p = document.createElement("label")
      p.style.cssText = "font-size:10px;color:var(--muted);display:flex;align-items:center;gap:4px"
      p.textContent = key + " "
      const inp = document.createElement("input")
      inp.type = "range"
      inp.className = "_ngpslider"
      inp.dataset.param = key
      inp.min = min; inp.max = max; inp.value = def; inp.step = step
      inp.style.cssText = "width:90px;height:14px;accent-color:var(--brand)"
      const val = document.createElement("span")
      val.style.cssText = "font-size:10px;color:var(--brand);min-width:30px"
      val.textContent = def
      inp.oninput = () => { val.textContent = inp.value }
      inp.onchange = () => _ngBuildGraph()
      p.appendChild(inp); p.appendChild(val); pw.appendChild(p)
    }
    const container = document.getElementById("ngMemGraph")
    if (container && container.parentElement) {
      container.parentElement.insertBefore(pw, container)
    }
  }
}

async function loadGraph(level) {
  const name = document.getElementById("ngInstName")?.value || ""
  if (!name) return
  try {
    const resp = await fetch("/api/instances/nanoghost/" + encodeURIComponent(name) + "/memory/graph?level=" + level)
    const r = await resp.json()
    const container = document.getElementById("ngMemGraph")
    if (!container) return
    _ngNodes = r.nodes || []
    _ngEdges = r.edges || []

    const lvlBtns = document.querySelectorAll("._ngLvl")
    lvlBtns.forEach(b => {
      b.style.background = b.dataset.level == level ? "var(--brand)" : "transparent"
    })

    if (_ngNodes.length === 0) {
      container.textContent = "暂无流程转移图数据"
      container.style.cssText = "min-height:60px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:13px;border:1px solid var(--border);border-radius:12px"
      return
    }
    if (_ngNodes.length < 2) {
      container.textContent = _ngNodes[0]?.label || _ngNodes[0]?.id || "单节点"
      container.style.cssText = "min-height:60px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:13px;border:1px solid var(--border);border-radius:12px"
      return
    }
    container.style.cssText = "min-height:400px;border:1px solid var(--border);border-radius:12px;overflow:hidden"
    _ngBuildToolbar()
    await _ngBuildGraph()
  } catch (e) {
    const toast = document.getElementById("toast")
    if (toast) toast.textContent = String(e)
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search)
  const name = params.get("name") || ""
  const level = parseInt(params.get("level") || "2")

  const nameEl = document.getElementById("ngInstName")
  if (nameEl) nameEl.value = name

  document.getElementById("ngInstTitle").textContent = name || "N/A"

  const lvlBtns = document.querySelectorAll("._ngLvl")
  lvlBtns.forEach(b => {
    b.style.background = b.dataset.level == level ? "var(--brand)" : "transparent"
    b.addEventListener("click", () => loadGraph(parseInt(b.dataset.level)))
  })

  loadGraph(level)
})

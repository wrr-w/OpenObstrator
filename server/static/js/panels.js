// NanoGhost Memory graph rendering
let _ngNodes = []
let _ngEdges = []
let _ngCurLayout = "d3-force"
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

async function _ngBuildGraph() {
  const container = document.getElementById("ngMemGraph")
  if (!container || _ngNodes.length < 2) return
  if (_ngGraph) _ngGraph.destroy()
  container.textContent = ""
  container.style.cssText = "height:480px;border:1px solid var(--border);border-radius:12px"

  const W = container.clientWidth || container.parentElement.clientWidth || 800
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
  const g6nodes = _ngNodes.map(n => ({ id: n.id, data: { label: n.label || n.id }, style: { fill: _ngColor(n.path || n.id) } }))
  const g6edges = _ngEdges.map(e => ({
    id: e.from + ">" + e.to, source: e.from, target: e.to,
    data: { type: e.label || "FOLLOWS", count: e.total_count || 1 },
    style: { lineWidth: Math.min(e.total_count || 1, 5) },
  }))

  _ngGraph = new G6.Graph({
    container, width: W, height: 460, autoFit: "view",
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

  // Auto-reheat: re-run layout 5s after settling for a "breathing" effect
  _ngGraph.on("afterlayout", () => {
    setTimeout(() => {
      if (_ngGraph && !_ngGraph.destroyed) _ngGraph.layout()
    }, 5000)
  })

  await _ngGraph.render()
}

function _ngBuildToolbar() {
  const container = document.getElementById("ngMemGraph")
  if (!container) return
  const cardBody = container.parentElement
  let tb = cardBody.querySelector("._ngtb")
  if (!tb) { tb = document.createElement("div"); tb.className = "_ngtb"; cardBody.insertBefore(tb, container) }
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

  const params = _NG_LAYOUT_PARAMS[_ngCurLayout] || {}
  const keys = Object.keys(params)
  if (keys.length) {
    const pw = document.createElement("div")
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
    cardBody.insertBefore(pw, container)
  }
}

async function _renderNgFlowGraph(container, nodes, edges) {
  _ngNodes = nodes; _ngEdges = edges
  if (nodes.length < 2) {
    container.textContent = nodes[0]?.label || nodes[0]?.id || "单节点"
    container.style.cssText = "min-height:60px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:13px;border:1px solid var(--border);border-radius:12px"
    return
  }
  _ngBuildToolbar()
  await _ngBuildGraph()
}

function _parseNgMemSections(raw) {
  const sections = []
  let cur = null
  for (const line of (raw || "").split("\n")) {
    const m = line.match(/^##\s+(.+)$/)
    if (m) { cur = { section: m[1].trim(), items: [] }; sections.push(cur) }
    else if (cur) { const t = line.replace(/^[-*]\s+/, "").trim(); if (t) cur.items.push(t) }
  }
  return sections
}

async function refreshNanoGhostMemories() {
  const rt = _activeRuntime
  const name = _activeName
  if (!name || rt !== "nanoghost") return

  // Show NanoGhost memories block, hide Hermes
  const ngBlock = document.getElementById("nanoghost-memories-block")
  const hermesBlock = document.getElementById("hermes-memories-block")
  if (ngBlock) ngBlock.style.display = ""
  if (hermesBlock) hermesBlock.style.display = "none"

  const pathEl = document.getElementById("ngMemPath")
  const ta = document.getElementById("ngMemRaw")

  try {
    const r = await loadNgMemoryRaw(name)
    if (pathEl && r.path) pathEl.textContent = "path: " + r.path
    if (ta) ta.value = r.raw || ""
  } catch (e) {
    if (ta) ta.value = ""
    setToast(String(e))
  }

  // Render memory.md sections
  try {
    const mdBody = document.getElementById("ngMemMdBody")
    if (mdBody) {
      mdBody.textContent = ""
      const sections = _parseNgMemSections(ta ? ta.value : "")
      for (const sec of sections) {
        const card = document.createElement("div")
        card.style.cssText = "margin-bottom:8px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px"
        const h = document.createElement("div")
        h.textContent = sec.section
        h.style.cssText = "font-weight:bold;font-size:12px;margin-bottom:4px;color:var(--brand)"
        card.appendChild(h)
        for (const item of sec.items) {
          const d = document.createElement("div")
          d.textContent = item
          d.style.cssText = "font-size:11px;padding:2px 4px;color:var(--text)"
          card.appendChild(d)
        }
        mdBody.appendChild(card)
      }
      if (sections.length === 0) {
        mdBody.textContent = "暂无 memory.md 条目"
        mdBody.style.cssText = "font-size:12px;color:var(--muted);text-align:center;padding:12px"
      }
    }
  } catch (e) {
    setToast(String(e))
  }

  // Render memory cards
  try {
    const cardsBody = document.getElementById("ngMemCardsBody")
    const cardsCount = document.getElementById("ngMemCardsCount")
    if (cardsBody) cardsBody.textContent = ""
    if (!cardsBody) return
    let cards = []
    try {
      const r = await loadNgMemoryCards(name)
      cards = r.cards || []
    } catch {}
    if (cardsCount) cardsCount.textContent = cards.length + " 张"
    if (cards.length === 0) {
      cardsBody.textContent = "暂无流程记忆卡片"
      cardsBody.style.cssText = "font-size:12px;color:var(--muted);text-align:center;padding:12px"
      cardsBody.className = ""
    } else {
      cardsBody.className = "cardBody"
      cardsBody.style.cssText = ""
      for (const card of cards) {
        const d = document.createElement("div")
        d.style.cssText = "background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px;margin-bottom:6px;font-size:11px;line-height:1.5;cursor:pointer"
        const userEl = document.createElement("div")
        userEl.textContent = card.user_input || ""
        userEl.style.cssText = "color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
        d.appendChild(userEl)
        const meta = document.createElement("div")
        meta.style.cssText = "display:flex;gap:8px;color:var(--muted);font-size:10px;margin-top:4px"
        const ts = document.createElement("span")
        ts.textContent = card.finished_at || ""
        meta.appendChild(ts)
        for (const [label, key] of [["成功", "success_count"], ["轮次", "total_steps"], ["赞成", "approve_count"], ["拒绝", "reject_count"], ["触发", "trigger_count"]]) {
          if (card[key] != null) {
            const sp = document.createElement("span")
            sp.textContent = label + " " + card[key]
            meta.appendChild(sp)
          }
        }
        d.appendChild(meta)
        d.onclick = () => {
          const txt = "用户: " + (card.user_input || "") + "\n\n助手: " + (card.agent_output || "")
          alert(txt)
        }
        cardsBody.appendChild(d)
      }
    }
  } catch (e) {
    setToast(String(e))
  }

  // Render graph
  try {
    const r = await loadNgMemoryGraph(name)
    const container = document.getElementById("ngMemGraph")
    if (!container) return
    const nodes = r.nodes || []
    const edges = r.edges || []
    if (nodes.length === 0) {
      container.textContent = "暂无流程转移图数据"
      container.style.cssText = "min-height:60px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:13px;border:1px solid var(--border);border-radius:12px"
      return
    }
    await _renderNgFlowGraph(container, nodes, edges)
  } catch (e) {
    setToast(String(e))
  }
}

async function refreshEnv() {
  const rt = _activeRuntime
  const name = _activeName
  const env = await loadEnv(rt, name)
  const envPathEl = document.getElementById("envPath")
  if (envPathEl) envPathEl.textContent = env.path ? `path: ${env.path}` : ""
  const tbody = document.getElementById("envBody")
  if (!tbody) return
  tbody.textContent = ""
  for (const it of env.items || []) {
    const tr = document.createElement("tr")
    tr.dataset.envKey = it.key
    const k = document.createElement("td")
    k.textContent = it.key
    const v = document.createElement("td")
    const inp = document.createElement("input")
    inp.value = it.value || ""
    inp.dataset.orig = it.value || ""
    v.appendChild(inp)
    const a = document.createElement("td")
    const delBtn = document.createElement("button")
    delBtn.textContent = "删除"
    delBtn.className = "danger"
    delBtn.addEventListener("click", async () => {
      if (!confirm(`确认删除 ${it.key} ?`)) return
      try {
        setToast("")
        await deleteEnv(_activeRuntime, _activeName, it.key)
        await refreshEnv()
      } catch (err) {
        setToast(String(err))
      }
    })
    a.appendChild(delBtn)
    tr.appendChild(k)
    tr.appendChild(v)
    tr.appendChild(a)
    tbody.appendChild(tr)
  }
}

async function refreshPrompts() {
  const rt = _activeRuntime
  const name = _activeName
  try {
    const r = await apiJson(`/api/instances/${encodeURIComponent(rt)}/${encodeURIComponent(name)}/prompts`, { method: "GET" })
    const dirEl = document.getElementById("promptsDir")
    if (dirEl) dirEl.textContent = r.dir ? `dir: ${r.dir}` : ""
    const body = document.getElementById("promptsBody")
    if (!body) return
    body.textContent = ""
    const items = r.items || []
    if (items.length === 0) {
      body.textContent = "暂无 prompt 文件"
      body.className = "hint"
      return
    }
    body.className = ""
    for (const f of items) {
      const block = document.createElement("div")
      block.style.marginTop = "8px"
      block.style.border = "1px solid var(--border)"
      block.style.borderRadius = "8px"
      block.style.padding = "8px"

      const header = document.createElement("div")
      header.style.cursor = "pointer"
      header.style.userSelect = "none"
      header.style.display = "flex"
      header.style.alignItems = "center"
      header.style.gap = "8px"
      header.style.padding = "4px 0"
      const arrow = document.createElement("span")
      arrow.textContent = "\u25b6"
      arrow.style.fontSize = "11px"
      const nameSpan = document.createElement("span")
      nameSpan.style.fontWeight = "700"
      nameSpan.textContent = f.name
      header.appendChild(arrow)
      header.appendChild(nameSpan)
      block.appendChild(header)

      const editor = document.createElement("div")
      editor.style.display = "none"
      const ta = document.createElement("textarea")
      ta.style.width = "100%"
      ta.style.minHeight = "200px"
      ta.style.fontFamily = "monospace"
      ta.style.fontSize = "13px"
      ta.style.marginTop = "8px"
      ta.readOnly = true
      editor.appendChild(ta)
      block.appendChild(editor)

      const btnRow = document.createElement("div")
      btnRow.style.display = "none"
      btnRow.style.marginTop = "8px"
      btnRow.style.gap = "8px"
      btnRow.style.alignItems = "center"

      const editBtn = document.createElement("button")
      editBtn.textContent = "编辑"
      const saveBtn = document.createElement("button")
      saveBtn.textContent = "保存"
      saveBtn.className = "primary"
      saveBtn.style.display = "none"
      const cancelBtn = document.createElement("button")
      cancelBtn.textContent = "取消"
      cancelBtn.style.display = "none"

      btnRow.appendChild(editBtn)
      btnRow.appendChild(saveBtn)
      btnRow.appendChild(cancelBtn)
      block.appendChild(btnRow)

      let isEditing = false
      let originalContent = ""

      editBtn.addEventListener("click", async () => {
        if (!isEditing) {
          const data = await apiJson(`/api/instances/${encodeURIComponent(rt)}/${encodeURIComponent(name)}/prompts/${encodeURIComponent(f.name)}`, { method: "GET" })
          ta.value = data.raw || ""
          ta.readOnly = false
          originalContent = ta.value
          isEditing = true
          editBtn.textContent = "取消"
          saveBtn.style.display = ""
          cancelBtn.style.display = "none"
        } else {
          ta.value = originalContent
          ta.readOnly = true
          isEditing = false
          editBtn.textContent = "编辑"
          saveBtn.style.display = "none"
        }
      })

      saveBtn.addEventListener("click", async () => {
        try {
          setToast("")
          await apiJson(`/api/instances/${encodeURIComponent(rt)}/${encodeURIComponent(name)}/prompts/${encodeURIComponent(f.name)}`, {
            method: "PUT",
            body: JSON.stringify({ raw: ta.value }),
          })
          originalContent = ta.value
          ta.readOnly = true
          isEditing = false
          editBtn.textContent = "编辑"
          saveBtn.style.display = "none"
          setToast("已保存")
        } catch (e) {
          setToast(String(e))
        }
      })

      header.addEventListener("click", () => {
        const isOpen = editor.style.display !== "none"
        editor.style.display = isOpen ? "none" : ""
        btnRow.style.display = isOpen ? "none" : ""
        arrow.textContent = isOpen ? "\u25b6" : "\u25bc"
        if (!isOpen && !ta.value) {
          apiJson(`/api/instances/${encodeURIComponent(rt)}/${encodeURIComponent(name)}/prompts/${encodeURIComponent(f.name)}`, { method: "GET" }).then(data => {
            ta.value = data.raw || ""
            originalContent = ta.value
          }).catch(() => {})
        }
      })

      body.appendChild(block)
    }
  } catch (e) {
    setToast(String(e))
  }
}

async function refreshSkills() {
  const rt = _activeRuntime
  const name = _activeName
  const sk = await loadSkills(rt, name)
  const body = document.getElementById("skillsBody")
  if (!body) return
  body.textContent = ""
  const groups = {}
  for (const it of sk.items || []) {
    const cat = it.category ? String(it.category) : "(root)"
    const src = it.source ? String(it.source) : "local"
    const g = `${src} / ${cat}`
    if (!groups[g]) groups[g] = []
    groups[g].push(it)
  }
  for (const [gPath, items] of Object.entries(groups)) {
    const block = document.createElement("div")
    block.style.marginTop = "10px"
    const header = document.createElement("div")
    header.style.cursor = "pointer"
    header.style.userSelect = "none"
    header.style.display = "flex"
    header.style.alignItems = "center"
    header.style.gap = "10px"
    header.style.padding = "4px 0"
    const arrow = document.createElement("span")
    arrow.textContent = "\u25b6"
    arrow.style.fontSize = "11px"
    const label = document.createElement("span")
    label.style.fontWeight = "700"
    label.style.fontSize = "13px"
    label.textContent = gPath
    const selAll = document.createElement("input")
    selAll.type = "checkbox"
    selAll.title = "全选/取消此分组"
    selAll.addEventListener("change", () => {
      for (const cb of Array.from(block.querySelectorAll(".skillCb"))) {
        cb.checked = selAll.checked
      }
    })
    header.appendChild(arrow)
    header.appendChild(selAll)
    header.appendChild(label)
    block.appendChild(header)
    const tbl = document.createElement("table")
    tbl.style.display = "none"
    const tbdy = document.createElement("tbody")
    for (const it of items) {
      const tr = document.createElement("tr")
      tr.dataset.skill = it.name
      tr.dataset.skillDesc = it.description || ""
      const n = document.createElement("td")
      const e = document.createElement("td")
      const ptd = document.createElement("td")
      const nc = document.createElement("code")
      nc.textContent = it.name
      n.appendChild(nc)
      const cb = document.createElement("input")
      cb.type = "checkbox"
      cb.className = "skillCb"
      cb.checked = Boolean(it.enabled)
      cb.dataset.skillName = it.name
      e.appendChild(cb)
      const desc = (it.description || "").trim()
      const path = it.path || ""
      ptd.textContent = desc ? `${desc}\n${path}` : path
      ptd.style.fontSize = "12px"
      ptd.style.color = "var(--muted)"
      tr.appendChild(n)
      tr.appendChild(e)
      tr.appendChild(ptd)
      tbdy.appendChild(tr)
    }
    tbl.appendChild(tbdy)
    block.appendChild(tbl)
    header.addEventListener("click", (ev) => {
      if (ev.target === selAll) return
      const isOpen = tbl.style.display !== "none"
      tbl.style.display = isOpen ? "none" : ""
      arrow.textContent = isOpen ? "\u25b6" : "\u25bc"
    })
    body.appendChild(block)
  }
}

async function refreshNanoGhostMcp() {
  if (_activeRuntime !== "nanoghost") return
  const name = _activeName
  const allow = await ngMcpAllowlistGet(name)
  const inp = document.getElementById("ngMcpAllowlist")
  if (inp) inp.value = (allow.enabled_only || []).join(",")
  const tbody = document.getElementById("ngMcpProbeBody")
  if (tbody) tbody.textContent = ""
  const toolsOut = document.getElementById("ngMcpToolsOut")
  if (toolsOut) toolsOut.value = ""
}

async function refreshHermesExtras() {
  const name = _activeName
  try {
    const cfg = await apiJson(`/api/profiles/${encodeURIComponent(name)}/config/raw`, { method: "GET" })
    const cfgPathEl = document.getElementById("cfgPath")
    if (cfgPathEl) cfgPathEl.textContent = cfg.path ? `path: ${cfg.path}` : ""
    const ta = document.getElementById("cfgRaw")
    if (ta) ta.value = cfg.raw || ""
  } catch (e) {
    setToast(String(e))
  }

  try {
    const soul = await apiJson(`/api/profiles/${encodeURIComponent(name)}/soul/raw`, { method: "GET" })
    const soulPathEl = document.getElementById("soulPath")
    if (soulPathEl) soulPathEl.textContent = soul.path ? `path: ${soul.path}` : ""
    const ta = document.getElementById("soulRaw")
    if (ta) ta.value = soul.raw || ""
  } catch (e) {
    setToast(String(e))
  }

  try {
    const userMem = await apiJson(`/api/profiles/${encodeURIComponent(name)}/memories/user/raw`, { method: "GET" })
    const p1 = document.getElementById("userMemPath")
    if (p1) p1.textContent = userMem.path ? `path: ${userMem.path}` : ""
    const ta1 = document.getElementById("userMemRaw")
    if (ta1) ta1.value = userMem.raw || ""
  } catch (e) {
    setToast(String(e))
  }

  try {
    const mem = await apiJson(`/api/profiles/${encodeURIComponent(name)}/memories/memory/raw`, { method: "GET" })
    const p2 = document.getElementById("memoryMemPath")
    if (p2) p2.textContent = mem.path ? `path: ${mem.path}` : ""
    const ta2 = document.getElementById("memoryMemRaw")
    if (ta2) ta2.value = mem.raw || ""
  } catch (e) {
    setToast(String(e))
  }

  try {
    const cr = await apiJson(`/api/profiles/${encodeURIComponent(name)}/cron`, { method: "GET" })
    const cd = document.getElementById("cronDir")
    if (cd) cd.textContent = cr.dir ? `dir: ${cr.dir}` : ""
    const body = document.getElementById("cronBody")
    if (body) {
      body.textContent = ""
      if (cr.items.length === 0) {
        body.textContent = "暂无 cron 任务"
        body.className = "hint"
      } else {
        body.className = ""
        for (const it of cr.items) {
          const block = document.createElement("div")
          block.style.marginTop = "10px"
          const label = document.createElement("div")
          label.style.fontWeight = "700"
          label.style.fontSize = "13px"
          label.textContent = it.name
          block.appendChild(label)
          const pre = document.createElement("pre")
          pre.style.fontSize = "12px"
          pre.style.margin = "4px 0"
          pre.style.padding = "8px"
          pre.style.background = "var(--panel)"
          pre.style.borderRadius = "8px"
          pre.style.overflow = "auto"
          pre.style.maxHeight = "200px"
          pre.textContent = it.raw || "(empty)"
          block.appendChild(pre)
          body.appendChild(block)
        }
      }
    }
  } catch (e) {
    setToast(String(e))
  }

  try {
    const lg = await apiJson(`/api/profiles/${encodeURIComponent(name)}/logs`, { method: "GET" })
    const ld = document.getElementById("logsDir")
    if (ld) ld.textContent = lg.dir ? `dir: ${lg.dir}` : ""
    const body = document.getElementById("logsBody")
    if (body) {
      body.textContent = ""
      if (lg.files.length === 0) {
        body.textContent = "暂无日志"
        body.className = "hint"
      } else {
        body.className = ""
        for (const f of lg.files) {
          const block = document.createElement("div")
          block.style.marginTop = "8px"
          const label = document.createElement("div")
          label.style.cursor = "pointer"
          label.style.userSelect = "none"
          label.style.display = "flex"
          label.style.alignItems = "center"
          label.style.gap = "10px"
          label.style.padding = "4px 0"
          const arrow = document.createElement("span")
          arrow.textContent = "\u25b6"
          arrow.style.fontSize = "11px"
          const nameSpan = document.createElement("span")
          nameSpan.style.fontWeight = "700"
          nameSpan.style.fontSize = "13px"
          const sizeKB = (f.size / 1024).toFixed(1)
          nameSpan.textContent = `${f.name} (${sizeKB} KB)`
          label.appendChild(arrow)
          label.appendChild(nameSpan)
          block.appendChild(label)
          const content = document.createElement("pre")
          content.style.display = "none"
          content.style.fontSize = "11px"
          content.style.margin = "4px 0"
          content.style.padding = "8px"
          content.style.background = "var(--panel)"
          content.style.borderRadius = "8px"
          content.style.overflow = "auto"
          content.style.maxHeight = "400px"
          content.textContent = f.tail || "(empty)"
          block.appendChild(content)
          label.addEventListener("click", () => {
            const isOpen = content.style.display !== "none"
            content.style.display = isOpen ? "none" : ""
            arrow.textContent = isOpen ? "\u25b6" : "\u25bc"
          })
          body.appendChild(block)
        }
      }
    }
  } catch (e) {
    setToast(String(e))
  }

  try {
    const ss = await apiJson(`/api/profiles/${encodeURIComponent(name)}/sessions`, { method: "GET" })
    const sd = document.getElementById("sessionsDir")
    if (sd) sd.textContent = ss.dir ? `dir: ${ss.dir}` : ""
    const body = document.getElementById("sessionsBody")
    if (body) {
      body.textContent = ""
      if (ss.items.length === 0) {
        body.textContent = "暂无 sessions"
        body.className = "hint"
      } else {
        body.className = ""
        const tbl = document.createElement("table")
        const thead = document.createElement("thead")
        const thr = document.createElement("tr")
        for (const h of ["名称", "大小", "修改时间"]) {
          const th = document.createElement("th")
          th.textContent = h
          thr.appendChild(th)
        }
        thead.appendChild(thr)
        tbl.appendChild(thead)
        const tbdy = document.createElement("tbody")
        for (const it of ss.items) {
          const tr = document.createElement("tr")
          const tdN = document.createElement("td")
          tdN.textContent = it.preview || it.name
          const tdS = document.createElement("td")
          const sizeKB = (it.size / 1024).toFixed(1)
          tdS.textContent = `${sizeKB} KB`
          const tdM = document.createElement("td")
          const d = new Date(it.mtime * 1000)
          tdM.textContent = d.toLocaleString()
          tdM.style.fontSize = "12px"
          tdM.style.color = "var(--muted)"
          tr.appendChild(tdN)
          tr.appendChild(tdS)
          tr.appendChild(tdM)
          tbdy.appendChild(tr)
        }
        tbl.appendChild(tbdy)
        body.appendChild(tbl)
      }
    }
  } catch (e) {
    setToast(String(e))
  }
}

async function refreshChannels() {
  const rt = _activeRuntime
  const name = _activeName
  const body = document.getElementById("channelsBody")
  const chPathEl = document.getElementById("chPath")
  if (body) body.textContent = ""
  if (chPathEl) chPathEl.textContent = ""

  if (rt === "hermes") {
    const ch = await apiJson(`/api/profiles/${encodeURIComponent(name)}/channels`, { method: "GET" })
    if (chPathEl) chPathEl.textContent = ch.path ? `path: ${ch.path}` : ""
    if (!body) return
    if (ch.updated_at) {
      const ts = document.createElement("div")
      ts.className = "hint"
      ts.textContent = "更新于: " + ch.updated_at
      body.appendChild(ts)
    }
    for (const [platform, channels] of Object.entries(ch.platforms || {})) {
      const block = document.createElement("div")
      block.style.marginTop = "10px"
      const header = document.createElement("div")
      header.style.cursor = "pointer"
      header.style.userSelect = "none"
      header.style.display = "flex"
      header.style.alignItems = "center"
      header.style.gap = "10px"
      header.style.padding = "4px 0"
      const arrow = document.createElement("span")
      arrow.textContent = "\u25b6"
      arrow.style.fontSize = "11px"
      const label = document.createElement("span")
      label.style.fontWeight = "700"
      label.style.fontSize = "13px"
      const count = channels ? channels.length : 0
      label.textContent = `${platform} (${count})`
      header.appendChild(arrow)
      header.appendChild(label)
      block.appendChild(header)
      const content = document.createElement("div")
      content.style.display = "none"
      if (channels && channels.length > 0) {
        const tbl = document.createElement("table")
        const thead = document.createElement("thead")
        const thr = document.createElement("tr")
        for (const h of ["名称", "类型", "ID"]) {
          const th = document.createElement("th")
          th.textContent = h
          thr.appendChild(th)
        }
        thead.appendChild(thr)
        tbl.appendChild(thead)
        const tbdy = document.createElement("tbody")
        for (const chItem of channels) {
          const tr = document.createElement("tr")
          const tdName = document.createElement("td")
          tdName.textContent = chItem.name || "-"
          const tdType = document.createElement("td")
          tdType.textContent = chItem.type || "-"
          const tdId = document.createElement("td")
          const idCode = document.createElement("code")
          idCode.textContent = chItem.id || "-"
          tdId.appendChild(idCode)
          tr.appendChild(tdName)
          tr.appendChild(tdType)
          tr.appendChild(tdId)
          tbdy.appendChild(tr)
        }
        tbl.appendChild(tbdy)
        content.appendChild(tbl)
      } else {
        const empty = document.createElement("div")
        empty.className = "hint"
        empty.style.padding = "4px 20px"
        empty.textContent = "无活跃频道"
        content.appendChild(empty)
      }
      block.appendChild(content)
      header.addEventListener("click", () => {
        const isOpen = content.style.display !== "none"
        content.style.display = isOpen ? "none" : ""
        arrow.textContent = isOpen ? "\u25b6" : "\u25bc"
      })
      body.appendChild(block)
    }
    return
  }

  if (rt === "nanoghost") {
    const ch = await loadChannels(rt, name)
    if (!body) return
    if (chPathEl) chPathEl.textContent = ch.path ? `path: ${ch.path}` : ""
    const cfg = ch.config || {}
    const channels = cfg.channels || {}
    const items = Object.entries(channels)
    const table = document.createElement("table")
    const thead = document.createElement("thead")
    const thr = document.createElement("tr")
    for (const h of ["渠道", "启用"]) {
      const th = document.createElement("th")
      th.textContent = h
      thr.appendChild(th)
    }
    thead.appendChild(thr)
    table.appendChild(thead)
    const tbdy = document.createElement("tbody")
    for (const [k, v] of items) {
      const tr = document.createElement("tr")
      tr.dataset.channelKey = k
      const td1 = document.createElement("td")
      const code = document.createElement("code")
      code.textContent = k
      td1.appendChild(code)
      const td2 = document.createElement("td")
      const cb = document.createElement("input")
      cb.type = "checkbox"
      cb.checked = Boolean(v && v.enabled)
      td2.appendChild(cb)
      tr.appendChild(td1)
      tr.appendChild(td2)
      tbdy.appendChild(tr)
    }
    table.appendChild(tbdy)
    body.appendChild(table)
    const row = document.createElement("div")
    row.className = "row"
    row.style.marginTop = "10px"
    const btn = document.createElement("button")
    btn.className = "primary"
    btn.textContent = "确认保存"
    btn.addEventListener("click", async () => {
      try {
        const next = { ...(cfg || {}), channels: { ...(cfg.channels || {}) } }
        for (const tr of Array.from(tbdy.querySelectorAll("tr"))) {
          const key = tr.dataset.channelKey
          const inp = tr.querySelector("input")
          if (!key || !inp) continue
          const old = next.channels[key] || {}
          next.channels[key] = { ...old, enabled: Boolean(inp.checked) }
        }
        setToast("")
        await saveChannels(rt, name, next)
        await refreshChannels()
      } catch (e) {
        setToast(String(e))
      }
    })
    row.appendChild(btn)
    body.appendChild(row)
    return
  }
}

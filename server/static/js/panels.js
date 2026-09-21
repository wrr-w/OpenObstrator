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
  if (_ngGraph) { try { _ngGraph.destroy() } catch (e) {}; _ngGraph = null }
  if (container) container.textContent = ""
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

  // Remove old slider params container to prevent duplication
  const oldParams = cardBody.querySelector("._ngParams")
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
    cardBody.insertBefore(pw, container)
  }
  // Wire level buttons directly (avoids closure issues with block-scoped function declarations)
  const lvlBtns = document.getElementById("ngLevelBtns")
  if (lvlBtns && !lvlBtns._ngWired) {
    lvlBtns._ngWired = true
    Array.from(lvlBtns.children).forEach(btn => {
      if (btn.dataset && btn.dataset.level) {
        const level = parseInt(btn.dataset.level)
        btn.onclick = () => _ngLoadGraph(level)
      }
    })
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

async function _ngLoadGraph(level) {
  const rt = _activeRuntime
  const name = _activeName
  if (!name || rt !== "nanoghost") return
  try {
    const r = await loadNgMemoryGraph(name, level)
    const container = document.getElementById("ngMemGraph")
    if (!container) return
    const nodes = r.nodes || []
    const edges = r.edges || []
    const lvlBtns = document.getElementById("ngLevelBtns")
    if (lvlBtns) {
      const btns = lvlBtns.querySelectorAll("button")
      btns.forEach(b => {
        b.style.background = b.dataset.level == level ? "var(--brand)" : "transparent"
      })
    }
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
  let _ngMemRaw = ""

  try {
    const r = await loadNgMemoryRaw(name)
    if (pathEl && r.path) pathEl.textContent = "path: " + r.path
    _ngMemRaw = r.raw || ""
  } catch (e) {
    setToast(String(e))
  }

  // Render memory.md Markdown preview
  try {
    const mdPreview = document.getElementById("ngMemMdPreview")
    if (mdPreview) {
      const raw = _ngMemRaw
      if (raw.trim()) {
        if (typeof marked !== "undefined") {
          mdPreview.innerHTML = marked.parse(raw)
        } else {
          mdPreview.textContent = raw
        }
        mdPreview.style.cssText = "font-size:13px;line-height:1.7;padding:8px"
      } else {
        mdPreview.textContent = "暂无 memory.md 条目"
        mdPreview.style.cssText = "font-size:12px;color:var(--muted);text-align:center;padding:12px"
      }
    }
  } catch (e) {
    setToast(String(e))
  }

  // Render memory.md sections
  try {
    const mdBody = document.getElementById("ngMemMdBody")
    if (mdBody) {
      mdBody.textContent = ""
      const sections = _parseNgMemSections(_ngMemRaw)
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
        d.title = "点击查看/编辑"
        const userEl = document.createElement("div")
        userEl.textContent = (card.user_input || "").slice(0, 60)
        userEl.style.cssText = "color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
        d.appendChild(userEl)
        const meta = document.createElement("div")
        meta.style.cssText = "display:flex;gap:8px;color:var(--muted);font-size:10px;margin-top:4px;flex-wrap:wrap"
        const ts = document.createElement("span")
        ts.textContent = card.finished_at || ""
        meta.appendChild(ts)
        if (card.flow_hash) {
          const fh = document.createElement("span")
          fh.textContent = "flow: " + (card.flow_hash || "").slice(0, 8)
          meta.appendChild(fh)
        }
        if (card.l1_code != null) {
          const l1 = document.createElement("span")
          l1.textContent = "L1: " + card.l1_code
          meta.appendChild(l1)
        }
        for (const [label, key] of [["\u6210\u529f", "success_count"], ["\u8f6e\u6b21", "total_steps"], ["\u8f6e\u6b21", "total_rounds"]]) {
          if (card[key] != null) {
            const sp = document.createElement("span")
            sp.textContent = label + " " + card[key]
            meta.appendChild(sp)
          }
        }
        d.appendChild(meta)
        d.addEventListener("click", async () => {
          const result = await openMemoryCardModal(card, name)
          if (result === "deleted") {
            // Refresh the card list
            await refreshNanoGhostMemories()
          }
        })
        cardsBody.appendChild(d)
      }
    }
  } catch (e) {
    setToast(String(e))
  }
}

function openNgMemGraph() {
  const name = _activeName
  const rt = _activeRuntime
  if (!name || rt !== "nanoghost") return
  window.open("/pages/memory-graph?name=" + encodeURIComponent(name) + "&level=2", "_blank")
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
      arrow.textContent = "▶"
      arrow.style.fontSize = "11px"
      const nameSpan = document.createElement("span")
      nameSpan.style.fontWeight = "700"
      nameSpan.textContent = f.name
      header.appendChild(arrow)
      header.appendChild(nameSpan)
      block.appendChild(header)

      // Markdown 渲染预览（非编辑态显示）
      const mdPreview = document.createElement("div")
      mdPreview.style.cssText = "font-size:13px;line-height:1.7;padding:8px 4px;display:none;word-break:break-word"
      block.appendChild(mdPreview)

      // 编辑用 textarea（编辑态显示）
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
      let rendered = false

      function renderPreview() {
        const raw = ta.value || ""
        if (raw.trim() && typeof marked !== "undefined") {
          mdPreview.innerHTML = marked.parse(raw)
        } else {
          mdPreview.textContent = raw
        }
      }

      async function loadContent() {
        const data = await apiJson(`/api/instances/${encodeURIComponent(rt)}/${encodeURIComponent(name)}/prompts/${encodeURIComponent(f.name)}`, { method: "GET" })
        ta.value = data.raw || ""
        originalContent = ta.value
        rendered = true
        renderPreview()
      }

      function showPreview() {
        mdPreview.style.display = ""
        editor.style.display = "none"
        ta.readOnly = true
      }

      function showEditor() {
        mdPreview.style.display = "none"
        editor.style.display = ""
      }

      editBtn.addEventListener("click", async () => {
        if (!isEditing) {
          if (!rendered) await loadContent()
          showEditor()
          ta.readOnly = false
          isEditing = true
          editBtn.textContent = "取消"
          saveBtn.style.display = ""
          cancelBtn.style.display = "none"
        } else {
          ta.value = originalContent
          isEditing = false
          editBtn.textContent = "编辑"
          saveBtn.style.display = "none"
          cancelBtn.style.display = "none"
          renderPreview()
          showPreview()
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
          isEditing = false
          editBtn.textContent = "编辑"
          saveBtn.style.display = "none"
          cancelBtn.style.display = "none"
          renderPreview()
          showPreview()
          setToast("已保存")
        } catch (e) {
          setToast(String(e))
        }
      })

      header.addEventListener("click", async () => {
        const isOpen = editor.style.display !== "none" || mdPreview.style.display !== "none"
        if (isOpen) {
          editor.style.display = "none"
          mdPreview.style.display = "none"
          btnRow.style.display = "none"
          arrow.textContent = "▶"
        } else {
          if (!rendered) {
            try {
              await loadContent()
            } catch (e) {
              setToast(String(e))
            }
          }
          if (isEditing) {
            showEditor()
          } else {
            showPreview()
          }
          btnRow.style.display = ""
          arrow.textContent = "▼"
        }
      })

      body.appendChild(block)
    }
  } catch (e) {
    setToast(String(e))
  }
}

function _updateGroupCheck(header) {
  const block = header.parentElement
  const selAll = block.querySelector("input[type=checkbox]:first-child")
  if (!selAll) return
  const cbs = Array.from(block.querySelectorAll(".skillCb"))
  selAll.checked = cbs.length > 0 && cbs.some(cb => cb.checked)
}

function _renderSkillRow(it, cbCls, onChange) {
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
  cb.className = cbCls
  cb.checked = Boolean(it.enabled)
  cb.dataset.skillName = it.name
  if (onChange) cb.addEventListener("change", onChange)
  e.appendChild(cb)
  const desc = (it.description || "").trim()
  const path = it.path || ""
  ptd.textContent = desc ? `${desc}\n${path}` : path
  ptd.style.fontSize = "12px"
  ptd.style.color = "var(--muted)"
  tr.appendChild(n)
  tr.appendChild(e)
  tr.appendChild(ptd)
  return tr
}

async function refreshSkills() {
  const rt = _activeRuntime
  const name = _activeName
  const sk = await loadSkills(rt, name)
  const body = document.getElementById("skillsBody")
  if (!body) return
  body.textContent = ""
  const groupMeta = sk.group_meta || {}
  const groups = {}
  const flatItems = []
  for (const it of sk.items || []) {
    if (it.category) {
      const src = it.source ? String(it.source) : "local"
      const g = `${src} / ${it.category}`
      if (!groups[g]) groups[g] = []
      groups[g].push(it)
    } else {
      flatItems.push(it)
    }
  }
  for (const [gPath, items] of Object.entries(groups)) {
    const cat = gPath.includes("/") ? gPath.split("/").pop().trim() : gPath
    // 分组入口行**留着**，别当"父节点"跳掉。NanoGhost 把分组目录自己的 SKILL.md 也
    // 注册成一个技能（名字取目录名），而 system prompt 里给模型的就是
    // `use_skill(name="分组名")` —— 子技能名根本不在上下文里。所以白名单里少这一个名字，
    // 整组就够不着，而且全程不报错。以前这里 `it.name === cat` 就 continue，于是这个
    // 名字面板永远勾不到，只能靠手改 config.yaml。
    const rows = items
    // 0 行 → 跳过; 1 行 → 扁平显示; >1 行 → 折叠组
    if (rows.length === 0) continue
    if (rows.length === 1) {
      flatItems.push(rows[0])
      continue
    }
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
    arrow.textContent = "\u25bc"
    arrow.style.fontSize = "11px"
    const label = document.createElement("span")
    label.style.fontWeight = "700"
    label.style.fontSize = "13px"
    const groupDesc = groupMeta[cat] || ""
    label.textContent = groupDesc ? `📁 ${gPath} — ${groupDesc}` : `📁 ${gPath}`
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
    const tbdy = document.createElement("tbody")
    const onChange = () => {
      const cbs = Array.from(tbdy.querySelectorAll(".skillCb"))
      selAll.checked = cbs.length > 0 && cbs.some(cb => cb.checked)
    }
    for (const it of rows) tbdy.appendChild(_renderSkillRow(it, "skillCb", onChange))
    tbl.appendChild(tbdy)
    block.appendChild(tbl)
    onChange()
    header.addEventListener("click", (ev) => {
      if (ev.target === selAll) return
      const isOpen = tbl.style.display !== "none"
      tbl.style.display = isOpen ? "none" : ""
      arrow.textContent = isOpen ? "\u25b6" : "\u25bc"
    })
    body.appendChild(block)
  }
  if (flatItems.length > 0) {
    const block = document.createElement("div")
    block.style.marginTop = "10px"
    const tbl = document.createElement("table")
    const tbdy = document.createElement("tbody")
    for (const it of flatItems) tbdy.appendChild(_renderSkillRow(it, "skillCb"))
    tbl.appendChild(tbdy)
    block.appendChild(tbl)
    body.appendChild(block)
  }

  // 保存按钮
  const saveRow = document.createElement("div")
  saveRow.style.cssText = "margin-top:16px;display:flex;gap:10px;align-items:center"
  const saveBtn = document.createElement("button")
  saveBtn.className = "primary"
  saveBtn.textContent = "保存"
  saveBtn.addEventListener("click", async () => {
    const items = {}
    for (const cb of Array.from(body.querySelectorAll(".skillCb"))) {
      items[cb.dataset.skillName] = cb.checked
    }
    try {
      await saveSkills(rt, name, items)
      setToast("Skills 已保存 ✅")
    } catch (e) {
      setToast("保存失败: " + String(e))
    }
  })
  saveRow.appendChild(saveBtn)
  const resetBtn = document.createElement("button")
  resetBtn.textContent = "撤销"
  resetBtn.addEventListener("click", () => refreshSkills())
  saveRow.appendChild(resetBtn)
  body.appendChild(saveRow)
}

async function refreshNanoGhostMcp() {
  if (_activeRuntime !== "nanoghost") return
  const name = _activeName
  const body = document.getElementById("mcpBody")
  if (!body) return
  body.innerHTML = '<div class="hint">加载中...</div>'
  
  try {
    const [allowR, probeR] = await Promise.all([
      ngMcpAllowlistGet(name),
      ngMcpProbe(name),
    ])
    
    const enabledSet = new Set((allowR.enabled_only || []).filter(Boolean))
    const actionAllowlist = allowR.action_allowlist || {}
    const allServers = probeR.items || []
    
    const serverActions = {}
    const toolResults = await Promise.all(allServers.map(s =>
      ngMcpTools(name, s.id).then(r => ({ id: s.id, tools: (r.tools || []).map(t => t.name || "") }))
        .catch(() => ({ id: s.id, tools: [] }))
    ))
    for (const { id, tools } of toolResults) {
      serverActions[id] = tools
    }
    
    body.textContent = ""
    
    if (!allServers.length) {
      body.innerHTML = '<div class="hint">未安装 MCP 服务器</div>'
      return
    }
    
    for (const svr of allServers) {
      const sid = svr.id
      const actions = serverActions[sid] || []
      const currentAllowed = actionAllowlist[sid]
      const serverEnabled = enabledSet.has(sid)
      
      const block = document.createElement("div")
      block.style.marginTop = "10px"
      
      const header = document.createElement("div")
      header.style.cursor = "pointer"
      header.style.userSelect = "none"
      header.style.display = "flex"
      header.style.alignItems = "center"
      header.style.gap = "10px"
      header.style.padding = "6px 0"
      
      const arrow = document.createElement("span")
      arrow.textContent = "\u25b6"
      arrow.style.fontSize = "11px"
      
      const selAll = document.createElement("input")
      selAll.type = "checkbox"
      selAll.className = "mcpMasterCb"
      selAll.title = "启用/禁用此服务器"
      selAll.checked = serverEnabled
      
      const nameEl = document.createElement("code")
      nameEl.textContent = sid
      nameEl.style.fontWeight = "700"
      nameEl.style.fontSize = "13px"
      
      const transportHint = document.createElement("span")
      transportHint.style.fontSize = "11px"
      transportHint.style.color = "var(--muted)"
      transportHint.textContent = actions.length + " 个工具"
      
      const statusDot = document.createElement("span")
      statusDot.className = "dot" + (svr.ok ? " ok" : svr.error ? " bad" : "")
      statusDot.style.marginLeft = "auto"
      
      header.appendChild(arrow)
      header.appendChild(selAll)
      header.appendChild(nameEl)
      header.appendChild(transportHint)
      header.appendChild(statusDot)
      block.appendChild(header)
      
      const tbl = document.createElement("table")
      tbl.style.display = "none"
      const tbdy = document.createElement("tbody")
      
      if (actions.length > 0) {
        const allowedSet = new Set(currentAllowed || [])
        const allEnabled = !currentAllowed
        
        selAll.addEventListener("change", () => {
          for (const cb of Array.from(tbl.querySelectorAll(".mcpActCb"))) {
            cb.checked = selAll.checked && (allEnabled || allowedSet.has(cb.dataset.actionName))
          }
        })
        
        for (const a of actions) {
          const tr = document.createElement("tr")
          const tdName = document.createElement("td")
          tdName.style.paddingLeft = "24px"
          
          const code = document.createElement("code")
          code.textContent = a
          code.style.fontSize = "12px"
          
          tdName.appendChild(code)
          tr.appendChild(tdName)
          tbdy.appendChild(tr)
        }
      } else {
        const tr = document.createElement("tr")
        const td = document.createElement("td")
        td.colSpan = 2
        td.className = "hint"
        td.textContent = "(暂无工具信息)"
        td.style.padding = "8px 0"
        tr.appendChild(td)
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
    
    const saveRow = document.createElement("div")
    saveRow.style.cssText = "margin-top:16px;display:flex;gap:10px;align-items:center"
    
    const saveBtn = document.createElement("button")
    saveBtn.className = "primary"
    saveBtn.textContent = "保存"
    saveBtn.addEventListener("click", async () => {
      const enabledServers = []
      
      for (const block of Array.from(body.children)) {
        if (block === saveRow) continue
        const headerCb = block.querySelector(".mcpMasterCb")
        if (!headerCb) continue
        const sid = headerCb.nextElementSibling?.textContent || ""
        if (!sid) continue
        
        if (headerCb.checked) {
          enabledServers.push(sid)
        }
      }
      
      try {
        await ngMcpAllowlistPut(name, enabledServers)
        setToast("MCP 已保存 ✅ 需重启实例生效")
        await refreshNanoGhostMcp()
      } catch (e) {
        setToast("保存失败: " + String(e))
      }
    })
    saveRow.appendChild(saveBtn)
    
    const resetBtn = document.createElement("button")
    resetBtn.textContent = "撤销"
    resetBtn.addEventListener("click", () => refreshNanoGhostMcp())
    saveRow.appendChild(resetBtn)
    
    body.appendChild(saveRow)
    
  } catch (e) {
    body.innerHTML = '<div class="hint" style="color:var(--bad)">加载失败: ' + e.message + '</div>'
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


async function refreshTools() {
  const rt = _activeRuntime
  const name = _activeName
  if (!name) return
  const body = document.getElementById("toolsBody")
  if (!body) return
  body.innerHTML = '<div class="hint">加载工具列表中...</div>'
  try {
    const r = await loadTools(rt, name)
    if (!r || !r.ok) {
      body.innerHTML = '<div class="hint" style="color:var(--bad)">获取失败</div>'
      return
    }
    const builtins = r.builtins || []
    const mcp = r.mcp_servers || []
    const channels = r.channels || []
    const channelToolCount = channels.reduce(function(acc, ch) { return acc + (ch.tools || []).length }, 0)
    const total = builtins.length + mcp.length + channelToolCount
    
    let html = '<div class="card"><div class="cardHead"><div class="cardTitle">注册工具</div><span class="pill">' + total + ' 个</span></div>'
    html += '<div class="cardBody"><table><thead><tr><th>工具名</th><th>来源</th><th>描述 / 操作</th></tr></thead><tbody>'
    
    // 按 category 分组：system / skill / subagent
    var groups = { system: [], skill: [], subagent: [] }
    for (const t of builtins) {
      var g = groups[t.category]
      if (g) g.push(t)
    }
    var groupLabels = { system: '系统工具', skill: '技能工具', subagent: '子代理工具' }
    for (const key of ['system', 'skill', 'subagent']) {
      var items = groups[key]
      if (!items || !items.length) continue
      html += '<tr style="background:var(--bg2)"><td colspan="3" style="padding:6px 8px;font-weight:700;font-size:12px">' + groupLabels[key] + ' <span class="pill">' + items.length + '</span></td></tr>'
      for (const t of items) {
        html += '<tr><td style="padding-left:20px"><code>' + t.name + '</code></td><td><span class="pill">' + key + '</span></td><td style="font-size:12px;color:var(--muted)">' + t.description + '</td></tr>'
      }
    }
    
    // MCP 工具
    if (mcp.length) {
      html += '<tr style="background:var(--bg2)"><td colspan="3" style="padding:6px 8px;font-weight:700;font-size:12px">MCP 工具 <span class="pill">' + mcp.length + '</span></td></tr>'
      for (const s of mcp) {
        const status = s.error ? '<span class="pill bad">错误</span>' : '<span class="pill ok">' + s.tools_count + ' 个</span>'
        html += '<tr><td style="padding-left:20px"><code>' + s.tool_name + '</code></td><td><span class="pill">mcp</span></td><td style="font-size:12px;color:var(--muted)">' + (s.description || '') + ' ' + status + '</td></tr>'
        if (s.error) html += '<tr><td colspan="3" style="color:var(--bad);font-size:11px">错误: ' + s.error + '</td></tr>'
      }
    }
    
    // 频道工具
    for (const ch of channels) {
      var chTools = ch.tools || []
      if (!chTools.length) continue
      html += '<tr style="background:var(--bg2)"><td colspan="3" style="padding:6px 8px;font-weight:700;font-size:12px">' + ch.channel + ' 频道 <span class="pill">' + chTools.length + '</span></td></tr>'
      for (const t of chTools) {
        html += '<tr><td style="padding-left:20px"><code>' + t.name + '</code></td><td><span class="pill">' + ch.channel + '</span></td><td style="font-size:12px;color:var(--muted)">' + (t.description || '') + '</td></tr>'
      }
    }
    
    html += '</tbody></table></div></div>'
    body.innerHTML = html
  } catch (e) {
    body.innerHTML = '<div class="hint" style="color:var(--bad)">加载失败: ' + e.message + '</div>'
  }
}




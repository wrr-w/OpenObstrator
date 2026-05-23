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

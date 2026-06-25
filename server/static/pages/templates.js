(() => {
  const toastEl = () => document.getElementById("toast")

  function setToast(msg) {
    const el = toastEl()
    if (!el) return
    el.textContent = msg || ""
  }

  async function apiJson(path, opts) {
    const res = await fetch(path, {
      headers: { "content-type": "application/json", ...(opts && opts.headers ? opts.headers : {}) },
      ...opts,
    })
    const text = await res.text()
    let data = null
    try {
      data = text ? JSON.parse(text) : null
    } catch {
      data = { raw: text }
    }
    if (!res.ok) {
      const detail = data && data.detail ? data.detail : res.statusText
      throw new Error(`${res.status} ${detail}`)
    }
    return data
  }

  function withTemplateId(path, template_id) {
    const tid = (template_id || "root").trim() || "root"
    const u = new URL(path, window.location.origin)
    u.searchParams.set("template_id", tid)
    return u.pathname + u.search
  }

  async function templatesList(runtime) {
    return apiJson(`/api/templates/${encodeURIComponent(runtime)}/list`, { method: "GET" })
  }

  async function templateManifest(runtime, template_id) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/manifest`, template_id), { method: "GET" })
  }

  async function templateLoadEnv(runtime, template_id) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/env`, template_id), { method: "GET" })
  }

  async function templateDeleteEnv(runtime, template_id, key) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/env`, template_id), {
      method: "DELETE",
      body: JSON.stringify({ key }),
    })
  }

  async function templateBatchPutEnv(runtime, template_id, items) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/env/batch`, template_id), {
      method: "PUT",
      body: JSON.stringify({ items }),
    })
  }

  async function templatePutEnv(runtime, template_id, key, value) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/env`, template_id), {
      method: "PUT",
      body: JSON.stringify({ key, value }),
    })
  }

  async function templateLoadSkills(runtime, template_id) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/skills`, template_id), { method: "GET" })
  }

  async function templateSaveSkills(runtime, template_id, items) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/skills/batch`, template_id), {
      method: "PUT",
      body: JSON.stringify({ items }),
    })
  }

  async function templateChannelsGet(runtime, template_id) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/channels`, template_id), { method: "GET" })
  }

  async function templateChannelsPut(runtime, template_id, config) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/channels`, template_id), {
      method: "PUT",
      body: JSON.stringify({ config }),
    })
  }

  async function templateConfigGet(runtime, template_id) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/config/raw`, template_id), { method: "GET" })
  }

  async function templateConfigPut(runtime, template_id, raw) {
    return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/config/raw`, template_id), {
      method: "PUT",
      body: JSON.stringify({ raw }),
    })
  }

  function createTabBar() {
    const tabBar = document.createElement("div")
    tabBar.style.marginTop = "14px"
    tabBar.style.display = "flex"
    tabBar.style.gap = "8px"
    tabBar.style.flexWrap = "wrap"
    return tabBar
  }

  function styleTab(btn, active) {
    btn.style.padding = "8px 12px"
    btn.style.borderRadius = "999px"
    btn.style.background = "var(--panel)"
    btn.style.border = "1px solid var(--border)"
    btn.style.cursor = "pointer"
    btn.style.color = active ? "var(--text)" : "var(--muted)"
    btn.style.borderColor = active ? "rgba(125, 211, 252, 0.45)" : "var(--border)"
    btn.style.background = active ? "rgba(125, 211, 252, 0.10)" : "var(--panel)"
  }

  function envPanel(state) {
    const wrap = document.createElement("div")
    wrap.style.display = "none"
    const c = document.createElement("div")
    c.className = "card"
    const head = document.createElement("div")
    head.className = "cardHead"
    const hTitle = document.createElement("div")
    hTitle.className = "cardTitle"
    hTitle.textContent = ".env"
    const hint = document.createElement("span")
    hint.className = "hint"
    head.appendChild(hTitle)
    head.appendChild(hint)

    const body = document.createElement("div")
    body.className = "cardBody"

    const rowNew = document.createElement("div")
    rowNew.className = "row"
    const kInp = document.createElement("input")
    kInp.placeholder = "新增 KEY"
    const vInp = document.createElement("input")
    vInp.placeholder = "VALUE"
    const addBtn = document.createElement("button")
    addBtn.className = "primary"
    addBtn.textContent = "新增"
    rowNew.appendChild(kInp)
    rowNew.appendChild(vInp)
    rowNew.appendChild(addBtn)

    const table = document.createElement("table")
    const thead = document.createElement("thead")
    const trh = document.createElement("tr")
    const th1 = document.createElement("th")
    th1.style.width = "30%"
    th1.textContent = "Key"
    const th2 = document.createElement("th")
    th2.textContent = "值"
    const th3 = document.createElement("th")
    th3.style.width = "60px"
    trh.appendChild(th1)
    trh.appendChild(th2)
    trh.appendChild(th3)
    thead.appendChild(trh)
    table.appendChild(thead)
    const tbody = document.createElement("tbody")
    table.appendChild(tbody)

    const rowSave = document.createElement("div")
    rowSave.className = "row"
    rowSave.style.marginTop = "10px"
    const saveBtn = document.createElement("button")
    saveBtn.className = "primary"
    saveBtn.textContent = "确认保存"
    const saveHint = document.createElement("span")
    saveHint.className = "hint"
    saveHint.textContent = "修改后点击确认保存才会生效"
    rowSave.appendChild(saveBtn)
    rowSave.appendChild(saveHint)

    body.appendChild(rowNew)
    body.appendChild(table)
    body.appendChild(rowSave)
    c.appendChild(head)
    c.appendChild(body)
    wrap.appendChild(c)

    async function refresh() {
      const env = await templateLoadEnv(state.runtime, state.templateId)
      hint.textContent = env.path ? `path: ${env.path}` : ""
      tbody.textContent = ""
      for (const it of env.items || []) {
        const tr = document.createElement("tr")
        tr.dataset.envKey = it.key
        const tdK = document.createElement("td")
        tdK.textContent = it.key
        const tdV = document.createElement("td")
        const inp = document.createElement("input")
        inp.value = it.value || ""
        inp.dataset.orig = it.value || ""
        tdV.appendChild(inp)
        const tdA = document.createElement("td")
        const del = document.createElement("button")
        del.className = "danger"
        del.textContent = "删除"
        del.addEventListener("click", async () => {
          if (!confirm(`确认删除 ${it.key} ?`)) return
          try {
            setToast("")
            await templateDeleteEnv(state.runtime, state.templateId, it.key)
            await refresh()
          } catch (e) {
            setToast(String(e))
          }
        })
        tdA.appendChild(del)
        tr.appendChild(tdK)
        tr.appendChild(tdV)
        tr.appendChild(tdA)
        tbody.appendChild(tr)
      }
    }

    addBtn.addEventListener("click", async () => {
      const key = (kInp.value || "").trim()
      if (!key) return setToast("KEY 不能为空")
      try {
        setToast("")
        await templatePutEnv(state.runtime, state.templateId, key, vInp.value || "")
        kInp.value = ""
        vInp.value = ""
        await refresh()
      } catch (e) {
        setToast(String(e))
      }
    })

    saveBtn.addEventListener("click", async () => {
      const items = []
      for (const tr of Array.from(tbody.querySelectorAll("tr"))) {
        const key = tr.dataset.envKey
        const inp = tr.querySelector("input")
        if (!key || !inp) continue
        const next = inp.value || ""
        const orig = inp.dataset.orig || ""
        if (next !== orig) items.push({ key, value: next })
      }
      if (items.length === 0) return setToast("没有需要保存的修改")
      if (!confirm(`确认保存 ${items.length} 项 env 变更？`)) return
      try {
        setToast("")
        await templateBatchPutEnv(state.runtime, state.templateId, items)
        await refresh()
      } catch (e) {
        setToast(String(e))
      }
    })

    return { el: wrap, refresh }
  }

  function skillsPanel(state) {
    const wrap = document.createElement("div")
    wrap.style.display = "none"
    const c = document.createElement("div")
    c.className = "card"
    const head = document.createElement("div")
    head.className = "cardHead"
    const hTitle = document.createElement("div")
    hTitle.className = "cardTitle"
    hTitle.textContent = "Skills"
    const hint = document.createElement("span")
    hint.className = "hint"
    hint.textContent = "按路径分组，修改后点确认保存生效"
    head.appendChild(hTitle)
    head.appendChild(hint)

    const body = document.createElement("div")
    body.className = "cardBody"
    const rowFilter = document.createElement("div")
    rowFilter.className = "row"
    const inp = document.createElement("input")
    inp.placeholder = "过滤 skills..."
    rowFilter.appendChild(inp)

    const list = document.createElement("div")

    const rowSave = document.createElement("div")
    rowSave.className = "row"
    rowSave.style.marginTop = "10px"
    const saveBtn = document.createElement("button")
    saveBtn.className = "primary"
    saveBtn.textContent = "确认保存"
    rowSave.appendChild(saveBtn)

    body.appendChild(rowFilter)
    body.appendChild(list)
    body.appendChild(rowSave)
    c.appendChild(head)
    c.appendChild(body)
    wrap.appendChild(c)

    function applyFilter() {
      const q = (inp.value || "").trim().toLowerCase()
      for (const block of Array.from(list.children)) {
        const tbl = block.querySelector("table")
        if (!tbl) continue
        let hasVisible = false
        for (const tr of Array.from(tbl.querySelectorAll("tr"))) {
          const name = (tr.dataset.skill || "").toLowerCase()
          const desc = (tr.dataset.skillDesc || "").toLowerCase()
          const match = !q || name.includes(q) || desc.includes(q)
          tr.style.display = match ? "" : "none"
          if (match) hasVisible = true
        }
        block.style.display = hasVisible ? "" : "none"
      }
    }

      function _renderRow(it, cbCls) {
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

      async function refresh() {
        const sk = await templateLoadSkills(state.runtime, state.templateId)
        list.textContent = ""
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
          const rows = []
          for (const it of items) {
            if (cat && it.name === cat && items.length > 1) continue
            rows.push(it)
          }
          if (rows.length === 0) continue
          if (rows.length === 1) { flatItems.push(rows[0]); continue }
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
            for (const cb of Array.from(block.querySelectorAll(".tmplSkillCb"))) cb.checked = selAll.checked
          })
          header.appendChild(arrow)
          header.appendChild(selAll)
          header.appendChild(label)
          block.appendChild(header)
          const tbl = document.createElement("table")
          const tbdy = document.createElement("tbody")
          for (const it of rows) tbdy.appendChild(_renderRow(it, "tmplSkillCb"))
          tbl.appendChild(tbdy)
          block.appendChild(tbl)
          const ckbs = Array.from(tbdy.querySelectorAll(".tmplSkillCb"))
          selAll.checked = ckbs.length > 0 && ckbs.some(cb => cb.checked)
          header.addEventListener("click", (ev) => {
            if (ev.target === selAll) return
            const isOpen = tbl.style.display !== "none"
            tbl.style.display = isOpen ? "none" : ""
            arrow.textContent = isOpen ? "\u25b6" : "\u25bc"
          })
          list.appendChild(block)
        }
        // 平铺 skill 直出
        if (flatItems.length > 0) {
          const block = document.createElement("div")
          block.style.marginTop = "10px"
          const tbl = document.createElement("table")
          const tbdy = document.createElement("tbody")
          for (const it of flatItems) tbdy.appendChild(_renderRow(it, "tmplSkillCb"))
          tbl.appendChild(tbdy)
          block.appendChild(tbl)
          list.appendChild(block)
        }
        applyFilter()
      }

    inp.addEventListener("input", applyFilter)

    saveBtn.addEventListener("click", async () => {
      const items = {}
      for (const cb of Array.from(wrap.querySelectorAll(".tmplSkillCb"))) {
        const name = cb.dataset.skillName
        if (!name) continue
        items[name] = cb.checked
      }
      if (!confirm(`确认保存 ${Object.keys(items).length} 个 skill 的启用状态？`)) return
      try {
        setToast("")
        await templateSaveSkills(state.runtime, state.templateId, items)
        await refresh()
      } catch (e) {
        setToast(String(e))
      }
    })

    return { el: wrap, refresh }
  }

  function channelsPanel(state) {
    const wrap = document.createElement("div")
    wrap.style.display = "none"
    const c = document.createElement("div")
    c.className = "card"
    const head = document.createElement("div")
    head.className = "cardHead"
    const hTitle = document.createElement("div")
    hTitle.className = "cardTitle"
    hTitle.textContent = "Channels"
    const hint = document.createElement("span")
    hint.className = "hint"
    head.appendChild(hTitle)
    head.appendChild(hint)

    const body = document.createElement("div")
    body.className = "cardBody"
    const content = document.createElement("div")
    body.appendChild(content)
    c.appendChild(head)
    c.appendChild(body)
    wrap.appendChild(c)

    async function refresh() {
      const ch = await templateChannelsGet(state.runtime, state.templateId)
      hint.textContent = ch.path ? `path: ${ch.path}` : ""
      content.textContent = ""

      if (ch && typeof ch === "object" && "config" in ch) {
        const cfg = ch.config && typeof ch.config === "object" ? ch.config : {}
        const channels = cfg.channels && typeof cfg.channels === "object" ? cfg.channels : {}
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
        content.appendChild(table)

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
            await templateChannelsPut(state.runtime, state.templateId, next)
            await refresh()
          } catch (e) {
            setToast(String(e))
          }
        })
        row.appendChild(btn)
        content.appendChild(row)
        return
      }

      if (ch && typeof ch === "object" && "platforms" in ch) {
        const ta = document.createElement("textarea")
        ta.spellcheck = false
        ta.style.minHeight = "360px"
        ta.value = JSON.stringify({ updated_at: ch.updated_at || null, platforms: ch.platforms || {} }, null, 2)
        content.appendChild(ta)

        const row = document.createElement("div")
        row.className = "row"
        row.style.justifyContent = "flex-end"
        row.style.marginTop = "10px"
        const btn = document.createElement("button")
        btn.className = "primary"
        btn.textContent = "保存"
        btn.addEventListener("click", async () => {
          let parsed = null
          try {
            parsed = ta.value ? JSON.parse(ta.value) : {}
          } catch (e) {
            setToast(String(e))
            return
          }
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            setToast("channels 必须为 JSON object")
            return
          }
          try {
            setToast("")
            await templateChannelsPut(state.runtime, state.templateId, parsed)
            await refresh()
          } catch (e) {
            setToast(String(e))
          }
        })
        row.appendChild(btn)
        content.appendChild(row)
        return
      }
    }

    return { el: wrap, refresh }
  }

  function configPanel(state) {
    const wrap = document.createElement("div")
    wrap.style.display = "none"
    const c = document.createElement("div")
    c.className = "card"
    const head = document.createElement("div")
    head.className = "cardHead"
    const hTitle = document.createElement("div")
    hTitle.className = "cardTitle"
    hTitle.textContent = "config.yaml (raw)"
    const hint = document.createElement("span")
    hint.className = "hint"
    head.appendChild(hTitle)
    head.appendChild(hint)

    const body = document.createElement("div")
    body.className = "cardBody"
    const row = document.createElement("div")
    row.className = "row"
    const saveBtn = document.createElement("button")
    saveBtn.className = "primary"
    saveBtn.textContent = "保存"
    row.appendChild(saveBtn)
    const ta = document.createElement("textarea")
    ta.spellcheck = false
    ta.style.minHeight = "360px"
    body.appendChild(row)
    body.appendChild(ta)
    c.appendChild(head)
    c.appendChild(body)
    wrap.appendChild(c)

    async function refresh() {
      const cfg = await templateConfigGet(state.runtime, state.templateId)
      hint.textContent = cfg.path ? `path: ${cfg.path}` : ""
      ta.value = cfg.raw || ""
    }

    saveBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await templateConfigPut(state.runtime, state.templateId, ta.value || "")
        setToast("已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

    return { el: wrap, refresh }
  }

  function parseInitial() {
    const qp = new URLSearchParams(window.location.search)
    const runtime = (qp.get("runtime") || "hermes").trim().toLowerCase() || "hermes"
    const templateId = (qp.get("template_id") || "root").trim() || "root"
    return { runtime, templateId }
  }

  function render() {
    const root = document.getElementById("pageTemplatesRoot")
    if (!root) return
    root.textContent = ""

    const state = { ...parseInitial(), allowedTabs: [], activeTab: "env", path: "" }

    const topRow = document.createElement("div")
    topRow.className = "row"

    const runtimeSel = document.createElement("select")
    runtimeSel.style.minWidth = "180px"
    for (const rt of [
      { v: "hermes", t: "Hermes" },
      { v: "nanoghost", t: "NanoGhost" },
      { v: "openclaw", t: "OpenClaw" },
    ]) {
      const opt = document.createElement("option")
      opt.value = rt.v
      opt.textContent = rt.t
      runtimeSel.appendChild(opt)
    }
    runtimeSel.value = ["hermes", "nanoghost", "openclaw"].includes(state.runtime) ? state.runtime : "hermes"
    state.runtime = runtimeSel.value

    const tplSel = document.createElement("select")
    tplSel.style.minWidth = "220px"

    const pathHint = document.createElement("span")
    pathHint.className = "hint"
    pathHint.style.whiteSpace = "nowrap"
    pathHint.style.overflow = "hidden"
    pathHint.style.textOverflow = "ellipsis"
    pathHint.style.maxWidth = "520px"

    const refreshBtn = document.createElement("button")
    refreshBtn.className = "primary"
    refreshBtn.textContent = "刷新"

    topRow.appendChild(runtimeSel)
    topRow.appendChild(tplSel)
    topRow.appendChild(refreshBtn)
    topRow.appendChild(pathHint)

    const tabBar = createTabBar()
    const panels = document.createElement("div")
    const toast = document.createElement("div")
    toast.id = "toast"

    const tabBtns = {}
    const tabPanels = {}

    function setActiveTab(key) {
      state.activeTab = key
      for (const [k, b] of Object.entries(tabBtns)) styleTab(b, k === key)
      for (const [k, p] of Object.entries(tabPanels)) p.style.display = k === key ? "" : "none"
    }

    const env = envPanel(state)
    const skills = skillsPanel(state)
    const channels = channelsPanel(state)
    const config = configPanel(state)
    tabPanels.env = env.el
    tabPanels.skills = skills.el
    tabPanels.channels = channels.el
    tabPanels.config = config.el
    for (const p of Object.values(tabPanels)) {
      p.style.marginTop = "12px"
      panels.appendChild(p)
    }

    async function refreshActiveTab() {
      if (state.activeTab === "env") return env.refresh()
      if (state.activeTab === "skills") return skills.refresh()
      if (state.activeTab === "channels") return channels.refresh()
      if (state.activeTab === "config") return config.refresh()
    }

    async function refreshManifest() {
      const mf = await templateManifest(state.runtime, state.templateId)
      state.allowedTabs = mf.tabs || []
      state.path = mf.instance?.path || ""
      pathHint.textContent = state.path ? `path: ${state.path}` : ""
      const supported = new Set(["env", "skills", "channels", "config"])
      tabBar.textContent = ""
      for (const k of Object.keys(tabBtns)) delete tabBtns[k]

      const nextTabs = (state.allowedTabs || []).filter((t) => supported.has(t))
      for (const t of nextTabs) {
        const b = document.createElement("button")
        b.textContent = t === "env" ? "Env" : t === "skills" ? "Skills" : t === "channels" ? "Channels" : "Config"
        tabBtns[t] = b
        styleTab(b, false)
        b.addEventListener("click", async () => {
          try {
            setActiveTab(t)
            setToast("")
            await refreshActiveTab()
          } catch (e) {
            setToast(String(e))
          }
        })
        tabBar.appendChild(b)
      }

      const first = nextTabs.includes("env") ? "env" : nextTabs[0] || "env"
      setActiveTab(nextTabs.includes(state.activeTab) ? state.activeTab : first)
    }

    async function refreshTemplateList() {
      tplSel.textContent = ""
      let data = null
      try {
        data = await templatesList(state.runtime)
      } catch {
        data = null
      }
      const items = (data && data.items ? data.items : []).filter(Boolean)
      const rootOpt = document.createElement("option")
      rootOpt.value = "root"
      rootOpt.textContent = "root"
      tplSel.appendChild(rootOpt)
      for (const it of items) {
        if (!it || it.id === "root") continue
        const opt = document.createElement("option")
        opt.value = it.id
        opt.textContent = it.name || it.id
        tplSel.appendChild(opt)
      }
      const ids = ["root", ...items.map((x) => x.id).filter((x) => x && x !== "root")]
      tplSel.value = ids.includes(state.templateId) ? state.templateId : "root"
      state.templateId = tplSel.value
    }

    function syncQuery() {
      const url = new URL(window.location.href)
      url.searchParams.set("runtime", state.runtime)
      url.searchParams.set("template_id", state.templateId)
      history.replaceState(null, "", url.toString())
    }

    runtimeSel.addEventListener("change", async () => {
      state.runtime = (runtimeSel.value || "hermes").toLowerCase()
      try {
        setToast("")
        await refreshTemplateList()
        await refreshManifest()
        await refreshActiveTab()
        syncQuery()
      } catch (e) {
        setToast(String(e))
      }
    })

    tplSel.addEventListener("change", async (e) => {
      e.stopPropagation()
      state.templateId = (tplSel.value || "root").trim() || "root"
      try {
        setToast("")
        await refreshManifest()
        await refreshActiveTab()
        syncQuery()
      } catch (err) {
        setToast(String(err))
      }
    })

    refreshBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await refreshTemplateList()
        await refreshManifest()
        await refreshActiveTab()
      } catch (e) {
        setToast(String(e))
      }
    })

    root.appendChild(topRow)
    root.appendChild(tabBar)
    root.appendChild(panels)
    root.appendChild(toast)

    ;(async () => {
      try {
        setToast("")
        await refreshTemplateList()
        await refreshManifest()
        await refreshActiveTab()
        syncQuery()
      } catch (e) {
        setToast(String(e))
      }
    })()
  }

  window.addEventListener("DOMContentLoaded", render)
})();

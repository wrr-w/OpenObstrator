function openCreateModal() {
  return new Promise((resolve) => {
    const overlay = document.createElement("div")
    overlay.style.position = "fixed"
    overlay.style.inset = "0"
    overlay.style.background = "rgba(0,0,0,0.35)"
    overlay.style.display = "flex"
    overlay.style.alignItems = "center"
    overlay.style.justifyContent = "center"
    overlay.style.zIndex = "9999"

    const card = document.createElement("div")
    card.style.width = "460px"
    card.style.maxWidth = "92vw"
    card.style.border = "1px solid var(--border)"
    card.style.background = "var(--bg)"
    card.style.borderRadius = "16px"
    card.style.boxShadow = "var(--shadow)"
    card.style.padding = "14px"

    const title = document.createElement("div")
    title.style.fontWeight = "750"
    title.style.marginBottom = "10px"
    title.textContent = "新增实例"

    const row1 = document.createElement("div")
    row1.className = "row"
    const sel = document.createElement("select")
    sel.style.minWidth = "180px"
    for (const rt of [
      { v: "hermes", t: "Hermes" },
      { v: "nanoghost", t: "NanoGhost" },
      { v: "openclaw", t: "OpenClaw" },
    ]) {
      const opt = document.createElement("option")
      opt.value = rt.v
      opt.textContent = rt.t
      sel.appendChild(opt)
    }

    const inp = document.createElement("input")
    inp.placeholder = "实例名称（小写字母/数字/_/-，<=64）"
    inp.style.flex = "1"

    row1.appendChild(sel)
    row1.appendChild(inp)

    const rowTpl = document.createElement("div")
    rowTpl.className = "row"
    const tplSel = document.createElement("select")
    tplSel.style.minWidth = "180px"
    const tplLabel = document.createElement("span")
    tplLabel.className = "hint"
    tplLabel.textContent = "模板"
    tplLabel.style.minWidth = "44px"
    rowTpl.appendChild(tplLabel)
    rowTpl.appendChild(tplSel)

    const row2 = document.createElement("div")
    row2.className = "row"
    row2.style.justifyContent = "flex-end"

    const cancel = document.createElement("button")
    cancel.textContent = "取消"

    const ok = document.createElement("button")
    ok.textContent = "创建"
    ok.className = "primary"

    function close(v) {
      overlay.remove()
      resolve(v)
    }

    cancel.addEventListener("click", () => close(null))
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close(null)
    })
    ok.addEventListener("click", () => {
      const runtime = sel.value
      const name = (inp.value || "").trim()
      const template_id = tplSel.value || "root"
      close({ runtime, name, template_id })
    })
    inp.addEventListener("keydown", (e) => {
      if (e.key === "Enter") ok.click()
      if (e.key === "Escape") cancel.click()
    })

    async function refreshTemplates() {
      const runtime = sel.value
      tplSel.textContent = ""
      try {
        const data = await templatesList(runtime)
        const items = data.items || []
        const rootOpt = document.createElement("option")
        rootOpt.value = "root"
        rootOpt.textContent = "默认(root)"
        tplSel.appendChild(rootOpt)
        for (const it of items) {
          if (!it || it.id === "root") continue
          const opt = document.createElement("option")
          opt.value = it.id
          opt.textContent = it.name || it.id
          tplSel.appendChild(opt)
        }
        tplSel.value = "root"
      } catch (e) {
        const rootOpt = document.createElement("option")
        rootOpt.value = "root"
        rootOpt.textContent = "默认(root)"
        tplSel.appendChild(rootOpt)
        tplSel.value = "root"
      }
    }

    sel.addEventListener("change", () => { refreshTemplates() })

    row2.appendChild(cancel)
    row2.appendChild(ok)

    card.appendChild(title)
    card.appendChild(row1)
    card.appendChild(rowTpl)
    card.appendChild(row2)
    overlay.appendChild(card)
    document.body.appendChild(overlay)
    inp.focus()
    refreshTemplates()
  })
}

function openManagerConfigModal(initialRaw) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div")
    overlay.style.position = "fixed"
    overlay.style.inset = "0"
    overlay.style.background = "rgba(0,0,0,0.35)"
    overlay.style.display = "flex"
    overlay.style.alignItems = "center"
    overlay.style.justifyContent = "center"
    overlay.style.zIndex = "9999"

    const card = document.createElement("div")
    card.style.width = "820px"
    card.style.maxWidth = "94vw"
    card.style.border = "1px solid var(--border)"
    card.style.background = "var(--bg)"
    card.style.borderRadius = "16px"
    card.style.boxShadow = "var(--shadow)"
    card.style.padding = "14px"

    const title = document.createElement("div")
    title.style.fontWeight = "750"
    title.style.marginBottom = "10px"
    title.textContent = "管理台配置（data/config.yaml）"

    const ta = document.createElement("textarea")
    ta.value = initialRaw || ""
    ta.spellcheck = false
    ta.style.minHeight = "420px"

    const row = document.createElement("div")
    row.className = "row"
    row.style.justifyContent = "flex-end"
    row.style.marginTop = "10px"

    const cancel = document.createElement("button")
    cancel.textContent = "取消"
    const ok = document.createElement("button")
    ok.textContent = "保存"
    ok.className = "primary"

    function close(v) {
      overlay.remove()
      resolve(v)
    }

    cancel.addEventListener("click", () => close(null))
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close(null)
    })
    ok.addEventListener("click", () => close({ raw: ta.value }))
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Escape") cancel.click()
    })

    row.appendChild(cancel)
    row.appendChild(ok)

    card.appendChild(title)
    card.appendChild(ta)
    card.appendChild(row)
    overlay.appendChild(card)
    document.body.appendChild(overlay)
    ta.focus()
  })
}

function openRawEditorModal(titleText, initialRaw) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div")
    overlay.style.position = "fixed"
    overlay.style.inset = "0"
    overlay.style.background = "rgba(0,0,0,0.35)"
    overlay.style.display = "flex"
    overlay.style.alignItems = "center"
    overlay.style.justifyContent = "center"
    overlay.style.zIndex = "9999"

    const card = document.createElement("div")
    card.style.width = "880px"
    card.style.maxWidth = "94vw"
    card.style.border = "1px solid var(--border)"
    card.style.background = "var(--bg)"
    card.style.borderRadius = "16px"
    card.style.boxShadow = "var(--shadow)"
    card.style.padding = "14px"

    const title = document.createElement("div")
    title.style.fontWeight = "750"
    title.style.marginBottom = "10px"
    title.textContent = titleText || "Raw Editor"

    const ta = document.createElement("textarea")
    ta.value = initialRaw || ""
    ta.spellcheck = false
    ta.style.minHeight = "520px"

    const row = document.createElement("div")
    row.className = "row"
    row.style.justifyContent = "flex-end"
    row.style.marginTop = "10px"

    const cancel = document.createElement("button")
    cancel.textContent = "取消"
    const ok = document.createElement("button")
    ok.textContent = "保存"
    ok.className = "primary"

    function close(v) {
      overlay.remove()
      resolve(v)
    }

    cancel.addEventListener("click", () => close(null))
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close(null)
    })
    ok.addEventListener("click", () => close({ raw: ta.value }))
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Escape") cancel.click()
    })

    row.appendChild(cancel)
    row.appendChild(ok)

    card.appendChild(title)
    card.appendChild(ta)
    card.appendChild(row)
    overlay.appendChild(card)
    document.body.appendChild(overlay)
    ta.focus()
  })
}

function openTemplateMgrModal(initialRuntime, initialTemplateId) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div")
    overlay.style.position = "fixed"
    overlay.style.inset = "0"
    overlay.style.background = "rgba(0,0,0,0.35)"
    overlay.style.display = "flex"
    overlay.style.alignItems = "center"
    overlay.style.justifyContent = "center"
    overlay.style.zIndex = "9999"

    const card = document.createElement("div")
    card.style.width = "980px"
    card.style.maxWidth = "96vw"
    card.style.maxHeight = "92vh"
    card.style.overflow = "auto"
    card.style.border = "1px solid var(--border)"
    card.style.background = "var(--bg)"
    card.style.borderRadius = "16px"
    card.style.boxShadow = "var(--shadow)"
    card.style.padding = "14px"

    const state = {
      runtime: (initialRuntime || "hermes").toLowerCase(),
      templateId: (initialTemplateId || "root").trim() || "root",
      allowedTabs: [],
      activeTab: "env",
      path: "",
    }

    const title = document.createElement("div")
    title.style.fontWeight = "750"
    title.style.marginBottom = "10px"
    title.textContent = "模板管理"

    const topRow = document.createElement("div")
    topRow.className = "row"
    const sel = document.createElement("select")
    sel.style.minWidth = "180px"
    for (const rt of [
      { v: "hermes", t: "Hermes" },
      { v: "nanoghost", t: "NanoGhost" },
      { v: "openclaw", t: "OpenClaw" },
    ]) {
      const opt = document.createElement("option")
      opt.value = rt.v
      opt.textContent = rt.t
      sel.appendChild(opt)
    }
    sel.value = state.runtime

    const tplSel = document.createElement("select")
    tplSel.style.minWidth = "220px"

    const pathHint = document.createElement("span")
    pathHint.className = "hint"
    pathHint.style.whiteSpace = "nowrap"
    pathHint.style.overflow = "hidden"
    pathHint.style.textOverflow = "ellipsis"
    pathHint.style.maxWidth = "600px"
    topRow.appendChild(sel)
    topRow.appendChild(tplSel)
    topRow.appendChild(pathHint)

    const tabBar = document.createElement("div")
    tabBar.style.marginTop = "14px"
    tabBar.style.display = "flex"
    tabBar.style.gap = "8px"
    tabBar.style.flexWrap = "wrap"

    const panels = document.createElement("div")

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

    const tabBtns = {}
    const tabPanels = {}

    function setActiveTab(key) {
      state.activeTab = key
      for (const [k, b] of Object.entries(tabBtns)) styleTab(b, k === key)
      for (const [k, p] of Object.entries(tabPanels)) p.style.display = k === key ? "" : "none"
    }

    function onKeyDown(e) {
      if (e.key === "Escape") close(null)
    }

    function close(v) {
      document.removeEventListener("keydown", onKeyDown)
      overlay.remove()
      resolve(v)
    }

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close(null)
    })

    document.addEventListener("keydown", onKeyDown)

    function envPanel() {
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
        const value = vInp.value || ""
        if (!key) {
          setToast("env key 不能为空")
          return
        }
        try {
          setToast("")
          await templatePutEnv(state.runtime, state.templateId, key, value)
          kInp.value = ""
          vInp.value = ""
          await refresh()
        } catch (e) {
          setToast(String(e))
        }
      })

      saveBtn.addEventListener("click", async () => {
        const items = {}
        for (const tr of Array.from(tbody.querySelectorAll("tr"))) {
          const key = tr.dataset.envKey
          const inp = tr.querySelector("input")
          if (!key || !inp) continue
          const newVal = inp.value
          if (newVal !== inp.dataset.orig) items[key] = newVal
        }
        if (Object.keys(items).length === 0) {
          setToast("没有修改")
          return
        }
        if (!confirm(`确认保存 ${Object.keys(items).length} 个环境变量的修改？`)) return
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

    function skillsPanel() {
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

      async function refresh() {
        const sk = await templateLoadSkills(state.runtime, state.templateId)
        list.textContent = ""
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
            for (const cb of Array.from(block.querySelectorAll(".tmplSkillCb"))) cb.checked = selAll.checked
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
            cb.className = "tmplSkillCb"
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

    function channelsPanel() {
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

    function configPanel() {
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
        } catch (e) {
          setToast(String(e))
        }
      })

      return { el: wrap, refresh }
    }

    const env = envPanel()
    const skills = skillsPanel()
    const channels = channelsPanel()
    const config = configPanel()
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

    sel.addEventListener("change", async () => {
      state.runtime = (sel.value || "hermes").toLowerCase()
      try {
        setToast("")
        await refreshTemplateList()
        await refreshManifest()
        await refreshActiveTab()
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
      } catch (err) {
        setToast(String(err))
      }
    })

    const footer = document.createElement("div")
    footer.className = "row"
    footer.style.justifyContent = "flex-end"
    footer.style.marginTop = "12px"
    const closeBtn = document.createElement("button")
    closeBtn.textContent = "关闭"
    closeBtn.addEventListener("click", () => close(null))
    footer.appendChild(closeBtn)

    card.appendChild(title)
    card.appendChild(topRow)
    card.appendChild(tabBar)
    card.appendChild(panels)
    card.appendChild(footer)
    overlay.appendChild(card)
    document.body.appendChild(overlay)

    ;(async () => {
      try {
        setToast("")
        await refreshTemplateList()
        await refreshManifest()
        await refreshActiveTab()
      } catch (e) {
        setToast(String(e))
      }
    })()
  })
}


function openMemoryCardModal(card, name) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div")
    overlay.style.position = "fixed"
    overlay.style.inset = "0"
    overlay.style.background = "rgba(0,0,0,0.35)"
    overlay.style.display = "flex"
    overlay.style.alignItems = "center"
    overlay.style.justifyContent = "center"
    overlay.style.zIndex = "9999"

    const cardEl = document.createElement("div")
    cardEl.style.cssText = "width:680px;max-width:94vw;max-height:90vh;overflow-y:auto;border:1px solid var(--border);background:var(--bg);border-radius:16px;box-shadow:var(--shadow);padding:16px"

    // Title
    const title = document.createElement("div")
    title.style.cssText = "font-weight:700;font-size:14px;margin-bottom:4px;color:var(--brand)"
    title.textContent = "记忆卡片"
    cardEl.appendChild(title)

    // Card ID hint
    const idHint = document.createElement("div")
    idHint.style.cssText = "font-size:10px;color:var(--muted);margin-bottom:12px"
    let hints = "ID: " + (card.id || "-")
    if (card.flow_hash) hints += " | flow: " + card.flow_hash
    if (card.l1_code != null) hints += " | L1: " + card.l1_code
    if (card.success_count != null) hints += " | 成功: " + card.success_count
    idHint.textContent = hints
    cardEl.appendChild(idHint)

    // intent_summary (readonly)
    const intentLabel = document.createElement("div")
    intentLabel.style.cssText = "font-weight:700;font-size:11px;color:var(--text);margin-bottom:3px"
    intentLabel.textContent = "意图"
    cardEl.appendChild(intentLabel)
    const intentVal = document.createElement("div")
    intentVal.textContent = card.user_input || ""
    intentVal.style.cssText = "font-size:12px;color:var(--text);padding:6px 8px;background:var(--panel);border-radius:8px;margin-bottom:12px;line-height:1.5;word-break:break-all"
    cardEl.appendChild(intentVal)

    // Steps (operation sequence)
    const stepsLabel = document.createElement("div")
    stepsLabel.style.cssText = "font-weight:700;font-size:11px;color:var(--text);margin-bottom:3px"
    stepsLabel.textContent = "操作序列"
    cardEl.appendChild(stepsLabel)
    
    const stepsContainer = document.createElement("div")
    stepsContainer.style.cssText = "max-height:300px;overflow-y:auto;background:var(--panel);border-radius:8px;padding:6px 8px;margin-bottom:12px;font-family:monospace;font-size:11px;line-height:1.6"
    
    let stepsRaw = card.steps_json_raw || "[]"
    let steps = []
    try { steps = JSON.parse(stepsRaw) } catch {}
    
    if (steps.length === 0) {
      const empty = document.createElement("div")
      empty.style.cssText = "color:var(--muted);font-size:11px"
      empty.textContent = "(无步骤记录)"
      stepsContainer.appendChild(empty)
    } else {
      for (let i = 0; i < steps.length; i++) {
        const s = steps[i]
        if (typeof s !== "object") {
          const line = document.createElement("div")
          line.textContent = "[" + (i+1) + "] " + String(s).slice(0, 120)
          line.style.cssText = "padding:2px 0"
          stepsContainer.appendChild(line)
          continue
        }
        const stepNum = s.step || (i+1)
        const method = s.method || "?"
        const path = (s.path || s.command || "").slice(0, 150)
        const ok = s.ok === true ? "\u2705" : s.ok === false ? "\u274c" : ""
        const line = document.createElement("div")
        line.style.cssText = "padding:3px 0;border-bottom:1px solid var(--border);display:flex;gap:6px;align-items:flex-start"
        const numEl = document.createElement("span")
        numEl.textContent = "#" + stepNum
        numEl.style.cssText = "color:var(--brand);min-width:28px;flex-shrink:0"
        const methodEl = document.createElement("span")
        methodEl.textContent = method
        methodEl.style.cssText = "color:#facc15;min-width:36px;flex-shrink:0;font-weight:600"
        const pathEl = document.createElement("span")
        pathEl.textContent = path + " " + ok
        pathEl.style.cssText = "color:var(--text);word-break:break-all"
        line.appendChild(numEl)
        line.appendChild(methodEl)
        line.appendChild(pathEl)
        stepsContainer.appendChild(line)
      }
    }
    cardEl.appendChild(stepsContainer)

    // experience_notes
    const expLabel = document.createElement("div")
    expLabel.style.cssText = "font-weight:700;font-size:11px;color:var(--muted);margin-bottom:3px"
    expLabel.textContent = "经验总结（experience）"
    cardEl.appendChild(expLabel)
    const expTa = document.createElement("textarea")
    expTa.style.cssText = "width:100%;min-height:50px;max-height:120px;font-family:monospace;font-size:12px;padding:6px 8px;border-radius:8px;border:1px solid var(--border);background:var(--panel);color:var(--text);resize:vertical;margin-bottom:12px"
    let expVal = card.experience_notes || ""
    try { const ej = JSON.parse(expVal); expVal = Array.isArray(ej) ? ej.join("\n") : expVal } catch {}
    expTa.value = expVal
    cardEl.appendChild(expTa)

    // Buttons row
    const row = document.createElement("div")
    row.style.cssText = "display:flex;gap:10px;justify-content:space-between;align-items:center"

    const leftGroup = document.createElement("div")
    leftGroup.style.cssText = "display:flex;gap:10px"

    const deleteBtn = document.createElement("button")
    deleteBtn.className = "danger"
    deleteBtn.textContent = "删除"
    deleteBtn.addEventListener("click", async () => {
      if (!confirm("确认删除此卡片？\n(" + (card.user_input || "").slice(0, 40) + ")")) return
      try {
        await deleteNgMemoryCard(name, card.id)
        setToast("卡片已删除 \u2705")
        close("deleted")
      } catch (e) {
        setToast("删除失败: " + String(e))
      }
    })
    leftGroup.appendChild(deleteBtn)

    const rightGroup = document.createElement("div")
    rightGroup.style.cssText = "display:flex;gap:10px"

    const cancelBtn = document.createElement("button")
    cancelBtn.textContent = "取消"
    cancelBtn.addEventListener("click", () => close(false))

    const saveBtn = document.createElement("button")
    saveBtn.className = "primary"
    saveBtn.textContent = "保存"
    saveBtn.addEventListener("click", async () => {
      const expLines = expTa.value.split("\n").map(s => s.trim()).filter(Boolean)
      const toSave = {
        pitfalls: "[]",
        experience_notes: expLines.length ? JSON.stringify(expLines) : "[]",
      }
      try {
        await updateNgMemoryCard(name, card.id, toSave.pitfalls, toSave.experience_notes)
        setToast("卡片已保存 \u2705")
        close(true)
      } catch (e) {
        setToast("保存失败: " + String(e))
      }
    })

    rightGroup.appendChild(cancelBtn)
    rightGroup.appendChild(saveBtn)
    row.appendChild(leftGroup)
    row.appendChild(rightGroup)
    cardEl.appendChild(row)

    overlay.appendChild(cardEl)
    document.body.appendChild(overlay)

    function close(v) {
      overlay.remove()
      resolve(v)
    }

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close(false)
    })
    document.addEventListener("keydown", function _key(e) {
      if (e.key === "Escape") { close(false); document.removeEventListener("keydown", _key) }
    })
  })
}

function openNgMemoryEditModal(name, onSaved) {
  // Load raw content first
  loadNgMemoryRaw(name).then(r => {
    const raw = r.raw || ""
    
    const overlay = document.createElement("div")
    overlay.style.position = "fixed"
    overlay.style.inset = "0"
    overlay.style.background = "rgba(0,0,0,0.35)"
    overlay.style.display = "flex"
    overlay.style.alignItems = "center"
    overlay.style.justifyContent = "center"
    overlay.style.zIndex = "9999"

    const cardEl = document.createElement("div")
    cardEl.style.cssText = "width:680px;max-width:94vw;max-height:90vh;display:flex;flex-direction:column;border:1px solid var(--border);background:var(--bg);border-radius:16px;box-shadow:var(--shadow);padding:16px"

    // Title
    const title = document.createElement("div")
    title.style.cssText = "font-weight:700;font-size:14px;margin-bottom:4px;color:var(--brand)"
    title.textContent = "编辑 memory.md"
    cardEl.appendChild(title)

    const hint = document.createElement("div")
    hint.style.cssText = "font-size:10px;color:var(--muted);margin-bottom:12px"
    hint.textContent = "格式：## section_name\n- item1\n- item2"
    cardEl.appendChild(hint)

    // Textarea
    const ta = document.createElement("textarea")
    ta.spellcheck = false
    ta.style.cssText = "flex:1;min-height:300px;font-family:monospace;font-size:12px;padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--panel);color:var(--text);resize:vertical"
    ta.value = raw
    cardEl.appendChild(ta)

    // Buttons
    const row = document.createElement("div")
    row.style.cssText = "display:flex;gap:10px;justify-content:flex-end;margin-top:12px"

    const cancelBtn = document.createElement("button")
    cancelBtn.textContent = "取消"
    cancelBtn.addEventListener("click", () => { overlay.remove() })

    const saveBtn = document.createElement("button")
    saveBtn.className = "primary"
    saveBtn.textContent = "保存"
    saveBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await saveNgMemoryRaw(name, ta.value)
        setToast("已保存")
        overlay.remove()
        if (onSaved) onSaved()
      } catch (e) {
        setToast("保存失败: " + String(e))
      }
    })

    row.appendChild(cancelBtn)
    row.appendChild(saveBtn)
    cardEl.appendChild(row)

    overlay.appendChild(cardEl)
    document.body.appendChild(overlay)

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.remove()
    })
    document.addEventListener("keydown", function _key(e) {
      if (e.key === "Escape") { overlay.remove(); document.removeEventListener("keydown", _key) }
    })
  }).catch(e => {
    setToast("加载 memory.md 失败: " + String(e))
  })
}

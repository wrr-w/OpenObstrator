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

  async function globalSkills(runtime) {
    return apiJson(`/api/global-registry/${encodeURIComponent(runtime)}/skills`, { method: "GET" })
  }

  async function globalMcpConfig(runtime) {
    return apiJson(`/api/global-registry/${encodeURIComponent(runtime)}/mcp/config`, { method: "GET" })
  }

  async function globalMcpConfigPut(runtime, raw) {
    return apiJson(`/api/global-registry/${encodeURIComponent(runtime)}/mcp/config`, { method: "PUT", body: JSON.stringify({ raw }) })
  }

  async function managerConfigGet() {
    return apiJson("/api/manager/config/raw", { method: "GET" })
  }

  async function managerConfigPut(raw) {
    return apiJson("/api/manager/config/raw", { method: "PUT", body: JSON.stringify({ raw }) })
  }

  function render() {
    const root = document.getElementById("pageGlobalRegistryRoot")
    if (!root) return
    root.textContent = ""

    const state = { runtime: "hermes" }

    const hint = document.createElement("div")
    hint.className = "hint"
    hint.textContent = "全局配置 — 管理台配置、MCP Servers、Skills 全集"

    const topRow = document.createElement("div")
    topRow.className = "row"
    topRow.style.marginBottom = "12px"

    const runtimeSel = document.createElement("select")
    runtimeSel.style.minWidth = "180px"
    for (const rt of [
      { v: "hermes", t: "Hermes" },
      { v: "nanoghost", t: "NanoGhost" },
    ]) {
      const opt = document.createElement("option")
      opt.value = rt.v
      opt.textContent = rt.t
      runtimeSel.appendChild(opt)
    }
    runtimeSel.addEventListener("change", () => {
      state.runtime = runtimeSel.value
      refreshAll()
    })
    topRow.appendChild(runtimeSel)

    const refreshBtn = document.createElement("button")
    refreshBtn.textContent = "刷新"
    refreshBtn.addEventListener("click", () => refreshAll())
    topRow.appendChild(refreshBtn)

    // 管理台配置部分
    const managerConfigTitle = document.createElement("div")
    managerConfigTitle.style.marginTop = "18px"
    managerConfigTitle.style.marginBottom = "8px"
    managerConfigTitle.style.fontWeight = "700"
    managerConfigTitle.style.fontSize = "14px"
    managerConfigTitle.textContent = "管理台配置"

    const managerConfigPath = document.createElement("div")
    managerConfigPath.className = "hint"
    managerConfigPath.style.marginBottom = "4px"

    const managerConfigRow = document.createElement("div")
    managerConfigRow.className = "row"
    managerConfigRow.style.justifyContent = "flex-end"
    managerConfigRow.style.marginBottom = "6px"

    const managerConfigLoadBtn = document.createElement("button")
    managerConfigLoadBtn.textContent = "读取"
    const managerConfigSaveBtn = document.createElement("button")
    managerConfigSaveBtn.className = "primary"
    managerConfigSaveBtn.textContent = "保存"

    managerConfigRow.appendChild(managerConfigLoadBtn)
    managerConfigRow.appendChild(managerConfigSaveBtn)

    const managerConfigTa = document.createElement("textarea")
    managerConfigTa.spellcheck = false
    managerConfigTa.style.minHeight = "200px"

    managerConfigLoadBtn.addEventListener("click", async () => {
      try {
        setToast("")
        const cfg = await managerConfigGet()
        managerConfigTa.value = cfg.raw || ""
        managerConfigPath.textContent = cfg.path ? `path: ${cfg.path}` : ""
        setToast("已读取")
      } catch (e) {
        setToast(String(e))
      }
    })

    managerConfigSaveBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await managerConfigPut(managerConfigTa.value || "")
        setToast("已保存（需要刷新页面或重启服务才会影响扫描目录等行为）")
      } catch (e) {
        setToast(String(e))
      }
    })

    const mcpsTitle = document.createElement("div")
    mcpsTitle.style.marginTop = "18px"
    mcpsTitle.style.marginBottom = "8px"
    mcpsTitle.style.fontWeight = "700"
    mcpsTitle.style.fontSize = "14px"
    mcpsTitle.textContent = "MCP Servers（全局）"

    const mcpsPath = document.createElement("div")
    mcpsPath.className = "hint"
    mcpsPath.style.marginBottom = "4px"

    const mcpsRow = document.createElement("div")
    mcpsRow.className = "row"
    mcpsRow.style.justifyContent = "flex-end"
    mcpsRow.style.marginBottom = "6px"

    const mcpsLoadBtn = document.createElement("button")
    mcpsLoadBtn.textContent = "读取"
    const mcpsSaveBtn = document.createElement("button")
    mcpsSaveBtn.className = "primary"
    mcpsSaveBtn.textContent = "保存"

    mcpsRow.appendChild(mcpsLoadBtn)
    mcpsRow.appendChild(mcpsSaveBtn)

    const mcpsTa = document.createElement("textarea")
    mcpsTa.spellcheck = false
    mcpsTa.style.minHeight = "240px"

    const mcpsSummary = document.createElement("table")
    mcpsSummary.style.marginTop = "10px"
    const mcpsThead = document.createElement("thead")
    const mcpsTrh = document.createElement("tr")
    for (const h of ["ID", "Transport", "Enabled", "URL", "Headers"]) {
      const th = document.createElement("th")
      th.textContent = h
      mcpsTrh.appendChild(th)
    }
    mcpsThead.appendChild(mcpsTrh)
    mcpsSummary.appendChild(mcpsThead)
    const mcpsTbody = document.createElement("tbody")
    mcpsSummary.appendChild(mcpsTbody)

    function renderMcpsSummary(servers) {
      mcpsTbody.textContent = ""
      for (const s of servers || []) {
        const tr = document.createElement("tr")
        const tdId = document.createElement("td")
        const tdT = document.createElement("td")
        const tdEn = document.createElement("td")
        const tdUrl = document.createElement("td")
        const tdHdrs = document.createElement("td")
        tdId.textContent = s.id || ""
        tdT.textContent = s.transport || ""
        tdEn.textContent = String(Boolean(s.enabled))
        tdUrl.textContent = s.url || ""
        tdUrl.style.fontSize = "12px"
        tdUrl.style.wordBreak = "break-all"
        if (s.headers && Object.keys(s.headers).length > 0) {
          tdHdrs.textContent = JSON.stringify(s.headers)
          tdHdrs.style.fontSize = "12px"
          tdHdrs.style.wordBreak = "break-all"
        }
        tr.appendChild(tdId)
        tr.appendChild(tdT)
        tr.appendChild(tdEn)
        tr.appendChild(tdUrl)
        tr.appendChild(tdHdrs)
        mcpsTbody.appendChild(tr)
      }
    }

    mcpsLoadBtn.addEventListener("click", async () => {
      try {
        setToast("")
        const cfg = await globalMcpConfig(state.runtime)
        mcpsTa.value = cfg.raw || ""
        mcpsPath.textContent = cfg.path ? `path: ${cfg.path}` : ""
        renderMcpsSummary(cfg.servers)
        setToast("已读取")
      } catch (e) {
        setToast(String(e))
      }
    })

    mcpsSaveBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await globalMcpConfigPut(state.runtime, mcpsTa.value || "")
        setToast("已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

    const skillsTitle = document.createElement("div")
    skillsTitle.style.marginTop = "24px"
    skillsTitle.style.marginBottom = "6px"
    skillsTitle.style.fontWeight = "700"
    skillsTitle.style.fontSize = "14px"

    const skillsPath = document.createElement("div")
    skillsPath.className = "hint"
    skillsPath.style.marginBottom = "6px"

    const skillsTable = document.createElement("table")
    const skillsThead = document.createElement("thead")
    const skillsTrh = document.createElement("tr")
    for (const h of ["Name", "Category", "Description", "Path"]) {
      const th = document.createElement("th")
      th.textContent = h
      skillsTrh.appendChild(th)
    }
    skillsThead.appendChild(skillsTrh)
    skillsTable.appendChild(skillsThead)
    const skillsTbody = document.createElement("tbody")
    skillsTable.appendChild(skillsTbody)

    function renderSkills(data) {
      skillsTbody.textContent = ""
      skillsPath.textContent = data.skills_dir ? `dir: ${data.skills_dir}` : ""
      skillsTitle.textContent = `Skills 全集（${data.count || 0}）`
      for (const it of data.items || []) {
        const tr = document.createElement("tr")
        const tdName = document.createElement("td")
        const tdCat = document.createElement("td")
        const tdDesc = document.createElement("td")
        const tdPath = document.createElement("td")
        const nc = document.createElement("code")
        nc.textContent = it.name || ""
        tdName.appendChild(nc)
        tdCat.textContent = it.category || ""
        tdCat.className = "hint"
        tdDesc.textContent = it.description || ""
        tdDesc.style.maxWidth = "320px"
        tdDesc.style.overflow = "hidden"
        tdDesc.style.textOverflow = "ellipsis"
        tdDesc.style.whiteSpace = "nowrap"
        tdPath.textContent = it.path || ""
        tdPath.style.fontSize = "12px"
        tdPath.style.wordBreak = "break-all"
        tr.appendChild(tdName)
        tr.appendChild(tdCat)
        tr.appendChild(tdDesc)
        tr.appendChild(tdPath)
        skillsTbody.appendChild(tr)
      }
    }

    async function refreshAll() {
      try {
        setToast("")
        const cfg = await globalMcpConfig(state.runtime)
        mcpsTa.value = cfg.raw || ""
        mcpsPath.textContent = cfg.path ? `path: ${cfg.path}` : ""
        renderMcpsSummary(cfg.servers)

        const skillsData = await globalSkills(state.runtime)
        renderSkills(skillsData)
      } catch (e) {
        setToast(String(e))
      }
    }

    const toast = document.createElement("div")
    toast.id = "toast"

    root.appendChild(hint)
    root.appendChild(topRow)
    root.appendChild(managerConfigTitle)
    root.appendChild(managerConfigPath)
    root.appendChild(managerConfigRow)
    root.appendChild(managerConfigTa)
    root.appendChild(mcpsTitle)
    root.appendChild(mcpsPath)
    root.appendChild(mcpsRow)
    root.appendChild(mcpsTa)
    root.appendChild(mcpsSummary)
    root.appendChild(skillsTitle)
    root.appendChild(skillsPath)
    root.appendChild(skillsTable)
    root.appendChild(toast)

    ;(async () => {
      try {
        setToast("")
        // 加载管理台配置
        const managerCfg = await managerConfigGet()
        managerConfigTa.value = managerCfg.raw || ""
        managerConfigPath.textContent = managerCfg.path ? `path: ${managerCfg.path}` : ""
        // 加载 MCP 和 Skills
        await refreshAll()
      } catch (e) {
        setToast(String(e))
      }
    })()
  }

  window.addEventListener("DOMContentLoaded", render)
})()

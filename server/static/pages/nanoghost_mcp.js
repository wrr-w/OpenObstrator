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

  async function ngMcpConfigGetRaw() {
    return apiJson("/api/nanoghost/mcp/config/raw", { method: "GET" })
  }

  async function ngMcpConfigPutRaw(raw) {
    return apiJson("/api/nanoghost/mcp/config/raw", { method: "PUT", body: JSON.stringify({ raw }) })
  }

  async function ngInstancesGet() {
    return apiJson("/api/runtimes/nanoghost/instances", { method: "GET" })
  }

  async function ngAllowlistGet(name) {
    return apiJson(`/api/nanoghost/mcp/instances/${encodeURIComponent(name)}/allowlist`, { method: "GET" })
  }

  async function ngAllowlistPut(name, enabledOnly) {
    return apiJson(`/api/nanoghost/mcp/instances/${encodeURIComponent(name)}/allowlist`, {
      method: "PUT",
      body: JSON.stringify({ enabled_only: enabledOnly }),
    })
  }

  async function ngProbe(name) {
    const qp = name ? `?instance=${encodeURIComponent(name)}` : ""
    return apiJson(`/api/nanoghost/mcp/probe${qp}`, { method: "GET" })
  }

  async function ngTools(name, serverId) {
    return apiJson(`/api/nanoghost/mcp/instances/${encodeURIComponent(name)}/tools?server_id=${encodeURIComponent(serverId)}`, { method: "GET" })
  }

  function parseEnabledOnly(text) {
    const raw = (text || "").trim()
    if (!raw) return []
    const parts = raw
      .split(/[\n,]+/g)
      .map((x) => (x || "").trim())
      .filter(Boolean)
    return Array.from(new Set(parts)).sort()
  }

  function render() {
    const root = document.getElementById("pageNanoGhostMcpRoot")
    if (!root) return
    root.textContent = ""

    const hint = document.createElement("div")
    hint.className = "hint"
    hint.textContent =
      "全局配置：~/.nanoghost/config.yaml 的 mcp_servers；实例可见性：<instance>/config.yaml 的 mcp.enabled_only（空/缺失 = 全禁用）"

    const toast = document.createElement("div")
    toast.id = "toast"

    const globalTitle = document.createElement("div")
    globalTitle.style.fontWeight = "700"
    globalTitle.style.fontSize = "13px"
    globalTitle.textContent = "全局配置（raw）"

    const globalRow = document.createElement("div")
    globalRow.className = "row"
    globalRow.style.justifyContent = "flex-end"

    const globalRefreshBtn = document.createElement("button")
    globalRefreshBtn.textContent = "刷新"
    const globalSaveBtn = document.createElement("button")
    globalSaveBtn.className = "primary"
    globalSaveBtn.textContent = "保存"

    globalRow.appendChild(globalRefreshBtn)
    globalRow.appendChild(globalSaveBtn)

    const globalTa = document.createElement("textarea")
    globalTa.spellcheck = false
    globalTa.style.minHeight = "280px"

    const instTitle = document.createElement("div")
    instTitle.style.marginTop = "14px"
    instTitle.style.fontWeight = "700"
    instTitle.style.fontSize = "13px"
    instTitle.textContent = "实例白名单与探测"

    const instRow = document.createElement("div")
    instRow.className = "row"
    instRow.style.flexWrap = "wrap"

    const instSel = document.createElement("select")
    instSel.style.minWidth = "220px"

    const allowInput = document.createElement("input")
    allowInput.placeholder = "enabled_only: server1,server2"
    allowInput.style.minWidth = "320px"

    const allowLoadBtn = document.createElement("button")
    allowLoadBtn.textContent = "读取白名单"
    const allowSaveBtn = document.createElement("button")
    allowSaveBtn.className = "primary"
    allowSaveBtn.textContent = "保存白名单"

    const probeBtn = document.createElement("button")
    probeBtn.textContent = "探测"

    instRow.appendChild(instSel)
    instRow.appendChild(allowInput)
    instRow.appendChild(allowLoadBtn)
    instRow.appendChild(allowSaveBtn)
    instRow.appendChild(probeBtn)

    const toolsRow = document.createElement("div")
    toolsRow.className = "row"
    toolsRow.style.flexWrap = "wrap"
    toolsRow.style.marginTop = "8px"

    const toolsServerId = document.createElement("input")
    toolsServerId.placeholder = "server_id"
    toolsServerId.style.minWidth = "220px"

    const toolsBtn = document.createElement("button")
    toolsBtn.textContent = "拉取 tools/list"

    toolsRow.appendChild(toolsServerId)
    toolsRow.appendChild(toolsBtn)

    const probeTitle = document.createElement("div")
    probeTitle.style.marginTop = "10px"
    probeTitle.style.fontWeight = "700"
    probeTitle.style.fontSize = "13px"
    probeTitle.textContent = "探测结果"

    const table = document.createElement("table")
    const thead = document.createElement("thead")
    const trh = document.createElement("tr")
    for (const h of ["ID", "URL", "OK", "Status", "Duration(ms)", "Error"]) {
      const th = document.createElement("th")
      th.textContent = h
      trh.appendChild(th)
    }
    thead.appendChild(trh)
    table.appendChild(thead)
    const tbody = document.createElement("tbody")
    table.appendChild(tbody)

    const toolsTitle = document.createElement("div")
    toolsTitle.style.marginTop = "10px"
    toolsTitle.style.fontWeight = "700"
    toolsTitle.style.fontSize = "13px"
    toolsTitle.textContent = "tools/list 输出"

    const toolsOut = document.createElement("textarea")
    toolsOut.spellcheck = false
    toolsOut.style.minHeight = "220px"

    async function refreshGlobal() {
      const cfg = await ngMcpConfigGetRaw()
      globalTa.value = cfg.raw || ""
    }

    async function refreshInstances() {
      const data = await ngInstancesGet()
      const items = (data.instances || []).map((x) => x.name).filter(Boolean)
      instSel.textContent = ""
      for (const name of items) {
        const opt = document.createElement("option")
        opt.value = name
        opt.textContent = name
        instSel.appendChild(opt)
      }
    }

    async function loadAllowlist() {
      const name = instSel.value || ""
      if (!name) return
      const data = await ngAllowlistGet(name)
      allowInput.value = (data.enabled_only || []).join(",")
    }

    async function saveAllowlist() {
      const name = instSel.value || ""
      if (!name) return
      const enabledOnly = parseEnabledOnly(allowInput.value || "")
      await ngAllowlistPut(name, enabledOnly)
    }

    async function probeInstance() {
      const name = instSel.value || ""
      if (!name) return
      const r = await ngProbe(name)
      tbody.textContent = ""
      for (const it of r.items || []) {
        const tr = document.createElement("tr")
        const tdId = document.createElement("td")
        const tdUrl = document.createElement("td")
        const tdOk = document.createElement("td")
        const tdSt = document.createElement("td")
        const tdDur = document.createElement("td")
        const tdErr = document.createElement("td")
        tdId.textContent = it.id || ""
        tdUrl.textContent = it.url || ""
        tdOk.textContent = String(Boolean(it.ok))
        tdSt.textContent = it.status || ""
        tdDur.textContent = it.duration_ms == null ? "" : String(it.duration_ms)
        tdErr.textContent = it.error || ""
        tr.appendChild(tdId)
        tr.appendChild(tdUrl)
        tr.appendChild(tdOk)
        tr.appendChild(tdSt)
        tr.appendChild(tdDur)
        tr.appendChild(tdErr)
        tbody.appendChild(tr)
      }
    }

    globalRefreshBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await refreshGlobal()
        setToast("已刷新")
      } catch (e) {
        setToast(String(e))
      }
    })

    globalSaveBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await ngMcpConfigPutRaw(globalTa.value || "")
        setToast("已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

    allowLoadBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await loadAllowlist()
        setToast("已读取")
      } catch (e) {
        setToast(String(e))
      }
    })

    allowSaveBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await saveAllowlist()
        setToast("白名单已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

    probeBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await probeInstance()
        setToast("探测完成")
      } catch (e) {
        setToast(String(e))
      }
    })

    toolsBtn.addEventListener("click", async () => {
      try {
        setToast("")
        toolsOut.value = ""
        const name = instSel.value || ""
        const sid = (toolsServerId.value || "").trim()
        if (!name || !sid) {
          setToast("需要 instance 与 server_id")
          return
        }
        const r = await ngTools(name, sid)
        toolsOut.value = JSON.stringify(r, null, 2)
        setToast("已拉取")
      } catch (e) {
        setToast(String(e))
      }
    })

    instSel.addEventListener("change", async () => {
      try {
        setToast("")
        toolsOut.value = ""
        tbody.textContent = ""
        await loadAllowlist()
      } catch (e) {
        setToast(String(e))
      }
    })

    root.appendChild(hint)
    root.appendChild(globalTitle)
    root.appendChild(globalRow)
    root.appendChild(globalTa)
    root.appendChild(instTitle)
    root.appendChild(instRow)
    root.appendChild(toolsRow)
    root.appendChild(probeTitle)
    root.appendChild(table)
    root.appendChild(toolsTitle)
    root.appendChild(toolsOut)
    root.appendChild(toast)

    ;(async () => {
      try {
        setToast("")
        await refreshGlobal()
        await refreshInstances()
        if (instSel.value) await loadAllowlist()
      } catch (e) {
        setToast(String(e))
      }
    })()
  }

  window.addEventListener("DOMContentLoaded", render)
})()


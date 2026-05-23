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

  async function hermesMcpConfigGetRaw() {
    return apiJson("/api/hermes/mcp/config/raw", { method: "GET" })
  }

  async function hermesMcpConfigPutRaw(raw) {
    return apiJson("/api/hermes/mcp/config/raw", { method: "PUT", body: JSON.stringify({ raw }) })
  }

  async function hermesMcpProbe() {
    return apiJson("/api/hermes/mcp/probe", { method: "GET" })
  }

  function render() {
    const root = document.getElementById("pageHermesMcpRoot")
    if (!root) return
    root.textContent = ""

    const hint = document.createElement("div")
    hint.className = "hint"
    hint.textContent = "编辑 ~/.hermes/config.yaml 的 mcp_servers（全局一致）；探测只做连通性检查，不会修改配置"

    const row = document.createElement("div")
    row.className = "row"
    row.style.justifyContent = "flex-end"

    const refreshBtn = document.createElement("button")
    refreshBtn.textContent = "刷新"
    const probeBtn = document.createElement("button")
    probeBtn.textContent = "探测"
    const saveBtn = document.createElement("button")
    saveBtn.className = "primary"
    saveBtn.textContent = "保存"

    row.appendChild(refreshBtn)
    row.appendChild(probeBtn)
    row.appendChild(saveBtn)

    const ta = document.createElement("textarea")
    ta.spellcheck = false
    ta.style.minHeight = "360px"

    const subTitle = document.createElement("div")
    subTitle.style.marginTop = "12px"
    subTitle.style.fontWeight = "700"
    subTitle.style.fontSize = "13px"
    subTitle.textContent = "探测结果"

    const table = document.createElement("table")
    const thead = document.createElement("thead")
    const trh = document.createElement("tr")
    for (const h of ["ID", "Transport", "Enabled", "OK", "Code", "Error"]) {
      const th = document.createElement("th")
      th.textContent = h
      trh.appendChild(th)
    }
    thead.appendChild(trh)
    table.appendChild(thead)
    const tbody = document.createElement("tbody")
    table.appendChild(tbody)

    const toast = document.createElement("div")
    toast.id = "toast"

    async function refresh() {
      const cfg = await hermesMcpConfigGetRaw()
      ta.value = cfg.raw || ""
    }

    async function probe() {
      const r = await hermesMcpProbe()
      tbody.textContent = ""
      for (const it of r.items || []) {
        const tr = document.createElement("tr")
        const tdId = document.createElement("td")
        const tdT = document.createElement("td")
        const tdEn = document.createElement("td")
        const tdOk = document.createElement("td")
        const tdCode = document.createElement("td")
        const tdErr = document.createElement("td")
        tdId.textContent = it.id || ""
        tdT.textContent = it.transport || ""
        tdEn.textContent = String(Boolean(it.enabled))
        tdOk.textContent = String(Boolean(it.ok))
        tdCode.textContent = it.status_code == null ? "" : String(it.status_code)
        tdErr.textContent = it.error || ""
        tr.appendChild(tdId)
        tr.appendChild(tdT)
        tr.appendChild(tdEn)
        tr.appendChild(tdOk)
        tr.appendChild(tdCode)
        tr.appendChild(tdErr)
        tbody.appendChild(tr)
      }
    }

    refreshBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await refresh()
        setToast("已刷新")
      } catch (e) {
        setToast(String(e))
      }
    })

    probeBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await probe()
        setToast("探测完成")
      } catch (e) {
        setToast(String(e))
      }
    })

    saveBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await hermesMcpConfigPutRaw(ta.value || "")
        setToast("已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

    root.appendChild(hint)
    root.appendChild(row)
    root.appendChild(ta)
    root.appendChild(subTitle)
    root.appendChild(table)
    root.appendChild(toast)

    ;(async () => {
      try {
        setToast("")
        await refresh()
      } catch (e) {
        setToast(String(e))
      }
    })()
  }

  window.addEventListener("DOMContentLoaded", render)
})()


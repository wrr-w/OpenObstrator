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

  async function managerLogsGet(limit) {
    const u = new URL("/api/manager/logs", window.location.origin)
    u.searchParams.set("limit", String(limit || 500))
    return apiJson(u.pathname + u.search, { method: "GET" })
  }

  async function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return
    }
    const ta = document.createElement("textarea")
    ta.value = text || ""
    ta.style.position = "fixed"
    ta.style.left = "-9999px"
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    document.execCommand("copy")
    ta.remove()
  }

  function render() {
    const root = document.getElementById("pageLogsRoot");
    if (!root) return;
    root.textContent = ""

    const hint = document.createElement("div")
    hint.className = "hint"
    hint.textContent = "管理台进程内日志（内存 ring buffer）。刷新拿到最近 N 行。"

    const row = document.createElement("div")
    row.className = "row"

    const limitInp = document.createElement("input")
    limitInp.type = "number"
    limitInp.min = "10"
    limitInp.max = "5000"
    limitInp.value = "800"
    limitInp.style.width = "120px"

    const refreshBtn = document.createElement("button")
    refreshBtn.className = "primary"
    refreshBtn.textContent = "刷新"

    const autoLbl = document.createElement("label")
    autoLbl.style.display = "flex"
    autoLbl.style.alignItems = "center"
    autoLbl.style.gap = "8px"
    const autoCb = document.createElement("input")
    autoCb.type = "checkbox"
    const autoTxt = document.createElement("span")
    autoTxt.className = "hint"
    autoTxt.textContent = "自动刷新"
    autoLbl.appendChild(autoCb)
    autoLbl.appendChild(autoTxt)

    const copyBtn = document.createElement("button")
    copyBtn.textContent = "复制"

    row.appendChild(document.createTextNode("limit"))
    row.appendChild(limitInp)
    row.appendChild(refreshBtn)
    row.appendChild(copyBtn)
    row.appendChild(autoLbl)

    const pre = document.createElement("pre")
    pre.style.minHeight = "520px"
    pre.style.maxHeight = "70vh"
    pre.style.overflow = "auto"
    pre.style.padding = "10px 12px"
    pre.style.borderRadius = "12px"
    pre.style.border = "1px solid var(--border)"
    pre.style.background = "rgba(0,0,0,0.12)"

    const toast = document.createElement("div")
    toast.id = "toast"

    let _timer = null

    async function refresh() {
      const lim = Math.max(10, Math.min(5000, Number(limitInp.value || 800)))
      const data = await managerLogsGet(lim)
      const items = Array.isArray(data.items) ? data.items : []
      pre.textContent = items.join("\n")
    }

    function stopAuto() {
      if (_timer) clearInterval(_timer)
      _timer = null
    }

    function startAuto() {
      stopAuto()
      _timer = setInterval(async () => {
        try {
          await refresh()
        } catch (e) {
          setToast(String(e))
        }
      }, 2500)
    }

    refreshBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await refresh()
      } catch (e) {
        setToast(String(e))
      }
    })

    copyBtn.addEventListener("click", async () => {
      try {
        setToast("")
        await copyText(pre.textContent || "")
        setToast("已复制")
      } catch (e) {
        setToast(String(e))
      }
    })

    autoCb.addEventListener("change", async () => {
      if (autoCb.checked) startAuto()
      else stopAuto()
    })

    window.addEventListener("beforeunload", () => stopAuto())

    root.appendChild(hint)
    root.appendChild(row)
    root.appendChild(pre)
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

  window.addEventListener("DOMContentLoaded", render);
})();

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

const _NAME_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/

function isValidName(name) {
  return _NAME_RE.test((name || "").trim())
}

function withTemplateId(path, template_id) {
  const tid = (template_id || "root").trim() || "root"
  const u = new URL(path, window.location.origin)
  u.searchParams.set("template_id", tid)
  return u.pathname + u.search
}

function isHttpError(e, status) {
  const msg = String(e || "")
  return msg.includes(`Error: ${status} `) || msg.includes(`${status} `)
}

function setPill(el, running, suffix) {
  if (!el) return
  el.classList.remove("ok", "bad")
  if (running) {
    el.textContent = suffix ? `运行中 ${suffix}` : "运行中"
    el.classList.add("ok")
    return
  }
  el.textContent = "已停止"
  el.classList.add("bad")
}

function setLink(el, port) {
  if (!el) return
  if (!port) {
    el.textContent = ""
    el.removeAttribute("href")
    return
  }
  const url = `http://127.0.0.1:${port}/`
  el.textContent = url
  el.href = url
}

function parseInitialSelection() {
  const qp = new URLSearchParams(window.location.search)
  const runtime = qp.get("runtime") || document.body.dataset.runtime || ""
  const name = qp.get("profile") || document.body.dataset.profile || ""
  return { runtime, name }
}

function setQuery(runtime, name) {
  const url = new URL(window.location.href)
  if (runtime) url.searchParams.set("runtime", runtime)
  if (name) url.searchParams.set("profile", name)
  history.replaceState(null, "", url.toString())
}

async function loadInstances() {
  return apiJson("/api/instances", { method: "GET" })
}

async function loadManifest(runtime, name) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/manifest`, { method: "GET" })
}

async function loadEnv(runtime, name) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/env`, { method: "GET" })
}

async function putEnv(runtime, name, key, value) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/env`, {
    method: "PUT",
    body: JSON.stringify({ key, value }),
  })
}

async function batchPutEnv(runtime, name, items) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/env/batch`, {
    method: "PUT",
    body: JSON.stringify({ items }),
  })
}

async function deleteEnv(runtime, name, key) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/env`, {
    method: "DELETE",
    body: JSON.stringify({ key }),
  })
}

async function loadSkills(runtime, name) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/skills`, { method: "GET" })
}

async function ngMcpConfigGetRaw() {
  return apiJson("/api/nanoghost/mcp/config/raw", { method: "GET" })
}

async function ngMcpConfigPutRaw(raw) {
  return apiJson("/api/nanoghost/mcp/config/raw", { method: "PUT", body: JSON.stringify({ raw }) })
}

async function ngMcpAllowlistGet(name) {
  return apiJson(`/api/nanoghost/mcp/instances/${encodeURIComponent(name)}/allowlist`, { method: "GET" })
}

async function ngMcpAllowlistPut(name, enabledOnly) {
  return apiJson(`/api/nanoghost/mcp/instances/${encodeURIComponent(name)}/allowlist`, {
    method: "PUT",
    body: JSON.stringify({ enabled_only: enabledOnly }),
  })
}

async function ngMcpProbe(name) {
  return apiJson(`/api/nanoghost/mcp/probe?instance=${encodeURIComponent(name)}`, { method: "GET" })
}

async function ngMcpTools(name, serverId) {
  return apiJson(
    `/api/nanoghost/mcp/instances/${encodeURIComponent(name)}/tools?server_id=${encodeURIComponent(serverId)}`,
    { method: "GET" }
  )
}

async function saveSkills(runtime, name, items) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/skills/batch`, {
    method: "PUT",
    body: JSON.stringify({ items }),
  })
}

async function svcStatus(runtime, name, service) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/services/${encodeURIComponent(service)}/status`, {
    method: "GET",
  })
}

async function svcStart(runtime, name, service) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/services/${encodeURIComponent(service)}/start`, {
    method: "POST",
  })
}

async function svcStop(runtime, name, service) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/services/${encodeURIComponent(service)}/stop`, {
    method: "POST",
  })
}

async function loadChannels(runtime, name) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/channels`, { method: "GET" })
}

async function saveChannels(runtime, name, config) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/channels`, {
    method: "PUT",
    body: JSON.stringify({ config }),
  })
}

async function createInstance(runtime, name, template_id) {
  const tid = (template_id || "root").trim()
  return apiJson("/api/instances", { method: "POST", body: JSON.stringify({ runtime, name, template_id: tid }) })
}

async function deleteInstance(runtime, name) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}`, { method: "DELETE" })
}

async function exportTemplate(runtime, name, template_name, overwrite) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/export-template`, {
    method: "POST",
    body: JSON.stringify({ template_name, overwrite: Boolean(overwrite) }),
  })
}

async function renameInstance(runtime, name, new_name) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/rename`, {
    method: "POST",
    body: JSON.stringify({ new_name }),
  })
}

async function managerConfigGet() {
  return apiJson("/api/manager/config/raw", { method: "GET" })
}

async function managerConfigPut(raw) {
  return apiJson("/api/manager/config/raw", { method: "PUT", body: JSON.stringify({ raw }) })
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

async function templatePutEnv(runtime, template_id, key, value) {
  return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/env`, template_id), {
    method: "PUT",
    body: JSON.stringify({ key, value }),
  })
}

async function templateBatchPutEnv(runtime, template_id, items) {
  return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/env/batch`, template_id), {
    method: "PUT",
    body: JSON.stringify({ items }),
  })
}

async function templateDeleteEnv(runtime, template_id, key) {
  return apiJson(withTemplateId(`/api/templates/${encodeURIComponent(runtime)}/env`, template_id), {
    method: "DELETE",
    body: JSON.stringify({ key }),
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

function badgeEl(badge) {
  const el = document.createElement("span")
  el.className = "typeBadge"
  el.textContent = badge?.text || ""
  if (badge?.color) {
    el.style.borderColor = badge.color
    el.style.background = badge.color + "22"
    el.style.color = badge.color
  }
  return el
}

let _ctxMenu = null
let _ctxMenuCleanup = null

function closeCtxMenu() {
  if (_ctxMenuCleanup) _ctxMenuCleanup()
  _ctxMenuCleanup = null
  if (_ctxMenu) _ctxMenu.remove()
  _ctxMenu = null
}

function openCtxMenu(anchorEl, items) {
  closeCtxMenu()
  const rect = anchorEl.getBoundingClientRect()
  const menu = document.createElement("div")
  menu.className = "ctxMenu"

  const width = 190
  const left = Math.max(10, Math.min(rect.right - width, window.innerWidth - width - 10))
  const top = Math.max(10, Math.min(rect.bottom + 8, window.innerHeight - 10))
  menu.style.left = `${left}px`
  menu.style.top = `${top}px`

  for (const it of items) {
    const btn = document.createElement("button")
    btn.type = "button"
    btn.textContent = it.label
    if (it.danger) btn.classList.add("dangerItem")
    btn.addEventListener("click", async (e) => {
      e.stopPropagation()
      closeCtxMenu()
      await it.onClick()
    })
    menu.appendChild(btn)
  }

  menu.addEventListener("click", (e) => e.stopPropagation())
  document.body.appendChild(menu)
  _ctxMenu = menu

  const onDocClick = () => closeCtxMenu()
  const onKey = (e) => {
    if (e.key === "Escape") closeCtxMenu()
  }

  setTimeout(() => {
    document.addEventListener("click", onDocClick)
    document.addEventListener("keydown", onKey)
  }, 0)

  _ctxMenuCleanup = () => {
    document.removeEventListener("click", onDocClick)
    document.removeEventListener("keydown", onKey)
  }
}

function renderInstanceList({ instances, statuses, activeKey, filter }) {
  const listEl = document.getElementById("profileList")
  if (!listEl) return
  listEl.textContent = ""
  closeCtxMenu()

  const f = (filter || "").trim().toLowerCase()
  for (const it of instances) {
    const key = `${it.runtime}:${it.name}`
    const label = it.name
    if (f && !label.toLowerCase().includes(f) && !String(it.runtime).toLowerCase().includes(f)) continue

    const item = document.createElement("div")
    item.className = "profileItem" + (key === activeKey ? " active" : "")

    const row = document.createElement("div")
    row.className = "profileRow"

    const left = document.createElement("div")
    left.className = "profileName"
    const nameSpan = document.createElement("span")
    nameSpan.textContent = label
    nameSpan.style.minWidth = "0"
    left.appendChild(nameSpan)
    left.appendChild(badgeEl(it.badge))

    const dots = document.createElement("div")
    dots.className = "dotRow"
    const st = statuses[key] || {}

    const addDot = (ok) => {
      const d = document.createElement("span")
      d.className = "dot"
      d.classList.add(ok ? "ok" : "bad")
      dots.appendChild(d)
    }

    if (it.runtime === "hermes") {
      addDot(Boolean(st.dashboard?.running))
      addDot(Boolean(st.gateway?.running))
    } else if (it.runtime === "nanoghost") {
      addDot(Boolean(st.gateway?.running))
    } else {
      addDot(false)
    }

    const moreBtn = document.createElement("button")
    moreBtn.type = "button"
    moreBtn.className = "moreBtn"
    moreBtn.textContent = "…"
    moreBtn.addEventListener("click", (e) => {
      e.stopPropagation()
      openCtxMenu(moreBtn, [
        {
          label: "删除实例",
          danger: true,
          onClick: async () => {
            try {
              await deleteInstanceFlow(it.runtime, it.name)
            } catch (err) {
              setToast(String(err))
            }
          },
        },
        {
          label: "设为模板",
          onClick: async () => {
            try {
              await exportTemplateFlow(it.runtime, it.name)
            } catch (err) {
              setToast(String(err))
            }
          },
        },
        {
          label: "编辑模板",
          onClick: async () => {
            try {
              setToast("")
              await openTemplateMgrModal(it.runtime, `tpl:${it.name}`)
            } catch (err) {
              setToast(String(err))
            }
          },
        },
        {
          label: "重命名实例",
          onClick: async () => {
            try {
              await renameInstanceFlow(it.runtime, it.name)
            } catch (err) {
              setToast(String(err))
            }
          },
        },
      ])
    })
    dots.appendChild(moreBtn)

    row.appendChild(left)
    row.appendChild(dots)

    const path = document.createElement("div")
    path.className = "profilePath"
    path.textContent = it.path || ""

    item.appendChild(row)
    item.appendChild(path)

    item.addEventListener("click", () => {
      selectInstance(it.runtime, it.name).catch((e) => setToast(String(e)))
    })

    listEl.appendChild(item)
  }
}

function setActiveHeader(instance, rootText) {
  const t = document.getElementById("activeProfileTitle")
  const b = document.getElementById("activeProfileBadge")
  const p = document.getElementById("activeProfilePath")
  const hr = document.getElementById("hermesRootMeta")
  if (t) t.textContent = instance?.name || ""
  if (b) b.textContent = instance?.badge?.text || instance?.runtime || ""
  if (p) p.textContent = instance?.path || ""
  if (hr) hr.textContent = rootText || ""
}

function applyTabs(allowedTabs) {
  const allowed = new Set(allowedTabs || [])
  const btns = Array.from(document.querySelectorAll(".tabBtn"))
  for (const btn of btns) {
    const tab = btn.dataset.tab
    btn.style.display = allowed.has(tab) ? "" : "none"
  }
  const panels = Array.from(document.querySelectorAll(".panel"))
  for (const p of panels) {
    const tab = p.id.replace("panel-", "")
    p.style.display = allowed.has(tab) ? "" : "none"
  }

  const activeBtn = btns.find((b) => b.classList.contains("active") && b.style.display !== "none")
  if (activeBtn) return
  for (const b of btns) b.classList.remove("active")
  const envBtn = btns.find((b) => b.dataset.tab === "env" && b.style.display !== "none")
  if (envBtn) envBtn.classList.add("active")
  for (const p of panels) p.classList.toggle("active", p.id === "panel-env" && p.style.display !== "none")
}

function applyServices(services) {
  const keys = new Set((services || []).map((s) => s.key))
  const cards = document.getElementById("cardsServices")
  const dashCard = document.getElementById("dashPill")?.closest(".card")
  const gwCard = document.getElementById("gwPill")?.closest(".card")
  if (dashCard) dashCard.style.display = keys.has("dashboard") ? "" : "none"
  if (gwCard) gwCard.style.display = keys.has("gateway") ? "" : "none"
  if (cards) cards.style.display = keys.size > 0 ? "" : "none"
}

function bindTabs() {
  const btns = Array.from(document.querySelectorAll(".tabBtn"))
  for (const btn of btns) {
    btn.addEventListener("click", () => {
      if (btn.style.display === "none") return
      const tab = btn.dataset.tab
      if (!tab) return
      for (const b of btns) b.classList.toggle("active", b === btn)
      const panels = Array.from(document.querySelectorAll(".panel"))
      for (const p of panels) p.classList.toggle("active", p.id === `panel-${tab}`)
    })
  }
}

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

    sel.addEventListener("change", () => {
      refreshTemplates()
    })

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
          arrow.textContent = "▶"
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
            arrow.textContent = isOpen ? "▶" : "▼"
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

let _instances = []
let _statuses = {}
let _activeRuntime = ""
let _activeName = ""
let _activeKey = ""
let _activeManifest = null

async function refreshStatuses(instances) {
  const out = {}
  await Promise.all(
    instances.map(async (it) => {
      const key = `${it.runtime}:${it.name}`
      try {
        if (it.runtime === "hermes") {
          const [ds, gs] = await Promise.all([svcStatus("hermes", it.name, "dashboard"), svcStatus("hermes", it.name, "gateway")])
          out[key] = { dashboard: ds, gateway: gs }
        } else if (it.runtime === "nanoghost") {
          const gs = await svcStatus("nanoghost", it.name, "gateway")
          out[key] = { gateway: gs }
        } else {
          out[key] = {}
        }
      } catch {
        out[key] = {}
      }
    }),
  )
  return out
}

async function refreshSidebar(filter) {
  const data = await loadInstances()
  _instances = data.instances || []
  _statuses = await refreshStatuses(_instances)
  renderInstanceList({ instances: _instances, statuses: _statuses, activeKey: _activeKey, filter })
}

async function refreshAllFlow() {
  const search = document.getElementById("profileSearch")
  await refreshSidebar(search?.value || "")
  await refreshServices()
  await refreshEnv()
  await refreshSkills()
  if ((_activeManifest?.tabs || []).includes("channels")) await refreshChannels()
  if ((_activeManifest?.tabs || []).includes("mcp")) await refreshNanoGhostMcp()
  if (_activeRuntime === "hermes") await refreshHermesExtras()
}

async function refreshServices() {
  if (!_activeManifest) return
  const rt = _activeRuntime
  const name = _activeName
  const services = _activeManifest.services || []
  for (const svc of services) {
    if (svc.key === "dashboard") {
      if (rt !== "hermes") continue
      const ds = await svcStatus(rt, name, "dashboard")
      setPill(document.getElementById("dashPill"), ds.running, ds.port ? `:${ds.port}` : "")
      setLink(document.getElementById("dashLink"), ds.port)
      const dh = document.getElementById("dashHint")
      if (dh) dh.textContent = ds.pid ? `pid: ${ds.pid}` : ""
    }
    if (svc.key === "gateway") {
      const gs = await svcStatus(rt, name, "gateway")
      setPill(document.getElementById("gwPill"), gs.running, gs.port ? `:${gs.port}` : "")
      const gh = document.getElementById("gwHint")
      if (gh) {
        const url = gs.port ? `http://127.0.0.1:${gs.port}/api/health` : ""
        gh.textContent = gs.pid ? `pid: ${gs.pid}${url ? `\n${url}` : ""}` : url
      }
    }
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
    arrow.textContent = "▶"
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
      arrow.textContent = isOpen ? "▶" : "▼"
    })
    body.appendChild(block)
  }
}

function _parseEnabledOnly(text) {
  const raw = (text || "").trim()
  if (!raw) return []
  const parts = raw
    .split(/[\n,]+/g)
    .map((x) => (x || "").trim())
    .filter(Boolean)
  return Array.from(new Set(parts)).sort()
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
          arrow.textContent = "▶"
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
            arrow.textContent = isOpen ? "▶" : "▼"
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
      arrow.textContent = "▶"
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
        arrow.textContent = isOpen ? "▶" : "▼"
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

async function deleteInstanceFlow(runtime, name) {
  if (!runtime || !name) return
  if (!confirm(`确认永久删除实例「${name}」？此操作不可撤销！`)) return
  setToast("")
  const key = `${runtime}:${name}`
  await deleteInstance(runtime, name)
  const wasActive = _activeKey === key
  if (wasActive) {
    _activeRuntime = ""
    _activeName = ""
    _activeKey = ""
  }
  await refreshSidebar(document.getElementById("profileSearch")?.value || "")
  if (wasActive && _instances.length > 0) {
    const next = _instances[0]
    await selectInstance(next.runtime, next.name)
  }
}

async function exportTemplateFlow(runtime, name) {
  const suggested = name || ""
  const templateName = (prompt("模板名称（小写字母/数字/_/-，<=64）", suggested) || "").trim()
  if (!templateName) return
  if (!isValidName(templateName)) {
    setToast("模板名不合法")
    return
  }
  try {
    setToast("")
    await exportTemplate(runtime, name, templateName, false)
    setToast(`已导出模板：tpl:${templateName}`)
  } catch (e) {
    if (!isHttpError(e, 409)) throw e
    if (!confirm(`模板「${templateName}」已存在，是否覆盖？`)) return
    setToast("")
    await exportTemplate(runtime, name, templateName, true)
    setToast(`已覆盖模板：tpl:${templateName}`)
  }
}

async function renameInstanceFlow(runtime, name) {
  const newName = (prompt(`重命名实例「${name}」为：`, name) || "").trim()
  if (!newName) return
  if (newName === name) return
  if (!isValidName(newName)) {
    setToast("实例名不合法")
    return
  }
  setToast("")
  await renameInstance(runtime, name, newName)
  await refreshSidebar(document.getElementById("profileSearch")?.value || "")
  await selectInstance(runtime, newName)
}

async function selectInstance(runtime, name) {
  _activeRuntime = runtime
  _activeName = name
  _activeKey = `${runtime}:${name}`
  setQuery(runtime, name)

  _activeManifest = await loadManifest(runtime, name)
  applyServices(_activeManifest.services || [])
  applyTabs(_activeManifest.tabs || [])

  const inst = _instances.find((x) => x.runtime === runtime && x.name === name)
  const rootText = runtime === "hermes" ? "runtime: hermes" : runtime === "nanoghost" ? "runtime: nanoghost" : `runtime: ${runtime}`
  setActiveHeader(inst || _activeManifest.instance, rootText)

  await refreshSidebar(document.getElementById("profileSearch")?.value || "")
  await refreshServices()
  await refreshEnv()
  await refreshSkills()
  if ((_activeManifest.tabs || []).includes("channels")) await refreshChannels()
  if ((_activeManifest.tabs || []).includes("mcp")) await refreshNanoGhostMcp()
  if (runtime === "hermes") await refreshHermesExtras()
}

function bindActions() {
  const globalRefresh = document.getElementById("globalRefresh")
  const globalTemplates = document.getElementById("globalTemplates")
  const globalManagerConfig = document.getElementById("globalManagerConfig")
  const globalRegistry = document.getElementById("globalRegistry")
  const globalLogs = document.getElementById("globalLogs")
  const createBtn = document.getElementById("createProfile")
  const search = document.getElementById("profileSearch")

  if (globalRefresh)
    globalRefresh.addEventListener("click", async () => {
      try {
        setToast("")
        await refreshAllFlow()
      } catch (e) {
        setToast(String(e))
      }
    })

  if (globalTemplates) globalTemplates.addEventListener("click", () => window.open("/pages/templates", "_blank"))
  if (globalManagerConfig) globalManagerConfig.addEventListener("click", () => window.open("/pages/manager-config", "_blank"))
  if (globalRegistry) globalRegistry.addEventListener("click", () => window.open("/pages/global-registry", "_blank"))
  if (globalLogs) globalLogs.addEventListener("click", () => window.open("/pages/logs", "_blank"))

  if (createBtn)
    createBtn.addEventListener("click", async () => {
      const r = await openCreateModal()
      if (!r) return
      if (!r.runtime || !r.name) {
        setToast("类型/名称不能为空")
        return
      }
      try {
        setToast("")
        await createInstance(r.runtime, r.name, r.template_id)
        await refreshSidebar(search?.value || "")
        await selectInstance(r.runtime, r.name)
      } catch (e) {
        setToast(String(e))
      }
    })

  if (search)
    search.addEventListener("input", () => {
      renderInstanceList({ instances: _instances, statuses: _statuses, activeKey: _activeKey, filter: search.value })
    })

  const dashStart = document.getElementById("dashStart")
  const dashStop = document.getElementById("dashStop")
  const gwStart = document.getElementById("gwStart")
  const gwStop = document.getElementById("gwStop")

  if (dashStart)
    dashStart.addEventListener("click", async () => {
      try {
        setToast("")
        await svcStart("hermes", _activeName, "dashboard")
        await refreshSidebar(search?.value || "")
        await refreshServices()
      } catch (e) {
        setToast(String(e))
      }
    })

  if (dashStop)
    dashStop.addEventListener("click", async () => {
      try {
        setToast("")
        await svcStop("hermes", _activeName, "dashboard")
        await refreshSidebar(search?.value || "")
        await refreshServices()
      } catch (e) {
        setToast(String(e))
      }
    })

  if (gwStart)
    gwStart.addEventListener("click", async () => {
      try {
        setToast("")
        await svcStart(_activeRuntime, _activeName, "gateway")
        await refreshSidebar(search?.value || "")
        await refreshServices()
      } catch (e) {
        setToast(String(e))
      }
    })

  if (gwStop)
    gwStop.addEventListener("click", async () => {
      try {
        setToast("")
        await svcStop(_activeRuntime, _activeName, "gateway")
        await refreshSidebar(search?.value || "")
        await refreshServices()
      } catch (e) {
        setToast(String(e))
      }
    })

  const envSet = document.getElementById("envSet")
  const envSaveBatch = document.getElementById("envSaveBatch")
  if (envSet)
    envSet.addEventListener("click", async () => {
      const k = document.getElementById("envNewKey")
      const v = document.getElementById("envNewValue")
      const key = k ? k.value.trim() : ""
      const value = v ? v.value : ""
      if (!key) {
        setToast("env key 不能为空")
        return
      }
      try {
        setToast("")
        await putEnv(_activeRuntime, _activeName, key, value)
        if (k) k.value = ""
        if (v) v.value = ""
        await refreshEnv()
      } catch (e) {
        setToast(String(e))
      }
    })

  if (envSaveBatch)
    envSaveBatch.addEventListener("click", async () => {
      const tbody = document.getElementById("envBody")
      if (!tbody) return
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
        await batchPutEnv(_activeRuntime, _activeName, items)
        await refreshEnv()
      } catch (e) {
        setToast(String(e))
      }
    })

  const cfgSave = document.getElementById("cfgSave")
  if (cfgSave)
    cfgSave.addEventListener("click", async () => {
      if (_activeRuntime !== "hermes") return
      const ta = document.getElementById("cfgRaw")
      const raw = ta ? ta.value : ""
      try {
        setToast("")
        await apiJson(`/api/profiles/${encodeURIComponent(_activeName)}/config/raw`, { method: "PUT", body: JSON.stringify({ raw }) })
      } catch (e) {
        setToast(String(e))
      }
    })

  const soulSave = document.getElementById("soulSave")
  if (soulSave)
    soulSave.addEventListener("click", async () => {
      if (_activeRuntime !== "hermes") return
      const ta = document.getElementById("soulRaw")
      const raw = ta ? ta.value : ""
      try {
        setToast("")
        await apiJson(`/api/profiles/${encodeURIComponent(_activeName)}/soul/raw`, { method: "PUT", body: JSON.stringify({ raw }) })
      } catch (e) {
        setToast(String(e))
      }
    })

  const userMemSave = document.getElementById("userMemSave")
  if (userMemSave)
    userMemSave.addEventListener("click", async () => {
      if (_activeRuntime !== "hermes") return
      const ta = document.getElementById("userMemRaw")
      const raw = ta ? ta.value : ""
      try {
        setToast("")
        await apiJson(`/api/profiles/${encodeURIComponent(_activeName)}/memories/user/raw`, { method: "PUT", body: JSON.stringify({ raw }) })
      } catch (e) {
        setToast(String(e))
      }
    })

  const memoryMemSave = document.getElementById("memoryMemSave")
  if (memoryMemSave)
    memoryMemSave.addEventListener("click", async () => {
      if (_activeRuntime !== "hermes") return
      const ta = document.getElementById("memoryMemRaw")
      const raw = ta ? ta.value : ""
      try {
        setToast("")
        await apiJson(`/api/profiles/${encodeURIComponent(_activeName)}/memories/memory/raw`, { method: "PUT", body: JSON.stringify({ raw }) })
      } catch (e) {
        setToast(String(e))
      }
    })

  const skillSearch = document.getElementById("skillSearch")
  if (skillSearch)
    skillSearch.addEventListener("input", () => {
      const q = (skillSearch.value || "").trim().toLowerCase()
      const body = document.getElementById("skillsBody")
      if (!body) return
      for (const block of Array.from(body.children)) {
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
    })

  const skillsSaveBatch = document.getElementById("skillsSaveBatch")
  if (skillsSaveBatch)
    skillsSaveBatch.addEventListener("click", async () => {
      const items = {}
      for (const cb of Array.from(document.querySelectorAll(".skillCb"))) {
        const name = cb.dataset.skillName
        if (!name) continue
        items[name] = cb.checked
      }
      if (!confirm(`确认保存 ${Object.keys(items).length} 个 skill 的启用状态？`)) return
      try {
        setToast("")
        await saveSkills(_activeRuntime, _activeName, items)
        await refreshSkills()
      } catch (e) {
        setToast(String(e))
      }
    })

  const ngMcpEditGlobal = document.getElementById("ngMcpEditGlobal")
  if (ngMcpEditGlobal)
    ngMcpEditGlobal.addEventListener("click", async () => {
      if (_activeRuntime !== "nanoghost") return
      try {
        setToast("")
        const cur = await ngMcpConfigGetRaw()
        const r = await openRawEditorModal("NanoGhost MCP 全局 Registry（~/.nanoghost/config.yaml）", cur.raw || "")
        if (!r) return
        await ngMcpConfigPutRaw(r.raw || "")
        setToast("已保存全局 Registry")
      } catch (e) {
        setToast(String(e))
      }
    })

  const ngMcpAllowlistLoad = document.getElementById("ngMcpAllowlistLoad")
  if (ngMcpAllowlistLoad)
    ngMcpAllowlistLoad.addEventListener("click", async () => {
      if (_activeRuntime !== "nanoghost") return
      try {
        setToast("")
        await refreshNanoGhostMcp()
        setToast("已读取白名单")
      } catch (e) {
        setToast(String(e))
      }
    })

  const ngMcpAllowlistSave = document.getElementById("ngMcpAllowlistSave")
  if (ngMcpAllowlistSave)
    ngMcpAllowlistSave.addEventListener("click", async () => {
      if (_activeRuntime !== "nanoghost") return
      const inp = document.getElementById("ngMcpAllowlist")
      const enabledOnly = _parseEnabledOnly(inp ? inp.value : "")
      try {
        setToast("")
        await ngMcpAllowlistPut(_activeName, enabledOnly)
        await refreshNanoGhostMcp()
        setToast("白名单已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

  const ngMcpProbeBtn = document.getElementById("ngMcpProbe")
  if (ngMcpProbeBtn)
    ngMcpProbeBtn.addEventListener("click", async () => {
      if (_activeRuntime !== "nanoghost") return
      try {
        setToast("")
        const r = await ngMcpProbe(_activeName)
        const tbody = document.getElementById("ngMcpProbeBody")
        if (!tbody) return
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
        setToast("探测完成")
      } catch (e) {
        setToast(String(e))
      }
    })

  const ngMcpToolsFetch = document.getElementById("ngMcpToolsFetch")
  if (ngMcpToolsFetch)
    ngMcpToolsFetch.addEventListener("click", async () => {
      if (_activeRuntime !== "nanoghost") return
      const sidEl = document.getElementById("ngMcpToolsServerId")
      const sid = (sidEl ? sidEl.value : "").trim()
      if (!sid) {
        setToast("server_id 不能为空")
        return
      }
      try {
        setToast("")
        const r = await ngMcpTools(_activeName, sid)
        const out = document.getElementById("ngMcpToolsOut")
        if (out) out.value = JSON.stringify(r, null, 2)
        setToast("已拉取 tools/list")
      } catch (e) {
        setToast(String(e))
      }
    })
}

async function boot() {
  const page = document.body.dataset.page
  if (page !== "app") return
  bindTabs()
  bindActions()
  await refreshSidebar("")

  const initial = parseInitialSelection()
  const found = initial.runtime && initial.name ? _instances.find((x) => x.runtime === initial.runtime && x.name === initial.name) : null
  const first = _instances.length > 0 ? _instances[0] : null
  if (found) {
    await selectInstance(found.runtime, found.name)
  } else if (first) {
    await selectInstance(first.runtime, first.name)
  }
}

window.addEventListener("DOMContentLoaded", () => {
  boot().catch((e) => setToast(String(e)))
})

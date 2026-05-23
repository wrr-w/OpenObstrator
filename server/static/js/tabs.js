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

function clearPanelContents() {
  const envBody = document.getElementById("envBody")
  if (envBody) envBody.textContent = ""
  const skillsBody = document.getElementById("skillsBody")
  if (skillsBody) skillsBody.textContent = ""
  const chBody = document.getElementById("channelsBody")
  if (chBody) chBody.textContent = ""
  const promptsBody = document.getElementById("promptsBody")
  if (promptsBody) promptsBody.textContent = ""
}

function getActiveTab() {
  const activeBtn = document.querySelector(".tabBtn.active")
  return activeBtn ? activeBtn.dataset.tab : "env"
}

async function loadActiveTab() {
  const tab = getActiveTab()
  if (tab) await loadTabData(tab)
}

async function loadTabData(tab) {
  const rt = _activeRuntime
  const name = _activeName
  if (!rt || !name) return
  switch (tab) {
    case "env": if (!_loadedTabs.has("env")) { _loadedTabs.add("env"); await refreshEnv() } break
    case "skills": if (!_loadedTabs.has("skills")) { _loadedTabs.add("skills"); await refreshSkills() } break
    case "channels": if (!_loadedTabs.has("channels")) { _loadedTabs.add("channels"); await refreshChannels() } break
    case "mcp": if (!_loadedTabs.has("mcp")) { _loadedTabs.add("mcp"); await refreshNanoGhostMcp() } break
    case "prompts": if (!_loadedTabs.has("prompts")) { _loadedTabs.add("prompts"); await refreshPrompts() } break
    case "logs":
      if (rt === "hermes") {
        await refreshHermesExtras()
        await refreshManagerLogs(name)
        startLogAutoRefresh(name)
      }
      break
    case "cron":
    case "sessions":
      if (rt === "hermes") await refreshHermesExtras()
      break
    default:
      if (rt === "hermes" && !_loadedHermesExtras) {
        _loadedHermesExtras = true
        await refreshHermesExtras()
      }
      break
  }
}

function applyServices(services) {
  const keys = new Set((services || []).map((s) => s.key))
  const cards = document.getElementById("cardsServices")
  const gwCard = document.getElementById("gwPill")?.closest(".card")
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
      if (tab !== "logs") stopLogAutoRefresh()
      for (const b of btns) b.classList.toggle("active", b === btn)
      const panels = Array.from(document.querySelectorAll(".panel"))
      for (const p of panels) p.classList.toggle("active", p.id === `panel-${tab}`)
      loadTabData(tab)
    })
  }
}

function startLogAutoRefresh(name) {
  stopLogAutoRefresh()
  _logRefreshTimer = setInterval(() => refreshManagerLogs(name), 3000)
}

function stopLogAutoRefresh() {
  if (_logRefreshTimer) { clearInterval(_logRefreshTimer); _logRefreshTimer = null }
}

async function refreshManagerLogs(name) {
  try {
    const r = await apiJson("/api/manager/logs?limit=200", { method: "GET" })
    const el = document.getElementById("logsOpsBody")
    if (!el) return
    const items = r.items || []
    const filtered = name ? items.filter(line => {
      const lower = typeof line === "string" ? line : String(line)
      return lower.includes(name)
    }) : items
    el.textContent = filtered.slice(-100).join("\n") || "(暂无操作日志)"
  } catch {}
}

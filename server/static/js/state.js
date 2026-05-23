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

let _instances = []
let _statuses = {}
let _activeRuntime = ""
let _activeName = ""
let _activeKey = ""
let _activeManifest = null
let _loadedTabs = new Set()
let _loadedHermesExtras = false
let _logRefreshTimer = null

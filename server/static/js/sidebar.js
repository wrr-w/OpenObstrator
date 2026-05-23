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
      addDot(Boolean(st.gateway?.running))
    } else if (it.runtime === "nanoghost") {
      addDot(Boolean(st.gateway?.running))
    } else {
      addDot(false)
    }

    const moreBtn = document.createElement("button")
    moreBtn.type = "button"
    moreBtn.className = "moreBtn"
    moreBtn.textContent = "\u2026"
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

async function refreshStatuses(instances) {
  const out = {}
  await Promise.all(
    instances.map(async (it) => {
      const key = `${it.runtime}:${it.name}`
      try {
        if (it.runtime === "hermes") {
          const gs = await svcStatus("hermes", it.name, "gateway")
          out[key] = { gateway: gs }
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

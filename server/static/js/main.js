async function refreshAllFlow() {
  _loadedTabs = new Set()
  _loadedHermesExtras = false
  const search = document.getElementById("profileSearch")
  const tabs = _activeManifest?.tabs || []
  await refreshSidebar(search?.value || "")
  await refreshServices()
  for (const tab of tabs) {
    if (tab === "cron" || tab === "sessions" || tab === "memories") continue
    await loadTabData(tab)
  }
  if (_activeRuntime === "hermes" && !tabs.includes("logs")) {
    await refreshHermesExtras()
  }
}

async function refreshServices() {
  if (!_activeManifest) return
  const rt = _activeRuntime
  const name = _activeName
  const services = _activeManifest.services || []
  for (const svc of services) {
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

function startGwAutoRefresh() {
  stopGwAutoRefresh()
  _gwStatusTimer = setInterval(async () => {
    const rt = _activeRuntime
    const name = _activeName
    if (!rt || !name) return
    try {
      const gs = await svcStatus(rt, name, "gateway")
      setPill(document.getElementById("gwPill"), gs.running, gs.port ? `:${gs.port}` : "")
      const gh = document.getElementById("gwHint")
      if (gh) {
        const url = gs.port ? `http://127.0.0.1:${gs.port}/api/health` : ""
        gh.textContent = gs.pid ? `pid: ${gs.pid}${url ? `\n${url}` : ""}` : url
      }
    } catch (_) {}
  }, 10000)
}

function stopGwAutoRefresh() {
  if (_gwStatusTimer) { clearInterval(_gwStatusTimer); _gwStatusTimer = null }
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
  _loadedTabs = new Set()
  _loadedHermesExtras = false
  stopLogAutoRefresh()
  stopGwAutoRefresh()
  setQuery(runtime, name)

  _activeManifest = await loadManifest(runtime, name)
  applyServices(_activeManifest.services || [])
  applyTabs(_activeManifest.tabs || [])

  const inst = _instances.find((x) => x.runtime === runtime && x.name === name)
  const rootText = runtime === "hermes" ? "runtime: hermes" : runtime === "nanoghost" ? "runtime: nanoghost" : `runtime: ${runtime}`
  setActiveHeader(inst || _activeManifest.instance, rootText)

  clearPanelContents()
  await refreshSidebar(document.getElementById("profileSearch")?.value || "")
  await refreshServices()
  await loadActiveTab()
  startGwAutoRefresh()
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

  // Batch start/stop all NanoGhost instances
  const batchStart = document.getElementById("batchStartAll")
  const batchStop = document.getElementById("batchStopAll")

  if (batchStart)
    batchStart.addEventListener("click", async () => {
      try {
        setToast("正在启动所有实例...")
        const r = await apiJson("/api/instances/nanoghost/batch/start", { method: "POST" })
        const results = r.results || {}
        const lines = Object.entries(results).map(([name, res]) =>
          `  ${name}: ${res.ok ? "OK" : "FAIL: " + (res.error || "?")}`
        )
        setToast("启动完成:\n" + lines.join("\n"))
        await refreshAllFlow()
      } catch (e) {
        setToast("批量启动失败: " + String(e))
      }
    })

  if (batchStop)
    batchStop.addEventListener("click", async () => {
      try {
        setToast("正在停止所有实例...")
        const r = await apiJson("/api/instances/nanoghost/batch/stop", { method: "POST" })
        const results = r.results || {}
        const lines = Object.entries(results).map(([name, res]) =>
          `  ${name}: ${res.ok ? "OK" : "FAIL: " + (res.error || "?")}`
        )
        setToast("停止完成:\n" + lines.join("\n"))
        await refreshAllFlow()
      } catch (e) {
        setToast("批量停止失败: " + String(e))
      }
    })

  if (createBtn)
    createBtn.addEventListener("click", async () => {
      const r = await openCreateModal()
      if (!r) return
      const { runtime, name, template_id } = r
      if (!name) {
        setToast("名称不能为空")
        return
      }
      if (!isValidName(name)) {
        setToast("名称不合法（小写字母/数字/_/-，<=64）")
        return
      }
      try {
        setToast("")
        await createInstance(runtime, name, template_id)
        await refreshSidebar(search?.value || "")
        await selectInstance(runtime, name)
      } catch (e) {
        setToast(String(e))
      }
    })

  if (search)
    search.addEventListener("input", () => {
      renderInstanceList({ instances: _instances, statuses: _statuses, activeKey: _activeKey, filter: search.value })
    })

  const envSaveBtn = document.getElementById("envSaveBatch")
  if (envSaveBtn)
    envSaveBtn.addEventListener("click", async () => {
      const rt = _activeRuntime
      const name = _activeName
      if (!rt || !name) return
      const items = {}
      const tbody = document.getElementById("envBody")
      if (tbody) {
        for (const tr of Array.from(tbody.querySelectorAll("tr"))) {
          const key = tr.dataset.envKey
          const inp = tr.querySelector("input")
          if (!key || !inp) continue
          const val = inp.value
          if (val !== inp.dataset.orig) items[key] = val
        }
      }
      if (Object.keys(items).length === 0) {
        setToast("没有修改")
        return
      }
      if (!confirm(`确认保存 ${Object.keys(items).length} 个环境变量？`)) return
      try {
        setToast("")
        await batchPutEnv(rt, name, items)
        await refreshEnv()
      } catch (e) {
        setToast(String(e))
      }
    })

  const envSetBtn = document.getElementById("envSet")
  if (envSetBtn)
    envSetBtn.addEventListener("click", async () => {
      const rt = _activeRuntime
      const name = _activeName
      if (!rt || !name) return
      const keyEl = document.getElementById("envNewKey")
      const valEl = document.getElementById("envNewValue")
      if (!keyEl || !valEl) return
      const key = keyEl.value.trim()
      const val = valEl.value
      if (!key) { setToast("KEY 不能为空"); return }
      try {
        setToast("")
        await putEnv(rt, name, key, val)
        keyEl.value = ""
        valEl.value = ""
        await refreshEnv()
      } catch (e) {
        setToast(String(e))
      }
    })

  const skillsSaveBtn = document.getElementById("skillsSave")
  if (skillsSaveBtn)
    skillsSaveBtn.addEventListener("click", async () => {
      const rt = _activeRuntime
      const name = _activeName
      if (!rt || !name) return
      const items = {}
      for (const cb of Array.from(document.querySelectorAll(".skillCb"))) {
        const sn = cb.dataset.skillName
        if (!sn) continue
        items[sn] = cb.checked
      }
      if (!confirm(`确认保存 ${Object.keys(items).length} 个 skill ？`)) return
      try {
        setToast("")
        await saveSkills(rt, name, items)
        await refreshSkills()
      } catch (e) {
        setToast(String(e))
      }
    })

  const skillsFilter = document.getElementById("skillsFilter")
  const skillsBody = document.getElementById("skillsBody")
  if (skillsFilter && skillsBody) {
    skillsFilter.addEventListener("input", () => {
      const q = (skillsFilter.value || "").trim().toLowerCase()
      for (const block of Array.from(skillsBody.children)) {
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
  }

  const cfgSaveBtn = document.getElementById("cfgSave")
  if (cfgSaveBtn)
    cfgSaveBtn.addEventListener("click", async () => {
      const name = _activeName
      if (!name) return
      const ta = document.getElementById("cfgRaw")
      if (!ta) return
      try {
        setToast("")
        await apiJson(`/api/profiles/${encodeURIComponent(name)}/config/raw`, { method: "PUT", body: JSON.stringify({ raw: ta.value }) })
        setToast("已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

  const soulSaveBtn = document.getElementById("soulSave")
  if (soulSaveBtn)
    soulSaveBtn.addEventListener("click", async () => {
      const name = _activeName
      if (!name) return
      const ta = document.getElementById("soulRaw")
      if (!ta) return
      try {
        setToast("")
        await apiJson(`/api/profiles/${encodeURIComponent(name)}/soul/raw`, { method: "PUT", body: JSON.stringify({ raw: ta.value }) })
        setToast("已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

  const userMemSaveBtn = document.getElementById("userMemSave")
  if (userMemSaveBtn)
    userMemSaveBtn.addEventListener("click", async () => {
      const name = _activeName
      if (!name) return
      const ta = document.getElementById("userMemRaw")
      if (!ta) return
      try {
        setToast("")
        await apiJson(`/api/profiles/${encodeURIComponent(name)}/memories/user/raw`, { method: "PUT", body: JSON.stringify({ raw: ta.value }) })
        setToast("已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

  const memoryMemSaveBtn = document.getElementById("memoryMemSave")
  if (memoryMemSaveBtn)
    memoryMemSaveBtn.addEventListener("click", async () => {
      const name = _activeName
      if (!name) return
      const ta = document.getElementById("memoryMemRaw")
      if (!ta) return
      try {
        setToast("")
        await apiJson(`/api/profiles/${encodeURIComponent(name)}/memories/memory/raw`, { method: "PUT", body: JSON.stringify({ raw: ta.value }) })
        setToast("已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

  const ngMemSaveBtn = document.getElementById("ngMemSave")
  if (ngMemSaveBtn)
    ngMemSaveBtn.addEventListener("click", async () => {
      const name = _activeName
      if (!name || _activeRuntime !== "nanoghost") return
      const ta = document.getElementById("ngMemRaw")
      if (!ta) return
      try {
        setToast("")
        await saveNgMemoryRaw(name, ta.value)
        setToast("已保存")
      } catch (e) {
        setToast(String(e))
      }
    })

  const ngMemRefreshBtn = document.getElementById("ngMemRefresh")
  if (ngMemRefreshBtn)
    ngMemRefreshBtn.addEventListener("click", async () => {
      if (_activeRuntime !== "nanoghost") return
      _loadedTabs.delete("memories")
      await refreshNanoGhostMemories()
    })

  const ngMemEditBtn = document.getElementById("ngMemEdit")
  if (ngMemEditBtn)
    ngMemEditBtn.addEventListener("click", () => {
      if (_activeRuntime !== "nanoghost") return
      openNgMemoryEditModal(_activeName, refreshNanoGhostMemories)
    })

  const gwStartBtn = document.getElementById("gwStart")
  const gwStopBtn = document.getElementById("gwStop")
  if (gwStartBtn)
    gwStartBtn.addEventListener("click", async () => {
      const rt = _activeRuntime
      const name = _activeName
      if (!rt || !name) return
      try {
        setToast("")
        await svcStart(rt, name, "gateway")
        await refreshServices()
        await refreshSidebar(document.getElementById("profileSearch")?.value || "")
      } catch (e) {
        setToast(String(e))
      }
    })
  if (gwStopBtn)
    gwStopBtn.addEventListener("click", async () => {
      const rt = _activeRuntime
      const name = _activeName
      if (!rt || !name) return
      try {
        setToast("")
        await svcStop(rt, name, "gateway")
        await refreshServices()
        await refreshSidebar(document.getElementById("profileSearch")?.value || "")
      } catch (e) {
        setToast(String(e))
      }
    })

  const ngMcpAllowlistSave = document.getElementById("ngMcpAllowlistSave")
  if (ngMcpAllowlistSave)
    ngMcpAllowlistSave.addEventListener("click", async () => {
      if (_activeRuntime !== "nanoghost") return
      const inp = document.getElementById("ngMcpAllowlist")
      const raw = inp ? inp.value : ""
      try {
        setToast("")
        await ngMcpAllowlistPut(_activeName, _parseEnabledOnly(raw))
        setToast("已保存 allowlist")
      } catch (e) {
        setToast(String(e))
      }
    })

  const ngMcpProbeBtn = document.getElementById("ngMcpProbeBtn")
  if (ngMcpProbeBtn)
    ngMcpProbeBtn.addEventListener("click", async () => {
      if (_activeRuntime !== "nanoghost") return
      try {
        setToast("")
        const r = await ngMcpProbe(_activeName)
        const tbody = document.getElementById("ngMcpProbeBody")
        if (tbody) {
          tbody.textContent = ""
          for (const svr of r.servers || []) {
            const row = document.createElement("tr")
            const tdSid = document.createElement("td")
            const code = document.createElement("code")
            code.textContent = svr.server_id || "-"
            tdSid.appendChild(code)
            const tdOk = document.createElement("td")
            const pill = document.createElement("span")
            pill.className = "pill"
            pill.classList.add(svr.ok ? "ok" : "bad")
            pill.textContent = svr.ok ? "✓" : "✗"
            tdOk.appendChild(pill)
            const tdErr = document.createElement("td")
            tdErr.textContent = svr.error || ""
            tdErr.style.fontSize = "12px"
            tdErr.style.color = "var(--muted)"
            row.appendChild(tdSid)
            row.appendChild(tdOk)
            row.appendChild(tdErr)
            tbody.appendChild(row)
          }
        }
        setToast("已探测")
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

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

async function svcRestart(runtime, name, service) {
  return apiJson(`/api/instances/${encodeURIComponent(runtime)}/${encodeURIComponent(name)}/services/${encodeURIComponent(service)}/restart`, {
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

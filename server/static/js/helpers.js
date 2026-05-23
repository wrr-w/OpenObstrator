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

function _parseEnabledOnly(text) {
  const raw = (text || "").trim()
  if (!raw) return []
  const parts = raw
    .split(/[\n,]+/g)
    .map((x) => (x || "").trim())
    .filter(Boolean)
  return Array.from(new Set(parts)).sort()
}

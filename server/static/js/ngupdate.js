// NanoGhost 升级 / 安装弹窗。
//
// 单独一个文件而不塞进 modals.js：modals.js 里的都是"拿个值就关掉"的一次性
// 对话框，这个是**活**的 —— 自己起定时器拉进度，关闭时必须把定时器清掉，
// 否则关掉弹窗之后接口还会被无限轮询下去。
//
// 为什么是轮询而不是流：helpers.js 的 apiJson 做的是 res.text() + JSON.parse，
// 结构上消费不了 SSE / NDJSON。换流式要先改那个函数，会影响所有调用点。

const _NG_PHASE_TEXT = {
  idle: "空闲",
  preflight: "准备",
  checking: "检查更新",
  stopping: "停止进程",
  applying: "正在应用",
  verifying: "核对版本",
  restarting: "重启实例",
  done: "完成",
  failed: "失败",
}

// 这些阶段意味着有活儿在跑 —— 和 nanoghost_upgrade.py 的 _IN_FLIGHT 一致
const _NG_IN_FLIGHT = ["preflight", "checking", "stopping", "applying", "verifying", "restarting"]

let _ngTimer = null
let _ngEls = null
let _ngInfo = {}

function ngUpdateIsRunning(phase) {
  return _NG_IN_FLIGHT.indexOf(phase) >= 0
}

function ngUpdateStopPolling() {
  if (_ngTimer) {
    clearInterval(_ngTimer)
    _ngTimer = null
  }
}

function ngUpdateStartPolling() {
  ngUpdateStopPolling()
  _ngTimer = setInterval(async () => {
    let st = null
    try {
      st = await ngUpdateStatus()
    } catch (_) {
      return // 一次拉不到不算失败，下一拍再来
    }
    ngUpdateRender(st)
    if (!ngUpdateIsRunning(st.phase)) {
      // 结束了就停 —— 否则弹窗开着就会一直每秒打一次接口
      ngUpdateStopPolling()
      // 收尾信息可能已经变了（覆盖装到了别的目录、版本号变了），重新解析一次
      ngUpdateReloadInfo()
    }
  }, 1000)
}

async function ngUpdateReloadInfo() {
  try {
    _ngInfo = await ngUpdateInfo()
  } catch (e) {
    _ngInfo = { ok: false, error: String(e), program_exists: false }
  }
  ngUpdateRenderInfo()
}

function ngUpdateRenderInfo() {
  const e = _ngEls
  if (!e) return
  const info = _ngInfo || {}
  if (info.error) {
    e.prog.textContent = info.error
    e.prog.style.color = "var(--bad)"
  } else if (info.program_exists) {
    e.prog.textContent = info.program + (info.program_source ? `（${info.program_source}）` : "")
    e.prog.style.color = ""
  } else {
    e.prog.textContent = "未检测到 NanoGhost —— 本机还没装，用「下载并安装」"
    e.prog.style.color = "var(--muted)"
  }
  // 没程序就升不了；这时把「下载并安装」提为主按钮，也就是"自动解析、可覆盖"
  // 在界面上的样子
  const hasProg = Boolean(info.program_exists)
  e.btnUpdate.classList.toggle("primary", hasProg)
  e.btnInstall.classList.toggle("primary", !hasProg)
}

function ngUpdateRenderVersion(st) {
  const e = _ngEls
  if (!e) return
  const info = _ngInfo || {}
  const from = (st && st.from_version) || info.current_version || ""
  const to = (st && st.to_version) || info.latest_version || ""
  if (!from && !to) {
    e.ver.textContent = "版本未知"
    return
  }
  if (to && from && to !== from) {
    e.ver.textContent = `当前 ${from}  →  最新 ${to}`
  } else {
    e.ver.textContent = `当前 ${from || to}${to && from === to ? "（已是最新）" : ""}`
  }
}

function ngUpdateRender(st) {
  const e = _ngEls
  if (!e || !st) return

  e.pill.textContent = _NG_PHASE_TEXT[st.phase] || st.phase || ""
  e.pill.classList.remove("ok", "bad")
  if (st.phase === "done") e.pill.classList.add("ok")
  if (st.phase === "failed") e.pill.classList.add("bad")

  e.step.textContent = st.step || ""

  const running = ngUpdateIsRunning(st.phase)
  const pct = st.progress
  if (typeof pct === "number" && pct >= 0) {
    e.bar.style.display = "block"
    e.fill.classList.remove("ngIndeterminate")
    e.fill.style.width = Math.max(0, Math.min(100, pct)) + "%"
  } else if (running) {
    // 没有百分比（停进程、解压）不等于没进展，走不确定动画
    e.bar.style.display = "block"
    e.fill.classList.add("ngIndeterminate")
  } else {
    e.bar.style.display = "none"
  }

  const text = (st.log || []).join("\n")
  if (text !== e.log.dataset.text) {
    e.log.dataset.text = text
    e.log.textContent = text
    e.log.scrollTop = e.log.scrollHeight
  }

  if (st.error) {
    e.err.style.display = "block"
    e.err.textContent = st.error
  } else {
    e.err.style.display = "none"
    e.err.textContent = ""
  }

  ngUpdateRenderVersion(st)

  e.btnCheck.disabled = running
  e.btnUpdate.disabled = running || !(_ngInfo || {}).program_exists
  e.btnInstall.disabled = running
}

// 停进程是**机器级**的：覆盖脚本的等待循环按映像名匹配、不区分目录
// （update.py:_write_update_bat），所以只要还有任何一个别的目录下的 NanoGhost.exe
// 活着，覆盖就会报 FAIL:timeout。代价必须写在这里 —— 别的目录下的进程不在我们的
// 注册簿里，升级完不会被拉回来，是用户要同意的事。
const _NG_CONFIRM_PREFIX =
  "会先停掉本机所有 NanoGhost.exe 进程（包括其它安装目录下的）。\n" +
  "其它目录下的进程不会被自动重新启动。\n\n"

function ngUpdateConfirm(action) {
  return confirm(`${action}\n\n${_NG_CONFIRM_PREFIX}继续？`)
}

function ngUpdateRestartChecked() {
  const e = _ngEls
  return !!(e && e.restart && e.restart.checked)
}

function ngUpdateSetToast(msg) {
  if (typeof setToast === "function") setToast(msg)
}

function openNanoghostUpdateModal() {
  if (_ngEls) return // 已经开着

  const overlay = document.createElement("div")
  overlay.style.position = "fixed"
  overlay.style.inset = "0"
  overlay.style.background = "rgba(0,0,0,0.35)"
  overlay.style.display = "flex"
  overlay.style.alignItems = "center"
  overlay.style.justifyContent = "center"
  overlay.style.zIndex = "9999"

  const card = document.createElement("div")
  card.style.width = "720px"
  card.style.maxWidth = "94vw"
  card.style.maxHeight = "90vh"
  card.style.overflow = "auto"
  card.style.border = "1px solid var(--border)"
  card.style.background = "var(--bg)"
  card.style.borderRadius = "16px"
  card.style.boxShadow = "var(--shadow)"
  card.style.padding = "16px"

  const title = document.createElement("div")
  title.style.fontWeight = "750"
  title.style.marginBottom = "12px"
  title.textContent = "NanoGhost 升级 / 安装"

  // 程序路径
  const rowProg = document.createElement("div")
  rowProg.className = "row"
  const progLabel = document.createElement("span")
  progLabel.className = "hint"
  progLabel.style.minWidth = "44px"
  progLabel.textContent = "程序"
  const prog = document.createElement("code")
  prog.style.flex = "1"
  prog.style.minWidth = "260px"
  prog.style.fontSize = "12px"
  prog.style.wordBreak = "break-all"
  const btnReparse = document.createElement("button")
  btnReparse.textContent = "重新解析"
  const btnPick = document.createElement("button")
  btnPick.textContent = "手动指定"
  rowProg.appendChild(progLabel)
  rowProg.appendChild(prog)
  rowProg.appendChild(btnReparse)
  rowProg.appendChild(btnPick)

  // 版本
  const rowVer = document.createElement("div")
  rowVer.className = "row"
  const verLabel = document.createElement("span")
  verLabel.className = "hint"
  verLabel.style.minWidth = "44px"
  verLabel.textContent = "版本"
  const ver = document.createElement("span")
  ver.style.fontSize = "13px"
  rowVer.appendChild(verLabel)
  rowVer.appendChild(ver)

  // 状态
  const rowState = document.createElement("div")
  rowState.className = "row"
  const stateLabel = document.createElement("span")
  stateLabel.className = "hint"
  stateLabel.style.minWidth = "44px"
  stateLabel.textContent = "状态"
  const pill = document.createElement("span")
  pill.className = "pill"
  pill.textContent = "空闲"
  const step = document.createElement("span")
  step.className = "hint"
  rowState.appendChild(stateLabel)
  rowState.appendChild(pill)
  rowState.appendChild(step)

  // 进度条
  const bar = document.createElement("div")
  bar.className = "ngBar"
  const fill = document.createElement("i")
  bar.appendChild(fill)

  // 错误
  const err = document.createElement("div")
  err.style.display = "none"
  err.style.marginTop = "8px"
  err.style.padding = "8px 10px"
  err.style.borderRadius = "10px"
  err.style.border = "1px solid rgba(255,120,110,0.45)"
  err.style.background = "rgba(255,120,110,0.10)"
  err.style.fontSize = "12px"
  err.style.whiteSpace = "pre-wrap"
  err.style.wordBreak = "break-all"

  // 日志
  const log = document.createElement("div")
  log.className = "ngLog"
  log.style.marginTop = "10px"

  // 勾选框
  const rowRestart = document.createElement("div")
  rowRestart.className = "row"
  rowRestart.style.marginTop = "10px"
  const restart = document.createElement("input")
  restart.type = "checkbox"
  restart.checked = true
  restart.id = "ngUpdateRestart"
  const restartLabel = document.createElement("label")
  restartLabel.htmlFor = "ngUpdateRestart"
  restartLabel.style.fontSize = "12px"
  restartLabel.textContent = "升级后自动重启之前运行的实例"
  rowRestart.appendChild(restart)
  rowRestart.appendChild(restartLabel)

  // 按钮
  const rowBtns = document.createElement("div")
  rowBtns.className = "row"
  rowBtns.style.marginTop = "14px"
  rowBtns.style.justifyContent = "flex-end"
  const btnCheck = document.createElement("button")
  btnCheck.textContent = "检查更新"
  const btnUpdate = document.createElement("button")
  btnUpdate.textContent = "升级"
  const btnInstall = document.createElement("button")
  btnInstall.textContent = "下载并安装"
  const btnClose = document.createElement("button")
  btnClose.textContent = "关闭"
  rowBtns.appendChild(btnCheck)
  rowBtns.appendChild(btnUpdate)
  rowBtns.appendChild(btnInstall)
  rowBtns.appendChild(btnClose)

  card.appendChild(title)
  card.appendChild(rowProg)
  card.appendChild(rowVer)
  card.appendChild(rowState)
  card.appendChild(bar)
  card.appendChild(err)
  card.appendChild(log)
  card.appendChild(rowRestart)
  card.appendChild(rowBtns)
  overlay.appendChild(card)
  document.body.appendChild(overlay)

  _ngEls = {
    overlay, prog, ver, pill, step, bar, fill, err, log,
    restart, btnCheck, btnUpdate, btnInstall,
  }

  // close 会删掉自己 —— 不删的话每开一次弹窗就多挂一个 keydown 监听
  function onKey(ev) {
    if (ev.key === "Escape") close()
  }

  function close() {
    // 定时器一定要清：不清的话关掉弹窗之后接口会被一直轮询下去
    ngUpdateStopPolling()
    document.removeEventListener("keydown", onKey)
    _ngEls = null
    overlay.remove()
  }
  document.addEventListener("keydown", onKey)

  async function guard(fn) {
    try {
      ngUpdateSetToast("")
      await fn()
    } catch (e) {
      // apiJson 抛的是 "状态码 detail"，detail 里就是给人看的中文
      ngUpdateSetToast(String(e))
    }
  }

  btnClose.addEventListener("click", close)
  overlay.addEventListener("click", (ev) => {
    if (ev.target === overlay) close()
  })

  btnReparse.addEventListener("click", () =>
    guard(async () => {
      await ngUpdateReloadInfo()
      ngUpdateSetToast("已重新解析")
    })
  )

  btnPick.addEventListener("click", () =>
    guard(async () => {
      const cur = (_ngInfo || {}).program || ""
      const p = prompt("NanoGhost 可执行文件路径（留空 = 回到自动解析）", cur)
      if (p === null) return
      _ngInfo = await ngUpdateProgramPut(p.trim())
      ngUpdateRenderInfo()
      ngUpdateSetToast(p.trim() ? "已写入配置" : "已清除显式指定")
    })
  )

  btnCheck.addEventListener("click", () =>
    guard(async () => {
      btnCheck.disabled = true
      step.textContent = "正在检查新版本…"
      try {
        const r = await ngUpdateCheck(true)
        _ngInfo = Object.assign({}, _ngInfo, {
          latest_version: r.version || "",
        })
        ngUpdateRenderVersion({})
        ngUpdateRenderInfo()
        ngUpdateSetToast(`最新版本 ${r.version || "未知"}`)
      } finally {
        step.textContent = ""
        btnCheck.disabled = false
      }
    })
  )

  btnUpdate.addEventListener("click", () =>
    guard(async () => {
      if (!ngUpdateConfirm("确认升级 NanoGhost？")) return
      const st = await ngUpdateStart(ngUpdateRestartChecked())
      ngUpdateRender(st)
      ngUpdateStartPolling()
    })
  )

  btnInstall.addEventListener("click", () =>
    guard(async () => {
      if (!ngUpdateConfirm("确认下载并安装 NanoGhost？")) return
      const st = await ngInstallStart(ngUpdateRestartChecked())
      ngUpdateRender(st)
      ngUpdateStartPolling()
    })
  )

  // 打开时先渲染一次本地信息（不打网络），再读一次服务端状态 —— 如果控制台
  // 刚被重启过，这一步会把"结果未知"如实显示出来
  ngUpdateRenderInfo()
  ngUpdateRenderVersion({})
  guard(async () => {
    await ngUpdateReloadInfo()
    const st = await ngUpdateStatus()
    ngUpdateRender(st)
    if (ngUpdateIsRunning(st.phase)) ngUpdateStartPolling()
  })
}

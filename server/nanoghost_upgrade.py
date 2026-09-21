"""NanoGhost 升级 / 安装编排。

这是全仓第一个"慢活儿"：下载 70MB+、等进程退出、轮询覆盖脚本的结果文件 ——
每一步都是分钟级。所以这里只有一个 POST 起任务 + 一个 GET 读状态，
进度全靠前端定时拉。

**轮询是硬约束，不是偏好**：前端的 apiJson 做的是 res.text() + JSON.parse
（server/static/js/helpers.js:9-26，写死了 JSON content-type），结构上不可能
消费 SSE / NDJSON。想改成流式推送得先改那个函数，那会影响所有调用点。

这个模块**不 import server.app**（app.py 要 import 它挂路由，会成环）。它需要的
两样东西 —— "程序在哪"和"把 gateway 拉起来" —— 由 app.py 在导入后通过
configure() 注入。测试也走同一个注入口。

关于"为什么要自己解析程序路径"：控制台**启动哪个程序**和**升级覆盖哪个程序**
必须是同一个答案。分开的后果是最难查的一类故障 —— 点完更新、重启后还是旧版本，
而且没有任何报错，因为控制台压根没启动被更新的那个程序。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path

import httpx

from server.processes import find_nanoghost_processes
from server.processes import is_pid_running
from server.processes import kill_pid_tree
from server.registry import load_registry
from server.releases import ReleaseError
from server.releases import cached_latest
from server.releases import compare_versions
from server.releases import fetch_latest

logger = logging.getLogger(__name__)

# ---- 阶段 ----------------------------------------------------------------
PHASE_IDLE = "idle"
PHASE_PREFLIGHT = "preflight"
PHASE_CHECKING = "checking"
PHASE_STOPPING = "stopping"
PHASE_APPLYING = "applying"
PHASE_VERIFYING = "verifying"
PHASE_RESTARTING = "restarting"
PHASE_DONE = "done"
PHASE_FAILED = "failed"

# 这些阶段意味着"有活儿在跑"。控制台重启后如果盘上停在这里而线程已经不在了，
# 结果就是未知的 —— 覆盖脚本是脱离进程组的，它可能还在跑，也可能早就失败了。
_IN_FLIGHT = {
    PHASE_PREFLIGHT, PHASE_CHECKING, PHASE_STOPPING,
    PHASE_APPLYING, PHASE_VERIFYING, PHASE_RESTARTING,
}

LOG_LIMIT = 200

# 覆盖脚本等程序退出最多 60 秒（update.py），加上解压 70MB 和 robocopy，
# 给它 4 分钟。超时不是失败 —— 是这个时长内没等到结果，文案里要如实说。
RESULT_TIMEOUT = 240.0
CMD_TIMEOUT = 180.0
INSTALL_TIMEOUT = 300.0
DOWNLOAD_TIMEOUT = 120.0

# 78MB 升级包 + staging + 63MB 安装包，实打实要两百多兆。留到 500MB 是为了给
# 解压峰值和日志留余量。
DISK_MIN_FREE = 500 * 1024 * 1024


class UpgradeError(Exception):
    """编排过程中的可读失败。消息直接给界面显示，不要让上层再包一层技术前缀。"""


class UpgradeBusy(Exception):
    """已有任务在跑。"""


# ---------------------------------------------------------------------------
# 注入的上下文
# ---------------------------------------------------------------------------

_CTX: dict = {}


def configure(*, config_path: Path, registry_path: Path, data_dir: Path,
              locate_program, service_start) -> None:
    """由 app.py 在导入后调用。

    locate_program() -> (Path | None, 来源标记)，显式配置指不到文件时抛
        HTTPException(400)（app.py 的那份实现如此）。
    service_start(runtime, name, service) -> dict，即 app.py 的
        instance_service_start —— 直接调函数而不是走 HTTP，省掉一层自己调自己。
    """
    _CTX.update(
        config_path=Path(config_path),
        registry_path=Path(registry_path),
        data_dir=Path(data_dir),
        locate_program=locate_program,
        service_start=service_start,
    )


def _ctx(key: str):
    if key not in _CTX:
        raise UpgradeError("升级模块尚未初始化（app.py 没调 configure）")
    return _CTX[key]


# ---------------------------------------------------------------------------
# 状态
# ---------------------------------------------------------------------------

_STATE_LOCK = threading.RLock()
_THREAD: threading.Thread | None = None
_LOADED = False
_STATE: dict = {}


def _empty_state() -> dict:
    return {
        "ok": True,
        "mode": "",
        "phase": PHASE_IDLE,
        "step": "",
        "progress": None,          # 0..100，None = 不确定进度（进度条走动画）
        "log": [],
        "error": None,
        "program": "",
        "program_source": "",
        "from_version": "",
        "to_version": "",
        "stopped": [],
        "restarted": [],
        "started_at": None,
        "finished_at": None,
    }


def _job_path() -> Path:
    return Path(_ctx("data_dir")) / "nanoghost_update" / "job.json"


def _persist(st: dict) -> None:
    """状态落盘。

    为的是"控制台自己重启"这一种情况：线程随进程死了，但 NanoGhost 的覆盖脚本
    是脱离进程组的，它还在跑。这时候光看内存会显示一个永远不动的"正在应用"。
    """
    p = _job_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("写升级任务状态失败: %s", e)


def _ensure_loaded() -> None:
    """首次访问时把盘上的状态捡回来。

    盘上停在 in-flight 阶段而本进程没有线程在跑 —— 只可能是上一个控制台进程
    留下的。这时**宁可说不知道，也不要假装知道**：覆盖脚本可能已经成功、
    可能失败、也可能还在写文件，内存里的东西一样都判断不了。
    """
    global _LOADED, _STATE
    if _LOADED:
        return
    _LOADED = True
    _STATE = _empty_state()
    p = _job_path()
    if not p.is_file():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(data, dict):
        return
    st = _empty_state()
    st.update({k: v for k, v in data.items() if k in st})
    if st.get("phase") in _IN_FLIGHT:
        st["phase"] = PHASE_FAILED
        st["error"] = ("控制台重启过，本次升级的结果未知 —— 覆盖脚本可能已经成功，"
                       "也可能没有。请用界面上的「检查更新」或命令行 "
                       "`NanoGhost.exe --version` 核对实际版本。")
        _STATE = st
        _persist(st)
        return
    _STATE = st


def status() -> dict:
    with _STATE_LOCK:
        _ensure_loaded()
        return json.loads(json.dumps(_STATE, ensure_ascii=False))


def _reset(st: dict, mode: str) -> None:
    st.clear()
    st.update(_empty_state())
    st["mode"] = mode
    st["phase"] = PHASE_PREFLIGHT
    st["started_at"] = int(time.time())


def _set_phase(st: dict, phase: str, step: str, progress=None) -> None:
    with _STATE_LOCK:
        st["phase"] = phase
        st["step"] = step
        st["progress"] = progress
        _persist(st)


def _log(st: dict, line: str) -> None:
    line = str(line).rstrip()
    if not line:
        return
    with _STATE_LOCK:
        log = st.setdefault("log", [])
        log.append(line)
        if len(log) > LOG_LIMIT:
            del log[: len(log) - LOG_LIMIT]


# ---------------------------------------------------------------------------
# 跨进程锁
# ---------------------------------------------------------------------------
#
# in-process 锁挡不住第二个 OpenObstrator（本项目 dev server 和 frozen exe 会在
# 同一台机器上并存）。两个控制台同时跑升级的后果不是"慢一点"：两边都会去停
# gateway、都去起覆盖脚本，文件被占用时覆盖失败，然后各自报出互相矛盾的结论。
#
# 放在 nanoghost_root 下而不是 DATA_DIR —— 被锁的资源（那些实例、那个安装目录）
# 是共享的，而 DATA_DIR 在 frozen 和 dev 下取值不同。

def _lock_path() -> Path | None:
    try:
        from server.settings import resolve_nanoghost_root
        root = resolve_nanoghost_root(config_path=Path(_ctx("config_path")))
    except Exception:
        return None
    return Path(root) / "openobstrator_update.lock"


def _acquire_lock() -> Path | None:
    p = _lock_path()
    if p is None:
        return None              # 拿不到路径就别拿锁，总比拦住所有升级强
    for _ in range(2):
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "started_at": int(time.time())}, f)
            return p
        except FileExistsError:
            owner = None
            try:
                owner = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
            pid = (owner or {}).get("pid")
            try:
                alive = bool(pid) and is_pid_running(int(pid))
            except (TypeError, ValueError):
                alive = False
            if alive:
                raise UpgradeBusy(
                    f"另一个控制台（pid {pid}）正在执行升级任务。等它结束，"
                    f"或者确认那个进程已经不在之后再试。"
                )
            # owner 已经死了：锁是陈的，抢过来
            try:
                p.unlink()
            except OSError:
                raise UpgradeBusy("升级锁文件被占用且删不掉，请手工删除后重试。")
        except OSError as e:
            logger.warning("建升级锁失败（继续执行）: %s", e)
            return None
    return None


def _release_lock(p: Path | None) -> None:
    if p is None:
        return
    try:
        p.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 外部命令
# ---------------------------------------------------------------------------

def _run(argv: list[str], *, env: dict | None = None, timeout: float = CMD_TIMEOUT):
    """跑一条命令，返回 (returncode, stdout+stderr)。"""
    try:
        r = subprocess.run(
            argv, capture_output=True, text=True, check=False,
            timeout=timeout, env=env, errors="replace",
            stdin=subprocess.DEVNULL,   # 别让子进程等 stdin：曾因 NanoGhost.exe update --check
                                        # 末尾的 input("按任意键退出") 而空等 180s 超时
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # 别再闪控制台窗口
        )
    except subprocess.TimeoutExpired:
        return 124, f"命令超时（{int(timeout)} 秒）: {' '.join(argv)}"
    except OSError as e:
        return 1, str(e)
    out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
    return int(r.returncode), out


def _parse_json_line(text: str) -> dict | None:
    """从命令输出里挑出那一行 JSON。

    --json 承诺"输出只剩一行 JSON"，但程序启动横幅、警告都可能混进来。从后往前
    找第一个能解析成对象的行 —— 退路留着，不然一条无关的 stderr 警告就能让整个
    检查失败。
    """
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except Exception:
            continue
        if isinstance(data, dict):
            return data
    return None


def _pe_file_version(prog: Path) -> str:
    """从 PE 版本资源里读 FileVersion（走 version.dll，**不启动进程**）。"""
    try:
        import ctypes
        from ctypes import wintypes

        size = ctypes.windll.version.GetFileVersionInfoSizeW(str(prog), None)
        if not size:
            return ""
        buf = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(str(prog), 0, size, buf):
            return ""
        val = ctypes.c_void_p()
        length = wintypes.UINT()
        if not ctypes.windll.version.VerQueryValueW(
                buf, "\\", ctypes.byref(val), ctypes.byref(length)) or not val:
            return ""

        class _FixedFileInfo(ctypes.Structure):
            _fields_ = [("dwSignature", wintypes.DWORD),
                        ("dwStrucVersion", wintypes.DWORD),
                        ("dwFileVersionMS", wintypes.DWORD),
                        ("dwFileVersionLS", wintypes.DWORD)]

        info = ctypes.cast(val, ctypes.POINTER(_FixedFileInfo)).contents
        ms, ls = info.dwFileVersionMS, info.dwFileVersionLS
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:                     # noqa: BLE001 - 读不到就退回空串
        return ""


def _read_version(prog: Path) -> str:
    """读程序的版本号。**不启动进程**。

    历史实现是 `NanoGhost.exe --version`：它是个控制台程序，末尾还有
    input("按任意键退出")，每 spawn 一次都要跟它抢 stdin、还闪一个控制台窗口
    （见 _run 的注释）。版本号本来就在文件里 —— 直接读，最快也最稳。
    """
    for cand in (prog.parent / "_internal" / "VERSION", prog.parent / "VERSION"):
        try:
            if cand.is_file():
                v = cand.read_text(encoding="utf-8", errors="ignore").strip()
                if v:
                    return v.lstrip("vV")
        except OSError:
            pass
    return _pe_file_version(prog)


def _env_for_update() -> dict:
    """升级命令的环境变量。

    结果文件和日志路径**必须显式指定**，不能靠 %TEMP% 的默认值：实测默认路径会
    解析成 8.3 短路径，而且服务账号下的 %TEMP% 可能是**另一个账号的** temp ——
    那样我们会在一个永远不会出现文件的目录里等 4 分钟。
    """
    env = dict(os.environ)
    env["NANOGHOST_CALLER"] = "openobstrator"
    data = Path(_ctx("data_dir"))
    env["NANOGHOST_UPDATE_RESULT"] = str(data / "ng_update_result.txt")
    env["NANOGHOST_UPDATE_LOG"] = str(data / "ng_update.log")
    # 启动横幅的自动版本检查对我们没意义，还会往 stdout 里混东西
    env["NANOGHOST_DISABLE_AUTO_UPDATE"] = "true"
    return env


def _result_path() -> Path:
    return Path(_ctx("data_dir")) / "ng_update_result.txt"


def _update_log_path() -> Path:
    return Path(_ctx("data_dir")) / "ng_update.log"


# ---------------------------------------------------------------------------
# 进程
# ---------------------------------------------------------------------------

def _gateway_instances() -> list[dict]:
    """注册簿里登记的、**确实在跑**的 nanoghost gateway。

    注册簿不可信 —— 实测有整份记录全是死 pid 的情况。所以每条都拿
    is_pid_running 复核，只认 tasklist 说了算的。
    """
    reg = load_registry(Path(_ctx("registry_path")))
    out: list[dict] = []
    try:
        instances = reg["runtimes"]["nanoghost"]["instances"]
    except Exception:
        return out
    if not isinstance(instances, dict):
        return out
    for name, procs in instances.items():
        if not isinstance(procs, dict):
            continue
        rec = procs.get("gateway")
        if not isinstance(rec, dict):
            continue
        pid = rec.get("pid")
        try:
            pid = int(pid) if pid else 0
        except (TypeError, ValueError):
            pid = 0
        if pid and is_pid_running(pid):
            out.append({"name": str(name), "pid": pid})
    return out


def _same_path(a, b) -> bool:
    try:
        return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))
    except Exception:
        return False


def _stop_programs(st: dict, prog: Path | None) -> list[dict]:
    """停掉本机所有 NanoGhost.exe，返回被停的 gateway 列表（用于事后拉回）。

    为什么要**机器级**全停（而不是只停这次要覆盖的那个目录）：

    覆盖脚本的等待循环是
        tasklist /FI "IMAGENAME eq %EXE%" | find /I "%EXE%"
    （update.py:_write_update_bat），**按进程名匹配，不区分目录**。也就是说只要
    机器上还有任何一个别的目录下的 NanoGhost.exe 活着，这 60 次循环就会全部跑完，
    然后报 `FAIL:timeout` —— 一个指向"程序没能退出"、但其实是无关进程造成的失败。
    所以"停干净"不是保守，是这条链路的硬要求。

    代价要如实说：别的安装目录下的进程不在我们的注册簿里，事后**不会**被拉回来。
    界面上的 confirm 文案必须写明这一点。

    `python run.py` 起的 cli / feishu 不锁 exe、也不叫 NanoGhost.exe，不在处理
    范围里（feishu 槽正在被改成转发给 gateway）。
    """
    gateways = _gateway_instances()
    killed: set[int] = set()
    for g in gateways:
        kill_pid_tree(g["pid"])
        killed.add(g["pid"])
        _log(st, f"已停止 gateway 实例 {g['name']} (pid {g['pid']})")
        st.setdefault("stopped", []).append(
            {"name": g["name"], "pid": g["pid"],
             "detail": f"gateway 实例 {g['name']} (pid {g['pid']})"}
        )

    # 注册簿不可信（实测有整份记录全是死 pid 的情况），所以再用 psutil 按进程名
    # 扫一遍机器 —— 手工起过的、注册簿被删过的野进程都在这一网里。
    for p in find_nanoghost_processes(None):
        if p["pid"] in killed:
            continue
        kill_pid_tree(p["pid"])
        killed.add(p["pid"])
        where = p["exe"] or "路径未知"
        target = "本次要覆盖的目录" if (prog and _same_path(p["exe"], prog)) else "其它位置"
        _log(st, f"已停止 NanoGhost 进程 (pid {p['pid']}, {where}, {target})")
        st.setdefault("stopped", []).append(
            {"name": "", "pid": p["pid"],
             "detail": f"未登记进程 (pid {p['pid']}, {where}, {target})"}
        )

    # 兜底再按映像名杀一次：psutil 读不到进程名/路径的情况（别的账号、权限受限）
    # 它在前面两轮里是隐形的，而它照样能把上面那个等待循环拖到超时。
    # 没有匹配时 taskkill 返回 1，属于正常，不用管。
    # 这里**必须无条件执行**，不能拿 find_nanoghost_processes() 做前置判断 ——
    # 那个函数依赖 psutil，一旦它读不到（别的账号 / 权限受限 / 被禁用），判断就成了
    # False，兜底强杀被直接跳过；于是 NanoGhost 仍在跑，安装器覆盖 NanoGhost.exe 时
    # 因文件被占用而失败（实测 exit 1 / exit 5，且安装日志根本不生成）。
    # 改成「先杀、再复核」，直到真的没有 NanoGhost 进程为止。
    _killed_by_name = False
    deadline = time.time() + 10.0
    while True:
        rc_kill, _out_kill = _run(["taskkill", "/F", "/IM", "NanoGhost.exe", "/T"], timeout=30)
        if rc_kill == 0:
            _killed_by_name = True
        try:
            remain = find_nanoghost_processes(None)
        except Exception:
            remain = []
        if not remain:
            break
        if time.time() >= deadline:
            _log(st, f"警告：仍有 {len(remain)} 个 NanoGhost 进程没停掉，安装可能因文件占用失败")
            break
        time.sleep(0.5)

    if not st.get("stopped") and _killed_by_name:
        st.setdefault("stopped", []).append(
            {"name": "", "pid": 0, "detail": "按映像名强杀 NanoGhost.exe"}
        )
        _log(st, "已按映像名强杀 NanoGhost.exe")

    if not st.get("stopped"):
        _log(st, "没有正在运行的 NanoGhost 进程")

    # 文件锁不是立刻释放的，给系统一点时间。紧接着就写会偶发 FAIL:copy。
    if st.get("stopped"):
        time.sleep(1.5)
    return gateways


def _restart_gateways(st: dict, gateways: list[dict], restart: bool) -> None:
    """把停掉的 gateway 拉回来。

    飞书 worker 不用单独重启 —— gateway 每次启动都会重读 channel_directory.json
    并孵化已启用的通道（gateway_server.py:_auto_start_workers），所以把 gateway
    拉回来，worker 自己就回来了。
    """
    if not restart:
        _log(st, "按设置跳过自动重启")
        return
    if not gateways:
        return
    start = _ctx("service_start")
    for g in gateways:
        try:
            res = start("nanoghost", g["name"], "gateway")
            pid = int((res or {}).get("pid") or 0)
        except Exception as e:
            st.setdefault("restarted", []).append(
                {"name": g["name"], "pid": None, "ok": False, "detail": f"实例 {g['name']} 启动失败: {e}"}
            )
            _log(st, f"实例 {g['name']} 启动失败: {e}")
            continue
        # instance_service_start 里那个 time.sleep(3) 之后**没有存活检查**，
        # 崩掉的 gateway 也会被记成"在跑"。那一份是共享函数，不去动它，在编排层
        # 兜住：如实汇报，别把没起来的说成起来了。
        alive = bool(pid) and is_pid_running(pid)
        st.setdefault("restarted", []).append({
            "name": g["name"], "pid": pid, "ok": alive,
            "detail": (f"实例 {g['name']} 已启动 (pid {pid})" if alive
                       else f"实例 {g['name']} 启动后进程立刻退出了，请查日志"),
        })
        _log(st, f"实例 {g['name']} 已启动 (pid {pid})" if alive
             else f"实例 {g['name']} 启动后进程立刻退出了")


# ---------------------------------------------------------------------------
# 覆盖结果
# ---------------------------------------------------------------------------

def _tail_update_log(st: dict, seen: int) -> int:
    """把覆盖脚本的日志尾巴贴进状态里。

    这是唯一的**真实进度**来源 —— 覆盖脚本会往里写英文进度行。它同时是排查
    FAIL:copy 之类问题的第一现场，所以哪怕只为了留痕也该贴。
    """
    p = _update_log_path()
    if not p.is_file():
        return seen
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return seen
    lines = text.splitlines()
    if len(lines) == seen:
        return seen
    for line in lines[seen:]:
        _log(st, line)
    return len(lines)


def _await_result(st: dict) -> str:
    """等覆盖脚本写结果。

    返回值是结果文件的内容，超时返回空串。按 UPDATING.md：
        "OK"          覆盖成功
        "FAIL:timeout"  程序没能在 60 秒内退出
        "FAIL:expand"   解压失败（下载损坏 / 磁盘不足）
        "FAIL:copy"     写安装目录失败（exe 仍被占用）
    三种 FAIL 都意味着**没写进去**，可以安全重试 —— 文案要这么说，否则用户会
    去重装。
    """
    path = _result_path()
    deadline = time.time() + RESULT_TIMEOUT
    seen = 0
    while time.time() < deadline:
        seen = _tail_update_log(st, seen)
        if path.is_file():
            try:
                txt = path.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                txt = ""
            if txt:
                return txt
        time.sleep(1.0)
    _tail_update_log(st, seen)
    return ""


_FAIL_HINTS = {
    "timeout": "程序没能在 60 秒内退出，文件一直被占用。多半是还有 NanoGhost 进程在跑，"
               "或者是别的管理器又把它拉起来了。",
    "expand": "升级包解压失败。可能是下载损坏，也可能是磁盘空间不足 —— 后者会伪装成"
              "「包损坏」，先看一眼目标盘的剩余空间。",
    "copy": "写安装目录失败，exe 仍被占用。确认没有 NanoGhost 进程在跑，再试一次。",
}


def _fail_text(txt: str) -> str:
    stage = txt.split(":", 1)[1].strip().lower() if ":" in txt else ""
    hint = _FAIL_HINTS.get(stage, "")
    base = f"覆盖失败：{txt}"
    if hint:
        base += f"。{hint}"
    base += "（这次覆盖没有写进去，可以安全重试。）"
    return base


# ---------------------------------------------------------------------------
# 安装包下载
# ---------------------------------------------------------------------------

def _free_space_message(path: Path) -> str | None:
    """盘空间预检。

    空间不足会一路走到解压阶段才炸，而那时候的报错是 FAIL:expand —— 文档说那
    指向"升级包损坏"。这个症状极具误导性：人会去重新下载，而不是去清磁盘。
    所以宁可提前查，并用专门的文案指出来。
    """
    try:
        import psutil
    except Exception:
        return None
    probe = path
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        free = psutil.disk_usage(str(probe)).free
    except Exception:
        return None
    if free >= DISK_MIN_FREE:
        return None
    drive = str(probe)[:3]
    return (f"{drive} 只剩 {free / 1024 / 1024:.0f} MB 可用空间，安装至少需要 "
            f"{DISK_MIN_FREE / 1024 / 1024:.0f} MB。请先清理磁盘 —— 空间不足最后"
            f"会伪装成「安装包损坏」报出来。")


def _strip_zone_identifier(path: Path) -> None:
    """去掉 Mark-of-the-Web。

    下载来的 exe 默认带 zone identifier，SmartScreen / 部分 AV 会因此拦掉静默
    运行 —— 表现成几秒内非 0 退出、而且没有任何日志，极难判断。下载的是官方
    release 资产，去掉这个标记是我们自己的决定，写下原因以免被当成可疑操作。
    """
    try:
        os.remove(str(path) + ":Zone.Identifier")
    except OSError:
        pass


def _download(url: str, dest: Path, st: dict, *,
              expected_size: int = 0, expected_sha256: str = "") -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    if tmp.exists():
        tmp.unlink()
    got = 0
    try:
        with httpx.stream("GET", url, timeout=DOWNLOAD_TIMEOUT,
                          follow_redirects=True) as r:
            if r.status_code >= 400:
                raise UpgradeError(f"下载安装包失败：HTTP {r.status_code}（{url}）")
            total = int(r.headers.get("Content-Length") or 0)
            with open(tmp, "wb") as f:
                for chunk in r.iter_bytes(1024 * 256):
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        _set_phase(st, PHASE_APPLYING,
                                   f"正在下载安装包… {got / 1024 / 1024:.0f} / "
                                   f"{total / 1024 / 1024:.0f} MB",
                                   progress=int(got * 100 / total))
    except UpgradeError:
        tmp.unlink(missing_ok=True)
        raise
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise UpgradeError(f"下载安装包失败：{e}。检查本机网络，或在 "
                           f"~/.nanoghost/update.json 里配 download_base 换源。")

    if got < 1024 * 1024:
        tmp.unlink(missing_ok=True)
        raise UpgradeError(f"下载到的文件只有 {got} 字节，明显不是安装包（可能拿到"
                           f"了一个错误页）。稍后重试。")

    # Inno Setup 装出来的是 PE 可执行文件，魔数是 MZ —— **不是** zip 的 PK。
    # 照抄 update.py 的 PK 检查会在这里把好文件判成坏的。
    head = tmp.open("rb").read(2)
    if head != b"MZ":
        tmp.unlink(missing_ok=True)
        raise UpgradeError("下载到的不是 Windows 可执行文件（开头不是 MZ）。"
                           "多半是网络中间返回了错误页，稍后重试。")

    # 官方 release 带 size + sha256(digest)，逐字节对上再放行 —— 半截包、被中间设备
    # 换过的包在这里就拦下，而不是等安装器几秒后莫名退出、还什么都不说。
    if expected_size and got != expected_size:
        tmp.unlink(missing_ok=True)
        raise UpgradeError(
            f"下载不完整：拿到 {got} 字节，官方是 {expected_size} 字节"
            f"（差 {expected_size - got}）。网络中断或被代理改写，请重试。")
    if expected_sha256:
        digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
        if digest != expected_sha256:
            tmp.unlink(missing_ok=True)
            raise UpgradeError(
                f"安装包 sha256 校验失败：本地 {digest[:12]}…，官方 {expected_sha256[:12]}…。"
                f"包已损坏或被篡改，已丢弃。")

    tmp.replace(dest)
    _strip_zone_identifier(dest)


# ---------------------------------------------------------------------------
# 流程
# ---------------------------------------------------------------------------

def _do_update(st: dict, restart: bool) -> None:
    prog, source = _ctx("locate_program")()
    if prog is None:
        raise UpgradeError("本机没有找到 NanoGhost 程序。用「下载并安装」装一个，"
                           "或者在配置里显式指定 nanoghost_program。")
    prog = Path(prog)
    st["program"] = str(prog)
    st["program_source"] = source

    _set_phase(st, PHASE_PREFLIGHT, "正在读取当前版本…")
    from_version = _read_version(prog)
    st["from_version"] = from_version
    _log(st, f"目标程序: {prog}")
    _log(st, f"当前版本: {from_version or '读不出来'}")
    if not from_version:
        raise UpgradeError(f"没能从 {prog} 读出版本号（--version 没有输出）。"
                           f"这个程序可能已经损坏，请用安装包重装。")

    _set_phase(st, PHASE_CHECKING, "正在检查新版本…")
    env = _env_for_update()
    rc, out = _run([str(prog), "update", "--check", "--json"], env=env)
    payload = _parse_json_line(out)
    if payload is None and rc != 0:
        raise UpgradeError(f"检查更新失败（退出码 {rc}）。这**不是**说你装的版本坏了 ——"
                           f"多一半是网络到不了 GitHub。{out.strip()[:200]}")
    latest = str((payload or {}).get("latest_version") or "")
    if latest:
        st["to_version"] = latest
        _log(st, f"最新版本: {latest}")

    # 退出码约定见 UPDATING.md：0 已是最新 / 10 有新版本 / 1 检查失败。
    if rc == 1:
        raise UpgradeError(f"检查更新失败（退出码 1）。这**不是**说你装的版本坏了 ——"
                           f"是这次没查成（网络、DNS、超时都可能）。{out.strip()[:200]}")
    if rc == 0 or (payload is not None and not payload.get("update_available")):
        _log(st, "已经是最新版本，不需要升级")
        return

    if not latest:
        raise UpgradeError("程序说有新版本，却没给出最新版本号，没法核对。稍后重试。")

    gateways = _stop_programs(st, prog)
    _set_phase(st, PHASE_STOPPING, "已停止 NanoGhost 进程", progress=None)

    _set_phase(st, PHASE_APPLYING, "正在覆盖安装文件…", progress=None)
    result_path = _result_path()
    try:
        result_path.unlink()
    except OSError:
        pass
    rc, out = _run([str(prog), "update", "--yes", "--no-restart", "--json"], env=env)
    _log(st, f"update 退出码 {rc}")
    if rc == 1:
        raise UpgradeError(f"启动覆盖流程失败（退出码 1）。{out.strip()[:240]}")

    if rc == 10:
        # exit 10 只表示**已开始**：真正的覆盖要等 NanoGhost 退出、文件锁释放
        # 之后才发生。所以必须等结果文件，不能拿 10 当完成。
        txt = _await_result(st)
        if not txt:
            raise UpgradeError(
                f"等了 {int(RESULT_TIMEOUT)} 秒也没等到覆盖结果（{result_path}）。"
                f"覆盖脚本可能还在跑 —— 请稍后用「检查更新」或命令行 "
                f"`NanoGhost.exe --version` 核对实际版本，别直接重试。")
        _log(st, f"覆盖结果: {txt}")
        if txt.upper().startswith("FAIL"):
            raise UpgradeError(_fail_text(txt))
    elif rc == 0:
        _log(st, "程序报告已经是最新，什么都没做")
        st["to_version"] = st.get("to_version") or from_version
    else:
        raise UpgradeError(f"启动覆盖流程失败（退出码 {rc}）。{out.strip()[:240]}")

    _set_phase(st, PHASE_VERIFYING, "正在核对版本…")
    now_version = _read_version(prog)
    _log(st, f"覆盖后版本: {now_version or '读不出来'}")
    if not now_version:
        raise UpgradeError(f"覆盖完成了，但读不出 {prog} 的版本号。程序可能被写坏了，"
                           f"请用安装包修复。")
    if st.get("to_version") and compare_versions(now_version, st["to_version"]) != 0:
        # 这是最要命的一种：覆盖脚本说 OK、但版本没变。用户会以为升级成功了。
        raise UpgradeError(f"版本没变（还是 {now_version}，期望 {st['to_version']}）——"
                           f"覆盖没有真正生效。检查安装目录是不是被别的进程占用，"
                           f"或者程序装在了别的位置。")
    st["from_version"], st["to_version"] = from_version, now_version

    _set_phase(st, PHASE_RESTARTING, "正在重启之前的实例…")
    _restart_gateways(st, gateways, restart)


def _do_install(st: dict, restart: bool) -> None:
    _set_phase(st, PHASE_PREFLIGHT, "正在查最新版本…")
    try:
        rel = fetch_latest()
    except ReleaseError as e:
        raise UpgradeError(str(e))

    version = str(rel.get("version") or "")
    st["to_version"] = version
    _log(st, f"最新版本: {version}")
    if not rel.get("installer_url"):
        raise UpgradeError(
            f"release {version} 里没有安装包（NanoGhostSetup-*.exe），装不了。"
            f"这多半是发布时漏传了 —— 让发布的人把安装包补进 release（注意要发新"
            f"tag，不要往同一个 tag 重传文件）。")

    data_dir = Path(_ctx("data_dir"))
    downloads = data_dir / "downloads"
    msg = _free_space_message(downloads)
    if msg:
        raise UpgradeError(msg)

    dest = downloads / str(rel.get("installer_name") or f"NanoGhostSetup-{version}.exe")
    expect_size = int(rel.get("installer_size") or 0)
    expect_digest = str(rel.get("installer_digest") or "")
    if expect_digest.startswith("sha256:"):
        expect_digest = expect_digest.split(":", 1)[1]

    cached_ok = False
    if dest.is_file() and dest.stat().st_size > 1024 * 1024:
        if expect_size and dest.stat().st_size != expect_size:
            _log(st, f"缓存包大小不符（{dest.stat().st_size} ≠ {expect_size}），重下")
        elif expect_digest and hashlib.sha256(dest.read_bytes()).hexdigest() != expect_digest:
            _log(st, "缓存包 sha256 不符，重下")
        else:
            cached_ok = True
    if cached_ok:
        _log(st, f"复用已经下载过的安装包（已校验）: {dest}")
    else:
        _set_phase(st, PHASE_APPLYING, "正在下载安装包…", progress=0)
        _download(str(rel["installer_url"]), dest, st,
                  expected_size=expect_size, expected_sha256=expect_digest)
        _log(st, f"安装包已下载并校验: {dest}")

    old_prog, _ = _ctx("locate_program")()
    gateways = _stop_programs(st, Path(old_prog) if old_prog else None)
    _set_phase(st, PHASE_STOPPING, "已停止 NanoGhost 进程", progress=None)

    _set_phase(st, PHASE_APPLYING, "正在静默安装…", progress=None)
    install_log = data_dir / "ng_install.log"
    argv = [
        str(dest),
        "/VERYSILENT",          # 无界面
        "/SUPPRESSMSGBOXES",    # 一个框都不弹，否则会挂在那里等按键
        "/SP-",                 # 跳过「要安装吗？」确认页
        "/NORESTART",           # 重启时机由控制台定，不是由安装器
        "/NOCLOSEAPPLICATIONS", # 不让 Inno 用 Restart Manager 去关程序：它关不掉时
                                # 在静默模式下会直接 abort（实测 exit 1）。停程序由上面
                                # 的 _stop_programs 负责，这里只负责把文件覆盖下去。
        f"/LOG={install_log}",  # **不要自带引号**：以列表传参时 Python 会自己加引号，
                                # 内嵌的引号会变成路径的一部分 → Inno 打不开日志 →
                                # 静默模式下直接 abort（表现就是几秒内退出码 1 且没有日志）。
    ]
    _log(st, "运行安装包: " + " ".join(argv))
    t0 = time.time()
    rc, out = _run(argv, timeout=INSTALL_TIMEOUT)
    elapsed = time.time() - t0
    _log(st, f"安装包退出码 {rc}（耗时 {elapsed:.1f} 秒）")
    if out.strip():
        _log(st, out.strip()[:500])

    if rc != 0:
        # 不再猜「杀软 / 权限」—— 直接把证据摆出来：日志在不在、末尾写了什么。
        tail = ""
        if install_log.is_file():
            try:
                tail = "\n".join(
                    install_log.read_text(encoding="utf-8", errors="replace")
                    .splitlines()[-15:])
            except OSError:
                tail = ""
            hint = "安装日志末尾（真实原因在最后几行）："
        else:
            hint = ("安装器在 Inno 初始化前就退出了（一行日志都没写）：多半是被安全"
                    "软件 / EDR 拦下，或包被隔离；也可能是安装包不是有效的 Inno 可执行文件。")
        raise UpgradeError(
            f"安装包以退出码 {rc} 结束（耗时 {elapsed:.1f} 秒）。{hint}\n"
            f"日志: {install_log}\n{tail}")

    # 装完**必须重新解析**：安装目录可能和之前不一样（比如从源码 dist 换成了
    # %LOCALAPPDATA%），沿用旧路径会让界面显示一个已经不存在的位置。
    _set_phase(st, PHASE_VERIFYING, "正在核对版本…")
    prog, source = _ctx("locate_program")()
    if prog is None:
        raise UpgradeError("安装包跑完了，但按常规位置没找到 NanoGhost.exe。"
                           "如果安装时改了目录，请在配置里用 nanoghost_program 指定。")
    prog = Path(prog)
    st["program"] = str(prog)
    st["program_source"] = source
    st["from_version"] = _read_version(prog)
    _log(st, f"安装后程序: {prog}")
    _log(st, f"安装后版本: {st['from_version'] or '读不出来'}")
    if version and compare_versions(st["from_version"], version) != 0:
        raise UpgradeError(f"装完后版本对不上（读到 {st['from_version'] or '空'}，期望 "
                           f"{version}）。安装可能没真正生效，请手工运行 "
                           f"{dest} 看它报什么。")

    _set_phase(st, PHASE_RESTARTING, "正在重启之前的实例…")
    _restart_gateways(st, gateways, restart)


def _runner(mode: str, restart: bool, lock: Path | None) -> None:
    global _THREAD
    st = _STATE
    try:
        # 「升级」和「下载并安装」现在走**同一条路**：都用官方 Inno 安装包做覆盖安装。
        # 老的 update 模式（起 NanoGhost.exe update --yes → 分离式 .bat → 等进程退出
        # → 轮询结果文件 240s）已停用：那条链会卡在 cmd 的「终止批处理操作吗(Y/N)?」
        # 上（实测日志里刷了 20+ 次），还跟短命的控制台进程抢 stdin。
        # installer-as-updater 才是稳的 —— 关旧进程、换文件、重启，全交给安装器。
        _do_install(st, restart)
        with _STATE_LOCK:
            st["phase"] = PHASE_DONE
            st["step"] = "完成"
            st["progress"] = 100
            st["finished_at"] = int(time.time())
            _persist(st)
        _log(st, "任务完成")
        logger.info("nanoghost %s 完成", mode)
    except UpgradeError as e:
        _fail(st, str(e))
        logger.warning("nanoghost %s 失败: %s", mode, e)
    except Exception as e:                       # noqa: BLE001 - 线程里必须兜住
        _fail(st, f"升级过程中出现未预期的错误: {e}")
        logger.exception("nanoghost %s 异常", mode)
    finally:
        _release_lock(lock)
        with _STATE_LOCK:
            _THREAD = None


def _fail(st: dict, message: str) -> None:
    with _STATE_LOCK:
        st["phase"] = PHASE_FAILED
        st["step"] = "失败"
        st["error"] = message
        st["finished_at"] = int(time.time())
        _persist(st)
    _log(st, "失败: " + message)


def start(mode: str, *, restart: bool = True) -> dict:
    """起一个升级 / 安装任务。已有任务在跑时抛 UpgradeBusy。"""
    global _THREAD, _STATE
    if mode not in ("update", "install"):
        raise UpgradeError(f"未知的任务类型: {mode}")

    with _STATE_LOCK:
        _ensure_loaded()
        if _THREAD is not None and _THREAD.is_alive():
            raise UpgradeBusy("已有升级任务在进行中，等它结束后再试。")
        lock = _acquire_lock()
        _STATE = _empty_state()
        _reset(_STATE, mode)
        _log(_STATE, f"任务开始（{mode}）")
        _persist(_STATE)
        t = threading.Thread(
            target=_runner, args=(mode, bool(restart), lock),
            name=f"nanoghost-{mode}", daemon=True,
        )
        _THREAD = t
        t.start()
        return json.loads(json.dumps(_STATE, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 信息
# ---------------------------------------------------------------------------

def info() -> dict:
    """弹窗打开时的第一个调用。

    **必须快，且不打网络**：这里只做本地的路径解析 + --version（离线）。
    最新版本号只用上一次查询的缓存 —— 为了显示一个数字让弹窗卡十几秒，是最差的
    取舍；没有缓存就留空，等用户真点「检查更新」。
    """
    out = {
        "ok": True,
        "program": "",
        "program_source": "",
        "program_exists": False,
        "current_version": "",
        "latest_version": "",
        "installer_available": False,
        "config_path": str(_ctx("config_path")),
    }
    try:
        from server.releases import update_config_path
        out["update_config_path"] = str(update_config_path())
    except Exception:
        out["update_config_path"] = ""

    try:
        prog, source = _ctx("locate_program")()
    except Exception as e:
        # app.py 那份实现在"显式配了 nanoghost_program 却指不到文件"时抛 400，
        # 那条信息正是用户最需要的，原样带出去。
        out["ok"] = False
        out["error"] = getattr(e, "detail", None) or str(e)
        return out

    out["program_source"] = source
    if prog is not None:
        prog = Path(prog)
        out["program"] = str(prog)
        out["program_exists"] = True
        out["current_version"] = _read_version(prog)

    cached = cached_latest()
    if cached:
        out["latest_version"] = str(cached.get("version") or "")
        out["installer_available"] = bool(cached.get("installer_url"))
    return out


def check_latest(force: bool = False) -> dict:
    """查最新版本（要打网络）。用户点「检查更新」才走这里。"""
    try:
        rel = fetch_latest(force=force)
    except ReleaseError as e:
        raise UpgradeError(str(e))
    return {
        "ok": True,
        "version": rel.get("version") or "",
        "installer_available": bool(rel.get("installer_url")),
        "zip_available": bool(rel.get("zip_url")),
        "repo": rel.get("repo") or "",
        "html_url": rel.get("html_url") or "",
        "published_at": rel.get("published_at") or "",
    }

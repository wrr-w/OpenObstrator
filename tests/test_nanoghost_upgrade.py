"""升级 / 安装编排。

编排层的每一个慢动作（跑命令、停进程、下文件）都是模块级函数，用例里整片换掉 ——
**绝不碰真机**：不起真进程、不下真文件、不写真实安装目录。这是硬要求，
因为这套东西一旦在测试里跑起来，它会去 kill 本机所有 NanoGhost.exe。
"""
import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server.app as A
from server import nanoghost_upgrade as U
from server import releases

FAKE_EXE = Path(r"C:\fake\NanoGhost.exe")


@pytest.fixture
def env(tmp_path: Path, monkeypatch):
    """一个完全隔离的编排环境。

    configure() 是唯一的注入口 —— 生产路径上由 app.py 调用，测试里由这里调用，
    两边注入的是同一组东西。
    """
    cfg = tmp_path / "config.yaml"
    reg = tmp_path / "registry.json"
    data = tmp_path / "data"
    data.mkdir()

    monkeypatch.setattr(U, "fetch_latest",
                        lambda *a, **k: {"version": "1.0.1", "installer_url": "https://x/s.exe",
                                         "installer_name": "NanoGhostSetup-1.0.1.exe",
                                         "zip_url": "", "repo": "wrn/NanoGhost", "html_url": ""})
    monkeypatch.setattr(U, "_free_space_message", lambda p: None)
    monkeypatch.setattr(U, "_run", lambda argv, **k: pytest.fail(f"用例没准备这条命令: {argv}"))
    monkeypatch.setattr(U, "find_nanoghost_processes", lambda exe=None: [])
    monkeypatch.setattr(U, "is_pid_running", lambda pid: False)
    monkeypatch.setattr(U, "kill_pid_tree", lambda pid: pytest.fail("不该 kill 真进程"))
    # info() 会去读 releases 的模块级缓存，别的用例把它填上就会让断言随执行顺序变
    releases.clear_cache()
    U._LOADED = False
    U._STATE = {}
    U._THREAD = None
    U.configure(
        config_path=cfg, registry_path=reg, data_dir=data,
        locate_program=lambda: (FAKE_EXE, "config"),
        service_start=lambda *a: {"ok": True, "pid": 1},
    )
    yield {"tmp": tmp_path, "data": data, "cfg": cfg, "reg": reg}
    # 线程不收尾会污染后面的用例（状态是模块级的）
    t = U._THREAD
    if t is not None and t.is_alive():
        t.join(timeout=5)
    U._THREAD = None
    U._LOADED = False
    U._STATE = {}


def _wait(phase_expect=("done", "failed"), timeout=5.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = U.status()
        if st["phase"] in phase_expect:
            return st
        time.sleep(0.02)
    raise AssertionError(f"任务没有在 {timeout} 秒内结束: {U.status()}")


def _fake_download(url, dest: Path, st) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"MZ" + b"\0" * 10)


def _check_json(**kw) -> tuple[int, str]:
    payload = {"ok": True, "update_available": True,
               "current_version": "1.0.0", "latest_version": "1.0.1"}
    payload.update(kw)
    return (10 if payload.get("update_available") else 0), json.dumps(payload)


# ---------------------------------------------------------------------------
# 更新流程
# ---------------------------------------------------------------------------

def test_update_happy_path(env, monkeypatch):
    seen = []
    versions = iter(["1.0.0", "1.0.1"])
    monkeypatch.setattr(U, "_read_version", lambda prog: next(versions))
    monkeypatch.setattr(U, "_await_result", lambda st: "OK")
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: seen.append("stop") or [])
    monkeypatch.setattr(U, "_restart_gateways", lambda st, gw, restart: seen.append("restart"))

    def fake_run(argv, **k):
        seen.append("check" if "--check" in argv else "apply")
        return (10, json.dumps({})) if "--check" not in argv else _check_json()

    monkeypatch.setattr(U, "_run", fake_run)
    U.start("update")
    st = _wait()

    assert st["phase"] == "done", st
    assert st["from_version"] == "1.0.0" and st["to_version"] == "1.0.1"
    # 顺序是硬要求：必须先把进程停干净再覆盖（那个 bat 会等 exe 退出，
    # 而它的等待循环按进程名匹配、不区分目录），覆盖完了才能拉回来
    assert seen == ["check", "stop", "apply", "restart"]


def test_already_latest_does_nothing(env, monkeypatch):
    """exit 0 = 已是最新。不该停进程、不该跑覆盖。"""
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.1")
    monkeypatch.setattr(U, "_run", lambda argv, **k: _check_json(update_available=False))
    monkeypatch.setattr(U, "_stop_programs",
                        lambda st, prog: pytest.fail("已是最新，不该停进程"))
    U.start("update")
    st = _wait()
    assert st["phase"] == "done" and st["stopped"] == []


def test_check_failure_is_not_reported_as_a_broken_install(env, monkeypatch):
    """exit 1 是"这次没查成"（网络/DNS/超时），**不是**"你装的版本坏了"。
    把用户支去重装，是这种情况下最贵的错误动作。"""
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.0")
    monkeypatch.setattr(U, "_run", lambda argv, **k: (1, "connection refused"))
    monkeypatch.setattr(U, "_stop_programs",
                        lambda st, prog: pytest.fail("检查都没过，不该停进程"))
    U.start("update")
    st = _wait()
    assert st["phase"] == "failed"
    assert "检查更新失败" in st["error"]
    assert "不是" in st["error"] and "网络" in st["error"]


def test_apply_exit_10_waits_for_the_result_file(env, monkeypatch):
    """exit 10 只表示**覆盖脚本已开始**。真正的覆盖要等 NanoGhost 退出、文件锁
    释放之后才发生 —— 拿 10 当完成是最容易踩的坑。"""
    versions = iter(["1.0.0", "1.0.1"])
    monkeypatch.setattr(U, "_read_version", lambda prog: next(versions))
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: [])
    monkeypatch.setattr(U, "_restart_gateways", lambda st, gw, restart: None)
    asked = []
    monkeypatch.setattr(U, "_await_result", lambda st: asked.append(1) or "OK")
    monkeypatch.setattr(U, "_run",
                        lambda argv, **k: (10, "{}") if "--yes" in argv else _check_json())
    U.start("update")
    assert _wait()["phase"] == "done"
    assert asked == [1]


def test_overwrite_failure_names_the_stage_and_says_it_is_safe_to_retry(env, monkeypatch):
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.0")
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: [])
    monkeypatch.setattr(U, "_await_result", lambda st: "FAIL:copy")
    monkeypatch.setattr(U, "_run",
                        lambda argv, **k: (10, "{}") if "--yes" in argv else _check_json())
    U.start("update")
    st = _wait()
    assert st["phase"] == "failed"
    assert "FAIL:copy" in st["error"]
    assert "占用" in st["error"]            # 告诉人该做什么，而不是只报个码
    assert "安全重试" in st["error"]


def test_expand_failure_points_at_disk_not_at_a_corrupt_package(env, monkeypatch):
    """空间不足会伪装成"安装包损坏"，把人支去重新下载。文案要点出磁盘。"""
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.0")
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: [])
    monkeypatch.setattr(U, "_await_result", lambda st: "FAIL:expand")
    monkeypatch.setattr(U, "_run",
                        lambda argv, **k: (10, "{}") if "--yes" in argv else _check_json())
    U.start("update")
    assert "磁盘空间" in _wait()["error"]


def test_silent_version_mismatch_is_a_failure(env, monkeypatch):
    """覆盖脚本报 OK，但版本没变 —— 这是最要命的一种：用户会以为升级成功了。"""
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.0")   # 前后都是旧版本
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: [])
    monkeypatch.setattr(U, "_await_result", lambda st: "OK")
    monkeypatch.setattr(U, "_run",
                        lambda argv, **k: (10, "{}") if "--yes" in argv else _check_json())
    U.start("update")
    st = _wait()
    assert st["phase"] == "failed"
    assert "版本没变" in st["error"]


def test_result_file_never_appears_is_reported_as_unknown(env, monkeypatch):
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.0")
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: [])
    monkeypatch.setattr(U, "_await_result", lambda st: "")          # 超时
    monkeypatch.setattr(U, "_run",
                        lambda argv, **k: (10, "{}") if "--yes" in argv else _check_json())
    U.start("update")
    st = _wait()
    assert st["phase"] == "failed"
    assert "没等到" in st["error"]
    # 这时候覆盖脚本**可能还在跑**，让人立刻重试会撞上正在写的文件
    assert "别直接重试" in st["error"]


def test_update_without_a_program_says_install_instead_of_guessing(env, monkeypatch):
    U.configure(config_path=env["cfg"], registry_path=env["reg"], data_dir=env["data"],
                locate_program=lambda: (None, ""), service_start=lambda *a: {})
    U.start("update")
    st = _wait()
    assert st["phase"] == "failed" and "安装" in st["error"]


def test_restart_can_be_switched_off(env, monkeypatch):
    versions = iter(["1.0.0", "1.0.1"])
    monkeypatch.setattr(U, "_read_version", lambda prog: next(versions))
    monkeypatch.setattr(U, "_await_result", lambda st: "OK")
    gw = [{"name": "demo", "pid": 111}]
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: gw)
    monkeypatch.setattr(U, "is_pid_running", lambda pid: True)
    monkeypatch.setattr(U, "_run",
                        lambda argv, **k: (10, "{}") if "--yes" in argv else _check_json())
    U.start("update", restart=False)
    st = _wait()
    assert st["phase"] == "done" and st["restarted"] == []


def test_restart_reports_a_gateway_that_died_immediately(env, monkeypatch):
    """instance_service_start 里 sleep(3) 之后没有存活检查，崩掉的 gateway 也会被
    记成"在跑"。那一份是共享函数不去动它，所以在编排层如实复核。"""
    versions = iter(["1.0.0", "1.0.1"])
    monkeypatch.setattr(U, "_read_version", lambda prog: next(versions))
    monkeypatch.setattr(U, "_await_result", lambda st: "OK")
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: [{"name": "demo", "pid": 111}])
    monkeypatch.setattr(U, "is_pid_running", lambda pid: False)      # 起来就死了
    monkeypatch.setattr(U, "_run",
                        lambda argv, **k: (10, "{}") if "--yes" in argv else _check_json())
    U.start("update")
    st = _wait()
    assert st["restarted"][0]["ok"] is False
    assert "立刻退出" in st["restarted"][0]["detail"]


# ---------------------------------------------------------------------------
# 安装流程
# ---------------------------------------------------------------------------

def test_install_uses_silent_flags_and_never_restarts_by_itself(env, monkeypatch):
    """--no-restart 那类开关必须有：重启时机由控制台定，否则会和 installer.iss
    警告的"外部管理器抢跑"打架。"""
    ran = []
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: [])
    monkeypatch.setattr(U, "_download", _fake_download)
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.1")

    def fake_run(argv, **k):
        ran.append(argv)
        return 0, ""

    monkeypatch.setattr(U, "_run", fake_run)
    U.start("install")
    st = _wait()
    assert st["phase"] == "done", st
    argv = ran[0]
    assert "/VERYSILENT" in argv and "/SUPPRESSMSGBOXES" in argv
    assert "/NORESTART" in argv and "/NOCANCEL" in argv


def test_install_reports_a_missing_installer_asset(env, monkeypatch):
    """ver1.0.0 的 release 里就没有安装包 —— 发布时漏传。文案要指向"发布方"，
    而不是让用户以为是自己机器的问题。"""
    monkeypatch.setattr(U, "fetch_latest",
                        lambda *a, **k: {"version": "1.0.0", "installer_url": "", "zip_url": "https://x/a.zip"})
    U.start("install")
    st = _wait()
    assert st["phase"] == "failed"
    assert "没有安装包" in st["error"] and "发布" in st["error"]


def test_install_checks_disk_before_downloading(env, monkeypatch):
    monkeypatch.setattr(U, "_free_space_message",
                        lambda p: "C: 只剩 100 MB 可用空间，安装至少需要 500 MB。")
    monkeypatch.setattr(U, "_download", lambda *a: pytest.fail("空间不够就不该开始下载"))
    U.start("install")
    st = _wait()
    assert st["phase"] == "failed" and "可用空间" in st["error"]


def test_install_flags_a_wrapped_executable_by_how_fast_it_died(env, monkeypatch):
    """下载来的 exe 被 SmartScreen/AV 拦掉时，表现就是几秒内非 0 退出、且没有任何
    日志 —— 不识别这个形态的话，报出来的错会指向安装包本身。"""
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: [])
    monkeypatch.setattr(U, "_download", _fake_download)
    monkeypatch.setattr(U, "_run", lambda argv, **k: (1, ""))
    U.start("install")
    st = _wait()
    assert st["phase"] == "failed"
    assert "安全软件" in st["error"] or "SmartScreen" in st["error"]


def test_install_advises_admin_when_it_took_longer_but_failed(env, monkeypatch):
    """装过全机器版（Program Files）的机器上，普通权限静默安装会非 0 退出。
    不要写死返回码含义，指向权限 + 日志路径。"""
    monkeypatch.setattr(U, "_stop_programs", lambda st, prog: [])
    monkeypatch.setattr(U, "_download", _fake_download)

    def slow_run(argv, **k):
        time.sleep(3.2)
        return 2, ""

    monkeypatch.setattr(U, "_run", slow_run)
    U.start("install")
    st = _wait(timeout=10)
    assert st["phase"] == "failed"
    assert "管理员" in st["error"] and "ng_install.log" in st["error"]


# ---------------------------------------------------------------------------
# 并发 / 跨进程
# ---------------------------------------------------------------------------

def test_second_start_while_running_is_refused(env, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.0")

    def blocking_run(argv, **k):
        gate.wait(timeout=5)
        return (0, "{}")

    monkeypatch.setattr(U, "_run", blocking_run)
    U.start("update")
    with pytest.raises(U.UpgradeBusy):
        U.start("update")
    gate.set()
    _wait()


def test_a_live_other_console_blocks_start(env, monkeypatch):
    """dev server 和 frozen exe 会在同一台机器上并存。两个控制台同时升级不是
    "慢一点" —— 两边都会去停 gateway、都去起覆盖脚本，然后各自报出互相矛盾的
    结论。"""
    lock = Path(env["cfg"]).parent / "nanoghost" / "openobstrator_update.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"pid": 4242, "started_at": 1}), encoding="utf-8")
    monkeypatch.setattr(U, "is_pid_running", lambda pid: True)
    with pytest.raises(U.UpgradeBusy) as e:
        U.start("update")
    assert "4242" in str(e.value)


def test_a_dead_other_console_does_not_block_forever(env, monkeypatch):
    lock = Path(env["cfg"]).parent / "nanoghost" / "openobstrator_update.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"pid": 4242, "started_at": 1}), encoding="utf-8")
    monkeypatch.setattr(U, "is_pid_running", lambda pid: False)
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.0")
    monkeypatch.setattr(U, "_run", lambda argv, **k: (0, "{}"))
    U.start("update")
    assert _wait()["phase"] == "done"


def test_unknown_mode_is_rejected(env):
    with pytest.raises(U.UpgradeError):
        U.start("reticulate")


# ---------------------------------------------------------------------------
# 控制台自己重启
# ---------------------------------------------------------------------------

def test_in_flight_job_from_a_dead_console_reports_unknown(env, monkeypatch):
    """线程随控制台进程死了，但覆盖脚本是脱离进程组的、它还在跑。这时内存里什么
    都判断不了 —— **宁可说不知道，也不要假装知道**。"""
    job = env["data"] / "nanoghost_update" / "job.json"
    job.parent.mkdir(parents=True, exist_ok=True)
    job.write_text(json.dumps({"mode": "update", "phase": "applying",
                               "step": "正在覆盖安装文件…"}), encoding="utf-8")
    U._LOADED = False
    st = U.status()
    assert st["phase"] == "failed"
    assert "结果未知" in st["error"]
    assert "--version" in st["error"]        # 告诉人怎么自己核对


def test_finished_job_survives_a_console_restart(env):
    """已结束的任务不该被改写成"未知" —— 那会让刚做完的升级看起来失败了。"""
    job = env["data"] / "nanoghost_update" / "job.json"
    job.parent.mkdir(parents=True, exist_ok=True)
    job.write_text(json.dumps({"mode": "update", "phase": "done", "to_version": "1.0.1"}),
                   encoding="utf-8")
    U._LOADED = False
    st = U.status()
    assert st["phase"] == "done" and st["to_version"] == "1.0.1"


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

def test_routes_are_wired(env, monkeypatch):
    monkeypatch.setattr(A, "CONFIG_PATH", env["cfg"])
    monkeypatch.setattr(A, "REGISTRY_PATH", env["reg"])
    monkeypatch.setattr(A, "DATA_DIR", env["data"])
    monkeypatch.setattr(A, "locate_nanoghost_program", lambda **k: (FAKE_EXE, "config"))
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.0")
    U.configure(config_path=env["cfg"], registry_path=env["reg"], data_dir=env["data"],
                locate_program=A._locate_nanoghost_program, service_start=lambda *a: {})

    c = TestClient(A.app)
    info = c.get("/api/nanoghost/update/info").json()
    assert info["current_version"] == "1.0.0"
    assert info["program_exists"] is True
    assert info["latest_version"] == ""       # info 不打网络，只吃上一次的缓存
    assert c.get("/api/nanoghost/update/status").json()["phase"] in ("idle", "done", "failed")


def test_check_route_maps_release_errors_to_502(env, monkeypatch):
    monkeypatch.setattr(A, "CONFIG_PATH", env["cfg"])
    monkeypatch.setattr(A, "REGISTRY_PATH", env["reg"])
    monkeypatch.setattr(A, "DATA_DIR", env["data"])
    U.configure(config_path=env["cfg"], registry_path=env["reg"], data_dir=env["data"],
                locate_program=lambda: (None, ""), service_start=lambda *a: {})

    def boom(*a, **k):
        raise U.ReleaseError("GitHub API 限流，等一会儿再试。")

    monkeypatch.setattr(U, "fetch_latest", boom)
    r = TestClient(A.app).get("/api/nanoghost/update/check")
    assert r.status_code == 502
    assert "限流" in r.json()["detail"]


def test_start_route_maps_busy_to_409(env, monkeypatch):
    monkeypatch.setattr(A, "CONFIG_PATH", env["cfg"])
    monkeypatch.setattr(A, "REGISTRY_PATH", env["reg"])
    monkeypatch.setattr(A, "DATA_DIR", env["data"])
    U.configure(config_path=env["cfg"], registry_path=env["reg"], data_dir=env["data"],
                locate_program=lambda: (FAKE_EXE, "config"), service_start=lambda *a: {})
    monkeypatch.setattr(U, "start", lambda mode, restart=True: (_ for _ in ()).throw(
        U.UpgradeBusy("已有升级任务在进行中。")))
    r = TestClient(A.app).post("/api/nanoghost/update/start", json={"restart": False})
    assert r.status_code == 409


def test_program_put_writes_config_and_reports_immediately(env, monkeypatch):
    monkeypatch.setattr(A, "CONFIG_PATH", env["cfg"])
    env["cfg"].write_text("# 注释要留着\nbind_port: 8088\n", encoding="utf-8")
    U.configure(config_path=env["cfg"], registry_path=env["reg"], data_dir=env["data"],
                locate_program=lambda: (FAKE_EXE, "config"), service_start=lambda *a: {})
    monkeypatch.setattr(U, "_read_version", lambda prog: "1.0.1")

    real = env["tmp"] / "NanoGhost.exe"
    real.write_bytes(b"MZ")
    r = TestClient(A.app).put("/api/nanoghost/update/program", json={"path": str(real)})
    assert r.status_code == 200 and r.json()["program_exists"] is True
    text = env["cfg"].read_text(encoding="utf-8")
    assert "# 注释要留着" in text                    # 逐行改，不 safe_load + dump
    assert f"nanoghost_program: '{real}'" in text

    r = TestClient(A.app).put("/api/nanoghost/update/program", json={"path": ""})
    assert r.status_code == 200
    assert "nanoghost_program" not in env["cfg"].read_text(encoding="utf-8")


def test_program_put_refuses_a_bad_path_without_touching_the_config(env, monkeypatch):
    """先验后写。

    反过来的顺序（写进去、再解析、解析不成再报 400）会把一条走不通的路径**留在
    配置文件里**：用户看到的是"写入失败"，然后发现控制台连程序都找不到了。一次
    点击弄坏配置，这个代价不该付。
    """
    monkeypatch.setattr(A, "CONFIG_PATH", env["cfg"])
    before = "nanoghost_program: 'D:\\good\\NanoGhost.exe'\n# 注释要留着\n"
    env["cfg"].write_text(before, encoding="utf-8")
    U.configure(config_path=env["cfg"], registry_path=env["reg"], data_dir=env["data"],
                locate_program=lambda: (FAKE_EXE, "config"), service_start=lambda *a: {})

    r = TestClient(A.app).put("/api/nanoghost/update/program",
                              json={"path": r"C:\definitely\not\here.exe"})
    assert r.status_code == 400
    assert "不存在" in r.json()["detail"]
    assert env["cfg"].read_text(encoding="utf-8") == before     # 一个字都没动


# ---------------------------------------------------------------------------
# processes.find_nanoghost_processes
# ---------------------------------------------------------------------------

def test_find_nanoghost_processes_is_pure_lookup(monkeypatch):
    """只读扫描，**不杀**任何东西。

    注册簿实测有整份记录全是死 pid 的情况，所以"到底还有哪些 NanoGhost.exe 活着"
    必须能绕开注册簿直接问系统。这个函数是那个答案的唯一来源。
    """
    import psutil

    from server.processes import find_nanoghost_processes

    class _Fake:
        def __init__(self, pid, name, exe):
            self.info = {"pid": pid, "name": name, "exe": exe}

    # 这个函数在函数体里 `import psutil`，拿到的是 sys.modules 里那一个，
    # 所以在模块上打补丁就够
    monkeypatch.setattr(psutil, "process_iter",
                        lambda attrs: [_Fake(11, "NanoGhost.exe", r"C:\a\NanoGhost.exe"),
                                       _Fake(12, "NanoGhost.exe", r"C:\b\NanoGhost.exe"),
                                       _Fake(13, "python.exe", r"C:\a\python.exe")])
    got = find_nanoghost_processes(None)
    assert [p["pid"] for p in got] == [11, 12]

    # 给了路径就只认那一个目录 —— 升级只覆盖自己的那份，不该误伤别处的
    got = find_nanoghost_processes(r"C:\b\NanoGhost.exe")
    assert [p["pid"] for p in got] == [12]


def test_find_nanoghost_processes_skips_itself_and_survivors(monkeypatch):
    """自己不能被算进去 —— 否则"停干净再覆盖"第一步就把控制台和它拉的
    升级线程一起端了。读不到 info 的进程也要跳过，不能整轮炸掉。"""
    import os

    import psutil

    from server.processes import find_nanoghost_processes

    class _Fake:
        def __init__(self, pid, name, exe):
            self.info = {"pid": pid, "name": name, "exe": exe}

    class _Denied:
        @property
        def info(self):
            raise psutil.AccessDenied()

    monkeypatch.setattr(psutil, "process_iter",
                        lambda attrs: [_Fake(os.getpid(), "NanoGhost.exe", r"C:\a\NanoGhost.exe"),
                                       _Denied(),
                                       _Fake(14, "NANOGHOST.EXE", r"C:\a\NANOGHOST.EXE")])
    assert [p["pid"] for p in find_nanoghost_processes(None)] == [14]


def test_find_nanoghost_processes_on_a_real_machine_is_harmless():
    """不 monkeypatch 跑一遍真实现。只断言它不断言、不抛、不越界 —— 这台机器上
    有没有 NanoGhost.exe 是不确定的。"""
    import os

    from server.processes import find_nanoghost_processes

    got = find_nanoghost_processes(None)
    assert isinstance(got, list)
    assert os.getpid() not in [p["pid"] for p in got]
    assert all(set(p) >= {"pid", "exe", "name"} for p in got)

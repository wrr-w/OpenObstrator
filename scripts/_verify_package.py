"""跑一遍刚打出来的 dist\\OpenObstrator.exe，只用 GET，验完就关。

验的是"打包这个动作有没有把东西带进去"，不是业务逻辑（那是 tests/ 的事）：
  · exe 起得来 —— hiddenimports 少一个，启动就 ImportError
  · 新前端文件在包里 —— dist 下漏文件的话 dev 永远看不出来
  · 前端缓存号是新的 —— 漏了就是"代码写了、界面没变"
  · 两条新路由通 —— 走一遍新模块
全程不碰真机状态：没有任何 POST，不建实例、不起进程。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist")
EXE = os.path.abspath(os.path.join(DIST, "OpenObstrator.exe"))

fails: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        fails.append(label)


def get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def wait_for_url(log_path: str, proc: subprocess.Popen, timeout: float = 90) -> str:
    """从 stdout 里抓 `Web UI: http://localhost:PORT`，端口是程序自己挑的。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"进程提前退出，code={proc.returncode}")
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                m = re.search(r"Web UI:\s+(http://\S+)", f.read())
        except OSError:
            m = None
        if m:
            return m.group(1).rstrip("/")
        time.sleep(0.5)
    raise SystemExit("等不到 Web UI 那一行")


def main() -> int:
    if not os.path.isfile(EXE):
        raise SystemExit(f"没有 {EXE}")

    log_path = os.path.join(DIST, "_verify_stdout.log")
    log = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen([EXE], cwd=DIST, stdout=log, stderr=subprocess.STDOUT)
    print(f"起了 {EXE} (pid={proc.pid})")
    try:
        base = wait_for_url(log_path, proc)
        print(f"base = {base}\n")

        print("1) 页面和前端资源")
        st, html = get(f"{base}/")
        check("GET / == 200", st == 200, str(st))
        check("顶栏按钮 globalUpdate 在", 'id="globalUpdate"' in html)
        check("ngupdate.js 挂上了", "ngupdate.js?v=1" in html)
        check("panels.js 缓存号 bump 了", "panels.js?v=5" in html)
        check("modals.js 缓存号 bump 了", "modals.js?v=2" in html)

        st, js = get(f"{base}/static/js/ngupdate.js?v=1")
        check("GET ngupdate.js == 200", st == 200, str(st))
        st, js = get(f"{base}/static/js/panels.js?v=5")
        check("GET panels.js?v=5 == 200", st == 200, str(st))
        check(
            "panels.js 里旧的父节点跳过逻辑没了",
            "it.name === cat && items.length > 1" not in js,
        )
        st, css = get(f"{base}/static/js/modals.js?v=2")
        check("modals.js?v=2 == 200", st == 200, str(st))

        print("\n2) 新模块（hiddenimports 漏了的话这里就 500 或直接起不来）")
        st, body = get(f"{base}/api/nanoghost/update/info")
        check("GET /api/nanoghost/update/info == 200", st == 200, body[:200])
        if st == 200:
            info = json.loads(body)
            print(f"       program={info.get('program')!r} exists={info.get('program_exists')}")
            print(f"       current={info.get('current_version')!r} source={info.get('source')!r}")
            check("返回体有 program 字段", "program" in info)

        print("\n3) 技能清单走的是新遍历（分组入口 lark / image 应该在）")
        st, body = get(f"{base}/api/global-registry/nanoghost/skills")
        check("GET /api/global-registry/nanoghost/skills == 200", st == 200, body[:200])
        if st == 200:
            names = {x["name"] for x in json.loads(body)["items"]}
            check("lark / image 分组入口都在", {"lark", "image"} <= names, f"共 {len(names)} 个")

        st, body = get(f"{base}/api/runtimes/nanoghost/instances/cc/skills")
        check("GET .../instances/cc/skills == 200", st == 200, body[:200])
        if st == 200:
            items = json.loads(body)["items"]
            names = {x["name"] for x in items}
            check("cc 实例 34 个技能", len(items) == 34, f"实际 {len(items)}")
            check("lark / image 分组入口都在", {"lark", "image"} <= names)
            on = [x["name"] for x in items if x["enabled"]]
            print(f"       白名单开着的有 {len(on)} 个: {on[:5]}")
    finally:
        # 必须连子树一起杀：onefile 的 exe 是"引导进程 + 真正干活的子进程"两层，
        # terminate() 只杀得掉父的，子进程变成孤儿接着跑 —— 它攥着 stdout，
        # 连日志文件都删不掉。
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True, check=False,
        )
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()
        print(f"\n已关闭 pid={proc.pid} 及其子树（stdout 在 {log_path}）")

    print()
    if fails:
        print(f"FAILED: {len(fails)} 项 —— {fails}")
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

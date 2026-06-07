"""
OpenObstrator - 打包入口
"""
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

# 确保模块路径正确
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
else:
    _project_root = Path(__file__).resolve().parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

from server.app import app
from server.settings import load_app_config


def get_lan_ip():
    """获取本机局域网 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def find_available_port(start_port, max_try=10):
    """检测端口是否被占用，被占用则自动尝试下一个"""
    for offset in range(max_try):
        port = start_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return start_port


# 读取配置确定 host/port
if getattr(sys, 'frozen', False):
    config_path = Path(sys.executable).parent / "data" / "config.yaml"
else:
    config_path = Path(__file__).resolve().parent / "data" / "config.yaml"

cfg = load_app_config(config_path)
HOST = cfg.bind_host
PORT = find_available_port(cfg.bind_port)
LAN_IP = get_lan_ip()

LOCAL_URL = f"http://localhost:{PORT}"
LAN_URL = f"http://{LAN_IP}:{PORT}"


def open_browser():
    import time
    time.sleep(2)
    webbrowser.open(LOCAL_URL)


if __name__ == "__main__":
    import uvicorn

    print("=" * 55)
    print("Starting OpenObstrator server...")
    print(f"Web UI:     {LOCAL_URL}")
    print(f"API Docs:   {LOCAL_URL}/docs")
    if LAN_IP != "127.0.0.1":
        print(f"LAN Access: {LAN_URL}")
    print("=" * 55)

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT)

import sys

def fix_iwms():
    path = r'E:\OperationsAssistantORIG\Tech\Code\IWMS\backend\main.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old = """# MCP SSE 集成：双击启动后，AI 工具可通过 /mcp/sse 连接
try:
    from mcp.server.sse import SseServerTransport
    import iwms_mcp_server
    from starlette.routing import Route

    mcp_sse = SseServerTransport("/mcp/messages/")

    async def _mcp_sse_handler(scope, receive, send):
        async with mcp_sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
            await iwms_mcp_server.server.run(
                read_stream, write_stream, iwms_mcp_server.server.create_initialization_options()
            )

    async def _mcp_messages_handler(scope, receive, send):
        await mcp_sse.handle_post_message(scope, receive, send)

    app.router.routes.insert(0, Route("/mcp/sse", _mcp_sse_handler, methods=["GET"]))
    app.router.routes.insert(0, Route("/mcp/messages/", _mcp_messages_handler, methods=["POST"]))

except Exception as e:
    print(f\"[IWMS] MCP SSE not available: {e}\")"""

    new = """# MCP SSE 集成：双击启动后，AI 工具可通过 /mcp/sse 连接
try:
    from mcp.server.sse import SseServerTransport
    import iwms_mcp_server

    mcp_sse = SseServerTransport("/mcp/messages/")

    async def _mcp_asgi(scope, receive, send):
        if scope["type"] != "http":
            return
        if scope["method"] == "GET":
            async with mcp_sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await iwms_mcp_server.server.run(
                    read_stream, write_stream, iwms_mcp_server.server.create_initialization_options()
                )
        elif scope["method"] == "POST":
            await mcp_sse.handle_post_message(scope, receive, send)

    app.mount("/mcp", _mcp_asgi)

except Exception as e:
    print(f\"[IWMS] MCP SSE not available: {e}\")"""

    if old in content:
        content = content.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('IWMS: OK')
    else:
        print('IWMS: SKIP (already patched or different)')

def fix_capture():
    path = r'E:\OperationsAssistantORIG\Tech\Code\Capture\server\app.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old = """    # ── MCP SSE 端点 ──
    try:
        from mcp.server.sse import SseServerTransport
        from server.mcp.capture_mcp_manifest import (
            API_SPEC_PATH,
            CAPTURE_BASE_URL,
            build_capture_server,
        )
        from starlette.routing import Route

        capture_mcp_server = build_capture_server(API_SPEC_PATH, CAPTURE_BASE_URL)

        _mcp_sse = SseServerTransport("/mcp/messages/")

        async def _mcp_sse_handler(scope, receive, send):
            async with _mcp_sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await capture_mcp_server.run(
                    read_stream, write_stream, capture_mcp_server.create_initialization_options()
                )

        async def _mcp_messages_handler(scope, receive, send):
            await _mcp_sse.handle_post_message(scope, receive, send)

        app.router.routes.insert(0, Route("/mcp/sse", _mcp_sse_handler, methods=["GET"]))
        app.router.routes.insert(0, Route("/mcp/messages/", _mcp_messages_handler, methods=["POST"]))

        logger.info("[MCP] SSE endpoint registered at /mcp/sse")
    except Exception as e:
        logger.warning("[MCP] SSE not available: %s", e)"""

    new = """    # ── MCP SSE 端点 ──
    try:
        from mcp.server.sse import SseServerTransport
        from server.mcp.capture_mcp_manifest import (
            API_SPEC_PATH,
            CAPTURE_BASE_URL,
            build_capture_server,
        )

        capture_mcp_server = build_capture_server(API_SPEC_PATH, CAPTURE_BASE_URL)

        _mcp_sse = SseServerTransport("/mcp/messages/")

        async def _mcp_asgi(scope, receive, send):
            if scope["type"] != "http":
                return
            if scope["method"] == "GET":
                async with _mcp_sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                    await capture_mcp_server.run(
                        read_stream, write_stream, capture_mcp_server.create_initialization_options()
                    )
            elif scope["method"] == "POST":
                await _mcp_sse.handle_post_message(scope, receive, send)

        app.mount("/mcp", _mcp_asgi)

        logger.info("[MCP] SSE endpoint registered at /mcp/sse")
    except Exception as e:
        logger.warning("[MCP] SSE not available: %s", e)"""

    if old in content:
        content = content.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('Capture: OK')
    else:
        print('Capture: SKIP (already patched or different)')

if __name__ == '__main__':
    fix_iwms()
    fix_capture()

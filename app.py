"""
Hugging Face Spaces (Gradio + ZeroGPU Free Tier) & Cloud Self-Bootstrapping Entrypoint.
- Automatically syncs the latest codebase from GitHub (`https://github.com/selcukksezer/youtube.git`)
  if deployed as a standalone `app.py` inside a fresh Hugging Face Space.
- Satisfies Hugging Face's ZeroGPU `@spaces.GPU` startup check via `demo.launch(ssr_mode=False)`
  and attaches all `server.app` FastAPI routes + static mounts.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading

GIT_REPO_URL = os.getenv("GIT_SYNC_REPO_URL", "https://github.com/selcukksezer/youtube.git")
GIT_BRANCH = os.getenv("GIT_SYNC_BRANCH", "main")


def _bootstrap_from_github_if_needed() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_file = os.path.join(base_dir, "server.py")
    if not os.path.exists(server_file):
        subprocess.run(["git", "init"], cwd=base_dir, check=False)
        subprocess.run(["git", "remote", "remove", "origin"], cwd=base_dir, check=False)
        subprocess.run(["git", "remote", "add", "origin", GIT_REPO_URL], cwd=base_dir, check=False)
        subprocess.run(["git", "fetch", "--depth=20", "origin", GIT_BRANCH], cwd=base_dir, check=True)
        subprocess.run(["git", "checkout", "-B", GIT_BRANCH, f"origin/{GIT_BRANCH}"], cwd=base_dir, check=True)
        req_file = os.path.join(base_dir, "requirements.txt")
        if os.path.exists(req_file):
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", req_file], cwd=base_dir, check=False)
    elif os.getenv("SPACE_ID") and os.getenv("AUTO_GIT_UPDATE", "true").lower() in ("true", "1", "yes"):
        subprocess.run(["git", "remote", "set-url", "origin", GIT_REPO_URL], cwd=base_dir, check=False)
        subprocess.run(["git", "fetch", "--depth=20", "origin", GIT_BRANCH], cwd=base_dir, check=False)
        subprocess.run(["git", "pull", "--ff-only", "origin", GIT_BRANCH], cwd=base_dir, check=False)


_bootstrap_from_github_if_needed()

import server  # noqa: E402


def _run_with_gradio_zerogpu(host: str, port: int) -> None:
    import gradio as gr
    try:
        import spaces
        gpu_decorator = spaces.GPU
    except ImportError:
        def gpu_decorator(fn):  # type: ignore[misc]
            return fn

    @gpu_decorator
    def _zerogpu_platform_check() -> str:
        return "Shorts Studio ZeroGPU Ready"

    with gr.Blocks(title="Shorts Studio") as demo:
        btn = gr.Button("Health Check", visible=False)
        out = gr.Textbox(visible=False)
        btn.click(fn=_zerogpu_platform_check, outputs=out)

    demo.launch(
        server_name=host,
        server_port=port,
        prevent_thread_lock=True,
        ssr_mode=False,
    )

    if getattr(demo, "app", None) is not None:
        gradio_routes = list(demo.app.router.routes)
        custom_routes = [
            r for r in server.app.router.routes
            if getattr(r, "path", None) not in ("/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc")
        ]
        demo.app.router.routes[:] = custom_routes + gradio_routes

        def _startup_bg() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server.on_startup())

        threading.Thread(target=_startup_bg, daemon=True).start()

    demo.block_thread()


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860")))

    if os.getenv("SPACE_ID") or os.getenv("ZEROGPU"):
        try:
            _run_with_gradio_zerogpu(host, port)
            return
        except ImportError:
            pass

    import uvicorn
    uvicorn.run("server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

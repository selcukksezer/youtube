"""
Hugging Face Spaces (Gradio + ZeroGPU Free Tier) & Cloud Entrypoint.
Satisfies Hugging Face's ZeroGPU `@spaces.GPU` startup check via `demo.launch(ssr_mode=False)`
and attaches all `server.app` FastAPI routes + static mounts to the underlying Starlette/FastAPI app.
Falls back to standard `uvicorn.run("server:app")` when `gradio`/`spaces` are not installed.
"""
from __future__ import annotations

import asyncio
import os
import threading

import server


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
        # Required by Hugging Face ZeroGPU Free tier static check at startup.
        # Never allocates a GPU unless invoked directly.
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

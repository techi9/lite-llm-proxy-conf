"""
Thin middleware proxy: strips image_url content parts from messages,
then forwards requests to LiteLLM on port 4001.

Run with: python3 middleware.py
Listens on: 0.0.0.0:4000
Forwards to: http://localhost:4001
"""

import json
import asyncio
import aiohttp
from aiohttp import web

LITELLM_URL = "http://localhost:4001"


def strip_image_url(messages: list) -> list:
    """Remove image_url content parts from all messages."""
    cleaned = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            text_parts = [
                p for p in content
                if not (isinstance(p, dict) and p.get("type") == "image_url")
            ]
            if not text_parts:
                continue  # drop message entirely if only images
            # Unwrap single text part to plain string
            if len(text_parts) == 1 and isinstance(text_parts[0], dict) and text_parts[0].get("type") == "text":
                msg = {**msg, "content": text_parts[0]["text"]}
            else:
                msg = {**msg, "content": text_parts}
        cleaned.append(msg)
    return cleaned


async def proxy(request: web.Request) -> web.StreamResponse:
    body = await request.read()
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "content-length")}

    # Strip image_url from JSON body
    if "application/json" in request.headers.get("content-type", ""):
        try:
            data = json.loads(body)
            if "messages" in data:
                original_count = len(data["messages"])
                data["messages"] = strip_image_url(data["messages"])
                stripped = original_count - len(data["messages"])
                if stripped:
                    print(f"[middleware] stripped {stripped} image-only messages")
            body = json.dumps(data).encode()
        except Exception as e:
            print(f"[middleware] JSON parse error: {e}")

    target = LITELLM_URL + request.path_qs

    async with aiohttp.ClientSession() as session:
        async with session.request(
            method=request.method,
            url=target,
            headers=headers,
            data=body,
            allow_redirects=False,
        ) as resp:
            # Stream the response back
            response = web.StreamResponse(
                status=resp.status,
                headers={k: v for k, v in resp.headers.items()
                         if k.lower() not in ("transfer-encoding",)},
            )
            await response.prepare(request)
            async for chunk in resp.content.iter_any():
                await response.write(chunk)
            await response.write_eof()
            return response


async def main():
    app = web.Application()
    app.router.add_route("*", "/{path_info:.*}", proxy)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 4000)
    print("[middleware] Listening on :4000 → LiteLLM on :4001")
    await site.start()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

"""Haqiqiy Chromium'da qurilma cheklovi, fullscreen va safe area (Telegram stub'i bilan).

Chrome/Chromium o'rnatilmagan muhitda o'tkazib yuboriladi. Telegramga yoki bazaga ulanmaydi.
"""

import asyncio
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import aiohttp
import pytest

WEB = Path(__file__).resolve().parents[1] / "ilmbot" / "web"
PHONE_UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Mobile Safari/537.36"
IPHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile"


class Assets(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/app":
            file, content_type = WEB / "templates" / "miniapp.html", "text/html; charset=utf-8"
        elif self.path in {
            "/static/miniapp.js",
            "/static/miniapp.css",
            "/static/miniapp-art.svg",
            "/static/miniapp-pattern.svg",
        }:
            file = WEB / "static" / self.path.rsplit("/", 1)[1]
            content_type = {".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}[file.suffix]
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(file.read_bytes())

    def log_message(self, *args):
        pass


def browser_path():
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        if path := shutil.which(name):
            return path
    for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", "")):
        for suffix in ("Google/Chrome/Application/chrome.exe", "Microsoft/Edge/Application/msedge.exe"):
            path = Path(base) / suffix
            if path.is_file():
                return str(path)
    pytest.skip("Chrome/Chromium o'rnatilmagan")


def telegram_stub(platform="android", version="8.0", fail_fullscreen=False, already_fullscreen=False):
    return (
        """
    window.__events={};window.__calls={api:0,fullscreen:0,expand:0,settings:0};
    window.Telegram={WebApp:{
      platform:PLATFORM,version:VERSION,initData:'test',isFullscreen:ALREADY,
      safeAreaInset:{top:24,bottom:20,left:0,right:0},
      contentSafeAreaInset:{top:56,bottom:0,left:0,right:0},viewportStableHeight:844,
      ready(){},expand(){window.__calls.expand++},
      isVersionAtLeast(v){return parseFloat(this.version)>=parseFloat(v)},
      setHeaderColor(){},setBackgroundColor(){},disableVerticalSwipes(){},
      BackButton:{onClick(){},show(){},hide(){}},
      SettingsButton:{onClick(cb){window.__settings=cb},show(){window.__calls.settings++}},
      onEvent(name,cb){window.__events[name]=cb},
      requestFullscreen(){
        window.__calls.fullscreen++;
        if(FAIL){window.__events.fullscreenFailed?.({error:'UNSUPPORTED'});return}
        this.isFullscreen=true;window.__events.fullscreenChanged?.();
      }
    }};
    window.fetch=async(url)=>{
      window.__calls.api++;
      return new Response(JSON.stringify(url.endsWith('/me')?
        {user:{id:111,name:'Sinov',region_id:null,subscribed:false},today:'2026-10-22',bot_url:null}:
        url.endsWith('/menu')?{nodes:[]}:{regions:[]}));
    };
    """.replace("PLATFORM", json.dumps(platform))
        .replace("VERSION", json.dumps(version))
        .replace("FAIL", json.dumps(fail_fullscreen))
        .replace("ALREADY", json.dumps(already_fullscreen))
    )


async def test_phone_gate_fullscreen_and_native_safe_areas():
    browser = browser_path()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Assets)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="ilmbot-browser-", ignore_cleanup_errors=True) as profile:
        process = await asyncio.to_thread(
            subprocess.Popen,
            [
                browser,
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-gpu-sandbox",
                "--disable-software-rasterizer",
                "--no-first-run",
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(50):
                    try:
                        async with session.get(f"http://127.0.0.1:{port}/json") as response:
                            pages = await response.json()
                        break
                    except aiohttp.ClientError:
                        await asyncio.sleep(0.1)
                else:
                    pytest.fail("Chromium DevTools ishga tushmadi")
                page = next(p for p in pages if p["type"] == "page")
                async with session.ws_connect(page["webSocketDebuggerUrl"]) as ws:
                    sequence = 0
                    runtime_errors = []

                    async def command(method, params=None):
                        nonlocal sequence
                        sequence += 1
                        await ws.send_json({"id": sequence, "method": method, "params": params or {}})
                        while True:
                            message = await asyncio.wait_for(ws.receive_json(), timeout=15)
                            if message.get("method") == "Runtime.exceptionThrown":
                                runtime_errors.append(message["params"])
                            if message.get("id") == sequence:
                                assert "error" not in message, message
                                return message.get("result", {})

                    async def js(expression):
                        result = await command(
                            "Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True}
                        )
                        assert "exceptionDetails" not in result, result
                        return result["result"].get("value")

                    await command("Page.enable")
                    await command("Runtime.enable")
                    await command("Network.enable")
                    await command("Network.setBlockedURLs", {"urls": ["*telegram.org/js/*"]})
                    await command(
                        "Emulation.setDeviceMetricsOverride",
                        {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True},
                    )
                    cases = [
                        ("desktop", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "tdesktop", "phone-only"),
                        ("tablet", "Mozilla/5.0 (Linux; Android 14; Pixel Tablet)", "android", "phone-only"),
                        ("ipad", "Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X)", "ios", "phone-only"),
                        ("ipad-desktop", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)", "ios", "phone-only"),
                        ("android", PHONE_UA, "android", "app-main"),
                        ("iphone", IPHONE_UA, "ios", "app-main"),
                        ("phone-browser", IPHONE_UA, "unknown", "auth-error"),
                    ]
                    for name, agent, platform, expected in cases:
                        await command("Emulation.setUserAgentOverride", {"userAgent": agent})
                        injected = await command(
                            "Page.addScriptToEvaluateOnNewDocument", {"source": telegram_stub(platform)}
                        )
                        await command("Page.navigate", {"url": f"http://127.0.0.1:{server.server_port}/app"})
                        for _ in range(50):
                            if await js(
                                "Boolean(document.getElementById('phone-only')) && "
                                "document.getElementById('loading').hidden"
                            ):
                                break
                            await asyncio.sleep(0.05)
                        assert await js(f"!document.getElementById('{expected}').hidden"), name
                        if expected != "app-main":
                            assert await js("window.__calls.api") == 0, name
                            assert await js("window.__calls.fullscreen") == 0, name
                        else:
                            assert await js("window.__calls.fullscreen") == 1, name
                            assert await js("window.__calls.settings") == 1, name
                            assert (
                                await js("parseFloat(getComputedStyle(document.querySelector('.app-wrap')).paddingTop)")
                                == 80
                            )
                            assert (
                                await js("parseFloat(getComputedStyle(document.getElementById('bottom-nav')).bottom)")
                                == 32
                            )
                            await js("Telegram.WebApp.isFullscreen=false;window.__events.fullscreenChanged()")
                            assert await js("!document.getElementById('fullscreen-retry').hidden")
                            await js("document.getElementById('fullscreen-retry').click()")
                            assert await js("window.__calls.fullscreen") == 2
                            assert await js("document.getElementById('fullscreen-retry').hidden")
                            await js("window.__settings()")
                            assert await js("!document.getElementById('view-settings').hidden")
                            await js("Telegram.WebApp.safeAreaInset.top=0;window.__events.safeAreaChanged()")
                            assert (
                                await js("parseFloat(getComputedStyle(document.querySelector('.app-wrap')).paddingTop)")
                                == 56
                            )
                        await command(
                            "Page.removeScriptToEvaluateOnNewDocument", {"identifier": injected["identifier"]}
                        )

                    for options, expected_calls in [
                        ({"version": "7.0"}, 0),
                        ({"fail_fullscreen": True}, 1),
                        ({"already_fullscreen": True}, 0),
                    ]:
                        await command("Emulation.setUserAgentOverride", {"userAgent": PHONE_UA})
                        injected = await command(
                            "Page.addScriptToEvaluateOnNewDocument", {"source": telegram_stub(**options)}
                        )
                        await command("Page.navigate", {"url": f"http://127.0.0.1:{server.server_port}/app"})
                        for _ in range(50):
                            if await js(
                                "Boolean(document.getElementById('app-main')) && "
                                "!document.getElementById('app-main').hidden"
                            ):
                                break
                            await asyncio.sleep(0.05)
                        assert await js("!document.getElementById('app-main').hidden"), options
                        assert await js("window.__calls.fullscreen") == expected_calls, options
                        await command(
                            "Page.removeScriptToEvaluateOnNewDocument", {"identifier": injected["identifier"]}
                        )
                    assert not runtime_errors, runtime_errors
                    await command("Browser.close")
        finally:
            if process.poll() is None:
                process.terminate()
            await asyncio.to_thread(process.wait, timeout=10)
            await asyncio.to_thread(server.shutdown)
            server.server_close()

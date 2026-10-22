import uvicorn

from ilmbot.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "ilmbot.web.main:build_app",
        factory=True,
        host=settings.web_host,
        port=settings.web_port,
        proxy_headers=False,  # reverse proxy ortida ishlatilsa, ishonchli proxy sozlangandan keyin yoqiladi
        server_header=False,
    )

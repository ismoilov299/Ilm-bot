"""Ommaviy Google Drive papkasidagi Telegram Desktop eksportini lokalga yuklaydi va foizni ko'rsatadi.

Drive login talab qilmaydi (papka "havola bilan ochiq" bo'lishi kerak). Eksport uzilgan bo'lsa `result.json`
oxiri avtomatik yopiladi va faqat unda tilga olingan fayllar yuklanadi.
Uzilsa qayta ishga tushiring: tayyor fayllar o'tkazib yuboriladi.

  python tools/drive_fetch/fetch_export.py <papka_id> [--out var/export] [--workers 4]
      [--kinds audio_file,voice_message]

Natija `--out` ichida Telegram eksporti tuzilmasida bo'ladi (`result.json`, `files/`, `video_files/`, ...), shuning
uchun `python -m ilmbot.cli import-content var/export/result.json` shundan o'qiy oladi.
"""

import argparse
import html
import json
import re
import sys
import threading
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}
ENTRY = re.compile(r'<div class="flip-entry" id="entry-([^"]+)".*?<div class="flip-entry-title">([^<]*)</div>', re.S)


def fetch(url: str, timeout: int = 60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)


def list_folder(folder_id: str) -> list[tuple[str, str]]:
    page = fetch(f"https://drive.google.com/embeddedfolderview?id={folder_id}").read().decode("utf-8", "replace")
    return [(identifier, html.unescape(name)) for identifier, name in ENTRY.findall(page)]


def norm(name: str) -> str:
    return unicodedata.normalize("NFC", name)


def human(size: float) -> str:
    return f"{size / 1024**3:.2f} GB" if size >= 1024**3 else f"{size / 1024**2:.1f} MB"


def clock(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def load_result(out: Path, root_id: str) -> dict:
    """`result.json` ni yuklaydi; uzilgan eksportning oxirini yopadi."""
    target = out / "result.json"
    entries = dict(((name, identifier) for identifier, name in list_folder(root_id)))
    if "result.json" not in entries:
        sys.exit("Papkada result.json yo'q")
    if not target.is_file():
        url = f"https://drive.usercontent.google.com/download?id={entries['result.json']}&export=download&confirm=t"
        target.write_bytes(fetch(url, 120).read())
    text = target.read_text(encoding="utf-8").rstrip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        data = json.loads(text + "\n ]\n}")  # uzilgan eksport: oxirgi to'liq xabargacha
        target.with_name("result.original.json").write_text(text, encoding="utf-8")
        target.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print("Eslatma: result.json uzilgan eksportdan, oxiri yopildi (asl nusxa result.original.json).")
        return data


class Progress:
    def __init__(self, total_files: int, total_bytes: int, out: Path) -> None:
        self.total_files, self.total_bytes = total_files, total_bytes
        self.files = self.bytes = self.start_bytes = 0
        self.inflight: dict[str, int] = {}
        self.failed: list[str] = []
        self.lock = threading.Lock()
        self.started = time.monotonic()
        self.last = 0.0
        self.out = out

    def show(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self.last < 0.5:
            return
        self.last = now
        done = self.bytes + sum(self.inflight.values())
        speed = (done - self.start_bytes) / max(now - self.started, 1e-6)
        left = (self.total_bytes - done) / speed if speed > 0 else 0
        percent = min(100.0, done * 100 / self.total_bytes) if self.total_bytes else 100.0
        line = (
            f"[{percent:5.1f}%] {self.files}/{self.total_files} fayl | {human(done)} / {human(self.total_bytes)} | "
            f"{human(speed)}/s | qoldi {clock(left)} | xato {len(self.failed)}"
        )
        print("\r" + line.ljust(130), end="", flush=True)
        (self.out / "progress.json").write_text(
            json.dumps(
                {
                    "percent": round(percent, 1),
                    "files": self.files,
                    "total_files": self.total_files,
                    "bytes": done,
                    "total_bytes": self.total_bytes,
                    "failed": len(self.failed),
                    "updated": time.time(),
                }
            ),
            encoding="utf-8",
        )


def download_one(identifier: str, destination: Path, size: int, progress: Progress, key: str) -> None:
    if destination.is_file() and (size == 0 or destination.stat().st_size == size):
        with progress.lock:
            progress.files += 1
            progress.bytes += destination.stat().st_size
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    url = f"https://drive.usercontent.google.com/download?id={identifier}&export=download&confirm=t"
    last_error = ""
    for attempt in range(4):
        try:
            with fetch(url, 120) as response:
                if "text/html" in response.headers.get("Content-Type", ""):
                    raise OSError("Drive fayl o'rniga sahifa qaytardi (kvota yoki ruxsat)")
                received = 0
                with partial.open("wb") as handle:
                    while chunk := response.read(1024 * 1024):
                        handle.write(chunk)
                        received += len(chunk)
                        progress.inflight[key] = received
                        progress.show()
            if size and received != size:
                raise OSError(f"hajm mos emas: {received} != {size}")
            partial.replace(destination)
            with progress.lock:
                progress.files += 1
                progress.bytes += received
            progress.inflight.pop(key, None)
            return
        except Exception as error:  # noqa: BLE001  (bitta fayl butun jarayonni to'xtatmasin)
            last_error = repr(error)
            progress.inflight.pop(key, None)
            time.sleep(5 * (attempt + 1))
    partial.unlink(missing_ok=True)
    progress.failed.append(f"{key}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder_id")
    parser.add_argument("--out", default="var/export")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--kinds", help="vergul bilan media_type ro'yxati (masalan audio_file,voice_message)")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    data = load_result(out, args.folder_id)
    kinds = set(args.kinds.split(",")) if args.kinds else None
    wanted: dict[str, int] = {}
    for message in data["messages"]:
        if message.get("type") != "message":
            continue
        media = message.get("media_type") or ("photo" if message.get("photo") else None)
        path = message.get("file") or message.get("photo")
        if not path or str(path).startswith("(") or (kinds and media not in kinds):
            continue
        wanted[path] = message.get("file_size") or message.get("photo_file_size") or 0

    folders = {name: identifier for identifier, name in list_folder(args.folder_id)}
    index: dict[tuple[str, str], str] = {}
    for folder in {path.split("/")[0] for path in wanted}:
        if folder in folders:
            for identifier, name in list_folder(folders[folder]):
                index[(folder, norm(name))] = identifier
    jobs, missing = [], []
    for path, size in wanted.items():
        folder, _, name = path.partition("/")
        identifier = index.get((folder, norm(name)))
        (jobs if identifier else missing).append((identifier, path, size) if identifier else path)
    print(f"Jami {len(wanted)} fayl, Drive'da topildi {len(jobs)}, topilmadi {len(missing)}.")

    progress = Progress(len(jobs), sum(size for _, _, size in jobs), out)
    progress.show(force=True)
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for identifier, path, size in jobs:
            pool.submit(download_one, identifier, out / path, size, progress, path)
        pool.shutdown(wait=True)
    progress.show(force=True)
    print(f"\nTayyor. Yuklandi {progress.files}/{len(jobs)}, xato {len(progress.failed)}, topilmadi {len(missing)}.")
    for line in progress.failed[:20]:
        print("  xato:", line)
    if missing:
        (out / "missing.txt").write_text("\n".join(missing), encoding="utf-8")
        print(f"Topilmaganlar ro'yxati: {out / 'missing.txt'}")
    return 1 if progress.failed else 0


if __name__ == "__main__":
    sys.exit(main())

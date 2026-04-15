"""
fetch_data.py

Step 1: make sure the two raw inputs are on disk.

Input 1, the labMT 1.0 lexicon
    data/raw/Data_Set_S1.txt
    Supporting Information from Dodds et al. 2011, PLoS ONE. Not
    redistributed inside this repo because it is a PLoS SI file, see
    data/raw/README.md for manual download instructions.

Input 2, the State of the Union (SOTU) corpus
    data/raw/sotu/*.txt
    Full text of every US presidential State of the Union address from
    George Washington (1790) through Donald Trump (2020). I pull these
    from the `martin-martin/sotu-speeches` GitHub repository, which
    mirrors the canonical texts from stateoftheunion.onetwothree. The
    files are public-domain government speech.

    File naming convention (as-is from the upstream repo):
        {president_slug}-{month}_{day}-{year}.txt
    for example:
        abraham_lincoln-december_1-1862.txt
        donald_j._trump-february_5-2019.txt

    This script downloads every .txt in the `speeches/` directory of
    the upstream repo via the GitHub contents API, skipping files that
    are already on disk. A cold run takes roughly two minutes.
"""

from __future__ import annotations

import json
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SOTU_DIR = RAW / "sotu"
LABMT = RAW / "Data_Set_S1.txt"

UPSTREAM_API = (
    "https://api.github.com/repos/martin-martin/sotu-speeches/contents/speeches"
)
USER_AGENT = "repair-assignment-labmt/1.0 (+https://github.com/)"


CURL = shutil.which("curl")


def _urllib_ctx() -> ssl.SSLContext:
    # Try system default, fall back to unverified. Public GitHub content.
    try:
        return ssl.create_default_context()
    except Exception:
        return ssl._create_unverified_context()


def _http_get_bytes(url: str) -> bytes:
    # Prefer curl when available, it works around the stock macOS Python
    # cert store problem. Falls back to urllib otherwise.
    if CURL:
        out = subprocess.run(
            [CURL, "-sSL", "--fail", "-A", USER_AGENT, url],
            capture_output=True, check=True,
        )
        return out.stdout
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60, context=_urllib_ctx()) as resp:
        return resp.read()


def _http_get_json(url: str) -> list[dict]:
    return json.loads(_http_get_bytes(url).decode("utf-8"))


def check_labmt() -> None:
    if not LABMT.exists():
        print(
            "[labmt] MISSING: expected data/raw/Data_Set_S1.txt\n"
            "        See data/raw/README.md for manual download\n"
            "        instructions (PLoS supporting information).",
            file=sys.stderr,
        )
        sys.exit(1)
    size_kb = LABMT.stat().st_size // 1024
    print(f"[labmt] ok, {size_kb} KB at {LABMT}")


def list_remote_sotu() -> list[dict]:
    items: list[dict] = []
    for page in (1, 2, 3):
        url = f"{UPSTREAM_API}?per_page=300&page={page}"
        try:
            chunk = _http_get_json(url)
        except urllib.error.HTTPError as err:
            raise RuntimeError(
                f"GitHub contents API failed at page {page}: {err}"
            ) from err
        if not chunk:
            break
        items.extend([
            f for f in chunk
            if f.get("type") == "file" and f.get("name", "").endswith(".txt")
        ])
        if len(chunk) < 300:
            break
    return items


def fetch_sotu() -> None:
    SOTU_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[sotu] listing upstream files via GitHub contents API ...")
    try:
        files = list_remote_sotu()
    except Exception as err:
        on_disk = sum(1 for p in SOTU_DIR.glob("*.txt"))
        if on_disk >= 200:
            print(f"[sotu] could not reach GitHub ({err}), but {on_disk} "
                  f"files are already on disk, continuing.")
            return
        print(
            f"[sotu] could not reach GitHub ({err}).\n"
            f"       If you are offline, place the .txt files manually in\n"
            f"       {SOTU_DIR} and rerun. See data/raw/README.md.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"[sotu] upstream has {len(files)} txt files")
    downloaded = 0
    cached = 0
    for i, f in enumerate(files, start=1):
        name = f["name"]
        local = SOTU_DIR / name
        if local.exists() and local.stat().st_size > 0:
            cached += 1
            continue
        url = f["download_url"]
        try:
            data = _http_get_bytes(url)
        except Exception as err:
            print(f"[sotu] WARN: could not fetch {name} ({err})")
            continue
        local.write_bytes(data)
        downloaded += 1
        if downloaded % 25 == 0:
            print(f"[sotu] downloaded {downloaded} so far "
                  f"({i}/{len(files)}) ...")
        time.sleep(0.05)

    on_disk = sum(1 for p in SOTU_DIR.glob("*.txt") if p.stat().st_size > 0)
    print(f"[sotu] done. cached={cached}, downloaded={downloaded}, "
          f"on_disk={on_disk}")
    if on_disk < 200:
        print(
            f"[sotu] WARN: only {on_disk} files on disk, expected ~460.\n"
            f"       Rerun, or fetch the rest manually from\n"
            f"       https://github.com/martin-martin/sotu-speeches",
            file=sys.stderr,
        )


def main() -> None:
    check_labmt()
    fetch_sotu()


if __name__ == "__main__":
    main()

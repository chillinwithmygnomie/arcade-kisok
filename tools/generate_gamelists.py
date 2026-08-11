#!/usr/bin/env python3
"""
generate_gamelists.py (enhanced)

Scans a roms directory (default /home/kiosk/roms) and creates/updates
~/.emulationstation/gamelists/<system>/gamelist.xml files.

Optional metadata and box-art fetching via TheGamesDB API when --fetch-art
is passed (or when enabled in the config file at
/home/kiosk/.config/arcade-kiosk/metadata.json).

This script tries to be robust: it falls back to local images if network
fetching fails or is disabled, backs up existing gamelists, and preserves
existing <game> entries when run with --merge.

Run as the kiosk user (or the systemd unit will run it as kiosk).
"""

import argparse
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import shutil
import time
import json
import sys

# For HTTP requests we use urllib so no extra deps are required
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# Basic mapping of system -> allowed extensions (lowercase)
DEFAULT_EXTS = {
    "nes": [".nes", ".zip"],
    "snes": [".sfc", ".smc", ".zip"],
    "genesis": [".md", ".gen", ".bin", ".zip"],
    "psx": [".iso", ".bin", ".img", ".cue", ".zip"],
    "n64": [".z64", ".n64", ".v64", ".zip"],
    "dreamcast": [".cdi", ".gdi", ".chd", ".zip"],
    "arcade": [".zip", ".7z"]
}

CONFIG_PATH = Path.home() / '.config' / 'arcade-kiosk' / 'metadata.json'
THEGAMESDB_API = 'https://api.thegamesdb.net/v1/Games/ByGameName'


def load_config():
    cfg = {
        'provider': 'thegamesdb',
        'api_key': None,
        'fetch_on_boot': False,
        'sleep_between_requests': 0.5
    }
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cfg.update({k: data.get(k, cfg[k]) for k in cfg})
    except Exception:
        pass
    return cfg


def pretty_name_from_filename(fn: str) -> str:
    name = Path(fn).stem
    name = name.replace('_', ' ').replace('-', ' ')
    import re
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name)
    return ' '.join(name.split()).strip()


def load_existing_gamelist(path: Path):
    if not path.exists():
        return {}
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        d = {}
        for game in root.findall('game'):
            gpath = game.findtext('path') or ''
            d[gpath] = game
        return d
    except Exception:
        return {}


def make_game_element(relpath: str, name: str, image: str = None, desc: str = '', releasedate: str = '', publisher: str = ''):
    g = ET.Element('game')
    p = ET.SubElement(g, 'path')
    p.text = relpath
    n = ET.SubElement(g, 'name')
    n.text = name
    if image:
        i = ET.SubElement(g, 'image')
        i.text = image
    d = ET.SubElement(g, 'desc')
    d.text = desc or ''
    ed = ET.SubElement(g, 'releasedate')
    ed.text = releasedate or ''
    pub = ET.SubElement(g, 'publisher')
    pub.text = publisher or ''
    return g


def write_gamelist(outpath: Path, game_elements):
    root = ET.Element('gameList')
    for g in game_elements:
        root.append(g)
    tree = ET.ElementTree(root)
    if outpath.exists():
        bak = outpath.with_suffix(outpath.suffix + '.' + datetime.utcnow().strftime('%Y%m%dT%H%M%SZ') + '.bak')
        try:
            shutil.copy2(str(outpath), str(bak))
        except Exception:
            pass
    outpath.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(outpath), encoding='utf-8', xml_declaration=True)


def download_image(url: str, dest: Path):
    try:
        req = Request(url, headers={'User-Agent': 'arcade-kiosk/1.0'})
        with urlopen(req, timeout=20) as resp:
            data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, 'wb') as f:
                f.write(data)
        return True
    except Exception as e:
        print(f'Image download failed: {e}', file=sys.stderr)
        return False


def query_thegamesdb(title: str, api_key: str):
    # Best-effort query. TheGamesDB expects ?name=...&apikey=...
    q = f"{THEGAMESDB_API}?name={quote(title)}&apikey={quote(api_key)}"
    try:
        req = Request(q, headers={'User-Agent': 'arcade-kiosk/1.0', 'Accept': 'application/json'})
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
            data = json.loads(raw.decode('utf-8', errors='ignore'))
            return data
    except HTTPError as e:
        print(f'HTTP error querying TheGamesDB: {e}', file=sys.stderr)
    except URLError as e:
        print(f'URL error querying TheGamesDB: {e}', file=sys.stderr)
    except Exception as e:
        print(f'Generic error querying TheGamesDB: {e}', file=sys.stderr)
    return None


def extract_metadata_from_response(resp_json):
    # Best-effort parsing of TheGamesDB response structure
    if not resp_json or 'data' not in resp_json:
        return None
    data = resp_json['data']
    games = data.get('games') or []
    base = data.get('base_url') or {}
    base_url = base.get('original') or base.get('thumb') or ''
    if not games:
        return None
    g = games[0]
    metadata = {}
    metadata['name'] = g.get('game_title') or g.get('name') or ''
    metadata['desc'] = g.get('overview') or g.get('short_description') or ''
    metadata['releasedate'] = g.get('release_date') or ''
    # publisher may be a list in some APIs; try several keys
    publisher = g.get('publisher') or g.get('publishers') or ''
    if isinstance(publisher, list):
        metadata['publisher'] = ', '.join(publisher)
    else:
        metadata['publisher'] = publisher or ''
    # find an image: try game.images.boxart or game.images.boxart[0]
    image_url = None
    imgs = g.get('images') or {}
    # common shape: images: {boxart: [{filename: '...'}], fanart: [...]}
    if isinstance(imgs, dict):
        boxarts = imgs.get('boxart') or imgs.get('boxart_front') or []
        if isinstance(boxarts, list) and boxarts:
            fname = boxarts[0].get('filename') if isinstance(boxarts[0], dict) else boxarts[0]
            if fname and base_url:
                image_url = base_url.rstrip('/') + '/' + fname.lstrip('/')
    # fallback: some APIs put 'image' or 'boxart' at top-level
    if not image_url:
        if g.get('image') and base_url:
            image_url = base_url.rstrip('/') + '/' + g.get('image').lstrip('/')
    metadata['image_url'] = image_url
    return metadata


def find_local_image(rompath: Path):
    images_dir = rompath.parent / 'images'
    if images_dir.is_dir():
        for ext in ('.png', '.jpg', '.jpeg'):
            candidate = images_dir / (rompath.stem + ext)
            if candidate.exists():
                return str(candidate.resolve())
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--romdir', default='/home/kiosk/roms', help='Top-level roms directory')
    ap.add_argument('--merge', action='store_true', help='Merge with existing gamelist entries when paths match')
    ap.add_argument('--exts-file', help='Optional JSON file mapping system->extensions')
    ap.add_argument('--fetch-art', action='store_true', help='Fetch metadata and box art from TheGamesDB')
    args = ap.parse_args()

    romroot = Path(args.romdir)
    if not romroot.is_dir():
        print(f'Rom dir does not exist: {romroot}', file=sys.stderr)
        return

    cfg = load_config()
    if not args.fetch_art and cfg.get('fetch_on_boot'):
        fetch_enabled = True
    else:
        fetch_enabled = bool(args.fetch_art)

    api_key = cfg.get('api_key')
    sleep_between = cfg.get('sleep_between_requests', 0.5)

    exts_map = DEFAULT_EXTS

    for system_dir in sorted(p for p in romroot.iterdir() if p.is_dir()):
        system = system_dir.name
        allowed = exts_map.get(system, None)

        def is_rom_file(p: Path):
            if p.is_dir():
                return False
            if allowed:
                return p.suffix.lower() in allowed
            return True

        rom_files = [p for p in system_dir.iterdir() if is_rom_file(p)]
        user_gamelist_dir = Path.home() / '.emulationstation' / 'gamelists' / system
        outpath = user_gamelist_dir / 'gamelist.xml'
        existing = load_existing_gamelist(outpath) if args.merge else {}
        game_elements = []

        for rom in sorted(rom_files):
            relpath = f'./{rom.name}'
            if args.merge and relpath in existing:
                game_elements.append(existing[relpath])
                continue

            name = pretty_name_from_filename(rom.name)
            desc = ''
            releasedate = ''
            publisher = ''
            image = find_local_image(rom)

            # Attempt metadata fetch if enabled and we have an API key
            if fetch_enabled and api_key:
                try:
                    # Query using cleaned name first
                    print(f'Querying metadata for: {name}', file=sys.stderr)
                    resp = query_thegamesdb(name, api_key)
                    meta = extract_metadata_from_response(resp)
                    # If no match, try without trailing tokens (common in rom filenames)
                    if not meta:
                        alt_name = name.split(' ')[0:5]
                        alt_name = ' '.join(alt_name)
                        resp = query_thegamesdb(alt_name, api_key)
                        meta = extract_metadata_from_response(resp)
                    if meta:
                        if meta.get('name'):
                            name = meta.get('name')
                        desc = meta.get('desc') or ''
                        releasedate = meta.get('releasedate') or ''
                        publisher = meta.get('publisher') or ''
                        image_url = meta.get('image_url')
                        if image_url and not image:
                            # download to /home/kiosk/roms/<system>/images/<stem>.<ext>
                            img_ext = os.path.splitext(image_url)[1]
                            if not img_ext:
                                img_ext = '.png'
                            dest = system_dir / 'images' / (rom.stem + img_ext)
                            ok = download_image(image_url, dest)
                            if ok:
                                image = str(dest.resolve())
                    time.sleep(sleep_between)
                except Exception as e:
                    print(f'Metadata fetch error for {name}: {e}', file=sys.stderr)

            game_elements.append(make_game_element(relpath, name, image, desc, releasedate, publisher))

        write_gamelist(outpath, game_elements)
        print(f'Wrote {outpath} with {len(game_elements)} games (system={system})')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
generate_gamelists.py

Scan a roms directory (default /home/kiosk/roms) and create/update
~/.emulationstation/gamelists/<system>/gamelist.xml files.

Usage:
  python3 generate_gamelists.py --romdir /home/kiosk/roms
  python3 generate_gamelists.py --romdir /home/kiosk/roms --merge

This script is intended to run as the kiosk user.
"""
import argparse
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import shutil

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


def pretty_name_from_filename(fn: str) -> str:
    name = Path(fn).stem
    # replace underscores/dashes with spaces, remove extraneous tokens
    name = name.replace('_', ' ').replace('-', ' ')
    # remove common region tags like (U), [!] etc.
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


def make_game_element(relpath: str, name: str, image: str = None):
    g = ET.Element('game')
    p = ET.SubElement(g, 'path')
    p.text = relpath
    n = ET.SubElement(g, 'name')
    n.text = name
    if image:
        i = ET.SubElement(g, 'image')
        i.text = image
    # placeholders for other metadata
    d = ET.SubElement(g, 'desc')
    d.text = ''
    ed = ET.SubElement(g, 'releasedate')
    ed.text = ''
    pub = ET.SubElement(g, 'publisher')
    pub.text = ''
    return g


def write_gamelist(outpath: Path, game_elements):
    root = ET.Element('gameList')
    for g in game_elements:
        root.append(g)
    tree = ET.ElementTree(root)
    # backup existing
    if outpath.exists():
        bak = outpath.with_suffix(outpath.suffix + '.' + datetime.utcnow().strftime('%Y%m%dT%H%M%SZ') + '.bak')
        try:
            shutil.copy2(str(outpath), str(bak))
        except Exception:
            pass
    outpath.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(outpath), encoding='utf-8', xml_declaration=True)


def find_local_image(rompath: Path):
    # Look for images with the same stem in an images/ subfolder (png/jpg)
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
    args = ap.parse_args()

    romroot = Path(args.romdir)
    if not romroot.is_dir():
        print(f'Rom dir does not exist: {romroot}')
        return

    exts_map = DEFAULT_EXTS

    for system_dir in sorted(p for p in romroot.iterdir() if p.is_dir()):
        system = system_dir.name
        allowed = exts_map.get(system, None)
        # if no known extensions, include most files
        def is_rom_file(p: Path):
            if p.is_dir():
                return False
            if allowed:
                return p.suffix.lower() in allowed
            return True

        rom_files = [p for p in system_dir.iterdir() if is_rom_file(p)]
        # target gamelist path
        user_gamelist_dir = Path.home() / '.emulationstation' / 'gamelists' / system
        outpath = user_gamelist_dir / 'gamelist.xml'
        existing = load_existing_gamelist(outpath) if args.merge else {}
        game_elements = []

        for rom in sorted(rom_files):
            relpath = f'./{rom.name}'
            if args.merge and relpath in existing:
                # reuse existing element to preserve metadata
                game_elements.append(existing[relpath])
                continue
            name = pretty_name_from_filename(rom.name)
            image = find_local_image(rom)
            game_elements.append(make_game_element(relpath, name, image))

        write_gamelist(outpath, game_elements)
        print(f'Wrote {outpath} with {len(game_elements)} games (system={system})')

if __name__ == '__main__':
    main()

from pathlib import Path
from datetime import datetime
import shutil
import unicodedata
import re
import sys
import xml.etree.ElementTree as ET
import json

OLD_ROOT = Path(r"C:\Users\bormi\Documents\vus-flask2")
NEW_ROOT = Path(r"C:\Users\bormi\Documents\vus-flask-clean")

OLD_CC = OLD_ROOT / "static" / "Krizanke" / "CrosswordCompilerApp"
NEW_CC = NEW_ROOT / "static" / "Krizanke" / "CrosswordCompilerApp"

OLD_IMAGES = OLD_ROOT / "static" / "Images"
NEW_IMAGES = NEW_ROOT / "static" / "Images"

MAX_IMAGE_WORDS = 30
IMAGE_MAP_FILE = NEW_ROOT / "data" / "image_map.json"


def load_image_map():
    if not IMAGE_MAP_FILE.exists():
        return {}

    try:
        with open(IMAGE_MAP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_image_map(image_map):
    IMAGE_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(IMAGE_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(
            image_map,
            f,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

def make_slug(opis: str, dodatno: str = "", max_words: int = 30) -> str:
    text = " ".join(
        part for part in [(opis or "").strip(), (dodatno or "").strip()]
        if part
    ).strip()

    if not text:
        return "slika"

    words = text.split()[:max_words]
    s = " ".join(words)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "slika"


def candidate_image_names(opis: str, dodatno: str = ""):
    slugs = []

    for max_words in (40, 30, 15):
        s = make_slug(opis, dodatno, max_words)
        if s and s not in slugs:
            slugs.append(s)

    exts = [".jpg", ".jpeg", ".png", ".webp"]
    dup_suffixes = [""] + [f" ({i})" for i in range(1, 6)]

    for slug in slugs:
        for ext in exts:
            for suf in dup_suffixes:
                yield f"{slug}{suf}{ext}"


def find_candidates_by_answer(geslo: str):
    if not geslo:
        return []

    needle = make_slug(geslo, "", 10)

    if len(needle) < 3:
        return []

    found = []

    for folder in (NEW_IMAGES, OLD_IMAGES):
        if not folder.exists():
            continue

        for p in folder.iterdir():
            if not p.is_file():
                continue

            if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                continue

            stem = p.stem.lower()
            tokens = stem.split("_")

            if needle in tokens:
                key = p.name.lower()

                if key not in {x.lower() for x in found}:
                    found.append(p.name)

    return sorted(found)
def get_mapped_image(geslo: str):
    if not geslo:
        return None

    image_map = load_image_map()
    key = geslo.strip().upper()

    filename = image_map.get(key)

    if not filename:
        return None

    for folder in (NEW_IMAGES, OLD_IMAGES):
        p = folder / filename

        if p.exists():
            return filename

    return None
def choose_and_save_image(geslo: str, candidates):
    if not geslo or not candidates:
        return None

    print()
    print(f"GESLO: {geslo}")
    print("Možne obstoječe slike:")

    for i, filename in enumerate(candidates, start=1):
        print(f"{i} - {filename}")

    print("0 - nobena od teh")

    while True:
        izbira = input("Izberi številko: ").strip()

        if izbira == "0":
            return None

        if izbira.isdigit():
            idx = int(izbira)

            if 1 <= idx <= len(candidates):
                filename = candidates[idx - 1]

                image_map = load_image_map()
                image_map[geslo.strip().upper()] = filename
                save_image_map(image_map)

                print(f"SHRANJENO: {geslo} -> {filename}")
                return filename

        print("Neveljavna izbira.")

def extract_texts_from_xml(xml_path: Path):
    """
    Prebere Crossword XML in poveže opis z dejanskim geslom/rešitvijo.
    Vrne trojice: (opis, dodatno, geslo).
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # word id -> rešitev
    solutions = {}

    for elem in root.iter():
        tag = elem.tag.split("}")[-1]

        if tag == "word":
            word_id = (elem.attrib.get("id") or "").strip()
            solution = (elem.attrib.get("solution") or "").strip()

            if word_id and solution:
                solutions[word_id] = solution

    pairs = set()

    for elem in root.iter():
        tag = elem.tag.split("}")[-1]

        if tag != "clue":
            continue

        opis = (elem.text or "").strip()
        if not opis:
            continue

        word_id = (elem.attrib.get("word") or "").strip()
        geslo = solutions.get(word_id, "")

        dodatno = (
            elem.attrib.get("answer")
            or elem.attrib.get("geslo")
            or elem.attrib.get("resitev")
            or ""
        ).strip()

        pairs.add((opis, dodatno, geslo))

    return pairs


def copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"OK kopirano: {dst}")


def transfer_crossword(date_str: str):
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    ym = d.strftime("%Y-%m")

    old_js = OLD_CC / ym / f"{date_str}.js"
    old_xml = OLD_CC / ym / f"{date_str}.xml"

    new_js = NEW_CC / ym / f"{date_str}.js"
    new_xml = NEW_CC / ym / f"{date_str}.xml"

    if not old_js.exists():
        print(f"MANJKA JS: {old_js}")
    else:
        copy_file(old_js, new_js)

    if old_xml.exists():
        copy_file(old_xml, new_xml)
        xml_for_reading = old_xml
    elif new_xml.exists():
        print(f"XML že obstaja v clean: {new_xml}")
        xml_for_reading = new_xml
    else:
        print(f"MANJKA XML tudi v starem in clean: {old_xml}")
        return

    NEW_IMAGES.mkdir(parents=True, exist_ok=True)

    pairs = extract_texts_from_xml(xml_for_reading)

    copied = 0
    missing = []
    used_files = set()

    for opis, dodatno, geslo in pairs:
        found = False

        # 1. Najprej išči sliko po trenutnem opisu
        for fname in candidate_image_names(opis, dodatno):
            src = OLD_IMAGES / fname

            if not src.exists():
                src = NEW_IMAGES / fname

            if src.exists():
                dst = NEW_IMAGES / fname

                if src.resolve() != dst.resolve():
                    copy_file(src, dst)
                else:
                    print(f"OK že obstaja: {dst}")

                used_files.add(fname)
                copied += 1
                found = True
                break

        # 2. Če je po opisu ni, preveri trajno povezavo po geslu
        if not found:
            mapped = get_mapped_image(geslo)

            if mapped:
                src = NEW_IMAGES / mapped

                if not src.exists():
                    src = OLD_IMAGES / mapped

                if src.exists():
                    dst = NEW_IMAGES / mapped

                    if src.resolve() != dst.resolve():
                        copy_file(src, dst)
                    else:
                        print(f"OK po geslu že obstaja: {dst}")

                    used_files.add(mapped)
                    copied += 1
                    found = True

        # 3. Če slike še vedno ni, poišči možne stare slike
        # najprej po geslu v imenu datoteke,
        # nato še po starih opisih istega gesla iz VUS.db
        if not found:
            candidates = find_candidates_by_answer(geslo)

            old_description_candidates = find_candidates_by_old_descriptions(geslo)

            for filename in old_description_candidates:
                if filename not in candidates:
                    candidates.append(filename)

            if candidates:
                print()
                print("=" * 70)
                print("SLIKA PO OPISU NI NAJDENA")
                print(f"GESLO: {geslo}")
                print(f"OPIS: {opis}")

                mapped = choose_and_save_image(geslo, candidates)

                if mapped:
                    src = NEW_IMAGES / mapped

                    if not src.exists():
                        src = OLD_IMAGES / mapped

                    if src.exists():
                        dst = NEW_IMAGES / mapped

                        if src.resolve() != dst.resolve():
                            copy_file(src, dst)
                        else:
                            print(f"OK izbrana slika že obstaja: {dst}")

                        used_files.add(mapped)
                        copied += 1
                        found = True

                if mapped:
                    src = NEW_IMAGES / mapped

                    if not src.exists():
                        src = OLD_IMAGES / mapped

                    if src.exists():
                        dst = NEW_IMAGES / mapped

                        if src.resolve() != dst.resolve():
                            copy_file(src, dst)
                        else:
                            print(f"OK izbrana slika že obstaja: {dst}")

                        used_files.add(mapped)
                        copied += 1
                        found = True

        # 4. Če tudi po geslu ni ustrezne slike
        if not found:
            missing.append((geslo, opis))

    MAX_MISSING = 40

    print()
    print("------ POVZETEK ------")
    print(f"Datum: {date_str}")
    print(f"Najdenih opisov: {len(pairs)}")
    print(f"Kopiranih slik: {copied}")
    print(f"Manjkajočih slik: {len(missing)}")

    if missing:
        print()
        print(f"Prvih {MAX_MISSING} manjkajočih:")

        for geslo, opis in missing[:MAX_MISSING]:
            print(f"- {geslo} :: {opis}")

    print()
    print("------ GIT UKAZI ------")
    print(f"git add static/Krizanke/CrosswordCompilerApp/{ym}/{date_str}.xml")
    print(f"git add static/Krizanke/CrosswordCompilerApp/{ym}/{date_str}.js")

    print()
    print(f'git commit -m "dodaj krizanko {date_str}"')
    print("git push")

def find_candidates_by_old_descriptions(geslo: str):
    if not geslo:
        return []

    db_path = Path(r"C:\Users\bormi\Documents\VUS\VUS.db")

    if not db_path.exists():
        return []

    import sqlite3

    found = []

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT opis
            FROM slovar
            WHERE UPPER(geslo) = UPPER(?)
              AND opis IS NOT NULL
              AND TRIM(opis) <> ''
            """,
            (geslo,),
        ).fetchall()

    for (old_opis,) in rows:
        old_slug = make_slug(old_opis, "", 40)

        if not old_slug:
            continue

        ignore_tokens = {
            "zastar", "star", "knjiz", "pog", "ekspr",
            "anat", "med", "gastr", "kem", "lingv",
            "zgod", "rel", "geogr", "zool", "bot", "nekd"
        }

        old_tokens = [
            x for x in old_slug.split("_")
            if len(x) >= 3 and x not in ignore_tokens
        ]

        for folder in (NEW_IMAGES, OLD_IMAGES):
            if not folder.exists():
                continue

            for p in folder.iterdir():
                if not p.is_file():
                    continue

                if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                    continue

                stem = p.stem.lower()
                stem_tokens = stem.split("_")

                matches = sum(1 for token in old_tokens if token in stem_tokens)

                if old_tokens and matches == len(old_tokens):
                    key = p.name.lower()

                    if key not in {x.lower() for x in found}:
                        found.append(p.name)

    return sorted(found)

def find_candidates_by_description_words(opis: str):
    if not opis:
        return []

    slug = make_slug(opis, "", 40)

    ignore_tokens = {
        "zastar", "star", "knjiz", "pog", "ekspr",
        "anat", "med", "gastr", "kem", "lingv",
        "zgod", "rel", "geogr", "zool", "bot", "nekd",
        "ki", "je", "in", "ali", "se", "na", "za",
        "od", "do", "pri", "kot", "ter", "s", "z",
        "v", "iz", "po"
    }

    tokens = [
        x for x in slug.split("_")
        if len(x) >= 4 and x not in ignore_tokens
    ]

    if not tokens:
        return []

    found = []

    for folder in (NEW_IMAGES, OLD_IMAGES):
        if not folder.exists():
            continue

        for p in folder.iterdir():
            if not p.is_file():
                continue

            if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                continue

            stem_tokens = set(p.stem.lower().split("_"))

            matches = sum(1 for token in tokens if token in stem_tokens)

            # Zahtevamo vsaj 3 pomembne skupne besede.
            # Pri kratkem opisu pa najmanj polovico besed.
            required = min(3, max(1, (len(tokens) + 1) // 2))

            if matches >= required:
                key = p.name.lower()

                if key not in {x.lower() for x in found}:
                    found.append(p.name)

    return sorted(found)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uporaba:")
        print("python prenesi_krizanko.py 2026-06-04")
        sys.exit(1)

    transfer_crossword(sys.argv[1])
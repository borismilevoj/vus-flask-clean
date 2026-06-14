from pathlib import Path
from datetime import datetime
import shutil
import unicodedata
import re
import sys
import xml.etree.ElementTree as ET

OLD_ROOT = Path(r"C:\Users\bormi\Documents\vus-flask2")
NEW_ROOT = Path(r"C:\Users\bormi\Documents\vus-flask-clean")

OLD_CC = OLD_ROOT / "static" / "Krizanke" / "CrosswordCompilerApp"
NEW_CC = NEW_ROOT / "static" / "Krizanke" / "CrosswordCompilerApp"

OLD_IMAGES = OLD_ROOT / "static" / "Images"
NEW_IMAGES = NEW_ROOT / "static" / "Images"

MAX_IMAGE_WORDS = 30


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

    s30 = make_slug(opis, dodatno, 30)
    if s30:
        slugs.append(s30)

    s15 = make_slug(opis, dodatno, 15)
    if s15 and s15 not in slugs:
        slugs.append(s15)

    exts = [".jpg", ".jpeg", ".png", ".webp"]
    dup_suffixes = [""] + [f" ({i})" for i in range(1, 6)]

    for slug in slugs:
        for ext in exts:
            for suf in dup_suffixes:
                yield f"{slug}{suf}{ext}"


def extract_texts_from_xml(xml_path: Path):
    """
    Prebere XML in pobere čim več možnih opisov/gesel.
    Namenoma je široko zastavljeno, ker imajo Crossword XML-ji različne strukture.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    pairs = set()

    for elem in root.iter():
        attrs = elem.attrib

        opis = (
            attrs.get("clue")
            or attrs.get("opis")
            or attrs.get("definition")
            or attrs.get("definicija")
            or attrs.get("text")
            or ""
        )

        dodatno = (
            attrs.get("answer")
            or attrs.get("solution")
            or attrs.get("geslo")
            or attrs.get("resitev")
            or ""
        )

        text = (elem.text or "").strip()

        if opis:
            pairs.add((opis.strip(), dodatno.strip()))

        if text and len(text) > 3:
            pairs.add((text, dodatno.strip()))

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
    for opis, dodatno in pairs:
        found = False

        for fname in candidate_image_names(opis, dodatno):
            src = OLD_IMAGES / fname
            if src.exists():
                dst = NEW_IMAGES / fname
                copy_file(src, dst)

                used_files.add(fname)

                copied += 1
                found = True
                break

        if not found:
            missing.append(opis)

    print()
    print("------ POVZETEK ------")
    print(f"Datum: {date_str}")
    print(f"Najdenih opisov: {len(pairs)}")
    print(f"Kopiranih slik: {copied}")
    print(f"Manjkajočih slik: {len(missing)}")

    # print()
    # print("Čiščenje nepotrebnih slik ...")
    #
    # deleted = 0
    #
    # for p in NEW_IMAGES.iterdir():
    #     if not p.is_file():
    #         continue
    #
    #     if p.name.endswith(".bak"):
    #         continue
    #
    #     if p.name not in used_files:
    #         p.unlink()
    #         deleted += 1
    #         print("IZBRISANA:", p.name)
    #
    # print()
    # print(f"Izbrisanih nepotrebnih slik: {deleted}")

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
        for m in missing[:MAX_MISSING]:
            print("-", m)


    print()
    print("------ GIT UKAZI ------")
    print(f"git add static/Krizanke/CrosswordCompilerApp/{ym}/{date_str}.xml")
    print(f"git add static/Krizanke/CrosswordCompilerApp/{ym}/{date_str}.js")
    print("git add static/Images")

    print()
    print(f'git commit -m "dodaj krizanko {date_str}"')
    print("git push")



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uporaba:")
        print("python prenesi_krizanko.py 2026-06-04")
        sys.exit(1)

    transfer_crossword(sys.argv[1])
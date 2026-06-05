from pathlib import Path
from datetime import date, datetime
import re
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CC_DIR = ROOT / "static" / "Krizanke" / "CrosswordCompilerApp"
IMAGES_DIR = ROOT / "static" / "Images"

DANES = date.today()
EXTS = [".jpg", ".jpeg", ".png", ".webp"]


def slug(text: str, max_words: int) -> str:
    text = (text or "").strip()
    words = text.split()[:max_words]
    s = " ".join(words)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "slika"


def datum_iz_xml(p: Path):
    try:
        return datetime.strptime(p.stem, "%Y-%m-%d").date()
    except ValueError:
        return None


def opisi_iz_xml(xml_path: Path):
    try:
        tree = ET.parse(xml_path)
    except Exception:
        return []

    opisi = []
    for elem in tree.getroot().iter():
        text = (elem.text or "").strip()
        if len(text) > 3:
            opisi.append(text)

        for key in ("clue", "opis", "definition", "definicija", "text"):
            val = (elem.attrib.get(key) or "").strip()
            if len(val) > 3:
                opisi.append(val)

    return opisi


def kandidati_slik(opis: str):
    for max_words in (30, 15):
        s = slug(opis, max_words)
        for ext in EXTS:
            yield f"{s}{ext}"
            for i in range(1, 6):
                yield f"{s} ({i}){ext}"


def main(delete=False):
    potrebne = set()

    for xml in CC_DIR.rglob("*.xml"):
        d = datum_iz_xml(xml)

        # obdržimo samo slike za današnje in prihodnje križanke
        if not d or d < DANES:
            continue

        for opis in opisi_iz_xml(xml):
            for fname in kandidati_slik(opis):
                potrebne.add(fname)

    vse_slike = [p for p in IMAGES_DIR.iterdir() if p.is_file()]
    odvecne = [p for p in vse_slike if p.name not in potrebne]

    print(f"Vseh slik: {len(vse_slike)}")
    print(f"Potrebnih za danes/prihodnost: {len([p for p in vse_slike if p.name in potrebne])}")
    print(f"Odvečnih za brisanje: {len(odvecne)}")

    skupno_mb = sum(p.stat().st_size for p in odvecne) / 1024 / 1024
    print(f"Možen prihranek: {skupno_mb:.1f} MB")

    if delete:
        for p in odvecne:
            print("BRIŠEM:", p.name)
            p.unlink()
    else:
        print()
        print("Testni način. Nič ni izbrisano.")
        print("Za dejansko brisanje zaženi:")
        print("python ocisti_slike.py --delete")


if __name__ == "__main__":
    import sys
    main(delete="--delete" in sys.argv)
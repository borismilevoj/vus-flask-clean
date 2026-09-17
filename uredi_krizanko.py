from pathlib import Path
import sys
import shutil
import re
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
OLD_ROOT = Path(r"C:\Users\bormi\Documents\vus-flask2")

CC_DIR = ROOT / "static" / "Krizanke" / "CrosswordCompilerApp"

NEW_IMAGES = ROOT / "static" / "Images"
OLD_IMAGES = OLD_ROOT / "static" / "Images"

EXTS = [".jpg", ".jpeg", ".png", ".webp"]


def local_name(elem):
    return elem.tag.split("}", 1)[-1]


def get_text(elem):
    return "".join(elem.itertext()).strip()


def set_text_preserve_attrs(elem, text):
    for child in list(elem):
        elem.remove(child)
    elem.text = text


def slug(text, max_words=40):
    text = (text or "").strip()
    words = text.split()[:max_words]
    s = " ".join(words)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "slika"


def kandidati_slik(opis):
    for max_words in (40, 30, 15):
        s = slug(opis, max_words)
        for ext in EXTS:
            yield f"{s}{ext}"
            for i in range(1, 21):
                yield f"{s} ({i}){ext}"


def najdi_sliko_po_opisu(opis):
    for fname in kandidati_slik(opis):
        for mapa in (NEW_IMAGES, OLD_IMAGES):
            p = mapa / fname
            if p.exists():
                return p
    return None


def kopiraj_sliko_na_novi_opis(stari_opis, novi_opis):
    src = najdi_sliko_po_opisu(stari_opis)

    if not src:
        print()
        print("SLIKA: stare slike po starem opisu nisem našel.")
        print("Novo sliko lahko dodaš ročno prek Preveri sliko.")
        return

    nova_datoteka = slug(novi_opis, 40) + src.suffix.lower()

    for ciljna_mapa in (NEW_IMAGES, OLD_IMAGES):
        ciljna_mapa.mkdir(parents=True, exist_ok=True)
        dst = ciljna_mapa / nova_datoteka

        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)

        print("SLIKA KOPIRANA:", dst)


def najdi_podatke(root):
    words = {}
    clues = []
    current = None

    for elem in root.iter():
        name = local_name(elem)

        if name == "word":
            wid = elem.attrib.get("id")
            if wid:
                words[wid] = {
                    "id": wid,
                    "solution": elem.attrib.get("solution", ""),
                    "x": elem.attrib.get("x", ""),
                    "y": elem.attrib.get("y", ""),
                }

        elif name == "title":
            t = get_text(elem).lower()
            if "vodoravno" in t:
                current = "vodoravno"
            elif "navpično" in t or "navpicno" in t:
                current = "navpicno"

        elif name == "clue" and current:
            wid = elem.attrib.get("word", "")
            num = elem.attrib.get("number", "")
            opis = get_text(elem)

            if wid and num:
                clues.append({
                    "elem": elem,
                    "word_id": wid,
                    "number": num,
                    "smer": current,
                    "opis": opis,
                    "word": words.get(wid, {}),
                })

    return words, clues


def popravi_js(js_path, stari_opis, novi_opis):
    if not js_path.exists():
        return False

    js_text = js_path.read_text(encoding="utf-8", errors="ignore")

    if stari_opis not in js_text:
        return False

    backup_js = js_path.with_suffix(".js.bak")
    shutil.copy2(js_path, backup_js)

    js_text = js_text.replace(stari_opis, novi_opis)
    js_path.write_text(js_text, encoding="utf-8")

    return True


def prikazi_zadetek(i, c):
    w = c["word"]
    smer = "vodoravno" if c["smer"] == "vodoravno" else "navpično"
    print(f'{i:>2}. št. {c["number"]:<4} {smer:<10} {w.get("solution","")}   x={w.get("x","")} y={w.get("y","")}')


def main(date_str):
    ym = date_str[:7]
    xml_path = CC_DIR / ym / f"{date_str}.xml"
    js_path = CC_DIR / ym / f"{date_str}.js"

    if not xml_path.exists():
        print("MANJKA XML:")
        print(xml_path)
        return

    tree = ET.parse(xml_path)
    root = tree.getroot()

    words, clues = najdi_podatke(root)

    print()
    print("=" * 60)
    print(f"UREDI KRIŽANKO: {date_str}")
    print("=" * 60)
    print("Urejam samo opise. Gesel ne spreminjam.")
    print()

    while True:
        geslo = input("Vpiši geslo za urejanje (Enter = konec): ").strip()

        if not geslo:
            break

        geslo_norm = geslo.upper().replace(" ", "")

        zadetki = []
        for c in clues:
            sol = (c["word"].get("solution", "") or "")
            sol_norm = sol.upper().replace(" ", "")
            if sol_norm == geslo_norm:
                zadetki.append(c)

        if not zadetki:
            print("Gesla nisem našel.")
            continue

        print()
        print("Najdeni zadetki:")
        for i, c in enumerate(zadetki, start=1):
            prikazi_zadetek(i, c)

        if len(zadetki) == 1:
            izbran = zadetki[0]
        else:
            izbira = input("Katero zaporedno številko urejava? ").strip()
            if not izbira.isdigit():
                print("Napačna izbira.")
                continue

            idx = int(izbira) - 1
            if idx < 0 or idx >= len(zadetki):
                print("Napačna izbira.")
                continue

            izbran = zadetki[idx]

        stari_opis = izbran["opis"]
        word = izbran["word"]

        print()
        print("-" * 60)
        print("Številka:", izbran["number"])
        print("Smer:", "vodoravno" if izbran["smer"] == "vodoravno" else "navpično")
        print("Geslo:", word.get("solution", ""))
        print("Koordinate: x =", word.get("x", ""), " y =", word.get("y", ""))
        print()
        print("STARI OPIS:")
        print(stari_opis)
        print("-" * 60)

        novi_opis = input("NOVI OPIS (Enter = preklic): ").strip()

        if not novi_opis:
            print("Preklicano.")
            continue

        print()
        print("NOVI OPIS:")
        print(novi_opis)

        potrdi = input("Shranim spremembo? (D/N): ").strip().lower()

        if potrdi != "d":
            print("Preklicano.")
            continue

        backup_xml = xml_path.with_suffix(".xml.bak")
        shutil.copy2(xml_path, backup_xml)

        set_text_preserve_attrs(izbran["elem"], novi_opis)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)

        js_spremenjen = popravi_js(js_path, stari_opis, novi_opis)

        kopiraj_sliko_na_novi_opis(stari_opis, novi_opis)

        izbran["opis"] = novi_opis

        print()
        print("✔ XML POPRAVLJEN:")
        print(xml_path)
        print("BACKUP:")
        print(backup_xml)

        if js_spremenjen:
            print("✔ JS POPRAVLJEN:")
            print(js_path)
        else:
            print("JS: starega opisa nisem našel ali JS ne obstaja.")

        print()
        print("Lahko urejaš naslednje geslo.")

    print()
    print("KONČANO.")
    print()
    print("GIT UKAZI, ko boš pripravljen:")
    print(f"git add static/Krizanke/CrosswordCompilerApp/{ym}/{date_str}.xml")
    print(f"git add static/Krizanke/CrosswordCompilerApp/{ym}/{date_str}.js")
    print("git add static/Images")
    print(f'git commit -m "popravi opise v krizanki {date_str}"')
    print("git push")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uporaba:")
        print("python uredi_krizanko.py 2026-09-04")
        sys.exit(1)

    main(sys.argv[1])
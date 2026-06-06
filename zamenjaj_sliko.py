from pathlib import Path
import shutil
import unicodedata
import re
import sys

ROOTS = [
    Path(r"C:\Users\bormi\Documents\vus-flask2\static\Images"),
    Path(r"C:\Users\bormi\Documents\vus-flask-clean\static\Images"),
]

EXTS = [".jpg", ".jpeg", ".png", ".webp"]


def slug(opis: str, max_words: int = 30) -> str:
    words = opis.strip().split()[:max_words]
    s = " ".join(words)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "slika"


def kandidati(opis: str):
    slugs = [slug(opis, 30), slug(opis, 15)]
    seen = set()

    for s in slugs:
        if not s or s in seen:
            continue
        seen.add(s)

        for ext in EXTS:
            yield f"{s}{ext}"
            for i in range(1, 6):
                yield f"{s} ({i}){ext}"


def main():
    if len(sys.argv) < 3:
        print("Uporaba:")
        print('python zamenjaj_sliko.py "opis gesla" "C:\\pot\\do\\nove_slike.jpg"')
        return

    opis = sys.argv[1]
    nova_slika = Path(sys.argv[2])

    if not nova_slika.exists():
        print(f"Nova slika ne obstaja: {nova_slika}")
        return

    najdeno = 0

    for mapa in ROOTS:
        if not mapa.exists():
            print(f"Mapa ne obstaja: {mapa}")
            continue

        for ime in kandidati(opis):
            cilj = mapa / ime

            if cilj.exists():
                backup = cilj.with_suffix(cilj.suffix + ".bak")
                shutil.copy2(cilj, backup)
                shutil.copy2(nova_slika, cilj)

                print(f"ZAMENJANO: {cilj}")
                print(f"Backup:    {backup}")
                najdeno += 1
                break

    if najdeno == 0:
        print("Ni našlo stare slike.")
        print("Preveri, ali je opis popolnoma enak tistemu iz križanke/slovarja.")


if __name__ == "__main__":
    main()
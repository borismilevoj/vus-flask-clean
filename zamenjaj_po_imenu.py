from pathlib import Path
import shutil
import sys

ROOTS = [
    Path(r"C:\Users\bormi\Documents\vus-flask2\static\Images"),
    Path(r"C:\Users\bormi\Documents\vus-flask-clean\static\Images"),
]

def main():
    if len(sys.argv) != 3:
        print("Uporaba:")
        print('python zamenjaj_po_imenu.py "ime_slike.jpg" "C:\\pot\\do\\nove_slike.jpg"')
        return

    ime_slike = sys.argv[1]
    nova_slika = Path(sys.argv[2])

    if not nova_slika.exists():
        print(f"NAPAKA: Nova slika ne obstaja: {nova_slika}")
        return

    najdeno = False

    for mapa in ROOTS:
        cilj = mapa / ime_slike

        if cilj.exists():
            backup = cilj.with_suffix(cilj.suffix + ".bak")

            shutil.copy2(cilj, backup)
            shutil.copy2(nova_slika, cilj)

            print()
            print(f"ZAMENJANO: {cilj}")
            print(f"BACKUP:    {backup}")

            najdeno = True

    if not najdeno:
        print()
        print(f"Slike '{ime_slike}' ni našel.")
        print("Preveri ime datoteke.")

if __name__ == "__main__":
    main()
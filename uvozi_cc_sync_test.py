#!/usr/bin/env python3
import argparse, csv, os, sqlite3

def norm(s):
    if s is None: return ""
    return " ".join(s.replace("\u00a0"," ").replace("\u2007"," ").replace("\u202f"," ").strip().split())

def read_pairs(path):
    last=None
    for enc in ("utf-8-sig","utf-8","cp1250","windows-1250","latin1"):
        try:
            f=open(path,"r",encoding=enc,newline="")
            sample=f.read(2048); f.seek(0); break
        except Exception as e: last=e
    else: raise RuntimeError(f"Ne morem odpreti CSV: {last}")
    delim=";" if sample.count(";") > sample.count(",") else ","
    pairs=set(); rows=empty=0
    with f:
        for row in csv.reader(f,delimiter=delim):
            if not row: continue
            rows+=1
            g=norm(row[0] if len(row)>0 else "")
            o=norm(row[1] if len(row)>1 else "")
            if not g or not o: empty+=1; continue
            pairs.add((g,o))
    return pairs,rows,empty,enc,delim

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("db")
    a=ap.parse_args()
    if not os.path.exists(a.db): raise SystemExit("STOP: testna baza ne obstaja.")
    pairs,rows,empty,enc,delim=read_pairs(a.csv)
    print("CSV vrstic:",rows); print("Unikatnih parov geslo+opis:",len(pairs))
    print("Praznih/neveljavnih:",empty); print("Encoding:",enc,"delimiter:",delim)
    if len(pairs)<100000: raise SystemExit("STOP: sumljivo malo zapisov; baza ni spremenjena.")
    c=sqlite3.connect(a.db)
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute("CREATE TABLE IF NOT EXISTS slovar (id INTEGER PRIMARY KEY AUTOINCREMENT, geslo TEXT NOT NULL, opis TEXT NOT NULL)")
        c.execute("DELETE FROM slovar")
        c.executemany("INSERT INTO slovar(geslo,opis) VALUES (?,?)", sorted(pairs,key=lambda x:(x[0].casefold(),x[1].casefold())))
        c.execute("DROP TABLE IF EXISTS slovar_sortiran")
        c.execute("CREATE TABLE slovar_sortiran (geslo TEXT, opis TEXT)")
        c.execute("""INSERT INTO slovar_sortiran(geslo,opis) SELECT geslo,opis FROM slovar ORDER BY CASE WHEN instr(opis,' - ')>0 THEN lower(trim(substr(opis,instr(opis,' - ')+3))) ELSE lower(opis) END, lower(opis), lower(geslo)""")
        n1=c.execute("SELECT COUNT(*) FROM slovar").fetchone()[0]
        n2=c.execute("SELECT COUNT(*) FROM slovar_sortiran").fetchone()[0]
        iten=c.execute("SELECT COUNT(*) FROM slovar WHERE geslo=? COLLATE NOCASE",("ITEN",)).fetchone()[0]
        lewis=c.execute("SELECT COUNT(*) FROM slovar WHERE geslo=? COLLATE NOCASE",("LEWIS",)).fetchone()[0]
        if n1!=len(pairs) or n2!=len(pairs): raise RuntimeError("Kontrola stevila ni uspela.")
        c.commit()
        print("-------- KONTROLA --------"); print("slovar =",n1); print("slovar_sortiran =",n2)
        print("ITEN =",iten); print("LEWIS =",lewis); print("SYNC TEST OK")
    except:
        if c.in_transaction: c.rollback()
        raise
    finally: c.close()

if __name__=="__main__": main()

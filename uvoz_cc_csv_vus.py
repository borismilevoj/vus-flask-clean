#!/usr/bin/env python3
"""Varni uvoz Crossword Compiler CSV v VUS.db.

Vsaka kombinacija (geslo, opis) je samostojen zapis. Uvoz zato samo doda
manjkajoce pare; nikoli ne brise in ne prepisuje obstojecih opisov.
"""
import csv
import os
import sqlite3
from contextlib import closing

WORD_COLUMNS = {"word", "geslo", "entry", "answer"}
CLUE_COLUMNS = {"clue", "opis", "definition", "hint"}


def _normalise(value):
    value = (value or "").replace("\u00a0", " ").replace("\u2007", " ").replace("\u202f", " ")
    return " ".join(value.strip().split())


def _open_csv(path):
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "cp1250", "windows-1250", "latin1"):
        try:
            handle = open(path, "r", encoding=encoding, newline="")
            sample = handle.read(8192)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;")
            except csv.Error:
                dialect = csv.excel
            return handle, encoding, dialect
        except UnicodeDecodeError as error:
            last_error = error
    raise RuntimeError(f"CSV ne morem prebrati: {last_error}")


def _column_index(header, allowed, label):
    columns = [_normalise(value).lower().lstrip("\ufeff") for value in header]
    for index, name in enumerate(columns):
        if name in allowed:
            return index
    raise ValueError(f"V CSV ne najdem stolpca za {label}. Glava: {header}")


def _find_column_index(header, allowed):
    """Vrne stolpec, če CSV ima glavo; sicer None."""
    columns = [_normalise(value).lower().lstrip("\ufeff") for value in header]
    for index, name in enumerate(columns):
        if name in allowed:
            return index
    return None


def _refresh_sortiran(connection):
    connection.execute("DELETE FROM slovar_sortiran")
    connection.execute("""
        INSERT OR IGNORE INTO slovar_sortiran(id, geslo, opis)
        SELECT id, geslo, opis FROM slovar
        ORDER BY CASE WHEN instr(opis, ' - ') > 0
                      THEN lower(trim(substr(opis, instr(opis, ' - ') + 3)))
                      ELSE lower(opis) END,
                 lower(opis), lower(geslo)
    """)


def run(csv_path, db_path, *, dry_run=False, verbose=False, **_unused):
    """Doda samo manjkajoce pare (geslo, opis) in vrne statistikо."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError("Nalozeni CC CSV na strezniku ne obstaja.")
    if not os.path.exists(db_path):
        raise FileNotFoundError("Ciljna VUS.db na strezniku ne obstaja.")

    handle, encoding, dialect = _open_csv(csv_path)
    with handle:
        reader = csv.reader(handle, dialect=dialect)
        header = next(reader, None)
        if not header:
            raise ValueError("CC CSV je prazen.")
        word_index = _find_column_index(header, WORD_COLUMNS)
        clue_index = _find_column_index(header, CLUE_COLUMNS)

        # Crossword Compiler izvozi CSV navadno brez glave: prvi dve polji
        # sta že geslo in opis. Če glava obstaja, jo seveda preskočimo.
        if word_index is None or clue_index is None:
            word_index, clue_index = 0, 1
            rows = [header]
        else:
            rows = []

        # Set odstrani ponovitve znotraj istega izvoza, ne pa razlicnih opisov
        # istega gesla.
        pairs = set()
        invalid = 0
        for row in rows:
            word = _normalise(row[word_index] if word_index < len(row) else "")
            clue = _normalise(row[clue_index] if clue_index < len(row) else "")
            if word and clue:
                pairs.add((word, clue))
            else:
                invalid += 1
        for row in reader:
            word = _normalise(row[word_index] if word_index < len(row) else "")
            clue = _normalise(row[clue_index] if clue_index < len(row) else "")
            if word and clue:
                pairs.add((word, clue))
            else:
                invalid += 1

    with closing(sqlite3.connect(db_path, timeout=60)) as connection:
        connection.execute("PRAGMA busy_timeout = 60000")
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = {
                (_normalise(row[0]).casefold(), _normalise(row[1]))
                for row in connection.execute("SELECT geslo, opis FROM slovar")
            }
            missing = [pair for pair in pairs if (pair[0].casefold(), pair[1]) not in existing]
            if not dry_run:
                connection.executemany(
                    "INSERT INTO slovar(geslo, opis) VALUES (?, ?)", missing
                )
                _refresh_sortiran(connection)
                connection.commit()
            else:
                connection.rollback()
        except Exception:
            connection.rollback()
            raise

    stats = {
        "csv_pairs": len(pairs), "inserted": len(missing),
        "updated": 0, "skipped": len(pairs) - len(missing),
        "invalid": invalid, "encoding": encoding,
    }
    if verbose:
        print(stats)
    return stats

"""Themenpool aus einer YAML-Datei (einzige Quelle fuer Runden, Optionen, Reserve und Format).

Schema: pool/README.md im Repo. Die Datei wird streng geprueft; Fehler brechen mit PoolError ab,
es gibt keinen stillen Rueckfall auf eingebaute Daten.
"""
import os
from pathlib import Path

import yaml

APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POOL_FILE = "../pool/doag-ak-2026.yaml"  # relativ zum App-Verzeichnis

OPTION_KEYS = ("A", "B", "C", "D")
DIFFICULTIES = ("Leicht", "Mittel", "Schwer")
RISKS = ("Niedrig", "Mittel", "Hoch")
MIN_OPTIONS, MAX_OPTIONS = 2, 4


class PoolError(Exception):
    """Pool-Datei fehlt oder ist ungueltig."""


def resolve_pool_path(value=None):
    """POOL_FILE (bzw. value) als absoluter Pfad; relative Pfade gelten ab dem App-Verzeichnis."""
    raw = value or os.environ.get("POOL_FILE") or DEFAULT_POOL_FILE
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = APP_ROOT / path
    return path.resolve()


def _text(obj, key, where, maxlen, required=True):
    val = obj.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        if required:
            raise PoolError("%s: Feld '%s' fehlt oder ist leer" % (where, key))
        return None
    if not isinstance(val, str):
        raise PoolError("%s: Feld '%s' muss Text sein (ist %s)" % (where, key, type(val).__name__))
    val = " ".join(val.split())
    if len(val) > maxlen:
        raise PoolError("%s: Feld '%s' ist zu lang (max. %d Zeichen)" % (where, key, maxlen))
    return val


def _choice(obj, key, where, allowed):
    val = _text(obj, key, where, 20, required=False)
    if val is not None and val not in allowed:
        raise PoolError("%s: %s '%s' ungueltig, erlaubt: %s" % (where, key, val, ", ".join(allowed)))
    return val


def _int(obj, key, where, lo, hi):
    val = obj.get(key)
    if isinstance(val, bool) or not isinstance(val, int) or not lo <= val <= hi:
        raise PoolError("%s: '%s' muss eine ganze Zahl von %d bis %d sein (ist %r)" % (where, key, lo, hi, val))
    return val


def parse_pool(data, source="Pool"):
    """Prueft die geladene YAML-Struktur und liefert ein normalisiertes dict."""
    if not isinstance(data, dict):
        raise PoolError("%s: oberste Ebene muss ein Mapping sein" % source)
    if data.get("schema") != 1:
        raise PoolError("%s: 'schema: 1' erwartet (ist %r)" % (source, data.get("schema")))

    fmt = data.get("format") or {}
    if not isinstance(fmt, dict):
        raise PoolError("%s: 'format' muss ein Mapping sein" % source)
    out_fmt = {"voting_seconds": None, "challenge_minutes": None, "scorecard": []}
    if "voting_seconds" in fmt:
        out_fmt["voting_seconds"] = _int(fmt, "voting_seconds", source + " format", 10, 600)
    if "challenge_minutes" in fmt:
        out_fmt["challenge_minutes"] = _int(fmt, "challenge_minutes", source + " format", 1, 60)
    sc = fmt.get("scorecard") or []
    if not isinstance(sc, list) or not all(isinstance(x, str) and x.strip() for x in sc):
        raise PoolError("%s format: 'scorecard' muss eine Liste von Texten sein" % source)
    out_fmt["scorecard"] = [" ".join(x.split()) for x in sc]

    rounds_in = data.get("rounds")
    if not isinstance(rounds_in, list) or not rounds_in:
        raise PoolError("%s: 'rounds' fehlt oder ist leer" % source)
    titles = {}
    rounds, numbers = [], set()
    for i, r in enumerate(rounds_in, 1):
        where = "%s rounds[%d]" % (source, i)
        if not isinstance(r, dict):
            raise PoolError("%s: muss ein Mapping sein" % where)
        number = _int(r, "number", where, 1, 99)
        if number in numbers:
            raise PoolError("%s: Rundennummer %d doppelt" % (where, number))
        numbers.add(number)
        name = _text(r, "name", where, 80)
        opts_in = r.get("options")
        if not isinstance(opts_in, list) or not MIN_OPTIONS <= len(opts_in) <= MAX_OPTIONS:
            raise PoolError("%s: 'options' braucht %d bis %d Eintraege" % (where, MIN_OPTIONS, MAX_OPTIONS))
        opts = []
        for j, o in enumerate(opts_in):
            ow = "%s option %d" % (where, j + 1)
            if not isinstance(o, dict):
                raise PoolError("%s: muss ein Mapping sein" % ow)
            key = o.get("key")
            if key != OPTION_KEYS[j]:
                raise PoolError("%s: key %r, erwartet %r (lueckenlos ab A)" % (ow, key, OPTION_KEYS[j]))
            title = _text(o, "title", ow, 200)
            if title in titles:
                raise PoolError("%s: Titel '%s' doppelt (auch in %s)" % (ow, title, titles[title]))
            titles[title] = ow
            opts.append({"key": key, "title": title,
                         "owner": _text(o, "owner", ow, 40, required=False) or "Gemeinsam",
                         "category": _text(o, "category", ow, 60, required=False) or "",
                         "difficulty": _choice(o, "difficulty", ow, DIFFICULTIES),
                         "risk": _choice(o, "risk", ow, RISKS)})
        rounds.append({"number": number, "name": name, "options": opts})
    rounds.sort(key=lambda x: x["number"])

    reserve_in = data.get("reserve") or []
    if not isinstance(reserve_in, list):
        raise PoolError("%s: 'reserve' muss eine Liste sein" % source)
    reserve = []
    for i, t in enumerate(reserve_in, 1):
        where = "%s reserve[%d]" % (source, i)
        if not isinstance(t, dict):
            raise PoolError("%s: muss ein Mapping sein" % where)
        title = _text(t, "title", where, 200)
        if title in titles:
            raise PoolError("%s: Titel '%s' doppelt (auch in %s)" % (where, title, titles[title]))
        titles[title] = where
        reserve.append({"title": title, "owner": _text(t, "owner", where, 40, required=False) or "Offen",
                        "category": _text(t, "category", where, 60, required=False) or ""})
    return {"format": out_fmt, "rounds": rounds, "reserve": reserve}


def load_pool(path=None):
    """Liest und prueft die Pool-Datei. path: absoluter oder relativer Pfad, sonst POOL_FILE/Standard."""
    p = resolve_pool_path(path)
    if not p.is_file():
        raise PoolError("Pool-Datei nicht gefunden: %s (POOL_FILE setzen oder --pool angeben)" % p)
    try:
        with p.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as e:
        raise PoolError("Pool-Datei %s nicht lesbar: %s" % (p, e))
    pool = parse_pool(data, source=p.name)
    pool["path"] = str(p)
    return pool

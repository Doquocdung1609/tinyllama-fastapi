"""Durable postings and positive-IDF BM25; no corpus tokenization on queries."""
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from math import log
from pathlib import Path
import re
import sqlite3

from app.financial_index.corpus import canonical
from app.services.financial_search_service import tokenize, _numeric_tokens


def financial_tokens(text: str) -> list[str]:
    tokens = tokenize(text)
    for match in re.finditer(r"(?<![\w.])(?:\(\s*[+-]?\d+(?:[.,]\d+)*\s*\)|[+-]?\d+(?:[.,]\d+)*)(?:\s*%)?", text):
        value = match.group().strip()
        negative = value.startswith(("(", "-"))
        percent = value.endswith("%")
        number = value.strip("()% +-\t\n")
        for normalized in _numeric_tokens(number):
            tokens.append(("pct:" if percent else "num:") + ("-" if negative else "+") + normalized)
    lowered = text.casefold()
    tokens.extend("form:" + value for value in re.findall(r"\b10-[kq](?:/a)?\b", lowered))
    tokens.extend("acc:" + value for value in re.findall(r"\b[0-9]{10}-[0-9]{2}-[0-9]{6}\b", lowered))
    tokens.extend("fy:" + value for value in re.findall(r"\bfy\s*([0-9]{4})\b", lowered))
    tokens.extend("quarter:" + value for value in re.findall(r"\b(q[1-4])\b", lowered))
    return tokens


class LexicalIndex:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS generations(
                    generation TEXT PRIMARY KEY,dataset TEXT NOT NULL,state TEXT NOT NULL,
                    metadata TEXT NOT NULL,error TEXT,n INTEGER,avg_length REAL,membership_hash TEXT);
                CREATE TABLE IF NOT EXISTS active(dataset TEXT PRIMARY KEY,generation TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents(
                    cid TEXT PRIMARY KEY,payload TEXT NOT NULL,payload_hash TEXT NOT NULL,length INTEGER NOT NULL,
                    filing_id TEXT NOT NULL,cik TEXT,ticker TEXT,form_type TEXT,fiscal_year INTEGER,fiscal_period TEXT);
                CREATE TABLE IF NOT EXISTS postings(term TEXT NOT NULL,cid TEXT NOT NULL,tf INTEGER NOT NULL,
                    PRIMARY KEY(term,cid));
                CREATE INDEX IF NOT EXISTS postings_cid ON postings(cid);
                CREATE TABLE IF NOT EXISTS members(generation TEXT NOT NULL,cid TEXT NOT NULL,source TEXT NOT NULL,
                    PRIMARY KEY(generation,cid));
                CREATE INDEX IF NOT EXISTS document_filters ON documents(cik,form_type,fiscal_year);
                CREATE TABLE IF NOT EXISTS frequencies(generation TEXT NOT NULL,term TEXT NOT NULL,df INTEGER NOT NULL,
                    PRIMARY KEY(generation,term));
                CREATE TABLE IF NOT EXISTS vectors(identity TEXT NOT NULL,input_hash TEXT NOT NULL,vector TEXT NOT NULL,
                    PRIMARY KEY(identity,input_hash));
                CREATE TABLE IF NOT EXISTS generation_protections(
                    generation TEXT NOT NULL,kind TEXT NOT NULL,reference TEXT NOT NULL,
                    created_at TEXT NOT NULL,PRIMARY KEY(generation,kind,reference),
                    FOREIGN KEY(generation) REFERENCES generations(generation) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS cleanup_audit(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,generation TEXT NOT NULL,state TEXT NOT NULL,
                    requested_at TEXT NOT NULL,completed_at TEXT,error_code TEXT);
            ''')
            c.commit()

    def connect(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        return c

    def generation(self, dataset: str, generation: str | None = None):
        with closing(self.connect()) as c:
            if generation is None:
                active = c.execute("SELECT generation FROM active WHERE dataset=?", (dataset,)).fetchone()
                if active is None:
                    raise ValueError("DATASET_NOT_INDEXED")
                generation = active[0]
            row = c.execute("SELECT * FROM generations WHERE dataset=? AND generation=?", (dataset, generation)).fetchone()
        if row is None:
            raise ValueError("INDEX_GENERATION_NOT_FOUND")
        return {**dict(row), "metadata": json.loads(row["metadata"])}

    def start(self, dataset: str, generation: str, metadata: dict):
        with closing(self.connect()) as c, c:
            active = c.execute("SELECT generation FROM active WHERE dataset=?", (dataset,)).fetchone()
            metadata = {**metadata, "base_active": active[0] if active else None}
            c.execute("INSERT OR IGNORE INTO generations(generation,dataset,state,metadata) VALUES(?,?,'BUILDING',?)",
                      (generation, dataset, canonical(metadata)))
            c.execute("UPDATE generations SET state='BUILDING',error=NULL WHERE generation=? AND state!='READY'", (generation,))

    def add(self, generation: str, batch: list[dict]) -> int:
        new = 0
        with closing(self.connect()) as c, c:
            for item in batch:
                chunk = item["chunk"]
                payload = canonical(chunk)
                digest = sha256(payload.encode()).hexdigest()
                cid = chunk["chunk_id"]
                existing = c.execute("SELECT payload_hash FROM documents WHERE cid=?", (cid,)).fetchone()
                if existing and existing[0] != digest:
                    raise ValueError("CHUNK_ID_CONTENT_COLLISION")
                if existing is None:
                    counts = Counter(financial_tokens(chunk["text"]))
                    m = chunk["metadata"]
                    c.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)", (
                        cid, payload, digest, sum(counts.values()), chunk["filing_id"], m.get("cik"),
                        (m.get("ticker") or "").upper(), (m.get("form_type") or "").upper(),
                        m.get("fiscal_year"), (m.get("fiscal_period") or "").upper()))
                    c.executemany("INSERT INTO postings VALUES(?,?,?)", [(term, cid, tf) for term, tf in counts.items()])
                    new += 1
                c.execute("INSERT OR IGNORE INTO members VALUES(?,?,?)", (generation, cid, canonical(item["source"])))
        return new

    def records(self, generation: str):
        with closing(self.connect()) as c:
            cursor = c.execute("SELECT d.cid,d.payload,m.source FROM members m JOIN documents d ON d.cid=m.cid WHERE m.generation=? ORDER BY d.cid", (generation,))
            for row in cursor:
                yield {"chunk": json.loads(row["payload"]), "source": json.loads(row["source"])}

    def seal(self, generation: str):
        with closing(self.connect()) as c, c:
            n, average = c.execute("SELECT COUNT(*),AVG(d.length) FROM members m JOIN documents d ON d.cid=m.cid WHERE m.generation=?", (generation,)).fetchone()
            if not n:
                raise ValueError("EMPTY_INDEX")
            digest = sha256()
            for row in c.execute("SELECT d.cid,d.payload_hash,m.source FROM members m JOIN documents d ON d.cid=m.cid WHERE m.generation=? ORDER BY d.cid", (generation,)):
                digest.update(canonical(list(row)).encode())
            c.execute("DELETE FROM frequencies WHERE generation=?", (generation,))
            c.execute("INSERT INTO frequencies SELECT ?,p.term,COUNT(*) FROM postings p JOIN members m ON m.cid=p.cid WHERE m.generation=? GROUP BY p.term", (generation, generation))
            c.execute("UPDATE generations SET n=?,avg_length=?,membership_hash=? WHERE generation=?", (n, max(1., average), digest.hexdigest(), generation))
        return n

    def publish(self, dataset: str, generation: str):
        with closing(self.connect()) as c, c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT metadata,n FROM generations WHERE generation=?", (generation,)).fetchone()
            active = c.execute("SELECT generation FROM active WHERE dataset=?", (dataset,)).fetchone()
            previous = json.loads(row["metadata"])["base_active"]
            if (active[0] if active else None) not in {previous, generation} or not row["n"]:
                raise ValueError("ACTIVE_GENERATION_CHANGED_DURING_BUILD")
            c.execute("UPDATE generations SET state='READY',error=NULL WHERE generation=?", (generation,))
            c.execute("INSERT INTO active VALUES(?,?) ON CONFLICT(dataset) DO UPDATE SET generation=excluded.generation", (dataset, generation))

    def fail(self, generation: str, error: str):
        with closing(self.connect()) as c, c:
            c.execute("UPDATE generations SET state='FAILED',error=? WHERE generation=? AND state!='READY'", (error[:500], generation))

    @staticmethod
    def scope(generation: str, filters: dict):
        conditions, values = ["m.generation=?"], [generation]
        for key, value in filters.items():
            if key in {"cik", "ticker", "form_type", "fiscal_year", "fiscal_period"}:
                conditions.append(f"d.{key}=?")
                values.append(value.upper() if isinstance(value, str) else value)
            elif key == "filing_ids" and value:
                conditions.append("d.filing_id IN (" + ",".join("?" for _ in value) + ")")
                values.extend(value)
            else:
                raise ValueError("Unsupported metadata filter")
        return " AND ".join(conditions), values

    def search(self, query: str, generation: dict, limit: int, filters: dict):
        terms = sorted(set(financial_tokens(query)))
        if not terms:
            return []
        where, params = self.scope(generation["generation"], filters)
        with closing(self.connect()) as c:
            if filters:
                n, avg = c.execute("SELECT COUNT(*),AVG(d.length) FROM members m JOIN documents d ON d.cid=m.cid WHERE " + where, params).fetchone()
                avg = max(1., avg or 1.)
            else:
                n, avg = generation["n"], generation["avg_length"]
            scores = {}
            for term in terms:
                if filters:
                    df = c.execute("SELECT COUNT(*) FROM postings p JOIN members m ON m.cid=p.cid JOIN documents d ON d.cid=p.cid WHERE p.term=? AND " + where, [term, *params]).fetchone()[0]
                else:
                    row = c.execute("SELECT df FROM frequencies WHERE generation=? AND term=?", (generation["generation"], term)).fetchone()
                    df = row[0] if row else 0
                if not df:
                    continue
                idf = log(1. + (n - df + .5) / (df + .5))
                rows = c.execute("SELECT p.cid,p.tf,d.length FROM postings p JOIN members m ON m.cid=p.cid JOIN documents d ON d.cid=p.cid WHERE p.term=? AND " + where, [term, *params])
                for row in rows:
                    score = idf * (row["tf"] * 2.5 / (row["tf"] + 1.5 * (.25 + .75 * row["length"] / avg)))
                    scores[row["cid"]] = scores.get(row["cid"], 0.) + score
        return [{"chunk_id": cid, "bm25_score": score} for cid, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]]

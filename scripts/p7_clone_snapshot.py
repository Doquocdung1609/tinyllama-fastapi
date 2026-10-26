"""Clone a research snapshot for destructive P7 tests, never mutate the source."""
import argparse
import json
from pathlib import Path
import shutil
import sqlite3


def clone(source: Path, target: Path) -> None:
    source = source.resolve(strict=True)
    target = target.resolve()
    if target.exists() or target == source or target.is_relative_to(source):
        raise ValueError('P7_CLONE_TARGET_MUST_BE_NEW_AND_SEPARATE')
    if not (source / 'ownership.json').is_file() or not (source / 'lexical_v1.sqlite3').is_file():
        raise ValueError('P7_SOURCE_IS_NOT_AN_OWNED_RESEARCH_SNAPSHOT')
    shutil.copytree(source, target)
    old = str(source)
    new = str(target)
    with sqlite3.connect(target / 'lexical_v1.sqlite3') as db:
        for rowid, raw in db.execute('SELECT rowid, source FROM members').fetchall():
            record = json.loads(raw)
            for key in ('raw_path', 'structured_path', 'chunks_path'):
                path = Path(record[key]).resolve()
                if not path.is_relative_to(source):
                    raise ValueError('P7_SOURCE_PATH_OUTSIDE_SNAPSHOT')
                record[key] = str(target / path.relative_to(source))
            db.execute('UPDATE members SET source=? WHERE rowid=?',
                       (json.dumps(record, sort_keys=True, separators=(',', ':')), rowid))
    sources = target / 'frozen_v1' / 'sources.json'
    rows = json.loads(sources.read_text(encoding='utf-8'))
    for row in rows:
        for key in ('raw_path', 'structured_path', 'chunks_path'):
            path = Path(row[key]).resolve()
            if not path.is_relative_to(source):
                raise ValueError('P7_SOURCE_PATH_OUTSIDE_SNAPSHOT')
            row[key] = str(target / path.relative_to(source))
    sources.write_text(json.dumps(rows, sort_keys=True, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({'clone': str(target), 'members': len(rows), 'source_unchanged': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--target', type=Path, required=True)
    args = parser.parse_args()
    clone(args.source, args.target)

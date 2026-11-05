"""Derive ampersand initials only when the pinned SEC source defines that alias."""
from contextlib import closing
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re
from app.financial_query.contracts import CorpusCatalogV1


def verified_alias_catalog(snapshot):
    registry_path=Path(__file__).resolve().parents[2]/'docs/topic3/milestone_d/d3/D3_FRESH_EXACT_ROW_FREEZE_v1.json'
    registry=json.loads(registry_path.read_text(encoding='utf-8'))
    from app.table_evidence.product_registry import product_registry
    registry=product_registry(snapshot.freeze) or registry
    from app.product.sec_product_snapshot import ProductSecSnapshot
    if isinstance(snapshot,ProductSecSnapshot):registry=snapshot.product_source_registry
    if (registry['manifest_hash'],registry['generation'])!=(snapshot.freeze['manifest_hash'],snapshot.freeze['generation']):
        raise ValueError('ALIAS_SOURCE_REGISTRY_MISMATCH')
    groups={g['raw_hash']:g for g in registry['source_groups']}
    modified=[]
    for issuer in snapshot.catalog.issuers:
        parts=re.split(r'\s*&\s*',issuer.company_name, maxsplit=1)
        if len(parts)!=2:
            modified.append(issuer);continue
        left=re.findall(r'[A-Za-z]+',parts[0]);right=re.findall(r'[A-Za-z]+',parts[1])
        if not left or not right:
            modified.append(issuer);continue
        alias=left[0][0].upper()+'&'+right[0][0].upper()
        with closing(snapshot.lexical.connect()) as db:
            row=db.execute('SELECT m.source FROM documents d JOIN members m ON m.cid=d.cid '
                           'WHERE d.cik=? AND m.generation=? LIMIT 1',(issuer.cik,snapshot.freeze['generation'])).fetchone()
        if row is None:
            modified.append(issuer);continue
        source=json.loads(row['source']);anchor=groups.get(source.get('raw_hash'))
        if anchor is None or anchor['cik']!=issuer.cik or source.get('manifest_hash')!=snapshot.freeze['manifest_hash']:
            raise ValueError('ALIAS_SOURCE_NOT_PINNED')
        path=Path(source['raw_path']).resolve()
        if not path.is_relative_to(snapshot.root) or path.stat().st_size>4_000_000:
            raise ValueError('ALIAS_SOURCE_PATH_OR_SIZE_INVALID')
        raw=path.read_bytes()
        if sha256(raw).hexdigest()!=anchor['raw_hash']:
            raise ValueError('ALIAS_RAW_HASH_MISMATCH')
        text=unescape(raw.decode('utf-8',errors='strict'))
        quoted=re.search(r'"'+re.escape(alias)+r'[,\"]',text)
        preceding=text[max(0,quoted.start()-240):quoted.start()] if quoted else ''
        if quoted and all(re.search(r'\b'+re.escape(name)+r'\b',preceding,re.I) for name in (left[0],right[0])):
            modified.append(issuer.model_copy(update={'verified_aliases':sorted(set(issuer.verified_aliases+[alias]))}))
        else:modified.append(issuer)
    catalog=snapshot.catalog.model_copy(update={'issuers':modified})
    return CorpusCatalogV1.model_validate(catalog.model_dump(mode='json'))

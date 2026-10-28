"""Additional committed product source anchor; historical registry stays default.

Only exact manifest+generation identity selects this profile. It does not accept
caller paths, arbitrary source hashes, or change any historical source registry.
"""
import json
from pathlib import Path


def product_registry(freeze):
    path=Path(__file__).resolve().parents[2]/'docs/topic3/final_product/SEC_PRODUCT_SOURCE_REGISTRY.json'
    if not path.is_file():return None
    registry=json.loads(path.read_text(encoding='utf-8'))
    if registry.get('schema')!='product-official-sec-source-registry/v1':return None
    if (registry.get('manifest_hash'),registry.get('generation'))!=(freeze['manifest_hash'],freeze['generation']):return None
    return registry

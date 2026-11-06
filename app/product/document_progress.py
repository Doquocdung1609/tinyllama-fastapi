"""Bounded, transient progress for authenticated document reasoning requests."""
from threading import Lock
from time import monotonic

_lock=Lock()
_records={}
TTL=180
CAPACITY=64


def update(owner, request_id, **data):
    if not request_id:
        return
    now=monotonic()
    key=(owner,request_id)
    with _lock:
        for k,(stamp,_) in list(_records.items()):
            if now-stamp>TTL:
                del _records[k]
        if key not in _records and len(_records)>=CAPACITY:
            del _records[min(_records,key=lambda k:_records[k][0])]
        previous=_records.get(key,(now,{}))[1]
        _records[key]=(now,{**previous,**data})


def get(owner, request_id):
    with _lock:
        stamp,data=_records.get((owner,request_id),(0,{}))
        return dict(data) if monotonic()-stamp<TTL else {}

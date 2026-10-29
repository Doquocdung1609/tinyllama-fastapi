"""Bounded owner-workspace admission;never stop other applications or models."""
from contextlib import contextmanager
from threading import RLock,Lock,local
from time import perf_counter
import psutil

class ResourceControl:
    def __init__(self,max_waiters=2):
        self.gate=RLock();self.metadata=Lock();self.local=local();self.active=None;self.waiting=0;self.max_waiters=max_waiters;self.max_active_observed=0;self.completed=0

    def status(self):
        available=psutil.virtual_memory().available
        with self.metadata:return {'available_ram_bytes':available,'warning':available<1536*1024**2,'heavy_minimum_mb':768,'search_minimum_mb':256,
            'active':self.active,'waiting':self.waiting,'max_active':1,'max_waiters':self.max_waiters,'max_active_observed':self.max_active_observed,'completed':self.completed,
            'demo_policy':'READY_DOCUMENTS_AND_PREPARED_INDEX;NO_BACKGROUND_REINGESTION'}

    @contextmanager
    def claim(self,phase,minimum_mb=768,timeout=120):
        if getattr(self.local,'depth',0):
            self.local.depth+=1
            try:yield
            finally:self.local.depth-=1
            return
        if psutil.virtual_memory().available<minimum_mb*1024**2:raise ValueError('LOW_MEMORY_DEFERRED')
        with self.metadata:
            if self.waiting>=self.max_waiters:raise ValueError('RESOURCE_BUSY_RETRY')
            self.waiting+=1
        acquired=False
        try:
            acquired=self.gate.acquire(timeout=timeout)
            if not acquired:raise ValueError('RESOURCE_BUSY_RETRY')
            with self.metadata:self.waiting-=1;self.active={'phase':phase,'since_monotonic':perf_counter()};self.max_active_observed=1
            if psutil.virtual_memory().available<minimum_mb*1024**2:raise ValueError('LOW_MEMORY_DEFERRED')
            self.local.depth=1
            try:yield
            finally:self.local.depth=0
        finally:
            with self.metadata:
                if acquired:self.active=None;self.completed+=1
                else:self.waiting-=1
            if acquired:self.gate.release()

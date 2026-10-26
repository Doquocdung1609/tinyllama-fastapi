"""Opt-in D2 evidence representation. Not wired into Financial Search."""
from app.table_evidence.builder import build_table_evidence
from app.table_evidence.bundle import build_evidence_bundle
from app.table_evidence.source import context_from_snapshot

__all__ = ['build_table_evidence', 'build_evidence_bundle', 'context_from_snapshot']

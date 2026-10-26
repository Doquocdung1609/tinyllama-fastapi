"""Opt-in deterministic D4 QA; no model call or production route side effect."""
from app.research_qa.verifier import answer_from_bundle,verify_claim
__all__=['answer_from_bundle','verify_claim']

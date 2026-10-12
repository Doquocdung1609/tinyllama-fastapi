# Document scope isolation

Each conversation stores validated hexadecimal document IDs, never filesystem paths. API creation and updates reject missing, malformed, non-ready or removed documents. Qdrant filtering uses the active ID list (`MatchAny` for multi-document scope). C07 verified two conversations do not contaminate one another. C10 deleted a document in the isolated test collection and received HTTP 409 with a clear missing-document message. C04 verified a two-document conversation can retrieve the requested bilingual document. Production data was not mutated.

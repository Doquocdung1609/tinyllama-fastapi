# SEC source scope and provenance

Primary workspace: `C:\Users\Admin\Documents\GitHub\tinyllama-fastapi\studio_workspace\react-product-20261028`; API `127.0.0.1:18110`. Four UI-selected filings were COST `0000909832-26-000051`, HD `0001628280-26-058715`, PG `0000080424-26-000256`, MSFT `0001193125-25-256321`. The preexisting HD/PG indexes remained intact. Official SEC COST/MSFT primary HTML was fetched with a contactable User-Agent and imported as separate lexical-ready `sec-user-library` sources; no frozen research corpus or source generation was overwritten. MSFT Dense indexing was not inferred from lexical readiness.

| Filing | Raw SHA-256 checked through source viewer | Selected tasks |
| --- | --- | --- |
| COST | `4657f8d910de719aa29cc11a979087760e104d27ca49345d15bd5e614d1637a7` | F06, H01/H06, T02/T06 |
| HD | `301a64049ae9e407c16d6b07b734614a1e64fa969acc3126f9e7a74023c9b614` | F01/F06, H07/T07 |
| PG | `1c60df5705b24abf1141221441e8a5f77e0233a9884a1927b84ce90ac74b7527` | F06, H01/H06, T06 |
| MSFT | `26f4b4397a2d85ff00350f375de34b2f419f111a7e64d4f3855809d55074a0b9` | F02/F03, H02/H03, T01/T03 |

For F01 the eligible filing was HD alone, despite COST/PG in question text. For F06 COST/HD/PG were eligible and MSFT excluded. F04/F05 left AMZN/PEP unselected and produced no source citation or calculation. The source viewer reopened all 16 acceptance citations: 14 numeric cells returned `VERIFIED_LOCAL_SEC_SNAPSHOT`, while two MSFT narrative excerpts returned `SOURCE_EVIDENCE_PARTIAL` with `PARTIAL_TABLE_EXTRACTION` warning. The narrative text and source locator were authenticated; this does not make whole-filing extraction complete.

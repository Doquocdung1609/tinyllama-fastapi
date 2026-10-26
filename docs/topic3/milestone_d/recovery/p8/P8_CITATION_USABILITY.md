# P8 citation usability

The research evidence panel now explicitly displays the verified filing accession, extracted table caption, row label, source column period, original displayed value and structural locator. It also emits a copyable JSON citation containing the SEC URL and these fields. The caption is faithfully extracted metadata and may be generic (for example a company heading); it is not inferred as a semantic statement title.

No unverified SEC URL fragment is constructed. Browser outcome for the HD test: correct filing opened VERIFIED; target table, row and exact cell NOT_VERIFIED in the external popup. The UI tells the user to locate the row manually. Source-cell correspondence is instead established by authenticated bytes, parser coordinates and iXBRL context as documented in `p8_source_cases_after.json`.

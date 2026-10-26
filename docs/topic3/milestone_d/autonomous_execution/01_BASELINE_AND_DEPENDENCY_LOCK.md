# Baseline and dependency lock

Accepted B/C/D1 base `32c4a4834c5f8a0b34ac28c42f960c862dd8077d`; D1 merge182771470841b805d2f8d78f11b7dfa70c2dfc99. Original D2 PR11c8d7283; repaired implementation `14014d2919a55f9cb087deaf120a4dc5d8498d1e`. Blueprint PR9bcd5728 remains unmerged. No production/parser/chunker/default changes. D3 must branch from exact final D2 delivery, D4 from D3, D5 from D4. Current embedding observation NOT_TESTED; accepted historical Nomic identity is not silently substituted.

## Final dependency identities v2

D2 final `470bf86a98baad6b8011c166f00288a914e7a1a4` → D3 final `e8230dddb29f57c5578050e23abb6169151e7986` → D4 final `1e0b9e0444a4595a39353938dd62fbe2b4a6e046` → D5 Draft PR #14. Each branch targeted its immediate predecessor. `git diff --name-status` from accepted base to D5 found zero modified/deleted baseline paths among 550 tracked blobs. Main and accepted target were not changed by this execution.

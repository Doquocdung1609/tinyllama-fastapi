# Milestone C — index retention and recovery

Retention là explicit, conservative và không xóa raw corpus.

- Inventory báo state, active flag, chunks, collection, vector count, disk bytes, protection và eligibility.
- Mặc định giữ 3 READY generations/dataset và 1 rollback generation; active, pin và evaluation references luôn protected.
- Cleanup mặc định dry-run. `apply=true` xóa collection trước, sau đó membership/frequency/orphan postings, documents và vector cache; audit ghi STARTED/COMPLETE/FAILED.
- Nếu crash sau dense delete, retry nhận biết collection đã mất và hoàn tất SQLite cleanup.
- Mutation lock chung serialize build, activate, pin/unpin và cleanup. Eligibility được revalidate sau khi lấy lock, đóng race stale-plan có thể xóa generation vừa activate/pin.
- Failed atomic artifact write xóa `.tmp` trong `finally`; raw snapshot và immutable source artifacts không bị retention chạm tới.

Bounded experiments giữ nhiều collection 822-point (58,35 MiB tổng), rollback/restart không rebuild, controlled build failure giữ old active, resume dùng 0 embedding mới, query trong build chỉ đọc generation cũ. Không claim power-loss/fsync durability hay disk-corruption recovery.

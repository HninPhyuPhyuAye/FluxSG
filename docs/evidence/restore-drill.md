# Restore drill evidence

- Executed: 14 October 2026 at 04:42 UTC
- Backup contents: PostgreSQL custom-format dump and object-store archive
- Integrity: both SHA-256 checks passed
- Restore target: isolated `fluxsg_restore_drill` database
- Verification: 16 application tables restored
- Cleanup: drill database removed automatically
- Production database: not modified

Commands:

```bash
make backup
make restore-drill
```

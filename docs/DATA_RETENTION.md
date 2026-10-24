# Data Retention Schedule (Draft)

> **DRAFT FOR LEGAL REVIEW.** This schedule documents intended technical
> behavior. Statutory retention, limitation periods, data-subject procedures,
> and processor deletion commitments must be approved by counsel before use.

Last engineering review: 2026-10-25

| Data category | Primary retention | Deletion trigger |
|---|---|---|
| Account, profile, pair membership | While account is active | Account deletion; pair-only records are removed when the relationship is dissolved where supported |
| Session token hashes | Up to 30 days per issued session | Expiry, replacement, or account deletion |
| Moods, answers, journal, events, wishlist, games, companion and movie data | While account/pair is active | Item deletion where available, pair removal, or account deletion |
| Photos | While referenced by active content | Content/account deletion and orphan cleanup |
| Precise partner location | Latest synchronized state while sharing is enabled | Sharing disabled or account deletion |
| Community-map posts and comments | Until deleted/moderated or account deletion | User deletion, moderation, or account deletion |
| Voice recordings | Device temporary cache only; not uploaded by the current backend | Operating-system cache cleanup, application data clearing, or uninstall |
| Push tokens | While notifications/session are active | Logout, token replacement, invalidation, or account deletion |
| Authentication abuse-prevention records | **[OPERATIONAL PERIOD TO BE SET]** | Scheduled security-record cleanup |
| Operational system logs | **[PERIOD TO BE SET, recommended 14-30 days]** | Log rotation |
| Payment and referral accounting | Anonymized on account deletion; statutory period **[TO BE SET]** | End of legally required accounting retention |
| Local and S3 backup snapshots | 14 days | Automatic daily retention cleanup |

## Account deletion

The authenticated `DELETE /account` workflow requires the current password. It
removes the user, credentials, locations, push tokens, private content, pair
state, community-map data, and referenced photos. The surviving partner account
is unpaired. Payment records needed for reconciliation are retained only in
anonymized form. Automated tests verify this behavior.

Deleted data may remain in backup snapshots until the 14-day retention window
expires. Restoring an older snapshot after a deletion requires re-running
deletion reconciliation before production traffic is enabled.

## Backup handling

- `deploy/backup.sh` creates a consistent SQLite `.backup` snapshot and checks
  `PRAGMA integrity_check`.
- The database and photos are copied to a timestamped S3 snapshot.
- Local and S3 snapshots older than 14 days are deleted automatically.
- Restore access is limited to server administrators. A pre-restore database
  snapshot is created automatically.
- `deploy/test-restore.sh` must pass after backup tooling or SQLite upgrades.

## Review requirements

The owner must document the production log period, accounting period, legal
basis, processor retention, deletion-request SLA, and contact procedure before
these documents are published.

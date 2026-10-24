# Privacy Policy (Draft)

> **DRAFT FOR LEGAL REVIEW.** This document is an engineering description of
> current data flows, not legal advice and not a publication-ready policy.
> The controller identity, address, contact details, lawful bases, applicable
> jurisdiction, age limits, and processor agreements must be completed by
> qualified counsel before publication.

Last engineering review: 2026-10-25

## 1. Service and controller

Enrwine is a private application for couples. The data controller is
**[LEGAL ENTITY / INDIVIDUAL TO BE INSERTED]**. Privacy requests should be sent
to **[PRIVACY CONTACT TO BE INSERTED]**.

## 2. Data processed

- Account data: email address, password hash, session token hash, internal user
  ID, pairing code, profile name, avatar, birth date, and relationship date.
- Couple content: moods, answers, quizzes, wishlist items, events, journal
  entries, shared game state, companion state, movie matches, and activity
  records.
- Photos: avatars, journal/widget/wishlist photos, and community-map photos.
- Location: coordinates shared with the partner, timestamps, location-sharing
  consent, and approximate community-map location selected by the user.
- Voice: the pet voice feature records up to 10 seconds into the application's
  temporary device cache for local playback. The current backend does not
  receive this recording.
- Device and delivery data: push-notification token, platform, application
  version, IP address used for security rate limits, and operational error logs.
- Payment and referral data: Telegram identifiers, payment charge identifiers,
  amounts, currency, subscription period, referral status, and payout records.
  Account deletion anonymizes accounting records that must remain for
  reconciliation.

## 3. Purposes

Data is processed to authenticate users, connect partners, deliver requested
features, synchronize private content, send notifications, process purchases,
prevent abuse, investigate failures, maintain backups, and restore the service.
Legal bases for each purpose are **[TO BE CONFIRMED BY COUNSEL]**.

## 4. Sharing and processors

Data is not intended for sale. Depending on enabled production configuration,
it may be processed by the hosting provider, an S3-compatible storage provider,
Firebase Cloud Messaging, Telegram, and movie-catalog providers. Exact provider
names, countries, transfer mechanisms, and processor agreements are
**[TO BE INSERTED AND REVIEWED]**.

Partners can see content deliberately shared within their pair. Approved
community-map posts are visible to other users according to product rules.

## 5. Security

The service uses HTTPS, hashed passwords and session tokens, authorization on
private routes, restricted photo access, encrypted Android credential storage,
firewall rules, SSH key authentication, rate limits, and access-controlled
backups. No security measure eliminates all risk.

## 6. Retention and deletion

Retention periods are described in [DATA_RETENTION.md](DATA_RETENTION.md).
Users can delete individual supported items and can delete their account from
the application after password confirmation. Primary account data and linked
content are deleted or anonymized immediately by the application workflow;
residual copies can remain in access-restricted backups for up to 14 days.

## 7. User rights

Depending on applicable law, users may have rights of access, correction,
deletion, restriction, objection, portability, withdrawal of consent, and
complaint to a supervisory authority. Request handling procedure and identity
verification are **[TO BE DEFINED BY COUNSEL]**.

## 8. Children and changes

The permitted minimum age and parental-consent rules are **[TO BE DEFINED]**.
Material policy changes should be announced in the application before they
take effect where required by law.

# Cross-application coverage modules

Select every module that applies. These are minimum probes, not feature requirements. Mark irrelevant states `not applicable` and unavailable checks `not run`.

## Universal web-interface module

- Purpose and primary action at first meaningful render
- Navigation, current location, addressability, back/forward, and reload
- Pointer, keyboard, focus, zoom/reflow, and small-screen operation
- Loading, empty, error, success, disabled, stale, and permission states that actually exist
- Feedback for every state-changing or asynchronous action
- Headings, landmarks, names, roles, relationships, live updates, and contrast
- Content specificity, terminology consistency, hierarchy, density, and identity
- Runtime performance when a trace is available
- Shared implementation blockers when source is available

## Reference, course, or documentation

- Find a known term and an unfamiliar term
- Resume after interruption
- Link/bookmark/share a specific unit
- Traverse sequentially and jump non-sequentially
- Reveal, quiz, transcript, print/export, media, and completion behavior when present
- Long-page readability and sparse-page composition

## SaaS dashboard or operations surface

- Identify the decision each summary supports
- Filter, sort, paginate, change scope, and clear state
- Empty, stale, partial, delayed, and contradictory data
- Drill down and return without losing context
- Role/permission differences and destructive-action confirmation
- Dense-table keyboard and responsive behavior

## Transactional, ecommerce, booking, or payment

- Search/browse → detail → selection → cart/booking → confirmation
- Price, fee, availability, inventory, and date changes
- Validation, retry, cancellation, duplicate submission, and idempotent feedback
- Authentication interruption and return to task
- Trust-critical copy and irreversible-action review

## Lookup or identity resolution

A person supplies an identifier — a name, address, order number, company — and the product decides which stored record they mean. Guest lookups, member directories, order tracking, patient check-in, registry search.

- Cost of a wrong match versus no match; a wrong match is usually worse, because it is confidently actionable
- Real data from every real upstream source, obtained before designing; sources disagree, and one may export explicit household grouping while another merges names and drops it
- Entity grouping: do records mean individuals, households, parties, or companies, and can a record cover someone with no name of their own — a plus-one, a dependent — who must still succeed
- The match ladder stated in order, with a stopping rule and an explicit position on fuzzy matching, which converts a lookup into a graded enumeration oracle
- Matched, ambiguous, and not-found as three distinct designed states; ambiguity resolved by returning the first hit is the wrong-match failure above
- Normalization: Unicode form, atomic versus decomposable letters, punctuation deleted versus substituted, case folding, particles — executed, not read
- Disclosure per outcome: does ambiguity leak existence, does a refusal differ from a rate-limit
- Bulk entry, where the data plausibly already exists elsewhere; the absence of an import path is a finding, not an enhancement
- Inference visibility: every value the importer guessed rather than read is shown and correctable before it is saved

## Form, onboarding, settings, or account management

- Initial, partial, invalid, valid, saving, saved, and failed states
- Labels, help, errors, required/optional distinction, and review-before-submit
- Back/forward, draft persistence, abandonment, resume, and reset
- Conditional fields, progressive disclosure, permission requests, and defaults
- Keyboard order and focus movement after validation

## Data-heavy, analytic, or developer tool

- Query/input → running → partial → complete → failed → retry
- Large result sets, truncation, pagination/virtualization, export, and copy
- Filters and URL/state reproducibility
- Units, precision, time zones, provenance, freshness, and comparison baselines
- Dense keyboard interaction and non-color status encoding

## Collaboration, messaging, or realtime

- Create/edit/delete, optimistic state, conflict, reconnect, and duplicate events
- Read/unread, presence, ordering, timestamps, and notification control
- Permission and ownership changes
- Offline queue and reconciliation when applicable
- Dynamic announcements without focus theft

## Media, creative, canvas, or editor

- Load/import, edit, undo/redo, save/export, failure, and recovery
- Selection, focus, shortcuts, context menus, and direct manipulation
- Large-file or long-session behavior
- Playback/recording permission and capability states
- Unsaved work, autosave truthfulness, version history, and destructive reset

## File or media ingestion

- Map the real journey from select, capture, or import through validation, transfer, processing, review or publication, retention, and deletion
- Build a source matrix from formats the product actually promises: file type, size, codec, dimensions or duration, metadata, filename shape, browser or device origin, and batch size
- Compare client-visible acceptance with server-authoritative acceptance; a picker accepting a file is not proof that transfer or processing will succeed
- Exercise per-file and batch progress, cancellation, retry, resume, duplicate submission, reordered completion, and partial success without collapsing the batch into one false status
- Distinguish transfer failure from downstream thumbnailing, transcoding, scanning, moderation, indexing, storage, quota, or publication failure in user-visible state and recovery
- Stress Unicode and long filenames, orientation, color profile, timestamps, location metadata, zero-byte input, misleading extensions, and valid-but-uncommon formats without exposing sensitive metadata unnecessarily
- Verify that held, rejected, or review-required items have literal status and recovery while private moderation or safety internals remain appropriately restricted
- Confirm that deletion, replacement, retention, and derived-output behavior match the visible promise; local previews and green unit tests do not prove provider persistence
- Treat unavailable real-device, codec, provider, storage-limit, or long-running processing evidence as `not run`, never as a pass

## Multi-channel service blueprint

- Map each representative journey stage across user actions, visible frontstage responses, backstage operations, external dependencies, responsible roles, and evidence of completion
- Exercise handoffs among every promised channel that actually exists — for example web, email, text message, support, kiosk, device, printed material, or an in-person step
- Verify that identifiers, state, deadlines, permissions, and recovery instructions remain coherent when a person leaves one channel and resumes in another
- Distinguish a request being accepted from queued, delivered, processed, acknowledged, and completed; a local success screen does not prove a downstream channel worked
- Test interruption, retry, duplicate delivery, delayed delivery, stale instructions, conflicting updates, escalation, and a channel becoming unavailable
- Identify who may view, change, approve, reverse, or communicate each state; do not infer operational authority from a visible control
- Compare terminology, accessibility, localization, privacy disclosures, and consequence language across channels without forcing every channel into identical presentation
- Separate product evidence from provider, staff, device, venue, legal, or physical-operation proof, and record unavailable external checks as `not run`

## Marketing, landing, or static content

- Audience/outcome clarity and primary conversion path
- Navigation, anchor/deep-link behavior, forms, and external destinations
- Content credibility, proof provenance, mobile reading, and reduced motion
- Image/media loading, layout stability, and print/share behavior when relevant
- Avoid inventing application-state requirements the page does not need

## Ceremonial, shared display, or physical print

- Classify each output as close-interaction, shared presentation, printed sign, or invitation-like artifact before applying size and density rules
- Record intended audience, physical or pixel size, likely viewing distance, orientation, lighting, trim, and safe area
- Preserve the subject or event identity as the dominant ceremonial layer without letting ornament obscure names, state, instructions, or participation cues
- Verify venue-screen and projector content at native presentation sizes; separate audience-facing content from operator-only chrome
- Verify printed output at intended paper dimensions, including trim, safe area, contrast, QR prominence, and legibility without editor zoom
- Stress short, long, compound, and localized names plus real event dates and venues; inspect line boxes against adjacent media and ornaments
- Check the handoff between ceremonial and operational surfaces: the gallery or sign may invite, while the upload, recovery, or setup flow must remain literal and task-efficient
- Treat unavailable physical-distance, lighting, printer, or device evidence as `not run`, never as a pass

## Hybrid or unknown product

Start with the universal module. Derive three to five tasks from visible behavior, supplied intent, and source structure. Add modules only when the interface exposes that application shape. Record uncertain classification as an inference and keep the coverage ledger explicit.

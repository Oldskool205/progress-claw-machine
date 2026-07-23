# Data Retention and Source-Control Policy

Last reviewed: 2026-07-23

## Purpose

Progress Claw OS processes player photos, camera captures, AI training data,
runtime logs, analytics events, and machine configuration. These files have
different privacy and recovery requirements and must not be treated as ordinary
source code.

This policy defines what belongs in Git, what remains local, and when an
operator should review or remove retained data. It does not automatically
delete existing local files.

## Source-Control Rules

| Data | Git policy | Local retention recommendation |
|---|---|---|
| Source code, tests, configuration templates, documentation | Track | Indefinite |
| Dashboard logos and deliberate UI artwork | Track | Indefinite |
| Current player photo | Never track | Replace on registration; remove within 24 hours after it is no longer active |
| Player photo history | Never track | 7 days maximum unless the operator has documented consent and a specific purpose |
| Raw camera/YOLO captures and metadata | Never track | 30 days maximum for labeling review, then move to approved private storage or remove |
| Human-image training datasets | Never track in the public repository | Approved private dataset storage with consent, provenance, and deletion records |
| Synthetic/non-human test fixtures | Track only when small and documented | Indefinite |
| YOLO training runs, predictions, charts, and caches | Never track | Keep the latest useful run and remove superseded runs after 30 days |
| Trained model weights | Do not commit directly | Store as a versioned release/artifact with model version and SHA-256 |
| Runtime logs | Never track | 14 days or 100 MiB per service, whichever is reached first |
| Analytics events | Do not commit | Current in-memory implementation resets on restart; future storage needs an approved limit |
| Wi-Fi rollback configuration | Never track; root-only | Keep one last-known-good copy while live Wi-Fi administration is enabled |
| Secrets and local `.env` | Never track | Retain only on the machine with restrictive permissions |

## Privacy Requirements

- Treat every identifiable player photo as personal data.
- Do not upload player photos, names, raw captures, or metadata to GitHub.
- Obtain appropriate consent before retaining a human image for model training.
- Keep dataset provenance, consent scope, collection date, and deletion status
  in private dataset records—not public image filenames.
- Do not place passwords, API keys, PINs, access tokens, or Wi-Fi credentials in
  filenames, logs, metadata, reports, shell arguments, or source control.
- Before sharing diagnostics, redact names, faces, network credentials, cloud
  keys, machine identifiers, and private IP information when it is not needed.

## Repository Hygiene

The repository ignores Python caches, test caches, logs, runtime databases,
camera output, player photos, raw training captures, training runs, and model
weights. A file already tracked by Git remains tracked even after a matching
ignore rule is added, so confirmed generated artifacts must also be removed
from the Git index.

The 2026-07-23 hygiene pass stopped tracking:

- the mutable current-player image
- dashboard player-photo history
- Python bytecode
- raw YOLO captures and their metadata
- generated YOLO runs and predictions
- human-image dataset samples

The files were retained locally. Removing them from the current Git tree does
not erase them from earlier Git commits or existing GitHub clones. Rewriting
published history is a separate disruptive operation and requires explicit
approval, coordination, and a fresh-clone migration plan.

## Operator Review Schedule

Review storage monthly and before making a device image or support archive:

1. Confirm `.env`, credentials, player images, logs, and model data are absent
   from staged Git changes.
2. Review player-photo and raw-capture ages against the limits above.
3. Confirm only approved private storage contains retained human-image data.
4. Remove superseded AI runs and temporary predictions after preserving needed
   metrics separately.
5. Check log and database sizes before disk usage can affect machine operation.
6. Record any retention exception with an owner, purpose, review date, and
   deletion date.

Run the read-only inventory at any time:

```bash
.venv/bin/python scripts/maintenance/audit_data_retention.py
.venv/bin/python scripts/maintenance/audit_data_retention.py --json
```

No cleanup command should run while a game, camera capture, labeling export, or
model-training job is active. Destructive cleanup must begin with a dry-run or
inventory and requires operator review of the exact targets.

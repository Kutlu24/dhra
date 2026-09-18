"""Seed a DHRA store with small, clearly-fake demo content.

Used only for the public demo deployment (see render.yaml / Dockerfile),
which runs on Render's free tier -- no persistent disk, so the store is
empty on every container start. This script is safe to run repeatedly:
it does nothing if the store already has items (e.g. a visitor already
added some during the container's lifetime).

None of this text is real research data -- it exists only so a first-time
visitor to the demo sees a non-empty corpus.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dhra.repo import DHRARepo  # noqa: E402

DEMO_PASSAGES = [
    (
        "The wooden bridge at Tokat was first recorded in a 1721 survey and "
        "was repaired after storm damage in 1849.",
        "demo_source_survey_1721",
    ),
    (
        "A 1902 traveller's account describes the market quarter of Tokat as "
        "busy with caravan trade from the east.",
        "demo_source_travel_account_1902",
    ),
    (
        "Local registers note a fire in the Tokat market quarter in 1867, "
        "after which several shops were rebuilt in stone rather than wood.",
        "demo_source_fire_register_1867",
    ),
]


def main() -> None:
    store_dir = os.environ.get("DHRA_STORE_DIR", "./store")
    repo = DHRARepo(store_dir)
    if repo.corpus_version().item_ids:
        print(f"DHRA demo seed: store already has items, skipping ({store_dir})")
        return
    for text, source_id in DEMO_PASSAGES:
        repo.ingest_text(text, source_id=source_id, original_reference="Demo deployment -- fabricated example, not real research data")
    print(f"DHRA demo seed: added {len(DEMO_PASSAGES)} demo passages to {store_dir}")


if __name__ == "__main__":
    main()

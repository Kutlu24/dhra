#!/bin/sh
# Runs as root (see Dockerfile) so it can fix ownership on a freshly-mounted
# volume before dropping to the non-root "user" for the actual server
# process - same pattern as fundraising-assistant's docker-entrypoint.sh.
# Needed because Render never mounted a persistent volume here (free tier
# has no disk), so this never surfaced there: a Docker named volume's mount
# point is created root:root regardless of the image's own directory
# ownership, and "user" (uid 1000, set at build time) can't write to it -
# a real, confirmed PermissionError on first boot against a real volume
# (see docs/home-server-migration-analysis.md in the interpreter's own
# repo for the debugging session this came out of).
set -e

for dir in "$DHRA_STORE_DIR" "$DHRA_ACCOUNTS_DIR"; do
  if [ -n "$dir" ]; then
    mkdir -p "$dir"
    chown -R user:user "$dir"
  fi
done

exec su -s /bin/sh user -c "python scripts/seed_demo_store.py && dhra --store \"$DHRA_STORE_DIR\" web --host 0.0.0.0 --port ${PORT:-7860}"

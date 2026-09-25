FROM python:3.11-slim

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1

# poppler-utils: pdftotext, used by PdfToTextTranscriber for PDF uploads.
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

RUN pip install --no-cache-dir --upgrade pip

COPY --chown=user pyproject.toml ./
COPY --chown=user src ./src
COPY --chown=user scripts ./scripts

RUN pip install --no-cache-dir --user -e .

# Bake the Whisper model (dhra.interpreter, mounted at /interpreter) into
# the image at build time instead of letting faster-whisper download it on
# the first real request - avoids a slow, user-facing first transcription.
# "base" (not config.py's local-dev default "small") to leave headroom on
# Render's free 512MB plan, which DHRA's own workload already shares - see
# the interpreter's own README for a real OOM incident this size choice
# was fixing there before it was mounted here. If WHISPER_MODEL_SIZE is
# changed in the Render dashboard, update this ARG to match, or the
# container just re-downloads the right one on first use (slower, not
# broken).
ARG WHISPER_MODEL_SIZE=base
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('$WHISPER_MODEL_SIZE', device='cpu', compute_type='int8')"

# Render's free plan has no persistent disk, so the store lives in the
# container's own filesystem and is reset on every restart -- fine for a
# temporary/demo deployment, and it's reseeded (only if empty) at startup.
ENV DHRA_STORE_DIR=$HOME/app/store

# Same container, same reset-on-restart caveat -- an account created on
# this deployment specifically is exactly as ephemeral as the shared demo
# corpus (see signup.html's own warning, shown whenever DHRA_DEMO_BANNER
# is set). Real persistence needs self-hosting or a plan with a disk.
ENV DHRA_ACCOUNTS_DIR=$HOME/app/accounts

EXPOSE 7860

# Root only to let the entrypoint chown a freshly-mounted volume before it
# execs the real server as "user" - never runs application code as root.
USER root
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

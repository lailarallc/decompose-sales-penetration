FROM python:3.11-slim AS base

WORKDIR /app

# Vendored packages first (they change less often than app code). Install order
# matters: cinderhaven-store-universe is the canonical-universe SSOT that the
# household panel depends on, so it goes in before the panel.
COPY packages/ /app/packages/
RUN pip install --no-cache-dir /app/packages/lailara-palette/ \
 && pip install --no-cache-dir /app/packages/cinderhaven-store-universe/ \
 && pip install --no-cache-dir /app/packages/cinderhaven-household-panel/

# Install app dependencies (the local packages above already satisfy their pins).
COPY pyproject.toml /app/
RUN pip install --no-cache-dir .

# Copy application code
COPY app/ /app/app/
COPY assets/ /app/assets/
COPY wsgi.py /app/

# Drop root: run the server as an unprivileged user (defense in depth — the app
# writes nothing to disk and needs no elevated capability).
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8050

# No DATABASE_URL — Decompose has no database. Each gunicorn worker warms its own
# in-process panel copy at boot (~0.6s), then serves everything from cache.
CMD ["gunicorn", "wsgi:server", "--bind", "0.0.0.0:8050", "--workers", "2", "--timeout", "120"]

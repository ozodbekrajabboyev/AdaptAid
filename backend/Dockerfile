# AdaptAid API. Build from the repo root: docker build -f backend/Dockerfile .
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OPENBLAS_NUM_THREADS=1

# libgomp1: OpenMP runtime. The implicit (ALS) wheel for linux/arm64 does not bundle it
# (the import check below fails without it). Retries ride out mirror hiccups.
RUN for i in 1 2 3; do apt-get -o Acquire::Retries=5 update && break || sleep 10; done \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

WORKDIR /srv/adaptaid
COPY backend/pyproject.toml backend/
COPY backend/app backend/app
COPY backend/engine backend/engine
# Editable install: the `adaptaid` command then resolves content/, alembic/ and research/
# relative to this source tree, exactly like `python -m app.cli` does.
RUN pip install -e ./backend \
    && python -c "import implicit, sklearn, numpy; from implicit.cpu.als import AlternatingLeastSquares; print('ML stack ok')"

COPY backend/alembic.ini backend/
COPY backend/alembic backend/alembic
COPY backend/entrypoint.sh backend/
# Content pack (for `adaptaid seed`) and offline research results (for `adaptaid import-research`)
COPY content content
COPY research/outputs research/outputs

RUN chmod +x backend/entrypoint.sh && chown -R app:app /srv/adaptaid
USER app
WORKDIR /srv/adaptaid/backend
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
ENTRYPOINT ["./entrypoint.sh"]

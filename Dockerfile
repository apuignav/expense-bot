# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm AS builder

ENV PATH="/opt/venv/bin:$PATH" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv "$VIRTUAL_ENV"

WORKDIR /build
COPY setup.py README.md ./
COPY expensebot ./expensebot
RUN pip install --upgrade pip wheel \
    && pip install .


FROM python:3.11-slim-bookworm

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Zurich

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 expensebot \
    && useradd --uid 10001 --gid expensebot --no-create-home expensebot \
    && mkdir -p /data \
    && chown expensebot:expensebot /data

COPY --from=builder /opt/venv /opt/venv

USER expensebot
WORKDIR /data

ENTRYPOINT ["expensebot"]
CMD ["--config", "/config/expensebot.yaml", "--state-path", "/data/state.yaml", "--log-path", "", "--interactive"]

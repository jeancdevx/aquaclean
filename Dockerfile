FROM node:22.22.2-bookworm-slim@sha256:9f6d5975c7dca860947d3915877f85607946403fc55349f39b4bc3688448bb6e AS web
ENV ASTRO_TELEMETRY_DISABLED=1 PNPM_HOME=/pnpm
ENV PATH="/pnpm:$PATH"
RUN corepack enable && corepack prepare pnpm@10.33.2 --activate
WORKDIR /build/web
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

FROM ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 AS uv
FROM python:3.12.15-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS runtime
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev
COPY migrations ./migrations
COPY knowledge ./knowledge
COPY config ./config
COPY reference_data ./reference_data
COPY --from=web /build/web/dist ./web/dist
RUN useradd --uid 10001 --create-home app && mkdir -p /data/media && chown -R app:app /data /app
USER app
EXPOSE 8000
CMD ["uvicorn", "aquaclean.interfaces.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# Multi-stage: React UI + Python API (Gemini + MiniLM/FAISS)
# Cloud Run: set memory ≥ 1Gi

# --- frontend ---
FROM node:22-alpine AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
ENV VITE_API_BASE=
RUN npm run build

# --- api ---
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Do not retain downloaded dependency archives in the final image.
ENV UV_NO_CACHE=1
COPY pyproject.toml uv.lock README.md ./
# Install third-party dependencies before copying frequently changing code/data.
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY scripts ./scripts
COPY data/structured ./data/structured
COPY data/raw ./data/raw

# Install the project; Linux PyTorch is locked to the CPU-only distribution.
RUN uv sync --frozen --no-dev
RUN uv run --frozen python -c "import torch; assert torch.version.cuda is None, 'Expected CPU-only PyTorch'; print('PyTorch CPU:', torch.__version__)"

# Build FAISS index at image build time; the script creates data/index itself.
# Needs filings in data/raw, but no local index or .gitkeep placeholder.
RUN uv run --frozen python scripts/build_index.py

COPY --from=frontend /web/dist ./web/dist

ENV HOST=0.0.0.0
ENV PORT=8080
ENV LLM_PROVIDER=gemini
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Cloud Run injects PORT
CMD ["sh", "-c", "exec uv run --frozen uvicorn finance_analyst.api:app --host 0.0.0.0 --port ${PORT:-8080}"]

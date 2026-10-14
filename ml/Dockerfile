FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY README.md ./
COPY tests ./tests

ENTRYPOINT ["fluxsg-forecast"]
CMD ["train", "--input-dir", "data/raw", "--output-dir", "artifacts/latest"]

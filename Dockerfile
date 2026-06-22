FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eval/       eval/
COPY storage/    storage/
COPY reporting/  reporting/
COPY data/       data/
COPY prompts/    prompts/
COPY main.py     .
COPY .env.example .env.example

RUN mkdir -p storage reports

ENV LLM_BACKEND=groq
ENV GROQ_MODEL=llama-3.1-8b-instant
ENV GROQ_BASE_URL=https://api.groq.com/openai/v1
ENV DEMO_MODE=false
ENV DEMO_CASE_LIMIT=10
ENV SKIP_JUDGE=false
ENV DB_PATH=storage/runs.db

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "from eval.config import PromptConfig; print('healthy')" || exit 1

ENTRYPOINT ["python", "main.py"]
CMD ["--yaml", "prompts/v1.yaml", "--dataset", "data/golden_dataset.json"]

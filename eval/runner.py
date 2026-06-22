"""Async runner that sends evaluation requests to LM Studio."""

from openai import AsyncOpenAI
import asyncio, time, json
from tqdm.asyncio import tqdm_asyncio
from eval.config import PromptConfig
from dotenv import load_dotenv
import os

load_dotenv(override=True)


def get_llm_config():
    backend = os.getenv("LLM_BACKEND", "local")
    if backend == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not set. Get a free key at console.groq.com"
            )
        return {
            "client": AsyncOpenAI(
                base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
                api_key=api_key
            ),
            "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "backend": "groq",
            "concurrency": 5  # Groq handles more concurrent requests
        }
    else:
        return {
            "client": AsyncOpenAI(
                base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
                api_key="lm-studio"
            ),
            "model": os.getenv("LM_STUDIO_MODEL", "qwen2.5-3b-instruct"),
            "backend": "local",
            "concurrency": 3
        }


async def warmup_model(client, model):
    """Send one dummy request so LM Studio loads model into VRAM before timed eval."""
    try:
        await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say: ready"}],
            max_tokens=5,
            temperature=0.0
        )
        print("Model warmed up successfully.")
    except Exception as e:
        print(f"Warmup failed (non-fatal): {e}")


def _clean_prediction(raw: str) -> str:
    """Clean LLM output — local models sometimes add extra words."""
    text = raw.strip().lower()
    if "positive" in text:
        return "positive"
    elif "negative" in text:
        return "negative"
    elif "neutral" in text:
        return "neutral"
    else:
        return "unknown"


async def run_single_case(client, config: PromptConfig, case: dict, model: str) -> dict:
    """Run a single evaluation case against the LLM."""
    messages = config.build_messages(case["text"])
    start = time.time()
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=10,
        temperature=0.0
    )
    latency_ms = (time.time() - start) * 1000

    raw_predicted = response.choices[0].message.content.strip().lower()
    predicted = _clean_prediction(raw_predicted)

    return {
        "id": case["id"],
        "text": case["text"],
        "true_label": case["label"],
        "predicted_label": predicted,
        "raw_predicted": raw_predicted,
        "correct": predicted == case["label"],
        "latency_ms": round(latency_ms, 1),
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "difficulty": case["expected_difficulty"],
        "edge_type": case.get("edge_type", "standard"),
        "version_id": config.version_id,
        "backend": os.getenv("LLM_BACKEND", "local"),
        "model_name": model,
    }


async def run_all(yaml_path: str, dataset_path: str, concurrency: int = 3) -> list:
    """Run evaluation across the entire dataset with controlled concurrency."""
    # Load config and dataset
    config = PromptConfig.from_yaml(yaml_path)
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    llm_config = get_llm_config()
    client = llm_config["client"]
    model = llm_config["model"]
    
    # Handle demo mode
    is_demo = os.getenv("DEMO_MODE", "false").lower() == "true"
    if is_demo:
        limit = int(os.getenv("DEMO_CASE_LIMIT", "10"))
        dataset = dataset[:limit]
        print(f"Backend: {llm_config['backend']} | Model: {model} | Cases: {limit} (demo mode)")
    else:
        print(f"Backend: {llm_config['backend']} | Model: {model} | Cases: {len(dataset)}")

    # Warm up the model before timed evaluation
    if llm_config["backend"] == "local":
        await warmup_model(client, model)

    concurrency = llm_config.get("concurrency", 3)
    semaphore = asyncio.Semaphore(concurrency)

    async def _run_with_semaphore(case):
        async with semaphore:
            try:
                return await run_single_case(client, config, case, model)
            except Exception as e:
                print(f"  ⚠ Error on case {case['id']}: {e}")
                return {
                    "id": case["id"],
                    "text": case["text"],
                    "true_label": case["label"],
                    "predicted_label": "error",
                    "correct": False,
                    "latency_ms": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "difficulty": case["expected_difficulty"],
                    "edge_type": case.get("edge_type", "standard"),
                    "version_id": config.version_id,
                    "backend": llm_config["backend"],
                    "model_name": model,
                }

    tasks = [_run_with_semaphore(case) for case in dataset]
    results = await tqdm_asyncio.gather(*tasks, desc=f"Evaluating {config.version_id}")

    error_count = sum(1 for r in results if r["predicted_label"] == "error")
    print(f"Completed {len(results)}/{len(dataset)} cases. Errors: {error_count}")

    return list(results)

import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os, re

load_dotenv()

JUDGE_PROMPT = """You are an evaluation judge for a sentiment classification system.

Your job: given a tweet, the correct sentiment label, and a model's predicted label,
score the prediction quality from 1 to 5.

Scoring rubric:
5 = Perfect: predicted label exactly matches the correct label
4 = Near-perfect: prediction is directionally correct but used a synonym
    (e.g. predicted "happy" when correct is "positive" — same direction, wrong vocabulary)
3 = Partial: prediction captures part of the sentiment but misses nuance
    (e.g. predicted "neutral" when correct is "positive" — adjacent, not opposite)
2 = Wrong direction: prediction is clearly incorrect
    (e.g. predicted "positive" when correct is "negative")
1 = Complete failure: prediction is incoherent, empty, or in wrong format

Input:
Tweet: {tweet}
Correct label: {true_label}
Predicted label: {predicted_label}

Respond with ONLY a JSON object in this exact format:
{{"score": <integer 1-5>, "reason": "<one sentence explanation>"}}
Do not add any text before or after the JSON."""

async def judge_single(client, model, tweet, true_label, predicted_label) -> dict:
    """Get LLM-as-judge score for one prediction."""
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": JUDGE_PROMPT.format(
                    tweet=tweet[:200],
                    true_label=true_label,
                    predicted_label=predicted_label
                )
            }],
            max_tokens=80,
            temperature=0.0
        )
        raw = response.choices[0].message.content.strip()
        
        # Parse JSON — local models sometimes wrap in backticks
        raw = re.sub(r'^```json?\s*|\s*```$', '', raw, flags=re.MULTILINE).strip()
        import json
        parsed = json.loads(raw)
        
        return {
            "judge_score": int(parsed.get("score", 3)),
            "judge_reason": parsed.get("reason", "")[:200]
        }
    except Exception as e:
        # Fallback: derive score from exact match
        fallback_score = 5 if predicted_label == true_label else 2
        return {
            "judge_score": fallback_score,
            "judge_reason": f"Fallback scoring (judge failed: {str(e)[:60]})"
        }

async def judge_batch(results: list, concurrency: int = 3) -> list:
    """Add judge scores to all results. Returns enriched results list."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    backend = os.getenv("LLM_BACKEND", "local")
    if backend == "groq":
        client = AsyncOpenAI(
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=os.getenv("GROQ_API_KEY", "")
        )
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    else:
        client = AsyncOpenAI(
            base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
            api_key="lm-studio"
        )
        model = os.getenv("LM_STUDIO_MODEL", "qwen2.5-3b-instruct")
    
    sem = asyncio.Semaphore(concurrency)
    
    async def judge_with_sem(result):
        async with sem:
            judgment = await judge_single(
                client, model,
                result['text'],
                result['true_label'],
                result.get('raw_predicted', result['predicted_label'])
            )
            return {**result, **judgment}
    
    from tqdm.asyncio import tqdm_asyncio
    print(f"Running LLM-as-judge on {len(results)} cases...")
    enriched = await tqdm_asyncio.gather(*[judge_with_sem(r) for r in results])
    return list(enriched)

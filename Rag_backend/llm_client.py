import json
import time
import random
import logging
import threading
from collections import deque
from enum import Enum
from pydantic import BaseModel, ValidationError
from typing import TypeVar, Type
from Rag_backend.config.settings import settings
from openai import OpenAI, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound = BaseModel)

#Task -> model mapping

class TaskType(str, Enum):
    JUDGE = 'judge'
    GENERATION = "generation"


Model_map = {
    TaskType.JUDGE : settings.GROQ_MODEL_JUDGE,
    TaskType.GENERATION: settings.GROQ_MODEL_GENERATION,
}

def resolve_model(task: TaskType, model_override: str | None) -> str:
    if model_override:
        return model_override
    return Model_map[task]


#ratelimiter using sliding window log algorithm - throttles Before you get a 429
#useful when firing many calls in loop (RAGAS eval, batch ingestion)

class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period = period_seconds
        self._calls : deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            while self._calls and now - self._calls[0] > self.period:
                self._calls.popleft()

            if len(self._calls) >= self.max_calls:
                sleep_for = self.period - (now - self._calls[0])
                if sleep_for > 0:
                    logger.debug(f"[LLM] rate limiter throttling | sleep={sleep_for:.2f}s")
                    time.sleep(sleep_for)
                now = time.monotonic()
                while self._calls and now - self._calls[0] > self.period:
                    self._calls.popleft()

            self._calls.append(time.monotonic())


rate_limiters: dict[TaskType, RateLimiter]= {
    TaskType.JUDGE : RateLimiter(settings.RATE_LIMIT_JUDGE_CALLS_PER_MIN, 60),
    TaskType.GENERATION: RateLimiter(settings.RATE_LIMIT_GENERATION_CALLS_PER_MIN, 60),
}            


def extract_retry_after(exc: RateLimitError)-> float | None:
    "Pull retry-after header from the API response if present"
    try:
        response = getattr(exc, "response", None)
        if response is not None:
            header_val = response.headers.get("retry-after")
            if header_val is not None:
                return float(header_val)
            
    except Exception:
        pass

    return None


def build_example_instance(schema: Type[T]) -> dict:
    """Builds a plausible example instance from schema fields, to show
    the model what an actual filled-in response looks like — not just
    the abstract schema, which smaller/faster models can echo back verbatim."""
    example = {}
    for field_name, field_info in schema.model_fields.items():
        annotation = field_info.annotation
        if annotation is bool:
            example[field_name] = True
        elif annotation is str:
            example[field_name] = "example value"
        else:
            example[field_name] = "..."
    return example

def backoff_wait(attempt: int, exc: RateLimitError, base: float =2.0, cap: float =60)->float:
    """Prefer server-provided Retry-after ; otherwise capped exponential backoff + jitter"""
    retry_after = extract_retry_after(exc)
    if retry_after is not None:
        return retry_after + random.uniform(0, 0.5)
    wait = min(cap, base*(2**(attempt -1)))
    
    return wait + random.uniform(0, wait*0.25)


def get_client() -> OpenAI:
    """openai -compactible client pointed at Groq's server."""
    return OpenAI(
        api_key = settings.active_api_key,
        base_url= settings.active_base_url,
        timeout= settings.LLM_TIMEOUT,
        max_retries = 0
    )


def call_llm_raw(
    prompt: str,
    system: str = "You are a helpful research assistant.",
    temperature: float = settings.LLM_TEMPERATURE,
    task: TaskType = TaskType.GENERATION,
    model: str | None = None,
) -> str:
    """
    Call Groq LLM and return plain text response.
    Use for freeform long outputs (e.g. synthesizer report)
    where JSON wrapping causes the model to drop the container.
 
    task: which model to route to (JUDGE for cheap/fast eval calls,
          GENERATION for user-facing answers). Override with `model=` if needed.
    """
    client = get_client()
    resolved_model = resolve_model(task, model)
    limiter = rate_limiters[task]
    last_error: Exception | None = None

    for attempt in range(1, settings.LLM_MAX_RETRIES + 1):
        try:
            limiter.acquire()  # proactive throttle before every call
 
            logger.debug(
                f"[LLM] groq/{resolved_model} | task={task} | "
                f"raw text call | attempt={attempt}"
            )
 
            response = client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
 
            raw = response.choices[0].message.content.strip()
            logger.debug(f"[LLM] raw success | chars={len(raw)}")
            return raw
        


        except RateLimitError as e:
            last_error = e
            wait = backoff_wait(attempt, e)
            logger.warning(f"[LLM] rate limit | task={task} | waiting {wait:.1f}s...")
            time.sleep(wait)
 
        except APITimeoutError as e:
            last_error = e
            logger.warning(f"[LLM] timeout | attempt={attempt}")
 
        except Exception as e:
            last_error = e
            logger.error(f"[LLM] unexpected error | attempt={attempt} | {e}")
            break
 
    raise RuntimeError(
        f"[LLM] all {settings.LLM_MAX_RETRIES} attempts failed "
        f"for raw call | task={task} | last_error={last_error}"
    )


def call_llm_structured(
    prompt: str,
    schema: Type[T],
    system: str = "You are a helpful research assistant.",
    temperature: float = settings.LLM_TEMPERATURE,
    task: TaskType = TaskType.JUDGE,
    model: str | None = None,
) -> T:
    """
    Call Groq LLM and return a validated Pydantic object.
    Groq doesn't support .parse() so we ask for JSON manually
    and validate through the schema ourselves.
 
    task: defaults to JUDGE since structured/schema calls are typically
          scoring, extraction, or guardrail checks rather than final generation.
          Pass task=TaskType.GENERATION if you need structured output from the
          generation model instead.
    """
    client = get_client()
    resolved_model = resolve_model(task, model)
    limiter = rate_limiters[task]
    last_error: Exception | None = None
 
    system_with_schema = (
        f"{system}\n\n"
        f"You must respond with ONLY valid JSON that matches this schema:\n"
        f"{json.dumps(schema.model_json_schema(), indent=2)}\n"
        f"Example of a valid response:\n"
        f"{json.dumps(build_example_instance(schema), indent=2)}\n\n"
        f"Return actual values for this specific input — do NOT return the schema "
        f"definition itself. No explanation. No markdown. Just the JSON object."
    )
 
    for attempt in range(1, settings.LLM_MAX_RETRIES + 1):
        try:
            limiter.acquire()
 
            logger.debug(
                f"[LLM] groq/{resolved_model} | task={task} | "
                f"schema={schema.__name__} | attempt={attempt}"
            )
 
            response = client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {"role": "system", "content": system_with_schema},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
 
            raw = response.choices[0].message.content.strip()
 
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
 
            parsed = schema.model_validate_json(raw)
            logger.debug(f"[LLM] success | schema={schema.__name__}")
            return parsed
 
        except RateLimitError as e:
            last_error = e
            wait = backoff_wait(attempt, e)
            logger.warning(f"[LLM] rate limit | task={task} | waiting {wait:.1f}s...")
            time.sleep(wait)
 
        except APITimeoutError as e:
            last_error = e
            logger.warning(f"[LLM] timeout | attempt={attempt}")
 
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            logger.warning(f"[LLM]  JSON/schema validation failed | attempt={attempt} | {e}")
 
        except Exception as e:
            last_error = e
            logger.error(f"[LLM] unexpected error | attempt={attempt} | {e}")
            break
 
    raise RuntimeError(
        f"[LLM] all {settings.LLM_MAX_RETRIES} attempts failed "
        f"for schema={schema.__name__} | task={task} | last_error={last_error}"
    )
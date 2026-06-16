from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from schemas import PersonExtraction
import instructor, asyncio
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

app = FastAPI(title="Local SLM API", version="1.0")

client = instructor.from_openai(
    OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
    mode=instructor.Mode.JSON,
)

executor = ThreadPoolExecutor(max_workers=4)


class ExtractRequest(BaseModel):
    text: str
    model: str = "mistral"  # default model


def _call_model(request: ExtractRequest):
    return client.chat.completions.create(
        model=request.model,
        messages=[
            {
                "role": "user",
                "content": (
                    f"""
Extract person information from this text and return a JSON object exactly matching the schema.

Text:
{request.text}

Return JSON with these fields:
- name (string) - required
- age (integer or null)
- role (string or null)
- location (string or null)
- confidence (float 0.0-1.0)

Example:
{{"name":"Alice Smith","age":30,"role":"Engineer","location":"Seattle","confidence":0.95}}
"""
                ),
            }
        ],
        response_model=PersonExtraction,
        max_retries=1,
    )


@app.post("/extract", response_model=PersonExtraction)
async def extract(request: ExtractRequest):
    future = executor.submit(_call_model, request)
    try:
        # Fail fast if upstream model hangs without blocking the event loop
        result = await asyncio.wait_for(asyncio.wrap_future(future), timeout=90)

        # Normalize result into a dict matching PersonExtraction
        # Try several common shapes returned by LLM clients
        parsed = None
        if hasattr(result, "dict"):
            parsed = result.dict()
        # If result is already a dict with expected keys, use it
        elif isinstance(result, dict):
            parsed = result
        else:
            # Try attribute access (e.g., result.choices[0].message.content)
            try:
                choices = getattr(result, "choices", None) or result.get("choices") if hasattr(result, 'get') else None
            except Exception:
                choices = None
            content = None
            if choices:
                try:
                    # support both object and dict choices
                    first = choices[0]
                    if hasattr(first, "message"):
                        content = getattr(first.message, "content", None)
                    elif isinstance(first, dict):
                        content = first.get("message", {}).get("content") or first.get("text")
                except Exception:
                    content = None
            if content is None:
                # fallback to string conversion
                content = str(result)

            # Extract first JSON object from content
            import re, json

            m = re.search(r"\{[\s\S]*\}", content)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except Exception:
                    parsed = None

        # Validate, normalize and return
        if parsed is not None:
            try:
                # If parsed is nested, try to find a dict that looks like extraction
                if not isinstance(parsed, dict):
                    raise ValueError("parsed is not a dict")

                # If parsed contains a nested dict with a name key, prefer that
                if "name" not in parsed:
                    for v in parsed.values():
                        if isinstance(v, dict) and "name" in v:
                            parsed = v
                            break

                # Coerce and normalize fields
                # name: if missing, try to extract from original request text
                if not parsed.get("name"):
                    import re

                    m = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", request.text)
                    if m:
                        parsed["name"] = m.group(1)

                # age: coerce strings like "30" or "30 years" to int, else None
                age = parsed.get("age")
                if age is not None and age != "":
                    try:
                        if isinstance(age, str):
                            import re

                            m = re.search(r"(\d{1,3})", age)
                            if m:
                                parsed["age"] = int(m.group(1))
                            else:
                                parsed["age"] = None
                        elif isinstance(age, (int, float)):
                            parsed["age"] = int(age)
                        else:
                            parsed["age"] = None
                    except Exception:
                        parsed["age"] = None
                else:
                    parsed["age"] = None

                # role and location: normalize empty strings to None
                for k in ("role", "location"):
                    v = parsed.get(k)
                    if v is None or (isinstance(v, str) and v.strip() == ""):
                        parsed[k] = None

                # confidence: coerce to float 0.0-1.0, if percentage convert
                conf = parsed.get("confidence")
                try:
                    if conf is None or conf == "":
                        parsed["confidence"] = 0.5
                    else:
                        if isinstance(conf, str):
                            conf_s = conf.strip().rstrip('%')
                            val = float(conf_s)
                        else:
                            val = float(conf)
                        # if value looks like percentage (>1), convert
                        if val > 1:
                            val = val / 100.0
                        parsed["confidence"] = max(0.0, min(1.0, val))
                except Exception:
                    parsed["confidence"] = 0.5

                # Final validation
                validated = PersonExtraction.parse_obj(parsed)
                return validated.dict()
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid extraction format: {e}")

        # If we reach here, we couldn't parse a valid JSON extraction
        raise HTTPException(status_code=422, detail="Could not parse model output as PersonExtraction JSON")
    except (FuturesTimeoutError, asyncio.TimeoutError):
        raise HTTPException(status_code=504, detail="Upstream model timeout")
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "models": ["mistral", "llama3.2", "phi3:mini"]}



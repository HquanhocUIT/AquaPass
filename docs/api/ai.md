# Optional AI assistance

AquaPass keeps the deterministic evidence and ranking modules as the source of
truth. The optional Gemini integration adds grounded suggestions and wording;
it never changes the evidence IDs, ranking order or prototype scores.

## Configuration

Set these values in the local repository `.env` file. Never commit the API key:

```text
LLM_ENABLED=true
LLM_API_KEY=your-gemini-api-key
LLM_MODEL=gemini-2.5-flash-lite
LLM_TIMEOUT_SECONDS=12
```

The API uses Gemini `generateContent` with JSON response schema. If the key is
missing, the model is unavailable, the request times out, or the response
contains an ID not present in the input, the endpoint returns the deterministic
fallback and explains the reason in `fallback_reason`.

## Grounded evidence-gap suggestions

`POST /api/ai/evidence-gaps` accepts the existing evidence graph contract and
returns only gaps grounded in records marked `missing_for` and `missing`.
Gemini is not allowed to invent evidence IDs, hypotheses or external facts.

## Grounded ranking explanations

`POST /api/ai/ranking-explanations` accepts the existing candidate contract.
The deterministic engine calculates the scores and order first. Gemini may
rewrite only the explanation, strengths and trade-offs using those values.
If validation fails, the original deterministic explanation is returned.

For a local test without an API key, run:

```powershell
cd backend
python -m pytest -q
```

## Refactoring Checklist

### Issues Found:
- [ ] Function `generate_listings_batch` does too much (input validation + image conversion + prompt creation + API call + output validation + retry pacing + result/error file writes)
- [ ] Function `image_to_base64` does too much (type detection + conversion + filesystem reads + base64 normalization + error branching)
- [ ] Error handling is too broad in `image_to_base64` (`except Exception: pass` hides real failures and makes debugging difficult)
- [ ] JSON parsing fallback in `safe_json_loads` can hide original malformed-response context by extracting first/last braces
- [ ] No real fallback when dataset load fails (prints "Using local images instead..." but `products_df` may still be undefined before batch call)
- [ ] Code repeated in models `ProductInput` and `ProductJSON` (duplicated schema fields and validators; should be shared base model/helper)
- [ ] Repeated client setup (`client = OpenAI(...)` created twice) increases drift risk and confusion
- [ ] Mixed concerns in `generate_listings_batch` (validation/domain processing mixed with persistence concerns: JSONL/CSV output and console reporting)
- [ ] Mixed concerns in `call_openai_for_listing` (transport/API call mixed with response parsing and schema validation)
- [ ] Hardcoded model/runtime values (`gpt-4.1-mini`, `temperature=0.7`, `n_products=10`, `sleep_seconds=0.5`)
- [ ] Hardcoded data/loading values (`split=\"train[:100]\"`, output folder `generated_listings`, `.env` relative path logic)
- [ ] Hardcoded business constraints duplicated (`year` range `1900..2100` appears in multiple models)
- [ ] Hardcoded image handling assumptions (always encoding as JPEG and using `data:image/jpeg;base64,...`)

### Priority:
1. Fix failure handling and silent errors first (`products_df` undefined path, `except Exception: pass`, and clearer parse/validation error surfacing).
2. Decompose monolithic functions and separate concerns (domain validation/processing vs API transport vs file persistence).
3. Centralize duplicated schemas/constants and parameterize hardcoded runtime/config values.

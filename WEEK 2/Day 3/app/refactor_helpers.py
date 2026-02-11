from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


YEAR_MIN = 1900
YEAR_MAX = 2100
logger = logging.getLogger(__name__)


# Build one consistent error message format.
def build_error_message(
    function_name: str,
    error_type: str,
    location: str,
    error_message: str,
    suggestion: str,
) -> str:
    return (
        f"ERROR in {function_name}(): {error_type}\n"
        f"  Location: {location}\n"
        f"  Message: {error_message}\n"
        f"  Suggestion: {suggestion}"
    )


# Find source file and line where exception happened.
def get_traceback_location(error: Exception) -> str:
    tb = traceback.extract_tb(error.__traceback__) if error.__traceback__ else []
    if not tb:
        return "unknown source"
    last = tb[-1]
    return f"{last.filename}:{last.lineno}"


# Print a detailed error and return the message text.
def report_error(
    function_name: str,
    error: Exception,
    location: str,
    suggestion: str,
    message_override: Optional[str] = None,
) -> str:
    source_location = get_traceback_location(error)
    full_location = f"{location}; source={source_location}"
    error_message = message_override or str(error) or repr(error)
    message = build_error_message(
        function_name=function_name,
        error_type=type(error).__name__,
        location=full_location,
        error_message=error_message,
        suggestion=suggestion,
    )
    logger.error(message)
    print(message)
    return message


# Clean a text value and reject empty text.
def strip_non_empty(value: str) -> str:
    """Trim string and enforce non-empty content."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


# Check that the year is in an allowed range.
def validate_year_range(value: Optional[float]) -> Optional[float]:
    """Validate optional year range used across product schemas."""
    if value is None:
        return None
    if value < YEAR_MIN or value > YEAR_MAX:
        raise ValueError(f"year must be between {YEAR_MIN} and {YEAR_MAX}")
    return value


# Product data model used for validation.
class ProductBase(BaseModel):
    """Shared product schema used for input row and JSON-file validation."""

    model_config = ConfigDict(extra="forbid")

    id: int
    gender: str = Field(..., min_length=1)
    masterCategory: str = Field(..., min_length=1)
    subCategory: str = Field(..., min_length=1)
    articleType: str = Field(..., min_length=1)
    baseColour: str = Field(..., min_length=1)
    season: str = Field(..., min_length=1)
    year: Optional[float] = None
    usage: str = Field(..., min_length=1)
    productDisplayName: str = Field(..., min_length=1)

    # Clean required text fields.
    @field_validator(
        "gender",
        "masterCategory",
        "subCategory",
        "articleType",
        "baseColour",
        "season",
        "usage",
        "productDisplayName",
    )
    @classmethod
    def _strip_required_strings(cls, value: str) -> str:
        return strip_non_empty(value)

    # Validate the optional year field.
    @field_validator("year")
    @classmethod
    def _validate_year(cls, value: Optional[float]) -> Optional[float]:
        return validate_year_range(value)


# Listing data model used for validation.
class ListingOutput(BaseModel):
    """Validated shape of generated listing response."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=5)
    description: str = Field(..., min_length=20)
    features: List[str] = Field(..., min_length=3, max_length=10)
    keywords: List[str] = Field(default_factory=list, max_length=20)

    # Clean text fields.
    @field_validator("title", "description")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return strip_non_empty(value)

    # Make sure list fields contain clean strings.
    @field_validator("features", "keywords")
    @classmethod
    def _normalize_lists(cls, value: List[Any]) -> List[str]:
        return normalize_string_list(value)


# Read a JSON file from disk.
def load_json_file(path: Path) -> Dict[str, Any]:
    """Read JSON from disk with UTF-8 decoding."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        logger.info("Loaded JSON file: %s", path)
        return data
    except FileNotFoundError as error:
        report_error(
            function_name="load_json_file",
            error=error,
            location=f"path={path}",
            suggestion="Check that the file path is correct and the file exists.",
        )
        raise
    except PermissionError as error:
        report_error(
            function_name="load_json_file",
            error=error,
            location=f"path={path}",
            suggestion="Check file read permissions for this path.",
        )
        raise
    except json.JSONDecodeError as error:
        report_error(
            function_name="load_json_file",
            error=error,
            location=f"path={path}, line={error.lineno}, column={error.colno}",
            suggestion="Fix JSON syntax at the shown line/column.",
            message_override=error.msg,
        )
        raise
    except OSError as error:
        report_error(
            function_name="load_json_file",
            error=error,
            location=f"path={path}",
            suggestion="Check disk availability and file accessibility.",
        )
        raise


# Parse a plain JSON string only.
def parse_json_strict(text: str) -> Dict[str, Any]:
    """Parse JSON without fallbacks."""
    try:
        payload = json.loads(text)
        logger.debug("Strict JSON parse succeeded")
        return payload
    except json.JSONDecodeError as error:
        report_error(
            function_name="parse_json_strict",
            error=error,
            location=f"line={error.lineno}, column={error.colno}",
            suggestion="Ensure the text is valid JSON with quoted keys and values.",
            message_override=error.msg,
        )
        raise


# Pull out the first JSON object from mixed text.
def extract_first_json_object(text: str) -> str:
    """Extract the outer-most object from text containing extra content."""
    cleaned = text.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise json.JSONDecodeError("No JSON object found", cleaned, 0)
    return cleaned[start : end + 1]


# Parse JSON safely, even if extra text exists around it.
def safe_json_loads(text: str) -> Dict[str, Any]:
    """Try strict parse first, then parse extracted object block."""
    cleaned = text.strip()
    try:
        return parse_json_strict(cleaned)
    except json.JSONDecodeError:
        try:
            candidate = extract_first_json_object(cleaned)
            logger.debug("Strict parse failed; trying extracted JSON object")
            return parse_json_strict(candidate)
        except json.JSONDecodeError as error:
            report_error(
                function_name="safe_json_loads",
                error=error,
                location="response_text",
                suggestion="Return JSON-only output from the model (no markdown or extra text).",
                message_override=error.msg,
            )
            raise


# Convert Pydantic validation errors into simple readable output.
def format_validation_error(error: ValidationError) -> Dict[str, Any]:
    """Convert Pydantic ValidationError into client-friendly error payload."""
    return {
        "error": "validation_error",
        "details": [
            {
                "field": ".".join(str(part) for part in item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ],
    }


# Validate one product payload against the product model.
def validate_product_payload(payload: Mapping[str, Any]) -> ProductBase:
    """Validate product payload and return typed model."""
    product = ProductBase.model_validate(payload)
    logger.debug("Product payload validation succeeded: id=%s", product.id)
    return product


# Validate one listing payload against the listing model.
def validate_listing_payload(payload: Mapping[str, Any]) -> ListingOutput:
    """Validate listing payload and return typed model."""
    listing = ListingOutput.model_validate(payload)
    logger.debug("Listing payload validation succeeded")
    return listing


# Convert year into display text for prompts.
def format_year_for_prompt(year: Optional[float]) -> str:
    """Format optional year value for prompt display."""
    return str(int(year)) if year is not None else "N/A"


# Build the text prompt sent to the model.
def build_listing_prompt(product: ProductBase) -> str:
    """Build listing prompt from product metadata."""
    year_text = format_year_for_prompt(product.year)

    return f"""
You are an expert ecommerce copywriter for fashion products.
Return valid JSON only. No markdown, no extra text.

Product data:
- id: {product.id}
- name: {product.productDisplayName}
- gender: {product.gender}
- masterCategory: {product.masterCategory}
- subCategory: {product.subCategory}
- articleType: {product.articleType}
- baseColour: {product.baseColour}
- season: {product.season}
- year: {year_text}
- usage: {product.usage}

Output JSON schema:
{{
  "title": "string",
  "description": "string",
  "features": ["string", "string", "string"],
  "keywords": ["string"]
}}

Rules:
- Output must be valid JSON
- Title should include key product attributes (type, color, usage)
- Description should be 2 to 4 sentences
- Features must be 3 to 10 bullet-style strings
- Keywords should include search-friendly terms (type, color, season, gender, usage)
""".strip()


# Parse model text output into JSON.
def parse_listing_json(raw_text: str) -> Dict[str, Any]:
    """Parse raw model output into a JSON object."""
    try:
        return safe_json_loads(raw_text)
    except json.JSONDecodeError as error:
        report_error(
            function_name="parse_listing_json",
            error=error,
            location="raw_model_response",
            suggestion="Update prompt to enforce JSON-only response format.",
            message_override=error.msg,
        )
        raise


# Convert validated listing model to plain dictionary.
def listing_model_to_dict(listing: ListingOutput) -> Dict[str, Any]:
    """Convert validated ListingOutput model to plain dict."""
    return listing.model_dump()


# Parse + validate listing response in one step.
def parse_listing_response(raw_text: str) -> Dict[str, Any]:
    """Parse and validate model response text against ListingOutput schema."""
    try:
        payload = parse_listing_json(raw_text)
        listing = validate_listing_payload(payload)
        logger.debug("Listing response parsed and validated")
        return listing_model_to_dict(listing)
    except (json.JSONDecodeError, ValidationError) as error:
        report_error(
            function_name="parse_listing_response",
            error=error,
            location="model_response_processing",
            suggestion="Check model output format and required listing fields.",
        )
        raise


# Clean a list of strings and remove empty items.
def normalize_string_list(value: Iterable[Any]) -> List[str]:
    """Normalize list-like strings by stripping and dropping empty entries."""
    if not isinstance(value, list):
        raise ValueError("must be a list")

    output: List[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("all items must be strings")
        cleaned = item.strip()
        if cleaned:
            output.append(cleaned)
    return output


# Build one final row to save for results.
def build_result_record(index: Any, product: ProductBase, listing: Mapping[str, Any]) -> Dict[str, Any]:
    """Create output row in one place to avoid repeated dict-building logic."""
    try:
        return {
            "index": index,
            "id": product.id,
            "productDisplayName": product.productDisplayName,
            "gender": product.gender,
            "masterCategory": product.masterCategory,
            "subCategory": product.subCategory,
            "articleType": product.articleType,
            "baseColour": product.baseColour,
            "season": product.season,
            "year": product.year,
            "usage": product.usage,
            "title": listing["title"],
            "description": listing["description"],
            "features": listing["features"],
            "keywords": listing["keywords"],
        }
    except KeyError as error:
        report_error(
            function_name="build_result_record",
            error=error,
            location=f"index={index}",
            suggestion="Ensure listing has title, description, features, and keywords keys.",
        )
        raise

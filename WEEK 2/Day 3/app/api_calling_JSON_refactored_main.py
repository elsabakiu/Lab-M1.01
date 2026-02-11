from __future__ import annotations

import argparse
import base64
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import pandas as pd
from pydantic import BaseModel, ValidationError, field_validator

try:
    # Works when running as module: python -m app.api_calling_JSON_refactored_main
    from app.logging_utils import setup_logging
    from app.openai_client_utils import OpenAIWrapper, build_openai_wrapper
    from app.refactor_helpers import (
        ProductBase,
        build_listing_prompt,
        build_result_record,
        format_validation_error,
        load_json_file,
        parse_listing_response,
        report_error,
        validate_product_payload,
    )
except ModuleNotFoundError:
    # Works when running file directly: python app/api_calling_JSON_refactored_main.py
    from logging_utils import setup_logging
    from openai_client_utils import OpenAIWrapper, build_openai_wrapper
    from refactor_helpers import (
        ProductBase,
        build_listing_prompt,
        build_result_record,
        format_validation_error,
        load_json_file,
        parse_listing_response,
        report_error,
        validate_product_payload,
    )

logger = logging.getLogger(__name__)


DEFAULT_DATASET = "ashraq/fashion-product-images-small"
DEFAULT_SPLIT = "train[:100]"
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_N_PRODUCTS = 10
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_OUTPUT_DIR = Path("outputs/generated_listings")


# Stores settings for one batch run.
@dataclass(frozen=True)
class BatchConfig:
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    n_products: int = DEFAULT_N_PRODUCTS
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS
    output_dir: Path = DEFAULT_OUTPUT_DIR


# Stores file paths where output will be saved.
@dataclass(frozen=True)
class BatchPaths:
    jsonl: Path
    results_csv: Path
    errors_csv: Path


# Simple model used in the learning demo.
class SimpleProduct(BaseModel):
    """Small Pydantic demo matching notebook cell 1."""

    name: str
    price: float
    quantity: int = 1

    # Ensure price is a positive number.
    @field_validator("price")
    @classmethod
    def validate_price(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Price must be positive")
        return value

    # Ensure quantity is a positive number.
    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Quantity must be positive")
        return value


# Product model used for dataset rows (includes image field).
class ProductWithImage(ProductBase):
    """Dataset row schema with image payload field."""

    image: Any


# Runs the small Pydantic tutorial example.
def run_pydantic_basics_demo() -> None:
    print("=" * 50)
    print("PYDANTIC BASICS")
    print("=" * 50)

    print("\n1. Valid data:")
    try:
        product = SimpleProduct(name="Widget", price=10.99, quantity=5)
        print(f"  Valid: {product.name} - ${product.price}")
    except Exception as error:
        print(f"  Error: {error}")

    print("\n2. Invalid data (negative price):")
    try:
        SimpleProduct(name="Widget", price=-10.99)
    except Exception as error:
        print(f"  Validation error (expected): {error}")

    print("\nPydantic basics working")


# Builds a product payload dictionary from a dataframe row.
def build_product_row_payload(row: pd.Series) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "gender": row.get("gender"),
        "masterCategory": row.get("masterCategory"),
        "subCategory": row.get("subCategory"),
        "articleType": row.get("articleType"),
        "baseColour": row.get("baseColour"),
        "season": row.get("season"),
        "year": row.get("year"),
        "usage": row.get("usage"),
        "productDisplayName": row.get("productDisplayName"),
        "image": row.get("image"),
    }


# Validates one product payload.
def validate_product_row_payload(payload: Mapping[str, Any]) -> ProductWithImage:
    try:
        return ProductWithImage.model_validate(payload)
    except ValidationError as error:
        report_error(
            function_name="validate_product_row_payload",
            error=error,
            location="row_payload",
            suggestion="Check row fields and include a valid image field.",
        )
        raise


# Turns one dataframe row into a validated product model.
def product_from_row(row: pd.Series) -> ProductWithImage:
    payload = build_product_row_payload(row)
    return validate_product_row_payload(payload)


# Encodes raw bytes into base64 text.
def encode_bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


# Encodes a PIL image into base64 text.
def encode_pil_image_to_base64(image: Any, image_format: str = "JPEG") -> str:
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return encode_bytes_to_base64(buffer.getvalue())


# Removes line breaks from a base64 string.
def normalize_base64_string(value: str) -> str:
    return value.replace("\n", "").replace("\r", "")


# Quick check if a string looks like base64 image data.
def looks_like_base64(value: str) -> bool:
    preview = value[:200]
    return len(value) > 200 and all(ch.isalnum() or ch in "+/=\n\r" for ch in preview)


# Loads file bytes from disk.
def load_file_bytes(path: Path) -> bytes:
    try:
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"image path does not exist: {path}")
        return path.read_bytes()
    except FileNotFoundError as error:
        report_error(
            function_name="load_file_bytes",
            error=error,
            location=f"path={path}",
            suggestion="Verify image file path and ensure the file exists.",
        )
        raise
    except PermissionError as error:
        report_error(
            function_name="load_file_bytes",
            error=error,
            location=f"path={path}",
            suggestion="Check read permissions for the image file.",
        )
        raise
    except OSError as error:
        report_error(
            function_name="load_file_bytes",
            error=error,
            location=f"path={path}",
            suggestion="Check file system availability and image path validity.",
        )
        raise


# Converts either a file path or base64 string into base64 output.
def image_path_or_base64_to_base64(image_value: str | Path) -> str:
    try:
        text = str(image_value).strip()
        if not text:
            raise ValueError("image path/string is empty")

        if looks_like_base64(text):
            return normalize_base64_string(text)

        return encode_bytes_to_base64(load_file_bytes(Path(text)))
    except (ValueError, FileNotFoundError, PermissionError, OSError) as error:
        report_error(
            function_name="image_path_or_base64_to_base64",
            error=error,
            location=f"image_value={image_value}",
            suggestion="Pass a valid image file path or a valid base64 image string.",
        )
        raise


# Converts a numpy image array into base64 text.
def numpy_image_to_base64(image_array: Any) -> str:
    try:
        import numpy as np
    except ImportError as error:
        converted = ValueError("numpy is not installed")
        report_error(
            function_name="numpy_image_to_base64",
            error=converted,
            location="numpy import",
            suggestion="Install numpy to process ndarray images.",
        )
        raise converted from error

    if not isinstance(image_array, np.ndarray):
        error = ValueError("value is not a numpy array")
        report_error(
            function_name="numpy_image_to_base64",
            error=error,
            location=f"type={type(image_array)}",
            suggestion="Provide a numpy ndarray or use another supported image type.",
        )
        raise error

    try:
        from PIL import Image
    except ImportError as error:
        converted = ValueError("Got numpy image but Pillow is not installed")
        report_error(
            function_name="numpy_image_to_base64",
            error=converted,
            location="Pillow import",
            suggestion="Install Pillow to convert numpy images.",
        )
        raise converted from error

    if image_array.ndim == 2:
        mode = "L"
    elif image_array.ndim == 3 and image_array.shape[2] == 3:
        mode = "RGB"
    elif image_array.ndim == 3 and image_array.shape[2] == 4:
        mode = "RGBA"
    else:
        error = ValueError(f"Unsupported numpy image shape: {image_array.shape}")
        report_error(
            function_name="numpy_image_to_base64",
            error=error,
            location=f"shape={image_array.shape}",
            suggestion="Use image arrays with shape (H,W), (H,W,3), or (H,W,4).",
        )
        raise error

    image = Image.fromarray(image_array.astype("uint8"), mode=mode)
    return encode_pil_image_to_base64(image)


# Main image conversion entry point used by processing code.
def image_to_base64(image_value: Any) -> str:
    if image_value is None:
        error = ValueError("image is missing")
        report_error(
            function_name="image_to_base64",
            error=error,
            location="image_value=None",
            suggestion="Provide image bytes, path, PIL image, or numpy array.",
        )
        raise error

    try:
        from PIL import Image
    except ImportError:
        Image = None

    if Image is not None and isinstance(image_value, Image.Image):
        return encode_pil_image_to_base64(image_value)

    try:
        return numpy_image_to_base64(image_value)
    except ValueError:
        pass

    if isinstance(image_value, (bytes, bytearray)):
        return encode_bytes_to_base64(bytes(image_value))

    if isinstance(image_value, (str, Path)):
        return image_path_or_base64_to_base64(image_value)

    error = ValueError(f"Unsupported image type: {type(image_value)}")
    report_error(
        function_name="image_to_base64",
        error=error,
        location=f"type={type(image_value)}",
        suggestion="Use one of: PIL image, numpy array, bytes, file path, or base64 string.",
    )
    raise error


# Builds a data URL that the API accepts for images.
def build_image_data_url(image_base64: str, mime_type: str = "image/jpeg") -> str:
    if not image_base64:
        error = ValueError("Missing or invalid image_base64")
        report_error(
            function_name="build_image_data_url",
            error=error,
            location="image_base64 input",
            suggestion="Ensure image conversion succeeds before API call.",
        )
        raise error
    return f"data:{mime_type};base64,{image_base64}"


# Builds product-listing API input format (prompt + image).
def create_listing_api_input(prompt: str, image_data_url: str) -> List[Dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": image_data_url},
            ],
        }
    ]


# Product-listing helper that calls the generic OpenAI request function.
def fetch_listing_text(
    client: OpenAIWrapper,
    prompt: str,
    image_base64: str,
    model: str,
    temperature: float,
) -> str:
    image_data_url = build_image_data_url(image_base64)
    api_input = create_listing_api_input(prompt, image_data_url)
    return client.request_response_text(
        model=model,
        input_payload=api_input,
        temperature=temperature,
        context={"operation": "fetch_listing_text"},
    )


# Chooses how many products to process.
def select_products_frame(products_df: pd.DataFrame, n_products: int) -> pd.DataFrame:
    return products_df.head(n_products) if n_products else products_df


# Builds a fallback product name for logging on errors.
def build_fallback_name(row: pd.Series, index: Any) -> str:
    return row.get("productDisplayName") or f"product_{index}"


# Builds a standard validation error row.
def build_validation_error_entry(index: Any, row: pd.Series, fallback_name: str, error: ValidationError) -> Dict[str, Any]:
    return {
        "index": index,
        "id": row.get("id"),
        "productDisplayName": fallback_name,
        "error_type": "validation_error",
        "error": json.dumps(format_validation_error(error), ensure_ascii=False),
    }


# Builds a standard runtime error row.
def build_runtime_error_entry(index: Any, row: pd.Series, fallback_name: str, error: Exception) -> Dict[str, Any]:
    return {
        "index": index,
        "id": row.get("id"),
        "productDisplayName": fallback_name,
        "error_type": "runtime_error",
        "error": str(error),
    }


# Processes one product row end-to-end.
def process_single_product_row(
    index: Any,
    row: pd.Series,
    client: OpenAIWrapper,
    model: str,
    temperature: float,
) -> Dict[str, Any]:
    logger.debug("Processing single product row: index=%s", index)
    product = product_from_row(row)
    prompt = build_listing_prompt(product)
    image_b64 = image_to_base64(product.image)
    raw_text = fetch_listing_text(client, prompt, image_b64, model, temperature)
    listing = parse_listing_response(raw_text)
    return build_result_record(index=index, product=product, listing=listing)


# Processes all selected rows and separates success/error outputs.
def process_products_frame(
    products_df: pd.DataFrame,
    client: OpenAIWrapper,
    model: str,
    temperature: float,
    sleep_seconds: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    logger.info("Starting batch processing for %s products", len(products_df))

    for index, row in products_df.iterrows():
        fallback_name = build_fallback_name(row, index)
        try:
            result = process_single_product_row(index, row, client, model, temperature)
            results.append(result)
            logger.info("Processed product successfully: index=%s, name=%s", index, result["productDisplayName"])
            print(f"[OK] [{index}] Generated listing for: {result['productDisplayName']}")
        except ValidationError as error:
            errors.append(build_validation_error_entry(index, row, fallback_name, error))
            logger.warning("Validation failed: index=%s, name=%s", index, fallback_name)
            print(f"[WARN] [{index}] Validation failed for {fallback_name}")
        except Exception as error:
            errors.append(build_runtime_error_entry(index, row, fallback_name, error))
            logger.error("Runtime failure: index=%s, name=%s, error=%s", index, fallback_name, error)
            print(f"[WARN] [{index}] Failed for {fallback_name}: {error}")

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return results, errors


# Creates a timestamp string for output filenames.
def generate_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# Builds all output file paths for one batch run.
def build_batch_paths(output_dir: Path, run_id: str) -> BatchPaths:
    return BatchPaths(
        jsonl=output_dir / f"listings_{run_id}.jsonl",
        results_csv=output_dir / f"listings_{run_id}.csv",
        errors_csv=output_dir / f"errors_{run_id}.csv",
    )


# Ensures output folder exists.
def ensure_output_dir(output_dir: Path) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        report_error(
            function_name="ensure_output_dir",
            error=error,
            location=f"path={output_dir}",
            suggestion="Check folder permissions and available disk space.",
        )
        raise


# Writes rows to a JSONL file.
def write_jsonl_file(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    try:
        with path.open("w", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as error:
        report_error(
            function_name="write_jsonl_file",
            error=error,
            location=f"path={path}",
            suggestion="Check write permissions and verify output path exists.",
        )
        raise


# Saves dataframe to CSV only when it has rows.
def write_dataframe_csv_if_not_empty(df: pd.DataFrame, path: Path) -> None:
    if df.empty:
        return
    try:
        df.to_csv(path, index=False)
    except OSError as error:
        report_error(
            function_name="write_dataframe_csv_if_not_empty",
            error=error,
            location=f"path={path}",
            suggestion="Check write permissions and output directory configuration.",
        )
        raise


# Saves all batch outputs (jsonl + csv files).
def save_batch_outputs(
    results: List[Dict[str, Any]],
    errors: List[Dict[str, Any]],
    output_dir: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, BatchPaths]:
    ensure_output_dir(output_dir)
    run_id = generate_run_id()
    paths = build_batch_paths(output_dir, run_id)

    results_df = pd.DataFrame(results)
    errors_df = pd.DataFrame(errors)

    write_jsonl_file(paths.jsonl, results)
    write_dataframe_csv_if_not_empty(results_df, paths.results_csv)
    write_dataframe_csv_if_not_empty(errors_df, paths.errors_csv)
    logger.info(
        "Saved batch outputs: jsonl=%s, results_csv=%s, errors_csv=%s",
        paths.jsonl,
        paths.results_csv,
        paths.errors_csv,
    )

    return results_df, errors_df, paths


# Top-level batch workflow (process + save + report).
def generate_listings_batch(
    products_df: pd.DataFrame,
    client: OpenAIWrapper,
    config: BatchConfig,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    frame = select_products_frame(products_df, config.n_products)
    logger.info("Selected %s products for listing generation", len(frame))

    results, errors = process_products_frame(
        products_df=frame,
        client=client,
        model=config.model,
        temperature=config.temperature,
        sleep_seconds=config.sleep_seconds,
    )

    results_df, errors_df, paths = save_batch_outputs(results, errors, config.output_dir)

    print("\nBatch complete")
    print(f"Saved listings JSONL: {paths.jsonl}")
    if not results_df.empty:
        print(f"Saved listings CSV:   {paths.results_csv}")
    if not errors_df.empty:
        print(f"Saved errors CSV:     {paths.errors_csv}")

    return results_df, errors_df


# Loads product dataset into a pandas dataframe.
def load_products_dataframe(dataset_name: str = DEFAULT_DATASET, split: str = DEFAULT_SPLIT) -> pd.DataFrame:
    from datasets import load_dataset

    try:
        logger.info("Loading dataset: %s (%s)", dataset_name, split)
        dataset = load_dataset(dataset_name, split=split)
        dataframe = pd.DataFrame(dataset)
        logger.info("Dataset loaded successfully with %s rows", len(dataframe))
        return dataframe
    except Exception as error:
        report_error(
            function_name="load_products_dataframe",
            error=error,
            location=f"dataset={dataset_name}, split={split}",
            suggestion="Check dataset name, split value, and internet connectivity.",
        )
        raise


# Builds sample JSON payloads for validation demo.
def build_example_json_payloads() -> List[Tuple[str, Dict[str, Any]]]:
    valid_product = {
        "id": 101,
        "gender": "Men",
        "masterCategory": "Apparel",
        "subCategory": "Topwear",
        "articleType": "Shirts",
        "baseColour": "Navy Blue",
        "season": "Summer",
        "year": 2012.0,
        "usage": "Casual",
        "productDisplayName": "Turtle Check Men Navy Blue Shirt",
    }

    invalid_missing_required = {
        "gender": "Men",
        "masterCategory": "Apparel",
        "subCategory": "Topwear",
        "articleType": "Shirts",
        "baseColour": "Navy Blue",
        "season": "Summer",
        "usage": "Casual",
    }

    invalid_wrong_types = {
        "id": "ABC",
        "gender": "Men",
        "masterCategory": "Apparel",
        "subCategory": "Topwear",
        "articleType": "Shirts",
        "baseColour": "Navy Blue",
        "season": "Summer",
        "year": "Two Thousand Twelve",
        "usage": "Casual",
        "productDisplayName": "Turtle Check Men Navy Blue Shirt",
    }

    invalid_bad_values = {
        "id": 103,
        "gender": "   ",
        "masterCategory": "Apparel",
        "subCategory": "Topwear",
        "articleType": "Shirts",
        "baseColour": "Navy Blue",
        "season": "Summer",
        "year": 3025,
        "usage": "Casual",
        "productDisplayName": "",
    }

    invalid_extra_field = {
        "id": 104,
        "gender": "Men",
        "masterCategory": "Apparel",
        "subCategory": "Topwear",
        "articleType": "Shirts",
        "baseColour": "Navy Blue",
        "season": "Summer",
        "year": 2012.0,
        "usage": "Casual",
        "productDisplayName": "Turtle Check Men Navy Blue Shirt",
        "unexpectedField": "should not be here",
    }

    return [
        ("valid_product.json", valid_product),
        ("invalid_missing_required.json", invalid_missing_required),
        ("invalid_wrong_types.json", invalid_wrong_types),
        ("invalid_bad_values.json", invalid_bad_values),
        ("invalid_extra_field.json", invalid_extra_field),
    ]


# Writes one JSON file.
def write_json_payload(path: Path, payload: Mapping[str, Any]) -> None:
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Wrote JSON payload to %s", path)
    except OSError as error:
        report_error(
            function_name="write_json_payload",
            error=error,
            location=f"path={path}",
            suggestion="Check output directory permissions and disk space.",
        )
        raise


# Writes many JSON files to a folder.
def write_json_payloads(folder: Path, payloads: Iterable[Tuple[str, Mapping[str, Any]]]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads:
        write_json_payload(folder / name, payload)


# Creates example JSON files for demo/checkpoint use.
def generate_example_json_files(out_dir: Path = Path("data/example_json")) -> Path:
    payloads = build_example_json_payloads()
    write_json_payloads(out_dir, payloads)
    return out_dir


# Validates product JSON payload.
def validate_product_json_payload(payload: Mapping[str, Any]) -> ProductBase:
    return validate_product_payload(payload)


# Validates one JSON file and returns either product or error.
def validate_json_file(path: Path) -> Tuple[Optional[ProductBase], Optional[Dict[str, Any]]]:
    try:
        payload = load_json_file(path)
        product = validate_product_json_payload(payload)
        logger.info("Validated JSON file successfully: %s", path)
        return product, None
    except FileNotFoundError as error:
        logger.warning("JSON file not found: %s", path)
        return None, {"error": "file_not_found", "message": str(error)}
    except PermissionError as error:
        logger.warning("JSON file permission error: %s", path)
        return None, {"error": "file_permission_error", "message": str(error)}
    except ValidationError as error:
        logger.warning("JSON validation failed: %s", path)
        return None, format_validation_error(error)
    except json.JSONDecodeError as error:
        logger.warning("JSON parse failed: %s", path)
        return None, {"error": "invalid_json", "message": str(error)}
    except OSError as error:
        logger.warning("JSON file I/O error: %s", path)
        return None, {"error": "file_io_error", "message": str(error)}
    except Exception as error:
        report_error(
            function_name="validate_json_file",
            error=error,
            location=f"path={path}",
            suggestion="Check file readability and payload structure.",
        )
        return None, {"error": "runtime_error", "message": str(error)}


# Validates all JSON files in a folder.
def validate_folder(folder: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    valid_items: List[Dict[str, Any]] = []
    invalid_items: List[Dict[str, Any]] = []

    for path in sorted(folder.glob("*.json")):
        product, error = validate_json_file(path)
        if product is not None:
            valid_items.append(product.model_dump())
            print(f"[OK] VALID   {path.name}")
        else:
            invalid_items.append({"file": path.name, **(error or {})})
            print(f"[ERR] INVALID {path.name}")
            print(json.dumps(error, indent=2, ensure_ascii=False))

    return valid_items, invalid_items


# Runs the API batch workflow from CLI args.
def run_batch_command(args: argparse.Namespace) -> None:
    logger.info("Running batch command")
    client = build_openai_wrapper(
        explicit_env_path=args.env_path,
        max_retries=3,
        initial_backoff_seconds=1.0,
        backoff_multiplier=2.0,
    )

    print("Loading product dataset...")
    products_df = load_products_dataframe(dataset_name=args.dataset_name, split=args.split)
    print(f"Loaded {len(products_df)} products")
    print(f"Dataset columns: {products_df.columns.tolist()}")

    config = BatchConfig(
        model=args.model,
        temperature=args.temperature,
        n_products=args.n_products,
        sleep_seconds=args.sleep_seconds,
        output_dir=args.output_dir,
    )
    results_df, errors_df = generate_listings_batch(products_df=products_df, client=client, config=config)

    print("\nResults preview:")
    print(results_df.head(3))
    print("\nErrors preview:")
    print(errors_df.head(3))


# Runs the JSON validation demo from CLI args.
def run_json_validation_demo(args: argparse.Namespace) -> None:
    logger.info("Running JSON validation demo for folder: %s", args.json_dir)
    folder = generate_example_json_files(out_dir=args.json_dir)
    valid_items, invalid_items = validate_folder(folder)

    print("\nSummary")
    print(f"Valid: {len(valid_items)}")
    print(f"Invalid: {len(invalid_items)}")


# Runs all demos one after another.
def run_all_command(args: argparse.Namespace) -> None:
    logger.info("Running full workflow: basics + batch + json-demo")
    run_pydantic_basics_demo()
    run_batch_command(args)
    run_json_validation_demo(args)


# Adds shared batch options to parser.
def add_batch_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env-path", type=Path, default=None, help="Path to .env file")
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET)
    parser.add_argument("--split", default=DEFAULT_SPLIT)
    parser.add_argument("--n-products", type=int, default=DEFAULT_N_PRODUCTS)
    parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)


# Builds CLI parser and all subcommands.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refactored Python version of api_calling_JSON_refactored.ipynb",
    )
    subparsers = parser.add_subparsers(dest="command")

    basics_parser = subparsers.add_parser("basics", help="Run basic Pydantic validation demo")
    basics_parser.set_defaults(func=lambda _args: run_pydantic_basics_demo())

    batch_parser = subparsers.add_parser("batch", help="Run dataset -> OpenAI listing generation batch")
    add_batch_arguments(batch_parser)
    batch_parser.set_defaults(func=run_batch_command)

    json_parser = subparsers.add_parser("json-demo", help="Generate and validate sample JSON files")
    json_parser.add_argument("--json-dir", type=Path, default=Path("data/example_json"))
    json_parser.set_defaults(func=run_json_validation_demo)

    all_parser = subparsers.add_parser("all", help="Run all notebook-equivalent flows")
    add_batch_arguments(all_parser)
    all_parser.add_argument("--json-dir", type=Path, default=Path("data/example_json"))
    all_parser.set_defaults(func=run_all_command)

    return parser


# Default arguments used when user runs script with no command.
def build_default_all_args() -> argparse.Namespace:
    return argparse.Namespace(
        command="all",
        env_path=None,
        dataset_name=DEFAULT_DATASET,
        split=DEFAULT_SPLIT,
        n_products=DEFAULT_N_PRODUCTS,
        sleep_seconds=DEFAULT_SLEEP_SECONDS,
        model=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
        output_dir=DEFAULT_OUTPUT_DIR,
        json_dir=Path("data/example_json"),
    )


# Program entry point.
def main() -> None:
    setup_logging("outputs/logs/product_generator.log")
    logger.info("Application started")
    if len(sys.argv) == 1:
        run_all_command(build_default_all_args())
        logger.info("Application finished (default all command)")
        return

    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    logger.info("Application finished command=%s", getattr(args, "command", "unknown"))


if __name__ == "__main__":
    main()

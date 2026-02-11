from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError, field_validator

from refactor_helpers import (
    ProductBase,
    build_listing_prompt,
    build_result_record,
    format_validation_error,
    load_json_file,
    parse_listing_response,
)


DEFAULT_DATASET = "ashraq/fashion-product-images-small"
DEFAULT_SPLIT = "train[:100]"
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_N_PRODUCTS = 10
DEFAULT_SLEEP_SECONDS = 0.5
DEFAULT_OUTPUT_DIR = Path("generated_listings")


class SimpleProduct(BaseModel):
    """Small Pydantic demo matching notebook cell 1."""

    name: str
    price: float
    quantity: int = 1

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Price must be positive")
        return value

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Quantity must be positive")
        return value


class ProductWithImage(ProductBase):
    """Dataset row schema with image payload field."""

    image: Any


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


def resolve_env_path(explicit_env_path: Optional[Path] = None) -> Optional[Path]:
    if explicit_env_path is not None and explicit_env_path.exists():
        return explicit_env_path

    cwd = Path.cwd()
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir / ".env",
        cwd / ".env",
        cwd.parent.parent / ".env",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def create_openai_client(env_path: Optional[Path] = None) -> OpenAI:
    resolved = resolve_env_path(env_path)
    if resolved is not None:
        load_dotenv(dotenv_path=resolved, override=True)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to environment or .env file.")
    return OpenAI(api_key=api_key)


def product_from_row(row: pd.Series) -> ProductWithImage:
    payload = {
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
    return ProductWithImage.model_validate(payload)


def image_to_base64(image_value: Any) -> str:
    if image_value is None:
        raise ValueError("image is missing")

    try:
        from PIL import Image
    except ImportError:
        Image = None

    if Image is not None and isinstance(image_value, Image.Image):
        buffer = BytesIO()
        image_value.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    try:
        import numpy as np
    except ImportError:
        np = None

    if np is not None and isinstance(image_value, np.ndarray):
        if Image is None:
            raise ValueError("Got numpy image but Pillow is not installed")

        array = image_value
        if array.ndim == 2:
            mode = "L"
        elif array.ndim == 3 and array.shape[2] == 3:
            mode = "RGB"
        elif array.ndim == 3 and array.shape[2] == 4:
            mode = "RGBA"
        else:
            raise ValueError(f"Unsupported numpy image shape: {array.shape}")

        image = Image.fromarray(array.astype("uint8"), mode=mode)
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    if isinstance(image_value, (bytes, bytearray)):
        return base64.b64encode(image_value).decode("utf-8")

    if isinstance(image_value, (str, Path)):
        text = str(image_value).strip()
        if not text:
            raise ValueError("image path/string is empty")

        if len(text) > 200 and all(ch.isalnum() or ch in "+/=\n\r" for ch in text[:200]):
            return text.replace("\n", "").replace("\r", "")

        path = Path(text)
        if not path.exists() or not path.is_file():
            raise ValueError(f"image path does not exist: {path}")
        return base64.b64encode(path.read_bytes()).decode("utf-8")

    raise ValueError(f"Unsupported image type: {type(image_value)}")


def call_openai_for_listing(
    client: OpenAI,
    prompt: str,
    image_base64: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
) -> Dict[str, Any]:
    if not image_base64:
        raise ValueError("Missing or invalid image_base64")

    data_url = f"data:image/jpeg;base64,{image_base64}"

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ],
            }
        ],
        temperature=temperature,
    )

    raw_text = response.output_text
    if not raw_text:
        raise RuntimeError("Empty response.output_text")

    return parse_listing_response(raw_text)


def save_batch_outputs(
    results: List[Dict[str, Any]],
    errors: List[Dict[str, Any]],
    output_dir: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_df = pd.DataFrame(results)
    errors_df = pd.DataFrame(errors)

    results_path_jsonl = output_dir / f"listings_{run_id}.jsonl"
    results_path_csv = output_dir / f"listings_{run_id}.csv"
    errors_path_csv = output_dir / f"errors_{run_id}.csv"

    with results_path_jsonl.open("w", encoding="utf-8") as file:
        for row in results:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    if not results_df.empty:
        results_df.to_csv(results_path_csv, index=False)

    if not errors_df.empty:
        errors_df.to_csv(errors_path_csv, index=False)

    return results_df, errors_df, results_path_jsonl, results_path_csv, errors_path_csv


def generate_listings_batch(
    products_df: pd.DataFrame,
    client: OpenAI,
    n_products: int = DEFAULT_N_PRODUCTS,
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    frame = products_df.head(n_products) if n_products else products_df

    for index, row in frame.iterrows():
        fallback_name = row.get("productDisplayName") or f"product_{index}"

        try:
            product = product_from_row(row)
            image_b64 = image_to_base64(product.image)
            prompt = build_listing_prompt(product)
            listing = call_openai_for_listing(
                client=client,
                prompt=prompt,
                image_base64=image_b64,
                model=model,
                temperature=temperature,
            )

            results.append(build_result_record(index=index, product=product, listing=listing))
            print(f"[OK] [{index}] Generated listing for: {product.productDisplayName}")

        except ValidationError as error:
            errors.append(
                {
                    "index": index,
                    "id": row.get("id"),
                    "productDisplayName": fallback_name,
                    "error_type": "validation_error",
                    "error": json.dumps(format_validation_error(error), ensure_ascii=False),
                }
            )
            print(f"[WARN] [{index}] Validation failed for {fallback_name}")

        except Exception as error:
            errors.append(
                {
                    "index": index,
                    "id": row.get("id"),
                    "productDisplayName": fallback_name,
                    "error_type": "runtime_error",
                    "error": str(error),
                }
            )
            print(f"[WARN] [{index}] Failed for {fallback_name}: {error}")

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    results_df, errors_df, jsonl_path, csv_path, errors_path = save_batch_outputs(
        results=results,
        errors=errors,
        output_dir=output_dir,
    )

    print("\nBatch complete")
    print(f"Saved listings JSONL: {jsonl_path}")
    if not results_df.empty:
        print(f"Saved listings CSV:   {csv_path}")
    if not errors_df.empty:
        print(f"Saved errors CSV:     {errors_path}")

    return results_df, errors_df


def load_products_dataframe(
    dataset_name: str = DEFAULT_DATASET,
    split: str = DEFAULT_SPLIT,
) -> pd.DataFrame:
    from datasets import load_dataset

    dataset = load_dataset(dataset_name, split=split)
    return pd.DataFrame(dataset)


def generate_example_json_files(out_dir: Path = Path("example_json")) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

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

    files = [
        ("valid_product.json", valid_product),
        ("invalid_missing_required.json", invalid_missing_required),
        ("invalid_wrong_types.json", invalid_wrong_types),
        ("invalid_bad_values.json", invalid_bad_values),
        ("invalid_extra_field.json", invalid_extra_field),
    ]

    for name, payload in files:
        (out_dir / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return out_dir


def validate_json_file(path: Path) -> Tuple[Optional[ProductBase], Optional[Dict[str, Any]]]:
    try:
        payload = load_json_file(path)
        product = ProductBase.model_validate(payload)
        return product, None
    except ValidationError as error:
        return None, format_validation_error(error)
    except json.JSONDecodeError as error:
        return None, {"error": "invalid_json", "message": str(error)}
    except Exception as error:
        return None, {"error": "runtime_error", "message": str(error)}


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


def run_batch_command(args: argparse.Namespace) -> None:
    client = create_openai_client(env_path=args.env_path)

    print("Loading product dataset...")
    products_df = load_products_dataframe(dataset_name=args.dataset_name, split=args.split)
    print(f"Loaded {len(products_df)} products")
    print(f"Dataset columns: {products_df.columns.tolist()}")

    results_df, errors_df = generate_listings_batch(
        products_df=products_df,
        client=client,
        n_products=args.n_products,
        sleep_seconds=args.sleep_seconds,
        model=args.model,
        temperature=args.temperature,
        output_dir=args.output_dir,
    )

    print("\nResults preview:")
    print(results_df.head(3))
    print("\nErrors preview:")
    print(errors_df.head(3))


def run_json_validation_demo(args: argparse.Namespace) -> None:
    folder = generate_example_json_files(out_dir=args.json_dir)
    valid_items, invalid_items = validate_folder(folder)

    print("\nSummary")
    print(f"Valid: {len(valid_items)}")
    print(f"Invalid: {len(invalid_items)}")


def run_all_command(args: argparse.Namespace) -> None:
    run_pydantic_basics_demo()
    run_batch_command(args)
    run_json_validation_demo(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refactored Python version of api_calling_JSON_refactored.ipynb",
    )
    subparsers = parser.add_subparsers(dest="command")

    basics_parser = subparsers.add_parser("basics", help="Run basic Pydantic validation demo")
    basics_parser.set_defaults(func=lambda _args: run_pydantic_basics_demo())

    batch_parser = subparsers.add_parser("batch", help="Run dataset -> OpenAI listing generation batch")
    batch_parser.add_argument("--env-path", type=Path, default=None, help="Path to .env file")
    batch_parser.add_argument("--dataset-name", default=DEFAULT_DATASET)
    batch_parser.add_argument("--split", default=DEFAULT_SPLIT)
    batch_parser.add_argument("--n-products", type=int, default=DEFAULT_N_PRODUCTS)
    batch_parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    batch_parser.add_argument("--model", default=DEFAULT_MODEL)
    batch_parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    batch_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    batch_parser.set_defaults(func=run_batch_command)

    json_parser = subparsers.add_parser("json-demo", help="Generate and validate sample JSON files")
    json_parser.add_argument("--json-dir", type=Path, default=Path("example_json"))
    json_parser.set_defaults(func=run_json_validation_demo)

    all_parser = subparsers.add_parser("all", help="Run all notebook-equivalent flows")
    all_parser.add_argument("--env-path", type=Path, default=None, help="Path to .env file")
    all_parser.add_argument("--dataset-name", default=DEFAULT_DATASET)
    all_parser.add_argument("--split", default=DEFAULT_SPLIT)
    all_parser.add_argument("--n-products", type=int, default=DEFAULT_N_PRODUCTS)
    all_parser.add_argument("--sleep-seconds", type=float, default=DEFAULT_SLEEP_SECONDS)
    all_parser.add_argument("--model", default=DEFAULT_MODEL)
    all_parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    all_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    all_parser.add_argument("--json-dir", type=Path, default=Path("example_json"))
    all_parser.set_defaults(func=run_all_command)

    return parser


def main() -> None:
    if len(sys.argv) == 1:
        default_args = argparse.Namespace(
            command="all",
            env_path=None,
            dataset_name=DEFAULT_DATASET,
            split=DEFAULT_SPLIT,
            n_products=DEFAULT_N_PRODUCTS,
            sleep_seconds=DEFAULT_SLEEP_SECONDS,
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMPERATURE,
            output_dir=DEFAULT_OUTPUT_DIR,
            json_dir=Path("example_json"),
        )
        run_all_command(default_args)
        return

    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

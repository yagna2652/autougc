"""
Product loader for the UGC pipeline.

Loads product configuration and images from the assets/products folder.
This allows running the pipeline with just a TikTok URL - the product
info is loaded automatically from the configured product folder.
"""

import base64
import io
import json
import logging
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

# Max size in bytes before base64 encoding (3.5MB to stay under 5MB limit after encoding)
MAX_IMAGE_SIZE_BYTES = 3.5 * 1024 * 1024


def resize_image_if_needed(image_data: bytes, filename: str = "") -> tuple[bytes, str]:
    """
    Resize an image if it exceeds the size limit for Claude API.

    Args:
        image_data: Raw image bytes
        filename: Original filename (for logging)

    Returns:
        Tuple of (image_bytes, mime_type) - possibly resized and converted to JPEG
    """
    original_size = len(image_data)

    # If under limit, return as-is with original format detection
    if original_size <= MAX_IMAGE_SIZE_BYTES:
        # Detect mime type from image data
        img = Image.open(io.BytesIO(image_data))
        format_to_mime = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }
        mime_type = format_to_mime.get(img.format, "image/jpeg")
        return image_data, mime_type

    # Need to resize
    logger.info(
        f"Image {filename} is {original_size / 1024 / 1024:.1f}MB, resizing to fit under limit"
    )

    img = Image.open(io.BytesIO(image_data))

    # Convert to RGB if necessary (for JPEG output)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Calculate scale factor based on file size ratio
    # We want final size < MAX_IMAGE_SIZE_BYTES
    # Use square root since area scales quadratically with linear dimensions
    target_ratio = MAX_IMAGE_SIZE_BYTES / original_size
    scale_factor = target_ratio ** 0.5

    # Apply scale factor with some margin
    scale_factor *= 0.9  # 10% safety margin

    new_width = int(img.width * scale_factor)
    new_height = int(img.height * scale_factor)

    logger.debug(
        f"Resizing {filename} from {img.width}x{img.height} to {new_width}x{new_height}"
    )

    # Resize with high-quality resampling
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Save as JPEG with good quality
    output = io.BytesIO()
    img_resized.save(output, format="JPEG", quality=85, optimize=True)
    resized_data = output.getvalue()

    new_size = len(resized_data)
    logger.info(
        f"Resized {filename}: {original_size / 1024 / 1024:.1f}MB -> {new_size / 1024 / 1024:.1f}MB "
        f"({new_width}x{new_height})"
    )

    return resized_data, "image/jpeg"

# Path to the products folder
PRODUCTS_DIR = Path(__file__).parent.parent.parent / "assets" / "products"
DEFAULT_PRODUCT = "keychain"


def load_product(product_name: str = DEFAULT_PRODUCT) -> dict[str, Any]:
    """
    Load a product configuration and images.

    Args:
        product_name: Name of the product folder (default: keychain)

    Returns:
        Dict containing:
            - name: Product name
            - description: Product description
            - category: Product category
            - images: List of base64-encoded images

    Raises:
        FileNotFoundError: If product folder or config doesn't exist
    """
    product_dir = PRODUCTS_DIR / product_name

    if not product_dir.exists():
        raise FileNotFoundError(f"Product folder not found: {product_dir}")

    # Load config
    config_path = product_dir / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Product config not found: {config_path}")

    with open(config_path) as f:
        config = json.load(f)

    # Load images
    images = []
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    for file_path in sorted(product_dir.iterdir()):
        if file_path.suffix.lower() in image_extensions:
            try:
                with open(file_path, "rb") as f:
                    image_data = f.read()

                # Resize if needed to fit under Claude API limit
                image_data, mime_type = resize_image_if_needed(
                    image_data, file_path.name
                )

                encoded = base64.b64encode(image_data).decode("utf-8")
                images.append(f"data:{mime_type};base64,{encoded}")
                logger.debug(f"Loaded product image: {file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to load image {file_path}: {e}")

    logger.info(
        f"Loaded product '{config.get('name')}' with {len(images)} images"
    )

    return {
        "name": config.get("name", product_name),
        "description": config.get("description", ""),
        "category": config.get("category", ""),
        "mechanics": config.get("mechanics", ""),
        "images": images,
    }


def load_default_product() -> tuple[str, list[str], str]:
    """
    Load the default product (keychain).

    Returns:
        Tuple of (description, images_base64, category)
    """
    try:
        product = load_product(DEFAULT_PRODUCT)
        return (
            product["description"],
            product["images"],
            product["category"],
        )
    except FileNotFoundError as e:
        logger.warning(f"Default product not found: {e}")
        return "", [], "mechanical_keyboard_keychain"


def get_available_products() -> list[str]:
    """
    Get list of available product names.

    Returns:
        List of product folder names that have a config.json
    """
    if not PRODUCTS_DIR.exists():
        return []

    products = []
    for product_dir in PRODUCTS_DIR.iterdir():
        if product_dir.is_dir() and (product_dir / "config.json").exists():
            products.append(product_dir.name)

    return sorted(products)

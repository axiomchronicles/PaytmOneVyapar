from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import InvalidRequestError

MAX_RECEIPT_IMAGE_BYTES = 10 * 1024 * 1024
MAX_RECEIPT_IMAGE_PIXELS = 40_000_000
MAX_RECEIPT_IMAGE_DIMENSION = 4096
MIN_RECEIPT_IMAGE_DIMENSION = 64
ALLOWED_RECEIPT_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def detect_image_type(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_receipt_image(state: dict) -> dict:
    content = state.get("image_bytes") or b""
    if not content:
        raise InvalidRequestError("The uploaded receipt image is empty")
    if len(content) > MAX_RECEIPT_IMAGE_BYTES:
        raise InvalidRequestError(
            "Receipt images must be 10 MB or smaller",
            details={"maximum_bytes": MAX_RECEIPT_IMAGE_BYTES},
        )
    detected = detect_image_type(content)
    if detected not in ALLOWED_RECEIPT_IMAGE_TYPES:
        raise InvalidRequestError("Upload a JPEG, PNG, or WebP receipt image")
    declared = (state.get("declared_content_type") or "").split(";", 1)[0].lower()
    if declared and declared != "application/octet-stream" and declared != detected:
        raise InvalidRequestError(
            "The uploaded file content does not match its declared image type",
            details={"declared_content_type": declared, "detected_content_type": detected},
        )
    return {"detected_content_type": detected}


def prepare_receipt_image(state: dict) -> dict:
    content = state["image_bytes"]
    try:
        with Image.open(BytesIO(content)) as source:
            width, height = source.size
            if width < MIN_RECEIPT_IMAGE_DIMENSION or height < MIN_RECEIPT_IMAGE_DIMENSION:
                raise InvalidRequestError("The receipt image is too small to read")
            if width * height > MAX_RECEIPT_IMAGE_PIXELS:
                raise InvalidRequestError("The receipt image resolution is too large")
            source.load()

            orientation = source.getexif().get(274, 1)
            needs_resize = max(width, height) > MAX_RECEIPT_IMAGE_DIMENSION
            grayscale = ImageOps.grayscale(source)
            low, high = grayscale.getextrema()
            needs_contrast = high - low < 55
            needs_mode_conversion = source.mode not in {"RGB", "RGBA", "L"}
            should_preprocess = (
                orientation != 1 or needs_resize or needs_contrast or needs_mode_conversion
            )

            if not should_preprocess:
                return {
                    "prepared_image_bytes": content,
                    "prepared_content_type": state["detected_content_type"],
                    "image_preprocessed": False,
                    "image_width": width,
                    "image_height": height,
                }

            image = ImageOps.exif_transpose(source)
            if needs_resize:
                image.thumbnail(
                    (MAX_RECEIPT_IMAGE_DIMENSION, MAX_RECEIPT_IMAGE_DIMENSION),
                    Image.Resampling.LANCZOS,
                )
            if needs_contrast:
                image = ImageOps.autocontrast(ImageOps.grayscale(image)).convert("RGB")
            elif image.mode == "RGBA":
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")
            output = BytesIO()
            image.save(output, format="JPEG", quality=90, optimize=True)
            prepared = output.getvalue()
            return {
                "prepared_image_bytes": prepared,
                "prepared_content_type": "image/jpeg",
                "image_preprocessed": True,
                "image_width": image.width,
                "image_height": image.height,
            }
    except InvalidRequestError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
        raise InvalidRequestError("The uploaded receipt image could not be decoded") from exc

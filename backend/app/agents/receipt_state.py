from typing import Any, TypedDict

from app.agents.receipt_schemas import ReceiptReviewResponse, VisionReceiptExtraction


class ReceiptExtractionState(TypedDict, total=False):
    filename: str
    declared_content_type: str
    image_bytes: bytes
    detected_content_type: str
    prepared_image_bytes: bytes
    prepared_content_type: str
    image_preprocessed: bool
    image_width: int
    image_height: int
    vision_result: Any
    parsed_extraction: VisionReceiptExtraction
    normalized_extraction: VisionReceiptExtraction
    review_items: list[dict[str, Any]]
    review_payload: ReceiptReviewResponse

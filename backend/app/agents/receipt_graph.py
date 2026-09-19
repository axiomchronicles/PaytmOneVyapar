from langgraph.graph import END, START, StateGraph

from app.agents.receipt_nodes import (
    detect_missing_fields,
    normalize_products,
    parse_structured_output,
    prepare_document,
    prepare_review_payload,
    validate_extracted_data,
    validate_image,
    vision_extraction,
)
from app.agents.receipt_schemas import ReceiptReviewResponse
from app.agents.receipt_state import ReceiptExtractionState
from app.domain.contracts import LLMProvider


class ReceiptExtractionWorkflow:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self.graph = build_receipt_extraction_graph(llm_provider)

    async def extract(
        self, *, filename: str, content_type: str, content: bytes
    ) -> ReceiptReviewResponse:
        result = await self.graph.ainvoke(
            {
                "filename": filename,
                "declared_content_type": content_type,
                "image_bytes": content,
            }
        )
        return result["review_payload"]


def build_receipt_extraction_graph(llm_provider: LLMProvider):
    async def vision_node(state: ReceiptExtractionState):
        return await vision_extraction(state, llm_provider=llm_provider)

    graph = StateGraph(ReceiptExtractionState)
    graph.add_node("validate_image", validate_image)
    graph.add_node("prepare_document", prepare_document)
    graph.add_node("vision_extraction", vision_node)
    graph.add_node("parse_structured_output", parse_structured_output)
    graph.add_node("validate_extracted_data", validate_extracted_data)
    graph.add_node("normalize_products", normalize_products)
    graph.add_node("detect_missing_fields", detect_missing_fields)
    graph.add_node("prepare_review_payload", prepare_review_payload)

    graph.add_edge(START, "validate_image")
    graph.add_edge("validate_image", "prepare_document")
    graph.add_edge("prepare_document", "vision_extraction")
    graph.add_edge("vision_extraction", "parse_structured_output")
    graph.add_edge("parse_structured_output", "validate_extracted_data")
    graph.add_edge("validate_extracted_data", "normalize_products")
    graph.add_edge("normalize_products", "detect_missing_fields")
    graph.add_edge("detect_missing_fields", "prepare_review_payload")
    graph.add_edge("prepare_review_payload", END)
    return graph.compile()

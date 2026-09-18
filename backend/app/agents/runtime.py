import time
from typing import Any
from uuid import UUID

from langgraph.types import Command
from opentelemetry import trace

from app.agents.services import ApprovalAuthority, workflow_request_context
from app.core.errors import ConflictError
from app.domain.enums import ApprovalStatus
from app.infrastructure.observability.metrics import agent_duration

tracer = trace.get_tracer("vyapaar.agents")


class WorkflowRuntime:
    def __init__(self, graph, approval_authority: ApprovalAuthority) -> None:
        self.graph = graph
        self.approval_authority = approval_authority

    @staticmethod
    def thread_id(merchant_id: str, request_id: str) -> str:
        return f"purchase:{merchant_id}:{request_id}"

    async def start(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        config = {
            "configurable": {
                "thread_id": self.thread_id(
                    initial_state["merchant_id"], initial_state["request_id"]
                )
            }
        }
        context_token = workflow_request_context.set(initial_state["request_id"])
        started = time.perf_counter()
        try:
            with tracer.start_as_current_span("purchase_workflow.start") as span:
                span.set_attribute("workflow.request_id", initial_state["request_id"])
                return await self.graph.ainvoke(initial_state, config=config)
        finally:
            agent_duration.record((time.perf_counter() - started) * 1000)
            workflow_request_context.reset(context_token)

    async def resume(
        self,
        *,
        merchant_id: UUID,
        request_id: str,
        action: ApprovalStatus,
        approval_token: str,
        quantity: float | None = None,
        max_unit_price: float | None = None,
        user_id: UUID | None = None,
        expected_approval_id: UUID | None = None,
        expected_proposal_id: UUID | None = None,
    ) -> dict[str, Any]:
        config = {"configurable": {"thread_id": self.thread_id(str(merchant_id), request_id)}}
        snapshot = await self.graph.aget_state(config)
        if not snapshot.next or snapshot.next[0] != "human_approval":
            raise ValueError("Workflow is not waiting for approval")
        approval_id = UUID(snapshot.values["approval_id"])
        if expected_approval_id is not None and approval_id != expected_approval_id:
            raise ConflictError("Approval does not belong to the active workflow revision")
        if expected_proposal_id is not None:
            proposal_id = UUID(snapshot.values["proposal"]["proposal_id"])
            if proposal_id != expected_proposal_id:
                raise ConflictError("Proposal does not match the active voice context")
        await self.approval_authority.decide(
            approval_id,
            merchant_id=merchant_id,
            action=action,
            token=approval_token,
            user_id=user_id,
        )
        decision: dict[str, Any] = {
            "action": {
                ApprovalStatus.APPROVED: "APPROVE",
                ApprovalStatus.MODIFIED: "MODIFY",
                ApprovalStatus.REJECTED: "REJECT",
            }[action]
        }
        if action == ApprovalStatus.MODIFIED:
            if quantity is None and max_unit_price is None:
                raise ValueError("A quantity or price limit is required for modification")
            if quantity is not None:
                if quantity <= 0:
                    raise ValueError("A positive quantity is required for modification")
                decision["quantity"] = quantity
            if max_unit_price is not None:
                if max_unit_price <= 0:
                    raise ValueError("A positive maximum price is required for modification")
                decision["max_unit_price"] = max_unit_price
        context_token = workflow_request_context.set(request_id)
        started = time.perf_counter()
        try:
            with tracer.start_as_current_span("purchase_workflow.resume") as span:
                span.set_attribute("workflow.request_id", request_id)
                span.set_attribute("workflow.approval_action", action.value)
                return await self.graph.ainvoke(Command(resume=decision), config=config)
        finally:
            agent_duration.record((time.perf_counter() - started) * 1000)
            workflow_request_context.reset(context_token)

    async def state(self, merchant_id: UUID, request_id: str) -> dict[str, Any]:
        config = {"configurable": {"thread_id": self.thread_id(str(merchant_id), request_id)}}
        return dict((await self.graph.aget_state(config)).values)

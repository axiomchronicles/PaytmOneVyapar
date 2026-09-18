from langgraph.graph import END, START, StateGraph

from app.agents.nodes.approval_gate import approval_gate
from app.agents.nodes.create_proposal import create_proposal
from app.agents.nodes.detect_need import detect_need
from app.agents.nodes.execute_order import execute_order
from app.agents.nodes.find_supplier import find_supplier
from app.agents.nodes.forecast_demand import forecast_demand
from app.agents.nodes.negotiate import negotiate
from app.agents.nodes.risk_check import risk_check
from app.agents.nodes.verify_result import verify_result
from app.agents.services import WorkflowServices
from app.agents.state import PurchaseWorkflowState


def build_purchase_graph(services: WorkflowServices, *, checkpointer):
    async def find_supplier_node(state):
        return await find_supplier(state, services)

    async def negotiate_node(state):
        return await negotiate(state, services)

    async def create_proposal_node(state):
        return await create_proposal(state, services)

    async def execute_order_node(state):
        return await execute_order(state, services)

    graph = StateGraph(PurchaseWorkflowState)
    graph.add_node("detect_need", detect_need)
    graph.add_node("forecast_demand", lambda state: forecast_demand(state, services))
    graph.add_node("find_supplier", find_supplier_node)
    graph.add_node("negotiate", negotiate_node)
    graph.add_node("risk_check", lambda state: risk_check(state, services))
    graph.add_node("create_proposal", create_proposal_node)
    graph.add_node("human_approval", approval_gate)
    graph.add_node("execute_order", execute_order_node)
    graph.add_node("verify_result", verify_result)

    graph.add_edge(START, "detect_need")
    graph.add_conditional_edges(
        "detect_need",
        lambda state: "stop" if state.get("failure_reason") else "continue",
        {"stop": END, "continue": "forecast_demand"},
    )
    graph.add_edge("forecast_demand", "find_supplier")
    graph.add_conditional_edges(
        "find_supplier",
        lambda state: "stop" if state.get("failure_reason") else "continue",
        {"stop": END, "continue": "negotiate"},
    )
    graph.add_conditional_edges(
        "negotiate",
        lambda state: "stop" if state.get("failure_reason") else "continue",
        {"stop": END, "continue": "risk_check"},
    )
    graph.add_conditional_edges(
        "risk_check",
        lambda state: "stop" if state.get("failure_reason") else "continue",
        {"stop": END, "continue": "create_proposal"},
    )
    graph.add_edge("create_proposal", "human_approval")
    graph.add_conditional_edges(
        "human_approval",
        lambda state: state["approval_status"],
        {"APPROVED": "execute_order", "MODIFIED": "forecast_demand", "REJECTED": END},
    )
    graph.add_edge("execute_order", "verify_result")
    graph.add_conditional_edges(
        "verify_result",
        lambda state: "recover" if state.get("execution_status") == "FAILED" else "done",
        {"recover": "find_supplier", "done": END},
    )
    return graph.compile(checkpointer=checkpointer)

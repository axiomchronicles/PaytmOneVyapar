from datetime import UTC, datetime

from app.agents.services import WorkflowServices
from app.agents.state import PurchaseWorkflowState
from app.agents.tools.forecasting_tools import forecast_demand as run_forecast
from app.agents.tools.inventory_tools import calculate_shortage


def forecast_demand(state: PurchaseWorkflowState, services: WorkflowServices) -> dict:
    delivery_days = max(
        1,
        (datetime.fromisoformat(state["delivery_requirement"]) - datetime.now(UTC)).days,
    )
    forecast = run_forecast(services.forecast_model, state["sales_history"], delivery_days)
    shortage = calculate_shortage(
        float(state["inventory_snapshot"]["quantity_on_hand"]),
        float(forecast["predicted_demand"]),
        float(state["inventory_snapshot"].get("safety_stock", 0)),
    )
    requested = state.get("required_quantity", 0)
    quantity = requested if state.get("merchant_quantity_override") else max(shortage, requested)
    return {"demand_forecast": forecast, "required_quantity": quantity}

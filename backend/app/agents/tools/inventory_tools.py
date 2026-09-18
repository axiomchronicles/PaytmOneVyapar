import math


def calculate_shortage(
    quantity_on_hand: float, predicted_demand: float, safety_stock: float = 0
) -> float:
    return max(0.0, math.ceil(predicted_demand + safety_stock - quantity_on_hand))

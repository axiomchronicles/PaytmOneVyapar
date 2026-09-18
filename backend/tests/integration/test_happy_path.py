from scripts.run_happy_path import run_demo


async def test_full_low_inventory_to_confirmed_order(capsys) -> None:
    result = await run_demo()
    assert result["execution_status"] == "VERIFIED"
    assert result["approval_status"] == "APPROVED"
    assert result["order_hash"]
    assert result["execution_result"]["status"] == "CONFIRMED"

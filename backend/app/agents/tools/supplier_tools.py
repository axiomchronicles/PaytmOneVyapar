from app.core.errors import ProviderError, SupplierUnavailableError
from app.domain.contracts import SupplierAdapter
from app.domain.entities import PurchaseRequest, SupplierQuote


async def collect_quotes(
    adapters: list[SupplierAdapter], request: PurchaseRequest
) -> list[SupplierQuote]:
    quotes: list[SupplierQuote] = []
    for adapter in adapters:
        try:
            quotes.extend(await adapter.discover(request))
        except (ProviderError, SupplierUnavailableError):
            continue
    return sorted(quotes, key=lambda quote: (quote.unit_price, quote.delivery_at))

from datetime import timedelta
from decimal import Decimal
from uuid import uuid5

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import utc_now
from app.domain.entities import OrderResult, PurchaseProposal, PurchaseRequest, SupplierQuote
from app.domain.enums import OrderStatus
from app.infrastructure.db.models import Product, Supplier, SupplierProduct


class CatalogSupplierAdapter:
    """Quotes from supplier-managed catalog stock and waits for supplier acceptance.

    This adapter deliberately owns no single supplier id.  It is the bridge between
    supplier accounts maintaining ``SupplierProduct`` rows and the buyer workflow,
    while the final stock reservation remains a supplier-side human decision.
    """

    handles_all_suppliers = True

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._quotes: dict[str, SupplierQuote] = {}

    async def discover(self, request: PurchaseRequest) -> list[SupplierQuote]:
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(SupplierProduct, Supplier, Product)
                    .join(Supplier, Supplier.id == SupplierProduct.supplier_id)
                    .join(Product, Product.id == SupplierProduct.product_id)
                    .where(
                        Supplier.is_active.is_(True),
                        SupplierProduct.available_quantity >= request.quantity,
                        func.upper(Product.sku) == request.sku.strip().upper(),
                    )
                    .order_by(SupplierProduct.unit_price, Supplier.trust_score.desc())
                )
            ).tuples()

        now = utc_now()
        quotes: list[SupplierQuote] = []
        for item, supplier, _ in rows:
            quote_id = f"catalog:{supplier.id}:{request.request_id}:{request.sku}"
            quote = SupplierQuote(
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                sku=request.sku,
                available_quantity=item.available_quantity,
                unit_price=item.unit_price,
                delivery_at=now + timedelta(days=item.lead_time_days),
                expires_at=now + timedelta(minutes=10),
                quote_id=quote_id,
            )
            self._quotes[quote_id] = quote
            quotes.append(quote)
        return quotes

    async def quote(self, request: PurchaseRequest) -> SupplierQuote:
        quotes = await self.discover(request)
        if not quotes:
            raise LookupError("No supplier catalog stock is available for this SKU")
        return quotes[0]

    async def counter_offer(
        self,
        quote: SupplierQuote,
        *,
        unit_price: float,
        quantity: float,
        idempotency_key: str,
    ) -> SupplierQuote | None:
        # Catalog suppliers accept a bounded, deterministic counter offer; the
        # supplier still gives the final fulfilment approval before settlement.
        if Decimal(str(quantity)) > quote.available_quantity:
            return None
        offered = Decimal(str(unit_price)).quantize(Decimal("0.01"))
        floor = (quote.unit_price * Decimal("0.90")).quantize(Decimal("0.01"))
        if offered < floor:
            return None
        revised = quote.model_copy(update={"unit_price": offered})
        self._quotes[revised.quote_id] = revised
        return revised

    async def place_order(self, proposal: PurchaseProposal, *, idempotency_key: str) -> OrderResult:
        quote = self._quotes.get(proposal.quote_id)
        if quote is None or quote.supplier_id != proposal.supplier_id:
            raise LookupError("Supplier quote is no longer available")
        return OrderResult(
            order_id=uuid5(proposal.proposal_id, idempotency_key),
            status=OrderStatus.APPROVAL_PENDING,
        )

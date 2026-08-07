"""Transaction economics: acquisition costs and sale proceeds.

Every trade needs complete cost accounting:
- All-in acquisition cost (purchase + tax + shipping + insurance)
- Net sale proceeds (sale price - fees - shipping - insurance - reserves)
- Profit calculation (proceeds - cost)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AcquisitionCost:
    """Complete cost to acquire and hold a card."""

    purchase_price: float
    sales_tax: float
    inbound_shipping: float
    inbound_insurance: float
    grading_cost: float = 0.0
    authentication_cost: float = 0.0
    other_costs: float = 0.0

    @property
    def total_cost(self) -> float:
        """Sum of all acquisition costs."""
        return sum([
            self.purchase_price,
            self.sales_tax,
            self.inbound_shipping,
            self.inbound_insurance,
            self.grading_cost,
            self.authentication_cost,
            self.other_costs,
        ])

    def cost_breakdown(self) -> dict:
        """Itemized breakdown for reporting."""
        return {
            "purchase_price": self.purchase_price,
            "sales_tax": self.sales_tax,
            "inbound_shipping": self.inbound_shipping,
            "inbound_insurance": self.inbound_insurance,
            "grading_cost": self.grading_cost,
            "authentication_cost": self.authentication_cost,
            "other_costs": self.other_costs,
            "total": self.total_cost,
        }


@dataclass
class SaleProceeds:
    """Net proceeds from selling a card."""

    sale_price: float
    platform_fee: float  # eBay 12.5%, PWCC 15%, etc.
    outbound_shipping: float
    outbound_insurance: float
    return_and_cancellation_reserve: float  # 2% typical
    consignment_fee: float = 0.0
    other_deductions: float = 0.0

    @property
    def total_deductions(self) -> float:
        """Sum of all fees and deductions."""
        return sum([
            self.platform_fee,
            self.outbound_shipping,
            self.outbound_insurance,
            self.return_and_cancellation_reserve,
            self.consignment_fee,
            self.other_deductions,
        ])

    @property
    def net_proceeds(self) -> float:
        """Amount of money you actually receive."""
        return self.sale_price - self.total_deductions

    def proceeds_breakdown(self) -> dict:
        """Itemized breakdown for reporting."""
        return {
            "sale_price": self.sale_price,
            "platform_fee": self.platform_fee,
            "outbound_shipping": self.outbound_shipping,
            "outbound_insurance": self.outbound_insurance,
            "return_reserve": self.return_and_cancellation_reserve,
            "consignment_fee": self.consignment_fee,
            "other_deductions": self.other_deductions,
            "total_deductions": self.total_deductions,
            "net_proceeds": self.net_proceeds,
        }


@dataclass
class TradeEconomics:
    """Complete economics of a buy/hold/sell trade."""

    acquisition_cost: AcquisitionCost
    expected_sale_proceeds: SaleProceeds
    expected_holding_days: int

    @property
    def expected_gross_profit(self) -> float:
        """Sale price minus purchase price (ignores costs)."""
        return self.expected_sale_proceeds.sale_price - self.acquisition_cost.purchase_price

    @property
    def expected_net_profit(self) -> float:
        """Proceeds minus all costs."""
        return self.expected_sale_proceeds.net_proceeds - self.acquisition_cost.total_cost

    @property
    def expected_roic(self) -> float:
        """Return on Invested Capital (%)."""
        if self.acquisition_cost.total_cost == 0:
            return 0.0
        return self.expected_net_profit / self.acquisition_cost.total_cost

    @property
    def expected_roi_pct(self) -> float:
        """Return on Investment as percentage."""
        return self.expected_roic * 100

    @property
    def annualized_return(self) -> float:
        """Holding period return annualized (%)."""
        if self.expected_holding_days == 0:
            return 0.0
        days_per_year = 365
        return self.expected_roic * (days_per_year / self.expected_holding_days)

    @property
    def annualized_return_pct(self) -> float:
        """Annualized return as percentage."""
        return self.annualized_return * 100

    def break_even_sale_price(self) -> float:
        """What must we sell for to break even?"""
        return (
            self.acquisition_cost.total_cost
            + self.expected_sale_proceeds.total_deductions
        )

    def profit_at_price(self, sale_price: float) -> float:
        """Calculate profit if card sells at given price."""
        deductions = self.expected_sale_proceeds.total_deductions * (sale_price / self.expected_sale_proceeds.sale_price)
        proceeds = sale_price - deductions
        return proceeds - self.acquisition_cost.total_cost

    def economics_summary(self) -> str:
        """Human-readable summary for reporting."""
        lines = [
            f"Acquisition Cost: ${self.acquisition_cost.total_cost:.2f}",
            f"  Purchase: ${self.acquisition_cost.purchase_price:.2f}",
            f"  Tax: ${self.acquisition_cost.sales_tax:.2f}",
            f"  Shipping: ${self.acquisition_cost.inbound_shipping:.2f}",
            f"",
            f"Expected Sale Proceeds: ${self.expected_sale_proceeds.net_proceeds:.2f}",
            f"  Sale Price: ${self.expected_sale_proceeds.sale_price:.2f}",
            f"  Fees: ${self.expected_sale_proceeds.platform_fee:.2f}",
            f"  Shipping: ${self.expected_sale_proceeds.outbound_shipping:.2f}",
            f"",
            f"Expected Net Profit: ${self.expected_net_profit:.2f}",
            f"Expected ROIC: {self.expected_roi_pct:.1f}%",
            f"Annualized: {self.annualized_return_pct:.1f}%",
            f"Days to Sale: {self.expected_holding_days}",
        ]
        return "\n".join(lines)


def calculate_acquisition_cost(platform: str, purchase_price: float, grading_cost: float = 0.0) -> AcquisitionCost:
    """Calculate all-in acquisition cost based on platform and purchase price.

    Args:
        platform: "ebay", "pwcc", "auction", etc.
        purchase_price: The asking/winning price
        grading_cost: Optional grading fee if buying raw and grading
    """
    platform = platform.lower()

    # Platform-specific tax rates
    if platform == "ebay":
        sales_tax = purchase_price * 0.08  # Varies by state, use 8% average
        inbound_shipping = 5.0
        inbound_insurance = (purchase_price + 50) * 0.01
    elif platform == "pwcc":
        sales_tax = purchase_price * 0.065
        inbound_shipping = 25.0  # PWCC flat rate
        inbound_insurance = (purchase_price + 50) * 0.015
    elif platform == "auction":
        sales_tax = purchase_price * 0.065
        inbound_shipping = 25.0
        inbound_insurance = (purchase_price + 50) * 0.015
    else:
        # Default fallback
        sales_tax = purchase_price * 0.07
        inbound_shipping = 5.0
        inbound_insurance = (purchase_price + 50) * 0.01

    return AcquisitionCost(
        purchase_price=purchase_price,
        sales_tax=sales_tax,
        inbound_shipping=inbound_shipping,
        inbound_insurance=inbound_insurance,
        grading_cost=grading_cost,
    )


def calculate_sale_proceeds(platform: str, sale_price: float, use_consignment: bool = False) -> SaleProceeds:
    """Calculate net proceeds from sale based on platform and sale price.

    Args:
        platform: "ebay", "pwcc", "local", etc.
        sale_price: Expected or actual sale price
        use_consignment: If True, use consignment model instead of direct sale
    """
    platform = platform.lower()

    # Platform-specific fees
    if platform == "ebay":
        platform_fee = sale_price * 0.125  # 12.5% for auctions
    elif platform == "pwcc":
        platform_fee = sale_price * 0.15  # 15% for auctions
    else:
        platform_fee = sale_price * 0.12

    # Standard outbound costs
    outbound_shipping = 5.0
    outbound_insurance = (sale_price + 50) * 0.01
    return_reserve = sale_price * 0.02  # 2% for potential returns/chargebacks

    consignment_fee = 0.0
    if use_consignment:
        # If using consignment service, higher fee
        platform_fee = 0.0  # Consignment handles it
        consignment_fee = sale_price * 0.20

    return SaleProceeds(
        sale_price=sale_price,
        platform_fee=platform_fee,
        outbound_shipping=outbound_shipping,
        outbound_insurance=outbound_insurance,
        return_and_cancellation_reserve=return_reserve,
        consignment_fee=consignment_fee,
    )


if __name__ == "__main__":
    # Example: Buy Mahomes card on eBay for $100, sell for $145
    acq = calculate_acquisition_cost("ebay", purchase_price=100.0)
    sale = calculate_sale_proceeds("ebay", sale_price=145.0)

    econ = TradeEconomics(
        acquisition_cost=acq,
        expected_sale_proceeds=sale,
        expected_holding_days=14,
    )

    print(econ.economics_summary())
    print(f"\nBreak-even sale price: ${econ.break_even_sale_price():.2f}")
    print(f"\nIf sell at $120: ${econ.profit_at_price(120):.2f} profit")
    print(f"If sell at $150: ${econ.profit_at_price(150):.2f} profit")

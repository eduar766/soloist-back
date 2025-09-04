"""Billing service for calculating rates, taxes, and billing amounts.
Handles complex billing logic and calculations.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date

from app.domain.models.base import Money, ValidationError, BusinessRuleViolation
from app.domain.models.time_entry import TimeEntry
from app.domain.models.invoice import InvoiceLineItem, TaxLineItem
from app.domain.models.project import Project, BillingConfiguration, BillingType


class BillingService:
    """
    Domain service for billing calculations and business logic.
    Handles rate calculations, tax computations, and billing validations.
    """

    def __init__(self):
        # Standard tax rates by country/region
        self.tax_rates = {
            "US": {"sales_tax": 0.0},  # Varies by state
            "CL": {"iva": 19.0},
            "AR": {"iva": 21.0},
            "BR": {"icms": 18.0},
            "MX": {"iva": 16.0},
            "CO": {"iva": 19.0},
            "PE": {"igv": 18.0},
            "EU": {"vat": 20.0},  # Varies by country
        }
        
        # Currency conversion factors (simplified - in reality would use live rates)
        self.currency_factors = {
            "USD": 1.0,
            "EUR": 0.85,
            "CLP": 800.0,
            "ARS": 350.0,
            "BRL": 5.0,
            "MXN": 18.0,
            "COP": 4000.0,
            "PEN": 3.8,
        }

    def calculate_hourly_billing(
        self,
        time_entries: List[TimeEntry],
        default_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate billing amounts for hourly time entries.
        """
        if not time_entries:
            return {
                "total_hours": 0.0,
                "billable_hours": 0.0,
                "total_amount": 0.0,
                "line_items": [],
                "summary_by_user": {},
                "summary_by_task": {}
            }
        
        line_items = []
        total_hours = 0.0
        billable_hours = 0.0
        total_amount = 0.0
        
        # Group entries for better organization
        entries_by_user = {}
        entries_by_task = {}
        
        for entry in time_entries:
            if not entry.is_billable:
                continue
                
            hours = entry.effective_duration_hours
            rate = entry.hourly_rate or default_rate
            
            if not rate or rate <= 0:
                raise ValidationError(f"Invalid hourly rate for entry {entry.id}", "hourly_rate")
            
            amount = self._round_currency(hours * rate)
            
            # Create line item
            description = self._format_time_entry_description(entry)
            line_item = InvoiceLineItem(
                description=description,
                quantity=hours,
                rate=rate,
                amount=amount,
                time_entry_id=entry.id,
                task_id=entry.task_id,
                unit="hours"
            )
            
            line_items.append(line_item)
            total_hours += hours
            billable_hours += hours
            total_amount += amount
            
            # Group by user
            user_key = entry.user_id
            if user_key not in entries_by_user:
                entries_by_user[user_key] = {"hours": 0.0, "amount": 0.0, "entries": 0}
            entries_by_user[user_key]["hours"] += hours
            entries_by_user[user_key]["amount"] += amount
            entries_by_user[user_key]["entries"] += 1
            
            # Group by task
            if entry.task_id:
                task_key = entry.task_id
                if task_key not in entries_by_task:
                    entries_by_task[task_key] = {"hours": 0.0, "amount": 0.0, "entries": 0}
                entries_by_task[task_key]["hours"] += hours
                entries_by_task[task_key]["amount"] += amount
                entries_by_task[task_key]["entries"] += 1
        
        return {
            "total_hours": self._round_hours(total_hours),
            "billable_hours": self._round_hours(billable_hours),
            "total_amount": self._round_currency(total_amount),
            "line_items": line_items,
            "summary_by_user": entries_by_user,
            "summary_by_task": entries_by_task
        }

    def calculate_fixed_price_billing(
        self,
        project: Project,
        completion_percentage: float
    ) -> Dict[str, Any]:
        """
        Calculate billing for fixed price projects based on completion.
        """
        if project.billing.billing_type != BillingType.FIXED:
            raise BusinessRuleViolation("Project is not set up for fixed price billing")
        
        if not project.billing.fixed_price:
            raise ValidationError("Fixed price amount not set for project", "fixed_price")
        
        if completion_percentage < 0 or completion_percentage > 100:
            raise ValidationError("Completion percentage must be between 0 and 100", "completion_percentage")
        
        fixed_price = project.billing.fixed_price
        billable_amount = self._round_currency(fixed_price * (completion_percentage / 100))
        
        line_item = InvoiceLineItem(
            description=f"Project: {project.name} ({completion_percentage}% complete)",
            quantity=completion_percentage,
            rate=fixed_price / 100,  # Rate per percentage point
            amount=billable_amount,
            unit="%"
        )
        
        return {
            "total_amount": billable_amount,
            "completion_percentage": completion_percentage,
            "fixed_price": fixed_price,
            "remaining_amount": self._round_currency(fixed_price - billable_amount),
            "line_items": [line_item]
        }

    def calculate_milestone_billing(
        self,
        project: Project,
        completed_milestones: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate billing for milestone-based projects.
        """
        if project.billing.billing_type != BillingType.MILESTONE:
            raise BusinessRuleViolation("Project is not set up for milestone billing")
        
        line_items = []
        total_amount = 0.0
        
        for milestone in completed_milestones:
            if not milestone.get("completed", False):
                continue
                
            amount = milestone.get("amount", 0.0)
            if amount <= 0:
                continue
                
            line_item = InvoiceLineItem(
                description=f"Milestone: {milestone.get('name', 'Unnamed')}",
                quantity=1,
                rate=amount,
                amount=amount,
                unit="milestone"
            )
            
            line_items.append(line_item)
            total_amount += amount
        
        return {
            "total_amount": self._round_currency(total_amount),
            "completed_milestones": len([m for m in completed_milestones if m.get("completed")]),
            "total_milestones": len(completed_milestones),
            "line_items": line_items
        }

    def calculate_retainer_billing(
        self,
        project: Project,
        billing_period: str,
        hours_used: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate billing for retainer-based projects.
        """
        if project.billing.billing_type != BillingType.RETAINER:
            raise BusinessRuleViolation("Project is not set up for retainer billing")
        
        if not project.billing.retainer_amount:
            raise ValidationError("Retainer amount not set for project", "retainer_amount")
        
        retainer_amount = project.billing.retainer_amount
        
        line_item = InvoiceLineItem(
            description=f"Retainer - {billing_period}",
            quantity=1,
            rate=retainer_amount,
            amount=retainer_amount,
            unit="month"  # Assuming monthly retainers
        )
        
        result = {
            "total_amount": self._round_currency(retainer_amount),
            "billing_period": billing_period,
            "hours_used": hours_used,
            "line_items": [line_item]
        }
        
        # Add overage if hours exceed retainer limit
        if hasattr(project.billing, 'retainer_hours') and project.billing.retainer_hours:
            if hours_used > project.billing.retainer_hours:
                overage_hours = hours_used - project.billing.retainer_hours
                overage_rate = project.billing.hourly_rate or 0.0
                
                if overage_rate > 0:
                    overage_amount = self._round_currency(overage_hours * overage_rate)
                    overage_item = InvoiceLineItem(
                        description=f"Overage hours ({overage_hours:.2f} hrs @ ${overage_rate:.2f}/hr)",
                        quantity=overage_hours,
                        rate=overage_rate,
                        amount=overage_amount,
                        unit="hours"
                    )
                    result["line_items"].append(overage_item)
                    result["total_amount"] += overage_amount
                    result["overage_hours"] = overage_hours
                    result["overage_amount"] = overage_amount
        
        return result

    def calculate_taxes(
        self,
        subtotal: float,
        currency: str,
        tax_region: str = "US",
        custom_tax_rates: Optional[List[Dict[str, Any]]] = None
    ) -> List[TaxLineItem]:
        """
        Calculate taxes for an invoice.
        """
        tax_items = []
        
        if custom_tax_rates:
            # Use custom tax rates
            for tax_config in custom_tax_rates:
                rate = tax_config.get("rate", 0.0)
                name = tax_config.get("name", "Tax")
                tax_id = tax_config.get("tax_id")
                
                if rate > 0:
                    tax_amount = self._round_currency(subtotal * (rate / 100))
                    tax_item = TaxLineItem(
                        name=name,
                        rate=rate,
                        amount=tax_amount,
                        tax_id=tax_id
                    )
                    tax_items.append(tax_item)
        else:
            # Use standard tax rates
            region_rates = self.tax_rates.get(tax_region, {})
            for tax_name, rate in region_rates.items():
                if rate > 0:
                    tax_amount = self._round_currency(subtotal * (rate / 100))
                    tax_item = TaxLineItem(
                        name=tax_name.upper(),
                        rate=rate,
                        amount=tax_amount
                    )
                    tax_items.append(tax_item)
        
        return tax_items

    def apply_discount(
        self,
        subtotal: float,
        discount_percentage: float = 0.0,
        discount_amount: float = 0.0
    ) -> Dict[str, float]:
        """
        Apply discount to subtotal.
        """
        if discount_percentage < 0 or discount_percentage > 100:
            raise ValidationError("Discount percentage must be between 0 and 100", "discount_percentage")
        
        if discount_amount < 0:
            raise ValidationError("Discount amount cannot be negative", "discount_amount")
        
        if discount_percentage > 0 and discount_amount > 0:
            raise ValidationError("Cannot apply both percentage and amount discount", "discount")
        
        actual_discount = 0.0
        if discount_percentage > 0:
            actual_discount = self._round_currency(subtotal * (discount_percentage / 100))
        elif discount_amount > 0:
            actual_discount = min(discount_amount, subtotal)  # Don't discount more than subtotal
        
        discounted_subtotal = max(0, subtotal - actual_discount)
        
        return {
            "original_subtotal": subtotal,
            "discount_amount": actual_discount,
            "discount_percentage": (actual_discount / subtotal * 100) if subtotal > 0 else 0,
            "discounted_subtotal": discounted_subtotal
        }

    def convert_currency(
        self,
        amount: float,
        from_currency: str,
        to_currency: str
    ) -> float:
        """
        Convert amount between currencies.
        Note: This is a simplified implementation. In production, use live exchange rates.
        """
        if from_currency == to_currency:
            return amount
        
        if from_currency not in self.currency_factors:
            raise ValidationError(f"Unsupported currency: {from_currency}", "from_currency")
        
        if to_currency not in self.currency_factors:
            raise ValidationError(f"Unsupported currency: {to_currency}", "to_currency")
        
        # Convert to USD first, then to target currency
        usd_amount = amount / self.currency_factors[from_currency]
        target_amount = usd_amount * self.currency_factors[to_currency]
        
        return self._round_currency(target_amount)

    def validate_billing_configuration(self, config: BillingConfiguration) -> List[str]:
        """
        Validate billing configuration and return list of issues.
        """
        issues = []
        
        if config.billing_type == BillingType.HOURLY:
            if not config.hourly_rate or config.hourly_rate <= 0:
                issues.append("Hourly rate is required and must be positive for hourly billing")
        
        elif config.billing_type == BillingType.FIXED:
            if not config.fixed_price or config.fixed_price <= 0:
                issues.append("Fixed price is required and must be positive for fixed price billing")
        
        elif config.billing_type == BillingType.RETAINER:
            if not config.retainer_amount or config.retainer_amount <= 0:
                issues.append("Retainer amount is required and must be positive for retainer billing")
        
        elif config.billing_type == BillingType.MILESTONE:
            if not config.milestones or len(config.milestones) == 0:
                issues.append("At least one milestone is required for milestone billing")
            else:
                total_milestone_amount = sum(m.get("amount", 0) for m in config.milestones)
                if total_milestone_amount <= 0:
                    issues.append("Milestone amounts must be positive")
        
        if config.budget_limit and config.budget_limit < 0:
            issues.append("Budget limit cannot be negative")
        
        if config.budget_alert_threshold and (config.budget_alert_threshold < 0 or config.budget_alert_threshold > 1):
            issues.append("Budget alert threshold must be between 0 and 1")
        
        return issues

    def calculate_profitability(
        self,
        revenue: float,
        costs: float,
        hours_worked: float
    ) -> Dict[str, Any]:
        """
        Calculate profitability metrics.
        """
        profit = revenue - costs
        profit_margin = (profit / revenue * 100) if revenue > 0 else 0
        hourly_profit = profit / hours_worked if hours_worked > 0 else 0
        
        return {
            "revenue": self._round_currency(revenue),
            "costs": self._round_currency(costs),
            "profit": self._round_currency(profit),
            "profit_margin_percentage": self._round_percentage(profit_margin),
            "hourly_profit": self._round_currency(hourly_profit),
            "hours_worked": self._round_hours(hours_worked)
        }

    def estimate_project_cost(
        self,
        estimated_hours: float,
        hourly_rate: float,
        overhead_percentage: float = 20.0
    ) -> Dict[str, Any]:
        """
        Estimate total project cost including overhead.
        """
        base_cost = estimated_hours * hourly_rate
        overhead_amount = base_cost * (overhead_percentage / 100)
        total_cost = base_cost + overhead_amount
        
        return {
            "estimated_hours": self._round_hours(estimated_hours),
            "hourly_rate": self._round_currency(hourly_rate),
            "base_cost": self._round_currency(base_cost),
            "overhead_percentage": overhead_percentage,
            "overhead_amount": self._round_currency(overhead_amount),
            "total_estimated_cost": self._round_currency(total_cost)
        }

    def _format_time_entry_description(self, entry: TimeEntry) -> str:
        """
        Format time entry for invoice line item description.
        """
        parts = []
        
        if entry.description:
            parts.append(entry.description)
        else:
            parts.append("Time tracking")
        
        # Add date
        parts.append(f"({entry.date.strftime('%m/%d/%Y')})")
        
        return " ".join(parts)

    def _round_currency(self, amount: float) -> float:
        """
        Round amount to 2 decimal places for currency.
        """
        return float(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def _round_hours(self, hours: float) -> float:
        """
        Round hours to 2 decimal places.
        """
        return float(Decimal(str(hours)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def _round_percentage(self, percentage: float) -> float:
        """
        Round percentage to 1 decimal place.
        """
        return float(Decimal(str(percentage)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
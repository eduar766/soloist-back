"""
Unit tests for BillingService domain service.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from unittest.mock import Mock

from app.domain.services.billing_service import BillingService
from app.domain.models.base import ValidationError, BusinessRuleViolation


class TestBillingService:
    """Test cases for BillingService domain service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.billing_service = BillingService()
    
    def test_currency_conversion_same_currency(self):
        """Test currency conversion with same currency."""
        amount = 100.0
        result = self.billing_service.convert_currency(amount, "USD", "USD")
        assert result == 100.0
    
    def test_currency_conversion_usd_to_eur(self):
        """Test currency conversion from USD to EUR."""
        amount = 100.0
        result = self.billing_service.convert_currency(amount, "USD", "EUR")
        expected = 100.0 * 0.85  # EUR factor from service
        assert result == expected
    
    def test_currency_conversion_eur_to_usd(self):
        """Test currency conversion from EUR to USD."""
        amount = 85.0
        result = self.billing_service.convert_currency(amount, "EUR", "USD")
        # Convert EUR to USD: (85 / 0.85) * 1.0 = 100.0
        expected = 100.0
        assert result == expected
    
    def test_currency_conversion_unsupported_currency(self):
        """Test currency conversion with unsupported currency."""
        with pytest.raises(ValidationError, match="Unsupported currency: XYZ"):
            self.billing_service.convert_currency(100.0, "XYZ", "USD")
        
        with pytest.raises(ValidationError, match="Unsupported currency: ABC"):
            self.billing_service.convert_currency(100.0, "USD", "ABC")
    
    def test_apply_discount_percentage(self):
        """Test applying percentage discount."""
        subtotal = 1000.0
        result = self.billing_service.apply_discount(
            subtotal=subtotal,
            discount_percentage=10.0
        )
        
        assert result["original_subtotal"] == 1000.0
        assert result["discount_amount"] == 100.0
        assert result["discount_percentage"] == 10.0
        assert result["discounted_subtotal"] == 900.0
    
    def test_apply_discount_amount(self):
        """Test applying amount discount."""
        subtotal = 1000.0
        result = self.billing_service.apply_discount(
            subtotal=subtotal,
            discount_amount=150.0
        )
        
        assert result["original_subtotal"] == 1000.0
        assert result["discount_amount"] == 150.0
        assert result["discount_percentage"] == 15.0  # 150/1000 * 100
        assert result["discounted_subtotal"] == 850.0
    
    def test_apply_discount_amount_exceeds_subtotal(self):
        """Test applying discount amount that exceeds subtotal."""
        subtotal = 100.0
        result = self.billing_service.apply_discount(
            subtotal=subtotal,
            discount_amount=150.0  # More than subtotal
        )
        
        assert result["original_subtotal"] == 100.0
        assert result["discount_amount"] == 100.0  # Capped at subtotal
        assert result["discount_percentage"] == 100.0
        assert result["discounted_subtotal"] == 0.0
    
    def test_apply_discount_invalid_percentage(self):
        """Test applying invalid discount percentage."""
        with pytest.raises(ValidationError, match="Discount percentage must be between 0 and 100"):
            self.billing_service.apply_discount(1000.0, discount_percentage=-5.0)
        
        with pytest.raises(ValidationError, match="Discount percentage must be between 0 and 100"):
            self.billing_service.apply_discount(1000.0, discount_percentage=150.0)
    
    def test_apply_discount_invalid_amount(self):
        """Test applying invalid discount amount."""
        with pytest.raises(ValidationError, match="Discount amount cannot be negative"):
            self.billing_service.apply_discount(1000.0, discount_amount=-50.0)
    
    def test_apply_discount_both_percentage_and_amount(self):
        """Test applying both percentage and amount discount (should fail)."""
        with pytest.raises(ValidationError, match="Cannot apply both percentage and amount discount"):
            self.billing_service.apply_discount(
                subtotal=1000.0,
                discount_percentage=10.0,
                discount_amount=100.0
            )
    
    def test_calculate_taxes_with_standard_rates(self):
        """Test calculating taxes with standard rates."""
        subtotal = 1000.0
        tax_items = self.billing_service.calculate_taxes(
            subtotal=subtotal,
            currency="USD",
            tax_region="CL"  # Chile has 19% IVA
        )
        
        assert len(tax_items) == 1
        tax_item = tax_items[0]
        assert tax_item.name == "IVA"
        assert tax_item.rate == 19.0
        assert tax_item.amount == 190.0  # 1000 * 0.19
    
    def test_calculate_taxes_with_custom_rates(self):
        """Test calculating taxes with custom rates."""
        subtotal = 1000.0
        custom_rates = [
            {"name": "Sales Tax", "rate": 8.5, "tax_id": "ST001"},
            {"name": "Service Tax", "rate": 2.0, "tax_id": "SV001"}
        ]
        
        tax_items = self.billing_service.calculate_taxes(
            subtotal=subtotal,
            currency="USD",
            custom_tax_rates=custom_rates
        )
        
        assert len(tax_items) == 2
        
        sales_tax = next(item for item in tax_items if item.name == "Sales Tax")
        assert sales_tax.rate == 8.5
        assert sales_tax.amount == 85.0
        assert sales_tax.tax_id == "ST001"
        
        service_tax = next(item for item in tax_items if item.name == "Service Tax")
        assert service_tax.rate == 2.0
        assert service_tax.amount == 20.0
        assert service_tax.tax_id == "SV001"
    
    def test_calculate_taxes_no_taxes(self):
        """Test calculating taxes for region with no taxes."""
        subtotal = 1000.0
        tax_items = self.billing_service.calculate_taxes(
            subtotal=subtotal,
            currency="USD",
            tax_region="US"  # US has 0% default
        )
        
        assert len(tax_items) == 0
    
    def test_calculate_profitability(self):
        """Test calculating profitability metrics."""
        revenue = 5000.0
        costs = 3000.0
        hours_worked = 100.0
        
        result = self.billing_service.calculate_profitability(
            revenue=revenue,
            costs=costs,
            hours_worked=hours_worked
        )
        
        assert result["revenue"] == 5000.0
        assert result["costs"] == 3000.0
        assert result["profit"] == 2000.0
        assert result["profit_margin_percentage"] == 40.0  # (2000/5000) * 100
        assert result["hourly_profit"] == 20.0  # 2000/100
        assert result["hours_worked"] == 100.0
    
    def test_calculate_profitability_zero_revenue(self):
        """Test profitability calculation with zero revenue."""
        result = self.billing_service.calculate_profitability(
            revenue=0.0,
            costs=1000.0,
            hours_worked=50.0
        )
        
        assert result["revenue"] == 0.0
        assert result["costs"] == 1000.0
        assert result["profit"] == -1000.0
        assert result["profit_margin_percentage"] == 0.0  # Can't divide by zero
        assert result["hourly_profit"] == -20.0
    
    def test_calculate_profitability_zero_hours(self):
        """Test profitability calculation with zero hours."""
        result = self.billing_service.calculate_profitability(
            revenue=5000.0,
            costs=3000.0,
            hours_worked=0.0
        )
        
        assert result["profit"] == 2000.0
        assert result["hourly_profit"] == 0.0  # Can't divide by zero
        assert result["hours_worked"] == 0.0
    
    def test_estimate_project_cost(self):
        """Test estimating project cost with overhead."""
        estimated_hours = 100.0
        hourly_rate = 80.0
        overhead_percentage = 25.0
        
        result = self.billing_service.estimate_project_cost(
            estimated_hours=estimated_hours,
            hourly_rate=hourly_rate,
            overhead_percentage=overhead_percentage
        )
        
        assert result["estimated_hours"] == 100.0
        assert result["hourly_rate"] == 80.0
        assert result["base_cost"] == 8000.0  # 100 * 80
        assert result["overhead_percentage"] == 25.0
        assert result["overhead_amount"] == 2000.0  # 8000 * 0.25
        assert result["total_estimated_cost"] == 10000.0  # 8000 + 2000
    
    def test_estimate_project_cost_default_overhead(self):
        """Test estimating project cost with default overhead."""
        result = self.billing_service.estimate_project_cost(
            estimated_hours=50.0,
            hourly_rate=100.0
        )
        
        assert result["base_cost"] == 5000.0
        assert result["overhead_percentage"] == 20.0  # Default
        assert result["overhead_amount"] == 1000.0  # 5000 * 0.20
        assert result["total_estimated_cost"] == 6000.0
    
    def test_rounding_currency(self):
        """Test currency rounding."""
        # Test rounding up
        assert self.billing_service._round_currency(123.456) == 123.46
        
        # Test rounding down
        assert self.billing_service._round_currency(123.454) == 123.45
        
        # Test exact value
        assert self.billing_service._round_currency(123.45) == 123.45
        
        # Test rounding .5 up
        assert self.billing_service._round_currency(123.455) == 123.46
    
    def test_rounding_hours(self):
        """Test hours rounding."""
        assert self.billing_service._round_hours(8.123) == 8.12
        assert self.billing_service._round_hours(8.125) == 8.13  # Rounds up
        assert self.billing_service._round_hours(8.12) == 8.12
    
    def test_rounding_percentage(self):
        """Test percentage rounding."""
        assert self.billing_service._round_percentage(12.34) == 12.3
        assert self.billing_service._round_percentage(12.35) == 12.4  # Rounds up
        assert self.billing_service._round_percentage(12.3) == 12.3
    
    def test_calculate_hourly_billing_empty_entries(self):
        """Test hourly billing calculation with empty entries."""
        result = self.billing_service.calculate_hourly_billing([])
        
        assert result["total_hours"] == 0.0
        assert result["billable_hours"] == 0.0
        assert result["total_amount"] == 0.0
        assert result["line_items"] == []
        assert result["summary_by_user"] == {}
        assert result["summary_by_task"] == {}
    
    def test_format_time_entry_description(self):
        """Test formatting time entry description."""
        # Mock time entry with description
        entry_with_desc = Mock()
        entry_with_desc.description = "Working on feature X"
        entry_with_desc.date = date(2024, 1, 15)
        
        result = self.billing_service._format_time_entry_description(entry_with_desc)
        assert result == "Working on feature X (01/15/2024)"
        
        # Mock time entry without description
        entry_no_desc = Mock()
        entry_no_desc.description = None
        entry_no_desc.date = date(2024, 1, 15)
        
        result = self.billing_service._format_time_entry_description(entry_no_desc)
        assert result == "Time tracking (01/15/2024)"


class TestBillingServiceValidation:
    """Test cases for billing configuration validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.billing_service = BillingService()
    
    def test_validate_hourly_billing_valid(self):
        """Test validation of valid hourly billing configuration."""
        config = Mock()
        config.billing_type = "hourly"  # Assuming BillingType.HOURLY
        config.hourly_rate = 75.0
        config.budget_limit = None
        config.budget_alert_threshold = None
        
        issues = self.billing_service.validate_billing_configuration(config)
        assert len(issues) == 0
    
    def test_validate_hourly_billing_no_rate(self):
        """Test validation of hourly billing without rate."""
        config = Mock()
        config.billing_type = "hourly"
        config.hourly_rate = None
        config.budget_limit = None
        config.budget_alert_threshold = None
        
        issues = self.billing_service.validate_billing_configuration(config)
        assert len(issues) == 1
        assert "Hourly rate is required" in issues[0]
    
    def test_validate_fixed_billing_valid(self):
        """Test validation of valid fixed price billing configuration."""
        config = Mock()
        config.billing_type = "fixed"
        config.fixed_price = 5000.0
        config.budget_limit = None
        config.budget_alert_threshold = None
        
        issues = self.billing_service.validate_billing_configuration(config)
        assert len(issues) == 0
    
    def test_validate_fixed_billing_no_price(self):
        """Test validation of fixed billing without price."""
        config = Mock()
        config.billing_type = "fixed"
        config.fixed_price = None
        config.budget_limit = None
        config.budget_alert_threshold = None
        
        issues = self.billing_service.validate_billing_configuration(config)
        assert len(issues) == 1
        assert "Fixed price is required" in issues[0]
    
    def test_validate_budget_limit_negative(self):
        """Test validation with negative budget limit."""
        config = Mock()
        config.billing_type = "hourly"
        config.hourly_rate = 75.0
        config.budget_limit = -1000.0
        config.budget_alert_threshold = None
        
        issues = self.billing_service.validate_billing_configuration(config)
        assert len(issues) == 1
        assert "Budget limit cannot be negative" in issues[0]
    
    def test_validate_budget_alert_threshold_invalid(self):
        """Test validation with invalid budget alert threshold."""
        config = Mock()
        config.billing_type = "hourly"
        config.hourly_rate = 75.0
        config.budget_limit = None
        config.budget_alert_threshold = 1.5  # > 1.0
        
        issues = self.billing_service.validate_billing_configuration(config)
        assert len(issues) == 1
        assert "Budget alert threshold must be between 0 and 1" in issues[0]
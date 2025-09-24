"""
AP2 Currency Manager - Implementation
Multi-currency support for AP2 payment protocol following best practices
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from decimal import Decimal, ROUND_HALF_UP

from ..constants import ValidationConstants, AP2Limits, BusinessConstants

logger = logging.getLogger(__name__)


class CurrencyCode(Enum):
    """Supported currency codes"""
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    JPY = "JPY"  # Japanese Yen
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    CHF = "CHF"  # Swiss Franc
    CNY = "CNY"  # Chinese Yuan


class CurrencyPrecision(Enum):
    """Currency precision settings"""
    USD = 2  # 2 decimal places
    EUR = 2  # 2 decimal places
    GBP = 2  # 2 decimal places
    JPY = 0  # No decimal places
    CAD = 2  # 2 decimal places
    AUD = 2  # 2 decimal places
    CHF = 2  # 2 decimal places
    CNY = 2  # 2 decimal places


@dataclass
class CurrencyInfo:
    """Currency information"""
    code: CurrencyCode
    name: str
    symbol: str
    precision: int
    is_crypto: bool = False
    is_supported: bool = True
    exchange_rate_source: Optional[str] = None


@dataclass
class ExchangeRate:
    """Exchange rate information"""
    from_currency: CurrencyCode
    to_currency: CurrencyCode
    rate: Decimal
    timestamp: datetime
    source: str
    expires_at: Optional[datetime] = None


@dataclass
class CurrencyConversion:
    """Currency conversion result"""
    from_currency: CurrencyCode
    to_currency: CurrencyCode
    from_amount: Decimal
    to_amount: Decimal
    exchange_rate: Decimal
    conversion_fee: Optional[Decimal] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class CurrencyManager:
    """Manages multi-currency operations for AP2 protocol following best practices"""
    
    def __init__(self, exchange_rate_provider: Optional[str] = None):
        self._exchange_rate_provider = exchange_rate_provider or "default"
        self._supported_currencies = self._initialize_supported_currencies()
        self._exchange_rates: Dict[Tuple[CurrencyCode, CurrencyCode], ExchangeRate] = {}
        self._conversion_fees: Dict[Tuple[CurrencyCode, CurrencyCode], Decimal] = {}
        self._rate_cache_ttl = timedelta(minutes=5)  # Cache rates for 5 minutes
        self._lock = asyncio.Lock()
    
    def _initialize_supported_currencies(self) -> Dict[CurrencyCode, CurrencyInfo]:
        """Initialize supported currencies"""
        currencies = {}
        
        for currency_code in CurrencyCode:
            precision = CurrencyPrecision[currency_code.name].value
            currency_info = CurrencyInfo(
                code=currency_code,
                name=self._get_currency_name(currency_code),
                symbol=self._get_currency_symbol(currency_code),
                precision=precision,
                exchange_rate_source=self._exchange_rate_provider
            )
            currencies[currency_code] = currency_info
        
        return currencies
    
    def _get_currency_name(self, currency_code: CurrencyCode) -> str:
        """Get human-readable currency name"""
        names = {
            CurrencyCode.USD: "US Dollar",
            CurrencyCode.EUR: "Euro",
            CurrencyCode.GBP: "British Pound Sterling",
            CurrencyCode.JPY: "Japanese Yen",
            CurrencyCode.CAD: "Canadian Dollar",
            CurrencyCode.AUD: "Australian Dollar",
            CurrencyCode.CHF: "Swiss Franc",
            CurrencyCode.CNY: "Chinese Yuan"
        }
        return names.get(currency_code, currency_code.value)
    
    def _get_currency_symbol(self, currency_code: CurrencyCode) -> str:
        """Get currency symbol"""
        symbols = {
            CurrencyCode.USD: "$",
            CurrencyCode.EUR: "€",
            CurrencyCode.GBP: "£",
            CurrencyCode.JPY: "¥",
            CurrencyCode.CAD: "C$",
            CurrencyCode.AUD: "A$",
            CurrencyCode.CHF: "CHF",
            CurrencyCode.CNY: "¥"
        }
        return symbols.get(currency_code, currency_code.value)
    
    def is_currency_supported(self, currency_code: str) -> bool:
        """Check if currency is supported"""
        try:
            currency = CurrencyCode(currency_code.upper())
            return currency in self._supported_currencies and self._supported_currencies[currency].is_supported
        except ValueError:
            return False
    
    def get_supported_currencies(self) -> List[CurrencyInfo]:
        """Get list of supported currencies"""
        return [info for info in self._supported_currencies.values() if info.is_supported]
    
    def get_currency_info(self, currency_code: str) -> Optional[CurrencyInfo]:
        """Get currency information"""
        try:
            currency = CurrencyCode(currency_code.upper())
            return self._supported_currencies.get(currency)
        except ValueError:
            return None
    
    def format_amount(self, amount: Decimal, currency_code: str) -> str:
        """Format amount with proper currency formatting"""
        currency_info = self.get_currency_info(currency_code)
        if not currency_info:
            raise ValueError(f"Unsupported currency: {currency_code}")
        
        # Round to proper precision
        rounded_amount = amount.quantize(
            Decimal('0.1') ** currency_info.precision,
            rounding=ROUND_HALF_UP
        )
        
        # Format with currency symbol
        if currency_code.upper() == "USD":
            return f"${rounded_amount:,.{currency_info.precision}f}"
        elif currency_code.upper() == "EUR":
            return f"€{rounded_amount:,.{currency_info.precision}f}"
        elif currency_code.upper() == "GBP":
            return f"£{rounded_amount:,.{currency_info.precision}f}"
        elif currency_code.upper() == "JPY":
            return f"¥{rounded_amount:,.0f}"
        else:
            return f"{currency_info.symbol}{rounded_amount:,.{currency_info.precision}f}"
    
    def parse_amount(self, amount_str: str, currency_code: str) -> Decimal:
        """Parse amount string to Decimal with proper precision"""
        try:
            # Remove currency symbols and commas
            cleaned_amount = amount_str.replace(",", "").replace("$", "").replace("€", "").replace("£", "").replace("¥", "")
            amount = Decimal(cleaned_amount)
            
            # Validate amount limits
            if amount < AP2Limits.MIN_PAYMENT_AMOUNT:
                raise ValueError(f"Amount too small: {amount}")
            if amount > AP2Limits.MAX_PAYMENT_AMOUNT:
                raise ValueError(f"Amount too large: {amount}")
            
            # Round to proper precision
            currency_info = self.get_currency_info(currency_code)
            if currency_info:
                amount = amount.quantize(
                    Decimal('0.1') ** currency_info.precision,
                    rounding=ROUND_HALF_UP
                )
            
            return amount
            
        except Exception as e:
            raise ValueError(f"Invalid amount format: {amount_str} - {str(e)}")
    
    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """Get exchange rate between currencies"""
        try:
            from_curr = CurrencyCode(from_currency.upper())
            to_curr = CurrencyCode(to_currency.upper())
            
            # Check cache first
            cache_key = (from_curr, to_curr)
            if cache_key in self._exchange_rates:
                rate = self._exchange_rates[cache_key]
                if rate.expires_at and datetime.now() < rate.expires_at:
                    return rate
            
            # Fetch new rate
            rate = await self._fetch_exchange_rate(from_curr, to_curr)
            if rate:
                self._exchange_rates[cache_key] = rate
                # Also cache reverse rate
                reverse_rate = ExchangeRate(
                    from_currency=to_curr,
                    to_currency=from_curr,
                    rate=Decimal('1') / rate.rate,
                    timestamp=rate.timestamp,
                    source=rate.source,
                    expires_at=rate.expires_at
                )
                self._exchange_rates[(to_curr, from_curr)] = reverse_rate
            
            return rate
            
        except Exception as e:
            logger.error(f"Failed to get exchange rate from {from_currency} to {to_currency}: {e}")
            return None
    
    async def _fetch_exchange_rate(self, from_currency: CurrencyCode, to_currency: CurrencyCode) -> Optional[ExchangeRate]:
        """Fetch exchange rate from external provider"""
        try:
            # Mock exchange rate provider (in production, this would call a real API)
            mock_rates = {
                (CurrencyCode.USD, CurrencyCode.EUR): Decimal('0.85'),
                (CurrencyCode.USD, CurrencyCode.GBP): Decimal('0.73'),
                (CurrencyCode.USD, CurrencyCode.JPY): Decimal('110.0'),
                (CurrencyCode.USD, CurrencyCode.CAD): Decimal('1.25'),
                (CurrencyCode.USD, CurrencyCode.AUD): Decimal('1.35'),
                (CurrencyCode.USD, CurrencyCode.CHF): Decimal('0.92'),
                (CurrencyCode.USD, CurrencyCode.CNY): Decimal('6.45'),
                (CurrencyCode.EUR, CurrencyCode.GBP): Decimal('0.86'),
                (CurrencyCode.EUR, CurrencyCode.JPY): Decimal('129.4'),
                (CurrencyCode.EUR, CurrencyCode.CAD): Decimal('1.47'),
                (CurrencyCode.EUR, CurrencyCode.AUD): Decimal('1.59'),
                (CurrencyCode.EUR, CurrencyCode.CHF): Decimal('1.08'),
                (CurrencyCode.EUR, CurrencyCode.CNY): Decimal('7.59'),
                # Add more rates as needed
            }
            
            # Check if we have a direct rate
            if (from_currency, to_currency) in mock_rates:
                rate_value = mock_rates[(from_currency, to_currency)]
            elif from_currency == to_currency:
                rate_value = Decimal('1.0')
            else:
                # Try to find rate through USD as intermediate currency
                if from_currency != CurrencyCode.USD and to_currency != CurrencyCode.USD:
                    usd_to_from = mock_rates.get((CurrencyCode.USD, from_currency))
                    usd_to_to = mock_rates.get((CurrencyCode.USD, to_currency))
                    if usd_to_from and usd_to_to:
                        rate_value = usd_to_to / usd_to_from
                    else:
                        logger.warning(f"No exchange rate available for {from_currency} to {to_currency}")
                        return None
                else:
                    logger.warning(f"No exchange rate available for {from_currency} to {to_currency}")
                    return None
            
            return ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate_value,
                timestamp=datetime.now(),
                source=self._exchange_rate_provider,
                expires_at=datetime.now() + self._rate_cache_ttl
            )
            
        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")
            return None
    
    async def convert_currency(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        include_fee: bool = True
    ) -> Optional[CurrencyConversion]:
        """Convert amount from one currency to another"""
        try:
            from_curr = CurrencyCode(from_currency.upper())
            to_curr = CurrencyCode(to_currency.upper())
            
            # Same currency
            if from_curr == to_curr:
                return CurrencyConversion(
                    from_currency=from_curr,
                    to_currency=to_curr,
                    from_amount=amount,
                    to_amount=amount,
                    exchange_rate=Decimal('1.0')
                )
            
            # Get exchange rate
            exchange_rate = await self.get_exchange_rate(from_currency, to_currency)
            if not exchange_rate:
                return None
            
            # Calculate converted amount
            converted_amount = amount * exchange_rate.rate
            
            # Apply conversion fee if requested
            conversion_fee = None
            if include_fee:
                conversion_fee = self._calculate_conversion_fee(amount, from_curr, to_curr)
                if conversion_fee:
                    converted_amount -= conversion_fee
            
            # Round to proper precision
            to_currency_info = self.get_currency_info(to_currency)
            if to_currency_info:
                converted_amount = converted_amount.quantize(
                    Decimal('0.1') ** to_currency_info.precision,
                    rounding=ROUND_HALF_UP
                )
            
            return CurrencyConversion(
                from_currency=from_curr,
                to_currency=to_curr,
                from_amount=amount,
                to_amount=converted_amount,
                exchange_rate=exchange_rate.rate,
                conversion_fee=conversion_fee
            )
            
        except Exception as e:
            logger.error(f"Currency conversion failed: {e}")
            return None
    
    def _calculate_conversion_fee(self, amount: Decimal, from_currency: CurrencyCode, to_currency: CurrencyCode) -> Optional[Decimal]:
        """Calculate conversion fee"""
        try:
            # Check if there's a specific fee for this currency pair
            fee_key = (from_currency, to_currency)
            if fee_key in self._conversion_fees:
                return self._conversion_fees[fee_key]
            
            # Default fee structure (0.5% of amount, minimum $1, maximum $50)
            default_fee_rate = Decimal('0.005')  # 0.5%
            fee = amount * default_fee_rate
            
            # Apply minimum and maximum limits (in USD)
            min_fee = Decimal('1.0')
            max_fee = Decimal('50.0')
            
            # Convert limits to from_currency if needed
            if from_currency != CurrencyCode.USD:
                # This is simplified - in production, you'd use current exchange rates
                fee = max(min_fee, min(fee, max_fee))
            else:
                fee = max(min_fee, min(fee, max_fee))
            
            return fee
            
        except Exception as e:
            logger.error(f"Error calculating conversion fee: {e}")
            return None
    
    def set_conversion_fee(self, from_currency: str, to_currency: str, fee: Decimal):
        """Set custom conversion fee for currency pair"""
        try:
            from_curr = CurrencyCode(from_currency.upper())
            to_curr = CurrencyCode(to_currency.upper())
            self._conversion_fees[(from_curr, to_curr)] = fee
            logger.info(f"Set conversion fee for {from_currency} to {to_currency}: {fee}")
        except ValueError as e:
            logger.error(f"Invalid currency code: {e}")
    
    def validate_payment_amount(self, amount: Decimal, currency_code: str) -> bool:
        """Validate payment amount for given currency"""
        try:
            currency_info = self.get_currency_info(currency_code)
            if not currency_info:
                return False
            
            # Check amount limits
            if amount < AP2Limits.MIN_PAYMENT_AMOUNT:
                return False
            if amount > AP2Limits.MAX_PAYMENT_AMOUNT:
                return False
            
            # Check precision
            precision_limit = Decimal('0.1') ** currency_info.precision
            if amount % precision_limit != 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating payment amount: {e}")
            return False
    
    async def get_currency_statistics(self) -> Dict[str, Any]:
        """Get currency management statistics"""
        try:
            total_currencies = len(self._supported_currencies)
            supported_currencies = len([c for c in self._supported_currencies.values() if c.is_supported])
            cached_rates = len(self._exchange_rates)
            custom_fees = len(self._conversion_fees)
            
            # Get currency usage statistics (mock data)
            currency_usage = {
                currency.value: 0 for currency in CurrencyCode
            }
            currency_usage["USD"] = 45  # 45% of transactions
            currency_usage["EUR"] = 25  # 25% of transactions
            currency_usage["GBP"] = 15  # 15% of transactions
            currency_usage["JPY"] = 8   # 8% of transactions
            currency_usage["CAD"] = 4   # 4% of transactions
            currency_usage["AUD"] = 2   # 2% of transactions
            currency_usage["CHF"] = 1   # 1% of transactions
            currency_usage["CNY"] = 0   # 0% of transactions
            
            return {
                "total_currencies": total_currencies,
                "supported_currencies": supported_currencies,
                "cached_exchange_rates": cached_rates,
                "custom_conversion_fees": custom_fees,
                "currency_usage_distribution": currency_usage,
                "exchange_rate_provider": self._exchange_rate_provider,
                "rate_cache_ttl_minutes": self._rate_cache_ttl.total_seconds() / 60,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting currency statistics: {e}")
            return {}
    
    async def clear_rate_cache(self):
        """Clear exchange rate cache"""
        async with self._lock:
            self._exchange_rates.clear()
            logger.info("Exchange rate cache cleared")
    
    async def refresh_all_rates(self):
        """Refresh all cached exchange rates"""
        try:
            async with self._lock:
                # Get all currency pairs
                currencies = list(CurrencyCode)
                refresh_tasks = []
                
                for from_curr in currencies:
                    for to_curr in currencies:
                        if from_curr != to_curr:
                            refresh_tasks.append(
                                self.get_exchange_rate(from_curr.value, to_curr.value)
                            )
                
                # Refresh all rates concurrently
                await asyncio.gather(*refresh_tasks, return_exceptions=True)
                
                logger.info(f"Refreshed exchange rates for {len(refresh_tasks)} currency pairs")
                
        except Exception as e:
            logger.error(f"Error refreshing exchange rates: {e}")


# Global currency manager instance
_currency_manager: Optional[CurrencyManager] = None


def get_currency_manager() -> CurrencyManager:
    """Get global currency manager instance"""
    global _currency_manager
    if _currency_manager is None:
        _currency_manager = CurrencyManager()
    return _currency_manager


# Convenience functions for common currency operations

async def convert_payment_amount(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    include_fee: bool = True
) -> Optional[CurrencyConversion]:
    """Convert payment amount between currencies"""
    manager = get_currency_manager()
    return await manager.convert_currency(amount, from_currency, to_currency, include_fee)


def format_payment_amount(amount: Decimal, currency_code: str) -> str:
    """Format payment amount with proper currency formatting"""
    manager = get_currency_manager()
    return manager.format_amount(amount, currency_code)


def validate_payment_currency(amount: Decimal, currency_code: str) -> bool:
    """Validate payment amount and currency"""
    manager = get_currency_manager()
    return manager.validate_payment_amount(amount, currency_code)


def is_currency_supported(currency_code: str) -> bool:
    """Check if currency is supported"""
    manager = get_currency_manager()
    return manager.is_currency_supported(currency_code)


if __name__ == "__main__":
    # Example usage
    async def main():
        manager = get_currency_manager()
        
        # Test currency support
        print("Supported currencies:")
        for currency_info in manager.get_supported_currencies():
            print(f"  {currency_info.code.value}: {currency_info.name} ({currency_info.symbol})")
        
        # Test currency conversion
        amount = Decimal('100.00')
        conversion = await manager.convert_currency(amount, 'USD', 'EUR')
        if conversion:
            print(f"\nCurrency conversion:")
            print(f"  {manager.format_amount(conversion.from_amount, 'USD')} = {manager.format_amount(conversion.to_amount, 'EUR')}")
            print(f"  Exchange rate: {conversion.exchange_rate}")
            if conversion.conversion_fee:
                print(f"  Conversion fee: {conversion.conversion_fee}")
        
        # Test amount formatting
        print(f"\nAmount formatting:")
        print(f"  USD: {manager.format_amount(Decimal('1234.56'), 'USD')}")
        print(f"  EUR: {manager.format_amount(Decimal('1234.56'), 'EUR')}")
        print(f"  JPY: {manager.format_amount(Decimal('1234'), 'JPY')}")
        
        # Get statistics
        stats = await manager.get_currency_statistics()
        print(f"\nCurrency statistics:")
        print(f"  Supported currencies: {stats['supported_currencies']}")
        print(f"  Cached exchange rates: {stats['cached_exchange_rates']}")
    
    asyncio.run(main())

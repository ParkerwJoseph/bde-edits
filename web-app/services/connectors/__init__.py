"""
Connector services for external data integrations.

Supported connectors:
- QuickBooks: Accounting and financial data
"""

from services.connectors.quickbooks.client import QuickBooksConnector

__all__ = [
    "QuickBooksConnector",
]

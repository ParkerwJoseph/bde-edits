"""
Connector adapter for normalizing and aggregating connector data.
"""
from typing import List, Any, Dict, Optional
from datetime import datetime
from collections import defaultdict

from services.chunking.adapters.base_adapter import BaseAdapter
from services.chunking.models import (
    ChunkInput,
    ChunkOutput,
    NormalizedInput,
    SourceType,
    ENTITY_AGGREGATION_CONFIG,
    DEFAULT_AGGREGATION_CONFIG,
)
from database.models.connector import ConnectorChunk, ConnectorType
from utils.logger import get_logger

logger = get_logger(__name__)


class ConnectorAdapter(BaseAdapter):
    """
    Adapter for connector data (QuickBooks, Salesforce, etc.).

    Key responsibility: Group records for aggregation instead of 1:1 chunking.
    For 10,000 invoices, this creates ~12-15 monthly groups, not 10,000 individual units.
    """

    def normalize(self, input: ChunkInput) -> NormalizedInput:
        """
        Convert connector records to normalized content units with aggregation.

        Groups records by time period or category based on entity type configuration.

        Args:
            input: ChunkInput with raw_records list

        Returns:
            NormalizedInput with grouped content units
        """
        records = input.raw_records or []
        entity_type = input.entity_type or "unknown"

        # Get aggregation config for this entity type
        config = ENTITY_AGGREGATION_CONFIG.get(entity_type, DEFAULT_AGGREGATION_CONFIG)

        logger.info(f"[ConnectorAdapter] Normalizing {len(records)} {entity_type} records")
        logger.info(f"[ConnectorAdapter] Aggregation strategy: {config['strategy']}, group_by: {config['group_by']}")

        # Group records based on strategy
        grouped = self._group_records(records, entity_type, config)
        logger.info(f"[ConnectorAdapter] Created {len(grouped)} groups")

        # Build content units from groups
        content_units = []
        for group_key, group_records in grouped.items():
            # Pre-aggregate data for this group
            pre_aggregated = self._pre_aggregate(group_records, entity_type)

            content_units.append({
                "unit_type": "record_group",
                "group_key": group_key,
                "records": group_records,
                "record_count": len(group_records),
                "aggregation_strategy": config["strategy"],
                "pre_aggregated": pre_aggregated,
                "record_ids": [r.get("Id") or r.get("id") for r in group_records if r.get("Id") or r.get("id")],
            })

        return NormalizedInput(
            content_units=content_units,
            context={
                "connector_type": input.connector_type or "unknown",
                "entity_type": entity_type,
                "total_records": len(records),
                "aggregation_config": config,
            },
            source_info={
                "connector_config_id": input.connector_config_id,
                "tenant_id": input.tenant_id,
                "company_id": input.company_id,
            }
        )

    def _group_records(
        self,
        records: List[dict],
        entity_type: str,
        config: dict
    ) -> Dict[str, List[dict]]:
        """
        Group records based on aggregation strategy.

        Args:
            records: Raw records to group
            entity_type: Type of entity
            config: Aggregation configuration

        Returns:
            Dict mapping group keys to record lists
        """
        strategy = config.get("strategy", "general_summary")
        group_by = config.get("group_by", "batch")

        if strategy == "temporal_summary":
            return self._group_by_time_period(records, group_by)
        elif strategy == "segment_summary":
            return self._group_by_segment(records, entity_type, group_by)
        elif strategy == "period_analysis":
            return self._group_by_report_period(records)
        elif strategy == "snapshot_analysis":
            return self._group_by_snapshot_date(records)
        elif strategy == "category_summary":
            return self._group_by_category(records, entity_type, group_by)
        elif strategy == "report_analysis":
            return self._group_report_data(records, entity_type, group_by)
        else:
            # General batching for unknown strategies
            return self._batch_records(records, batch_size=100)

    def _group_by_time_period(
        self,
        records: List[dict],
        period: str
    ) -> Dict[str, List[dict]]:
        """Group records by time period (month, quarter, year)"""
        groups: Dict[str, List[dict]] = defaultdict(list)

        for record in records:
            # Try common date field names
            date_str = (
                record.get("TxnDate") or
                record.get("txnDate") or
                record.get("Date") or
                record.get("date") or
                record.get("MetaData", {}).get("CreateTime") or
                record.get("CreateTime")
            )

            if date_str:
                dt = self._parse_date(date_str)
                if dt:
                    if period == "month":
                        key = dt.strftime("%Y-%m")
                    elif period == "quarter":
                        quarter = (dt.month - 1) // 3 + 1
                        key = f"{dt.year}-Q{quarter}"
                    else:  # year
                        key = str(dt.year)
                else:
                    key = "unknown_date"
            else:
                key = "no_date"

            groups[key].append(record)

        # Sort groups by key (chronological)
        return dict(sorted(groups.items()))

    def _group_by_segment(self, records: List[dict], entity_type: str, group_by: str = "segment") -> Dict[str, List[dict]]:
        """Group records by segment (customer type, size, department, etc.)"""
        groups: Dict[str, List[dict]] = defaultdict(list)

        for record in records:
            # Try to find segment info based on entity type and group_by
            if entity_type == "employee" and group_by == "department":
                segment = (
                    record.get("Department") or
                    record.get("department") or
                    record.get("DepartmentRef", {}).get("name") if isinstance(record.get("DepartmentRef"), dict) else None or
                    "general"
                )
            else:
                segment = (
                    record.get("CustomerType") or
                    record.get("customer_type") or
                    record.get("Category") or
                    record.get("Segment") or
                    "general"
                )
            groups[segment].append(record)

        return dict(groups)

    def _group_by_report_period(self, records: List[dict]) -> Dict[str, List[dict]]:
        """Group financial reports by their period"""
        groups: Dict[str, List[dict]] = defaultdict(list)

        for record in records:
            # Financial reports typically have period info
            period = (
                record.get("ReportPeriod") or
                record.get("Period") or
                record.get("Header", {}).get("ReportPeriod") or
                "current"
            )
            groups[period].append(record)

        return dict(groups)

    def _group_by_snapshot_date(self, records: List[dict]) -> Dict[str, List[dict]]:
        """Group balance sheet snapshots by date"""
        groups: Dict[str, List[dict]] = defaultdict(list)

        for record in records:
            date_str = (
                record.get("AsOfDate") or
                record.get("as_of_date") or
                record.get("Header", {}).get("DateMacro") or
                "current"
            )
            groups[date_str].append(record)

        return dict(groups)

    def _group_by_category(
        self,
        records: List[dict],
        entity_type: str,
        group_by: str = "category"
    ) -> Dict[str, List[dict]]:
        """Group by category (vendor type, item type, account type, etc.)"""
        groups: Dict[str, List[dict]] = defaultdict(list)

        for record in records:
            # Handle account type grouping specifically
            if entity_type == "account" and group_by == "account_type":
                category = (
                    record.get("AccountType") or
                    record.get("account_type") or
                    record.get("Classification") or
                    "other"
                )
            else:
                category = (
                    record.get("Type") or
                    record.get("type") or
                    record.get("Category") or
                    record.get("AccountType") or
                    "other"
                )
            groups[category].append(record)

        return dict(groups)

    def _group_report_data(
        self,
        records: List[dict],
        entity_type: str,
        group_by: str
    ) -> Dict[str, List[dict]]:
        """
        Group report data (AR/AP aging, cash flow, customer income).

        Reports typically come as single records with structured data inside.
        """
        groups: Dict[str, List[dict]] = defaultdict(list)

        for record in records:
            # For aging reports, try to extract aging bucket info
            if entity_type in ["ar_aging", "ap_aging"] and group_by == "aging_bucket":
                # Aging reports usually have the entire report in one record
                # Group by report type/date
                report_date = (
                    record.get("Header", {}).get("ReportDate") or
                    record.get("ReportDate") or
                    record.get("fetched_at", "")[:10] or
                    "current"
                )
                groups[f"aging_{report_date}"].append(record)

            elif entity_type == "cash_flow" and group_by == "period":
                # Cash flow reports grouped by period
                period = (
                    record.get("Header", {}).get("ReportPeriod") or
                    record.get("ReportPeriod") or
                    "current"
                )
                groups[period].append(record)

            elif entity_type == "customer_income" and group_by == "customer_segment":
                # Customer income report - typically one report with all customer data
                report_date = (
                    record.get("Header", {}).get("ReportDate") or
                    record.get("fetched_at", "")[:10] or
                    "current"
                )
                groups[f"customer_income_{report_date}"].append(record)

            else:
                # Default grouping
                groups["report_data"].append(record)

        return dict(groups)

    def _batch_records(self, records: List[dict], batch_size: int) -> Dict[str, List[dict]]:
        """Simple batching for unknown entity types"""
        groups = {}
        for i in range(0, len(records), batch_size):
            batch_num = i // batch_size + 1
            groups[f"batch_{batch_num}"] = records[i:i + batch_size]
        return groups

    def _pre_aggregate(self, records: List[dict], entity_type: str) -> Dict[str, Any]:
        """
        Pre-compute aggregations to help LLM focus on insights.

        These calculations are done in Python for accuracy, then passed
        to the LLM which creates natural language descriptions.
        """
        if entity_type == "invoice":
            return self._aggregate_invoices(records)
        elif entity_type == "customer":
            return self._aggregate_customers(records)
        elif entity_type in ["profit_loss", "balance_sheet"]:
            return self._aggregate_financial_report(records)
        elif entity_type == "vendor":
            return self._aggregate_vendors(records)
        elif entity_type == "bill":
            return self._aggregate_bills(records)
        elif entity_type == "payment":
            return self._aggregate_payments(records)
        elif entity_type == "item":
            return self._aggregate_items(records)
        elif entity_type == "account":
            return self._aggregate_accounts(records)
        elif entity_type == "employee":
            return self._aggregate_employees(records)
        elif entity_type == "cash_flow":
            return self._aggregate_cash_flow(records)
        elif entity_type == "ar_aging":
            return self._aggregate_ar_aging(records)
        elif entity_type == "ap_aging":
            return self._aggregate_ap_aging(records)
        elif entity_type == "customer_income":
            return self._aggregate_customer_income(records)
        else:
            return self._aggregate_generic(records)

    def _aggregate_invoices(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate invoice data"""
        total_amount = 0
        amounts = []
        customers = defaultdict(float)
        statuses = defaultdict(int)

        for r in records:
            amount = float(r.get("TotalAmt", 0) or r.get("total_amount", 0) or 0)
            total_amount += amount
            amounts.append(amount)

            # Customer tracking
            customer_ref = r.get("CustomerRef", {})
            customer_name = customer_ref.get("name") if isinstance(customer_ref, dict) else str(customer_ref)
            if customer_name:
                customers[customer_name] += amount

            # Status tracking
            balance = float(r.get("Balance", 0) or 0)
            if balance == 0:
                statuses["paid"] += 1
            elif balance < amount:
                statuses["partial"] += 1
            else:
                statuses["unpaid"] += 1

        # Top customers
        sorted_customers = sorted(customers.items(), key=lambda x: x[1], reverse=True)
        top_customers = [{"name": name, "amount": amt} for name, amt in sorted_customers[:5]]

        return {
            "total_amount": round(total_amount, 2),
            "count": len(records),
            "avg_amount": round(total_amount / len(records), 2) if records else 0,
            "min_amount": round(min(amounts), 2) if amounts else 0,
            "max_amount": round(max(amounts), 2) if amounts else 0,
            "top_customers": top_customers,
            "customer_count": len(customers),
            "status_distribution": dict(statuses),
            "date_range": self._get_date_range(records),
        }

    def _aggregate_customers(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate customer data"""
        total_balance = 0
        active_count = 0
        balances = []

        for r in records:
            balance = float(r.get("Balance", 0) or 0)
            total_balance += balance
            balances.append(balance)

            if r.get("Active", True):
                active_count += 1

        return {
            "total_customers": len(records),
            "active_count": active_count,
            "inactive_count": len(records) - active_count,
            "total_balance": round(total_balance, 2),
            "avg_balance": round(total_balance / len(records), 2) if records else 0,
            "customers_with_balance": sum(1 for b in balances if b > 0),
        }

    def _aggregate_financial_report(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate financial report data (P&L, Balance Sheet)"""
        # Financial reports are usually single records with nested data
        if not records:
            return {"note": "No records to aggregate"}

        # For financial reports, we typically pass through the structure
        # and let the LLM interpret the line items
        return {
            "report_count": len(records),
            "note": "Financial report data - see records for line items",
        }

    def _aggregate_vendors(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate vendor data"""
        total_balance = 0
        active_count = 0

        for r in records:
            balance = float(r.get("Balance", 0) or 0)
            total_balance += balance
            if r.get("Active", True):
                active_count += 1

        return {
            "total_vendors": len(records),
            "active_count": active_count,
            "total_balance_owed": round(total_balance, 2),
            "avg_balance": round(total_balance / len(records), 2) if records else 0,
        }

    def _aggregate_bills(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate bill/expense data"""
        total_amount = 0
        vendors = defaultdict(float)

        for r in records:
            amount = float(r.get("TotalAmt", 0) or r.get("Balance", 0) or 0)
            total_amount += amount

            vendor_ref = r.get("VendorRef", {})
            vendor_name = vendor_ref.get("name") if isinstance(vendor_ref, dict) else str(vendor_ref)
            if vendor_name:
                vendors[vendor_name] += amount

        sorted_vendors = sorted(vendors.items(), key=lambda x: x[1], reverse=True)
        top_vendors = [{"name": name, "amount": amt} for name, amt in sorted_vendors[:5]]

        return {
            "total_amount": round(total_amount, 2),
            "count": len(records),
            "avg_amount": round(total_amount / len(records), 2) if records else 0,
            "top_vendors": top_vendors,
            "vendor_count": len(vendors),
            "date_range": self._get_date_range(records),
        }

    def _aggregate_payments(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate payment data"""
        total_amount = 0

        for r in records:
            amount = float(r.get("TotalAmt", 0) or r.get("Amount", 0) or 0)
            total_amount += amount

        return {
            "total_amount": round(total_amount, 2),
            "count": len(records),
            "avg_amount": round(total_amount / len(records), 2) if records else 0,
            "date_range": self._get_date_range(records),
        }

    def _aggregate_items(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate item/product data"""
        types = defaultdict(int)
        active_count = 0

        for r in records:
            item_type = r.get("Type", "Other")
            types[item_type] += 1
            if r.get("Active", True):
                active_count += 1

        return {
            "total_items": len(records),
            "active_count": active_count,
            "type_distribution": dict(types),
        }

    def _aggregate_accounts(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate chart of accounts data"""
        account_types = defaultdict(int)
        classifications = defaultdict(int)
        total_balance = 0
        active_count = 0

        for r in records:
            account_type = r.get("AccountType", "Other")
            account_types[account_type] += 1

            classification = r.get("Classification", "Unknown")
            classifications[classification] += 1

            balance = float(r.get("CurrentBalance", 0) or r.get("Balance", 0) or 0)
            total_balance += balance

            if r.get("Active", True):
                active_count += 1

        return {
            "total_accounts": len(records),
            "active_count": active_count,
            "account_type_distribution": dict(account_types),
            "classification_distribution": dict(classifications),
            "total_balance": round(total_balance, 2),
        }

    def _aggregate_employees(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate employee data"""
        active_count = 0
        departments = defaultdict(int)

        for r in records:
            if r.get("Active", True):
                active_count += 1

            dept = (
                r.get("Department") or
                r.get("DepartmentRef", {}).get("name") if isinstance(r.get("DepartmentRef"), dict) else None or
                "Unassigned"
            )
            departments[dept] += 1

        return {
            "total_employees": len(records),
            "active_count": active_count,
            "inactive_count": len(records) - active_count,
            "department_distribution": dict(departments),
        }

    def _aggregate_cash_flow(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate cash flow statement data"""
        if not records:
            return {"note": "No cash flow data"}

        # Cash flow reports are typically single records with structured data
        # Extract key totals if available
        report = records[0]
        report_data = report.get("report_data", report)

        return {
            "report_count": len(records),
            "has_data": bool(report_data),
            "note": "Cash flow report - see records for detailed line items",
        }

    def _aggregate_ar_aging(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate AR aging report data"""
        if not records:
            return {"note": "No AR aging data"}

        # AR aging reports contain aging buckets
        report = records[0]
        report_data = report.get("report_data", report)

        # Try to extract summary info from the report structure
        columns = report_data.get("Columns", {}).get("Column", [])
        rows = report_data.get("Rows", {}).get("Row", [])

        return {
            "report_count": len(records),
            "has_columns": len(columns) > 0,
            "has_rows": len(rows) > 0,
            "note": "AR aging report - see records for bucket breakdown",
        }

    def _aggregate_ap_aging(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate AP aging report data"""
        if not records:
            return {"note": "No AP aging data"}

        # AP aging reports contain aging buckets
        report = records[0]
        report_data = report.get("report_data", report)

        columns = report_data.get("Columns", {}).get("Column", [])
        rows = report_data.get("Rows", {}).get("Row", [])

        return {
            "report_count": len(records),
            "has_columns": len(columns) > 0,
            "has_rows": len(rows) > 0,
            "note": "AP aging report - see records for bucket breakdown",
        }

    def _aggregate_customer_income(self, records: List[dict]) -> Dict[str, Any]:
        """Aggregate customer income report data"""
        if not records:
            return {"note": "No customer income data"}

        report = records[0]
        report_data = report.get("report_data", report)

        # Try to extract summary info
        rows = report_data.get("Rows", {}).get("Row", [])

        return {
            "report_count": len(records),
            "customer_count": len(rows) if rows else 0,
            "note": "Customer income report - see records for revenue by customer",
        }

    def _aggregate_generic(self, records: List[dict]) -> Dict[str, Any]:
        """Generic aggregation for unknown entity types"""
        return {
            "record_count": len(records),
            "sample_fields": list(records[0].keys()) if records else [],
        }

    def _get_date_range(self, records: List[dict]) -> Dict[str, Optional[str]]:
        """Get date range from records"""
        dates = []
        for r in records:
            date_str = (
                r.get("TxnDate") or
                r.get("Date") or
                r.get("MetaData", {}).get("CreateTime")
            )
            if date_str:
                dt = self._parse_date(date_str)
                if dt:
                    dates.append(dt)

        if dates:
            return {
                "start": min(dates).strftime("%Y-%m-%d"),
                "end": max(dates).strftime("%Y-%m-%d"),
            }
        return {"start": None, "end": None}

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str[:26].replace("Z", ""), fmt.replace("%z", ""))
            except ValueError:
                continue

        return None

    def denormalize(self, chunks: List[ChunkOutput], input: ChunkInput) -> List[ConnectorChunk]:
        """
        Convert ChunkOutput list to ConnectorChunk models.

        Args:
            chunks: List of ChunkOutput from chunking
            input: Original ChunkInput for IDs

        Returns:
            List of ConnectorChunk instances ready for database insertion
        """
        # Map connector type string to enum
        connector_type_map = {
            "quickbooks": ConnectorType.QUICKBOOKS,
        }
        connector_type = connector_type_map.get(
            input.connector_type.lower() if input.connector_type else "",
            ConnectorType.QUICKBOOKS
        )

        return [
            ConnectorChunk(
                tenant_id=input.tenant_id,
                company_id=input.company_id,
                connector_config_id=input.connector_config_id,
                connector_type=connector_type,
                entity_type=chunk.entity_type or input.entity_type,
                entity_id=chunk.entity_id,
                entity_name=chunk.entity_name,
                content=chunk.content,
                summary=chunk.summary,
                pillar=chunk.pillar,
                chunk_type=chunk.chunk_type or "aggregated_summary",
                confidence_score=chunk.confidence_score,
                metadata_json=chunk.metadata,
                embedding=chunk.embedding,
                data_as_of=chunk.data_as_of,
            )
            for chunk in chunks
        ]

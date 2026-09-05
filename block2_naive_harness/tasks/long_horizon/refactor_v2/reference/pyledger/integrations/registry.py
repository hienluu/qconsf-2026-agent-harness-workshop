"""Imports every integration; any broken module breaks the registry."""

from pyledger.integrations import activity
from pyledger.integrations import exporter_accounts_payable
from pyledger.integrations import exporter_accounts_receivable
from pyledger.integrations import exporter_cash
from pyledger.integrations import exporter_cost_of_goods
from pyledger.integrations import exporter_csv
from pyledger.integrations import exporter_equipment
from pyledger.integrations import exporter_inventory
from pyledger.integrations import exporter_loans_payable
from pyledger.integrations import exporter_owners_equity
from pyledger.integrations import exporter_rent_expense
from pyledger.integrations import exporter_retained_earnings
from pyledger.integrations import exporter_salaries_expense
from pyledger.integrations import exporter_sales_revenue
from pyledger.integrations import exporter_service_revenue
from pyledger.integrations import exporter_utilities_expense
from pyledger.integrations import health
from pyledger.integrations import importer
from pyledger.integrations import screening
from pyledger.integrations import statements
from pyledger.integrations import webhook

ALL_EXPORTERS = [
    exporter_accounts_payable,
    exporter_accounts_receivable,
    exporter_cash,
    exporter_cost_of_goods,
    exporter_equipment,
    exporter_inventory,
    exporter_loans_payable,
    exporter_owners_equity,
    exporter_rent_expense,
    exporter_retained_earnings,
    exporter_salaries_expense,
    exporter_sales_revenue,
    exporter_service_revenue,
    exporter_utilities_expense,
]

"""Miscellaneous report classes.
"""
import datetime
import re

from beancount.reports import report
from beancount.reports import table
from beancount.reports import gviz
from beancount.parser import printer
from beancount.parser import options
from beancount.core import data
from beancount.core import realization
from beancount.core import amount
from beancount.core import getters
from beancount.core import account_types
from beancount.ops import prices


class CommoditiesReport(report.TableReport):
    """Print out a list of commodities."""

    names = ['commodities']
    default_format = 'text'

    def generate_table(self, entries, errors, options_map):
        price_map = prices.build_price_map(entries)
        return table.create_table([(base_quote,)
                                   for base_quote in sorted(price_map.forward_pairs)],
                                  [(0, "Base/Quote", self.formatter.render_commodity)])


class CommodityPricesReport(report.TableReport):
    """Print all the prices for a particular commodity."""

    names = ['prices']
    default_format = 'text'

    @classmethod
    def add_args(cls, parser):
        parser.add_argument('-c', '--commodity', '--currency',
                            action='store', default=None,
                            help="The commodity to display.")

    def get_date_rates(self, entries):
        if not self.args.commodity:
            self.parser.error("Commodity must be specified.")
        price_map = prices.build_price_map(entries)
        try:
            date_rates = prices.get_all_prices(price_map, self.args.commodity)
        except KeyError as e:
            raise KeyError("Invalid commodity: {}".format(self.args.commodity))
        return date_rates

    def generate_table(self, entries, errors, options_map):
        date_rates = self.get_date_rates(entries)
        return table.create_table(date_rates,
                                  [(0, "Date", datetime.date.isoformat),
                                   (1, "Price", '{:.5f}'.format)])

    def render_htmldiv(self, entries, errors, options_map, file):
        date_rates = self.get_date_rates(entries)
        dates, rates = zip(*date_rates)
        scripts = gviz.gviz_timeline(dates,
                                     {'rates': rates, 'rates2': rates},
                                     css_id='chart')

        file.write('<div id="prices">\n')
        super().render_htmldiv(entries, errors, options_map, file)
        file.write('<scripts>\n')
        file.write(scripts)
        file.write('</scripts>\n')
        file.write('<div id="chart" style="height: 512px"></div>\n')
        file.write('</div>\n') # prices



class PricesReport(report.Report):
    """Print out the unnormalized price entries that we input.
    Unnormalized means that we may render both (base,quote) and (quote,base).
    This can be used to rebuild a prices database without having to share the
    entire ledger file.

    Note: this type of report should be removed once we have filtering on
    directive type, this is simply the 'print' report with type:price. Maybe
    rename the 'pricedb' report to just 'prices' for simplicity's sake.
    """

    names = ['all_prices']
    default_format = 'beancount'

    def render_beancount(self, entries, errors, options_map, file):
        price_entries = [entry
                         for entry in entries
                         if isinstance(entry, data.Price)]
        printer.print_entries(price_entries, file=file)


class PriceDBReport(report.Report):
    """Print out the normalized price entries from the price db.
    Normalized means that we print prices in the most common (base, quote) order.
    This can be used to rebuild a prices database without having to share the
    entire ledger file.

    Only the forward prices are printed; which (base, quote) pair is selected is
    selected based on the most common occurrence between (base, quote) and
    (quote, base). This is done in the price map.
    """

    names = ['pricedb', 'pricesdb', 'prices_db']
    default_format = 'beancount'

    def render_beancount(self, entries, errors, options_map, file):
        price_map = prices.build_price_map(entries)
        source = data.Source('<report_prices_db>', 0)
        for base_quote in price_map.forward_pairs:
            price_list = price_map[base_quote]
            base, quote = base_quote
            for date, price in price_list:
                entry = data.Price(source, date, base, amount.Amount(price, quote))
                file.write(printer.format_entry(entry))
            file.write('\n')


__reports__ = [
    CommoditiesReport,
    CommodityPricesReport,
    PricesReport,
    PriceDBReport,
    ]
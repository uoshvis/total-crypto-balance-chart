from krakenex.api import API
from binance.client import Client
from cryptowatch.api_client import Client as Client_cw
import plotly.graph_objs as go
import plotly.offline as py

import config


class TotalBalanceClient(object):

    KRAKEN_SYMBOL_DICT = {
        'BCH': 'BCH',
        'DASH': 'DASH',
        'XETH': 'ETH',
        'XREP': 'REP',
        'XXBT': 'BTC',
        'XXMR': 'XMR',
        'XXRP': 'XRP',
        'ZEUR': 'EUR'
    }

    def __init__(self):
        # init cryptowatch client
        self.client_cw = Client_cw()

    def _match_name(self, pair):
        return self.KRAKEN_SYMBOL_DICT.get(pair, pair)

    def _unify_kraken_name(self, asset):
        if asset in self.KRAKEN_SYMBOL_DICT:
            return self.KRAKEN_SYMBOL_DICT[asset]
        else:
            raise ValueError('Kraken has a new asset')

    def get_binance_balance(self, api_key, api_secret):
        """
        :returns: binace balance

        .. code-block:: python

            {
              'TRX': {
                'price_BTC': 0.000001,
                'value_BTC': 0.00001,
                'free': 10
              },
              'NEO': {
                'price_BTC': 0.000001,
                'value_BTC': 0.00001,
                'free': 10
              },
              'OMG': {
                'price_BTC': 0.000001,
                'value_BTC': 0.00001,
                'free': 10
              },
              'BTC': {
                'free': 0.002
              }
            }

        """

        client = Client(api_key, api_secret)

        # Get account information
        account = client.get_account()

        # Filter zero balances
        my_balance = {}
        for balance in account['balances']:
            if float(balance['free']) > 0:
                my_balance[balance['asset']] = {'free': float(balance['free'])}

        # Get current prices
        prices = client.get_all_tickers()

        # Filter only BTC prices by account assets and calculate total value
        for price in prices:
            symbol = price['symbol']
            if symbol[-3:] == 'BTC' and symbol[:-3] in my_balance.keys():
                my_asset = my_balance[symbol[:-3]]
                my_asset['price_BTC'] = float(price['price'])
                my_asset['value_BTC'] = (float(price['price']) * my_asset['free'])
        return my_balance

    def get_kraken_balance(self, api_key, private_key):
        """
        :returns: kraken balance

        .. code-block:: python

            {
              'TRX': {
                'price_BTC': 0.000001,
                'value_BTC': 0.00001,
                'free': 10
              },
              'NEO': {
                'price_BTC': 0.000001,
                'value_BTC': 0.00001,
                'free': 10
              },
              'OMG': {
                'price_BTC': 0.000001,
                'value_BTC': 0.00001,
                'free': 10
              },
              'BTC': {
                'free': 0.002
              }
            }

        """

        client = API(key=api_key, secret=private_key)
        balance = client.query_private('Balance', data=None)['result']
        my_balance = {}

        for asset, amount in balance.items():
            if float(amount) > 0.0:
                asset = self._unify_kraken_name(asset)
                if asset not in ['EUR', 'BTC']:
                    pair = asset.lower() + 'btc'
                    data = {'exchange': 'kraken', 'pair': pair, 'route': 'price'}
                    last_trade = self.client_cw.get_markets(data=data)['result']['price']
                    my_balance[asset] = {}
                    my_balance[asset]['price_BTC'] = float(last_trade)
                    my_balance[asset]['free'] = float(amount)
                    my_balance[asset]['value_BTC'] = float(last_trade) * float(amount)
                if asset == 'BTC':
                    my_balance[asset] = {'free': float(amount)}

        return my_balance

    def sum_balances(self, balance_binance, balance_kraken):
        for k, v in balance_kraken.items():
            if k == 'BTC' and k in balance_binance:
                balance_binance[k]['free'] += balance_kraken[k]['free']
            elif k in balance_binance:
                balance_binance[k]['value_BTC'] += balance_kraken[k]['value_BTC']
                balance_binance[k]['free'] += balance_kraken[k]['free']
            else:
                balance_binance[k] = {
                    'price_BTC': balance_kraken[k]['price_BTC'],
                    'value_BTC': balance_kraken[k]['value_BTC'],
                    'free': balance_kraken[k]['free']
                }

        return balance_binance

    def extract_labels_values(self, total_dict):
        labels = []
        values = []
        for k, v in total_dict.items():
            if k == 'BTC':
                labels.append(k)
                values.append(v['free'])
            elif 'value_BTC' in v:
                labels.append(k)
                values.append(v['value_BTC'])
            else:
                print('Skipping because does not have price values: ', k)

        return (labels, values)

    def add_wallet_balance(self, my_balance):
        """Add wallet data from config file
            wallet = {
                'symbol_1': amount,
                'symbol_2': amount
            }
        """
        for symbol, amount in config.wallet.items():
            if symbol == 'BTC':
                my_balance[symbol]['free'] += amount
            elif symbol in my_balance.keys():
                my_balance[symbol]['free'] += amount
                my_balance[symbol]['value_BTC'] += amount * my_balance[symbol]['price_BTC']
            elif symbol in self.KRAKEN_SYMBOL_DICT.values():
                pair = symbol.lower() + 'btc'
                data = {'exchange': 'kraken', 'pair': pair, 'route': 'price'}
                last_trade = self.client_cw.get_markets(data=data)['result']['price']
                my_balance[symbol] = {
                    'price_BTC': last_trade,
                    'value_BTC': amount * last_trade,
                    'free': amount
                }
            else:
                raise ValueError('New asset in your wallet')

        return my_balance

    def plot_pie(self, values, labels, name=''):
        total_BTC = sum(values)
        title = 'Estimated value: ' + str(total_BTC) + ' BTC'
        filename = name + '_chart.html'
        layout = go.Layout(title=title)
        trace = go.Pie(labels=labels, values=values)
        fig = go.Figure(data=[trace], layout=layout)
        py.plot(fig, filename=filename)


def main():
    client = TotalBalanceClient()
    balance_binance = client.get_binance_balance(
        config.api_key_binance,
        config.private_key_binance
    )
    balance_kraken = client.get_kraken_balance(
        config.api_key_kraken,
        config.private_key_kraken
    )

    total_balance = client.sum_balances(balance_binance, balance_kraken)

    total_balance = client.add_wallet_balance(total_balance)

    labels, values = client.extract_labels_values(total_balance)

    client.plot_pie(
        values=values, labels=labels, name='totalBalance'
    )


if __name__ == '__main__':
    main()

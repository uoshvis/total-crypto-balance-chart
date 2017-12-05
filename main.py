from krakenex.api import API
from binance.client import Client
from time import sleep
import plotly.graph_objs as go
import plotly.offline as py

import config


class TotalBalanceClient(object):

    KRAKEN_SYMBOL_DICT = {
        'XREP': 'REP',
        'XETH': 'ETH',
        'XXMR': 'XMR'
    }

    def __init__(self):
        pass

    def get_binance_balance(self, api_key, api_secret):

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
            if symbol[-3:] == 'BTC' and symbol[:-3] in list(my_balance.keys()):
                my_asset = my_balance[symbol[:-3]]
                my_asset['price'] = price['price']
                my_asset['value_BTC'] = (float(price['price']) * my_asset['free'])

        return my_balance

    def get_kraken_balance(self, api_key, private_key):

        client = API(key=api_key, secret=private_key)
        balance = client.query_private('Balance', data=None)['result']

        # Remove zero values
        balance = {k: v for k, v in balance.items() if float(v) > 0.0}

        # List alt coin symbols
        my_assets = list(balance.keys())
        base_assets = ['ZEUR', 'XXBT']
        alt_coins = list(set(my_assets) - set(base_assets))

        # Create altcoin + XBT pair symbol
        pairs = [p + 'XXBT' if p[0] == 'X' else p + 'XBT' for p in alt_coins]

        # Does not retrieve multiple pairs
        # tickers = client.query_public('Ticker', data={'pair': pairs})

        # Get ticker information
        my_balance = {}

        for pair in pairs:
            print('Getting ', pair)
            ticker = client.query_public('Ticker', data={'pair': pair})
            last_trade = ticker['result'][pair]['c'][0]
            asset_name = self._remove_pair(pair)
            asset_name_matched = self._match_name(asset_name)
            my_balance[asset_name_matched] = {}
            my_balance[asset_name_matched]['price'] = last_trade
            my_balance[asset_name_matched]['free'] = float(balance[asset_name])
            my_balance[asset_name_matched]['value_BTC'] = float(last_trade) * float(balance[asset_name])
            print('Got ', pair)
            sleep(1.5)

        # Also add XBT label and value
        my_balance['BTC'] = {'free': float(balance['XXBT'])}

        return my_balance

    def sum_balances(self, balance_binance, balance_kraken):

        for k, v in balance_kraken.items():
            if k == 'BTC' and k in balance_binance:
                balance_binance[k]['free'] += balance_kraken[k]['free']
            elif k in balance_binance:
                balance_binance[k]['value_BTC'] += balance_kraken[k]['value_BTC']
            else:
                balance_binance[k] = {}
                balance_binance[k]['value_BTC'] = balance_kraken[k]['value_BTC']

        return balance_binance

    def extract_labels_values(self, total_dict):

        labels = []
        values = []
        for k, v in total_dict.items():
            if k == 'BTC':
                labels.append(k)
                values.append(v['free'])
            else:
                labels.append(k)
                values.append(v['value_BTC'])

        return (labels, values)

    def plot_pie(self, values, labels, name=''):

        total_BTC = sum(values)
        title = 'Estimated value: ' + str(total_BTC) + ' BTC'
        filename = name + '_chart.html'
        layout = go.Layout(title=title)
        trace = go.Pie(labels=labels, values=values)
        fig = go.Figure(data=[trace], layout=layout)
        py.plot(fig, filename=filename)

    def _remove_pair(self, pair):

        """Remove XBT pair ending.
        :param pair: pair name
        :type pair: str
        :returs: symbol without pair ending

        """
        if pair[0] == 'X':
            pair = pair[:-4]
        else:
            pair = pair[:-3]
        return pair

    def _match_name(self, pair):
        if pair in self.KRAKEN_SYMBOL_DICT:
            return self.KRAKEN_SYMBOL_DICT[pair]
        else:
            return pair

    def add_wallet_balance(self, my_balance):
        '''Add wallet data from config file
            wallet = {
                'symbol_1': amount,
                'symbol_2': amount
            }
        '''
        for k, v in config.wallet.items():
            if k in list(my_balance.keys()):
                my_balance[k]['free'] = my_balance[k]['free'] + v
            else:
                my_balance[k] = {}
                my_balance[k]['free'] = v
        return my_balance


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

    labels, values = client.extract_labels_values(total_balance)

    client.plot_pie(
        values=values, labels=labels, name='totalBalance'
    )


if __name__ == '__main__':
    main()

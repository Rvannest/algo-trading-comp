import requests
import signal
from time import sleep
import sys

class MarketData:
    def __init__(self, session):
        self.session = session

    def get_tick(self):
        # example
        resp = self.session.get('http://localhost:9999/v1/case')
        if resp.ok:
            case = resp.json()
            return case['tick']
        raise ApiException('Authorization error. Please check API key.')

    def ticker_bid_ask(self, ticker):
        payload = {'ticker': ticker}
        resp = self.session.get('http://localhost:9999/v1/securities/book', params=payload)
        if resp.ok:
            book = resp. json()
            return book['bids'][0]['price'], book['asks'][0]['price']
        raise ApiException('Authorization error. Please check API key.')

    def open_sells(self, sym):
        resp = self.session.get('http://localhost:9999/v1/orders?status=OPEN')
        if resp.ok:
            open_sells_volume = 0 # total combined volume of all open sells
            ids = []
            prices = []
            order_volumes = []
            volume_filled = []
            open_orders = resp.json()
            for order in open_orders:
                if order['action'] == 'SELL' and order['ticker'] == sym:
                    volume_filled.append(order['quantity_filled'])
                    order_volumes.append(order['quantity'])
                    open_sells_volume = open_sells_volume + order['quantity']
                    prices.append(order['price'])
                    ids.append(order['order_id'])
        return volume_filled, open_sells_volume, ids, prices, order_volumes

    def open_buys(self, sym):
        resp = self.session.get('http://localhost:9999/v1/orders?status=OPEN')
        if resp.ok:
            open_buys_volume = 0
            ids = []
            prices = []
            order_volumes = []
            volume_filled = []
            open_orders = resp.json()
            for order in open_orders:
                if order['action'] == 'BUY' and order['ticker'] == sym:
                    open_buys_volume = open_buys_volume + order['quantity']
                    volume_filled.append(order['quantity_filled'])
                    order_volumes.append(order['quantity'])
                    prices.append(order['price'])
                    ids.append(order['order_id'])
        return volume_filled, open_buys_volume, ids, prices, order_volumes




class OrderManagement:
    #this class can use MarketData to make decisions based on current market conditions such as fething the latest bid/ask prices to decide order placement
    def __init__(self, session, market_data):
        self.session = session
        self.market_data = market_data

    def buy_sell(self, sell_price, buy_price, sym):
        for i in range (MAX_ORDERS):
            self.session.post('http://localhost:9999/v1/orders', params = {'ticker': sym, 'type': 'LIMIT', 'quantity': MAX_VOLUME[sym], 'price': sell_price, 'action': 'SELL'})
            self.session.post('http://localhost:9999/v1/orders', params = {'ticker': sym, 'type': 'LIMIT', 'quantity': MAX_VOLUME[sym], 'price': buy_price, 'action': 'BUY'})

    def re_order(self, number_of_orders, ids, volumes_filled, volumes, price, action, sym):
        for i in range(number_of_orders):
            id = ids[i]
            volume = volumes[i]
            volume_filled = volumes_filled[i]
            
            if (volume_filled != 0):
                volume = MAX_VOLUME[sym] - volume_filled
            
            deleted = self.session.delete('http://localhost:9999/v1/orders/{}'.format(id))
            if (deleted.ok):
                self.session.post('http://localhost:9999/v1/orders', params = {'ticker': sym, "type": 'LIMIT', 'quantity': volume, 'price': price, 'action': action})




class MarketMaker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'X-API-Key': 'K4P0T6H7'})
        self.market_data = MarketData(self.session)
        self.order_management = OrderManagement(self.session, self.market_data)
        self.shutdown = False

    def signal_handler(self, signum, frame):
        self.shutdown = True

    def run(self):
        # orchestrates the trading process, utilizing the functionalities provided by MarketData and OrderManagement to implement the trading logic.
        pass




if __name__ == '__main__':
    market_maker = MarketMaker()
    signal.signal(signal.SIGINT, market_maker.signal_handler)
    market_maker.run()
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
        self.SPEEDBUMP = 0.01
        self.MAX_VOLUME = {'HAWK': 2000, 'DOVE': 2000}
        self.MAX_ORDERS = 5
        self.SPREAD = 0.04
        self.market_data = MarketData(self.session)
        self.order_management = OrderManagement(self.session, self.market_data)
        self.shutdown = False

    def signal_handler(self, signum, frame):
        self.shutdown = True

    def run(self):
        # orchestrates the trading process, utilizing the functionalities provided by MarketData and OrderManagement to implement the trading logic.
        tick = self.market_data.get_tick()

        while tick > 0 and tick < 299 and not shutdown:
            for sym in ['HAWK', 'DOVE']:
                volume_filled_sells, open_sells_volume, sell_ids, sell_prices, sell_volumes = open_sells(s, sym)
                #return volume_filled, open_sells_volume, ids, prices, order_volumes
                volume_filled_buys, open_buys_volume, buy_ids, buy_prices, buy_volumes = open_buys(s, sym)
                bid_price, ask_price = ticker_bid_ask(s, sym)

                # Initiate a buy and sell order on each side of the order book when there are no open orders detected
                if(open_sells_volume == 0) and (open_buys_volume == 0):
                    single_side_filled[sym] = False
                    bid_ask_spread = ask_price - bid_price
                    sell_price = ask_price
                    buy_price = bid_price
                    if(bid_ask_spread >= SPREAD):
                        buy_sell(s, sell_price, buy_price, sym)
                        #sleep(SPEEDBUMP)
                
                # else, there are open orders in the order book
                else:
                    # if there are open sell orders, set the price to the lowest ask price
                    if len(sell_prices) > 0:
                        sell_price = sell_prices[0]
                    # if there are open buy orders, set the price to the highest bid price
                    if len(buy_prices) > 0:
                        buy_price = buy_prices[0]
                    
                    # Handles partial fills on one side of the order book
                    # This condition is met when one side of the order book is entirely filled
                    # Records the tick time of this occurrence
                    if (not single_side_filled[sym] and (open_buys_volume == 0 or open_sells_volume == 0)):
                        single_side_filled[sym] = True
                        single_side_transaction_time[sym] = tick
                    
                    # If there are no open sell orders, the algo checks if the current buy price is equal to the market's bid price
                    # Set the current buy price of those orders to the current bid price
                    if (open_sells_volume == 0):
                        if (buy_price == bid_price):
                            continue
                        
                        # The current buy price is not equal to the bid price, it has been 2 ticks since 1 side of the order book was completely filled
                        # Set and update the BUY parameters, then initiate the re-order.
                        elif(tick - single_side_transaction_time[sym] >= 2):
                            next_buy_price = bid_price + .02
                            potential_profit = sell_price - next_buy_price - .02
                            
                            # If potential profit is greater than 2 cents, then initiate a BUY re-order
                            if(potential_profit >= .02 or tick - single_side_transaction_time[sym] >= 2):
                                action = 'BUY'
                                number_of_orders = len(buy_ids)
                                buy_price = bid_price + .02
                                price = buy_price
                                ids = buy_ids
                                volumes = buy_volumes
                                volumes_filled = volume_filled_buys
                                re_order(s, number_of_orders, ids, volumes_filled, volumes, price, action, sym)
                                #sleep (SPEEDBUMP)

                    # If there was open sell orders, then check to see if there are no open buy orders instead
                    # Set current sell price of those orders to the current ask price
                    elif(open_buys_volume == 0):
                        if (sell_price == ask_price):
                            continue # next iteration of 100p
                        
                        # The current sell price is not equal to the ask price, it has been 2 ticks since 1 side of the order book was completely filled
                        # Set and update the SELL parameters, then initiate the re-order
                        elif(tick - single_side_transaction_time[sym] >= 2):
                            next_sell_price = ask_price - .02
                            potential_profit = next_sell_price - buy_price - .02
                            
                            # If potential profit is greater than 2 cents, then initiate a SELL re-order
                            if(potential_profit >= .02 or tick - single_side_transaction_time[sym] >= 2):
                                action = 'SELL'
                                number_of_orders = len(sell_ids)
                                sell_price = ask_price - .02
                                price = sell_price
                                ids = sell_ids
                                volumes = sell_volumes
                                volumes_filled = volume_filled_sells
                                re_order(s, number_of_orders, ids, volumes_filled, volumes, price, action, sym)
                                #sleep (SPEEDBUMP)
            tick = get_tick(s)



if __name__ == '__main__':
    market_maker = MarketMaker()
    signal.signal(signal.SIGINT, market_maker.signal_handler)
    market_maker.run()
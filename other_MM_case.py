import requests
import signal
from time import sleep
import sys

class ApiException (Exception):
    pass

def signal_handler (signum, frame):
    global shutdown
    signal. signal(signal.SIGINT, signal.SIGDFL)
    shutdown = True

API_KEY = {'X-API-Key': 'K4P0T6H7'}
shutdown = False


SPEEDBUMP = 0.1
MAX_VOLUME = {'HAWK': 10000, 'DOVE': 10000, 'RIT_C': 10000, 'RITC_U': 10000}

MAX_ORDERS = 5

SPREAD = .08


# Fetches the current tick (or time) of the case.
def get_tick(session):
    resp = session.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick']
    raise ApiException('Authorization error. Please check API key.')


# Retrieves the current best bid and ask prices for a given ticker.
def ticker_bid_ask(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp. json()
        return book['bids'][0]['price'], book['asks'][0]['price']
    raise ApiException('Authorization error. Please check API key.')


# Retrieves the current best bid and ask prices for a given ticker.
def open_sells(session, sym):
    resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
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
    #returns how much volume has been filled for sell orders, total volume of open sell orders, list of order IDs for the open sell order, prices of open sell orders, volume of the open sell order
    return volume_filled, open_sells_volume, ids, prices, order_volumes


# Retrieves the current best bid and ask prices for a given ticker.
def open_buys(session, sym):
    resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
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
    # returns how much volume has been filed for buy orders, total volume of open buy orders, a list of order IDs for the open buy orders, prices of the open buy orders, volumes of the open buy orders
    return volume_filled, open_buys_volume, ids, prices, order_volumes


# Places buy and sell orders at specified prices.
def buy_sell(session, sell_price, buy_price, sym):
    for i in range (MAX_ORDERS):
        session.post('http://localhost:9999/v1/orders', params = {'ticker': sym, 'type': 'LIMIT', 'quantity': MAX_VOLUME[sym], 'price': sell_price, 'action': 'SELL'})
        session.post('http://localhost:9999/v1/orders', params = {'ticker': sym, 'type': 'LIMIT', 'quantity': MAX_VOLUME[sym], 'price': buy_price, 'action': 'BUY'})

# Cancels and replaces orders based on the fill status and market conditions.
def re_order(session, number_of_orders, ids, volumes_filled, volumes, price, action, sym):
    for i in range(number_of_orders):
        id = ids[i]
        volume = volumes[i]
        volume_filled = volumes_filled[i]
        
        if (volume_filled != 0):
            volume = MAX_VOLUME[sym] - volume_filled
        
        deleted = session.delete('http://localhost:9999/v1/orders/{}'.format(id))
        if (deleted.ok):
            session.post('http://localhost:9999/v1/orders', params = {'ticker': sym, "type": 'LIMIT', 'quantity': volume, 'price': price, 'action': action})


# the algorithm enters a loop where it checks for opportunities to place new orders or adjust existing ones based on the market conditions and its own order status.
def main():
    single_side_transaction_time = {'HAWK': 0, 'DOVE': 0, 'RIT_C': 0}
    # dictionary that tracks whether a single side of MM transaction has been filled for each symbol
    single_side_filled = {'HAWK': False, 'DOVE': False, 'RIT_C': False}

    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)

        while tick > 0 and tick < 295 and not shutdown:
            for sym in ['HAWK', 'DOVE', 'RIT_C']:
                # see respective functions to understand the functionality
                volume_filled_sells, open_sells_volume, sell_ids, sell_prices, sell_volumes = open_sells(s, sym)
                volume_filled_buys, open_buys_volume, buy_ids, buy_prices, buy_volumes = open_buys(s, sym)
                bid_price, ask_price = ticker_bid_ask(s, sym)

                # if there is now open order for the current security
                if(open_sells_volume == 0 and open_buys_volume == 0):
                    # set flag to false if no open orders "This flag is likely used elsewhere in the algorithm to track whether there has been a partial fill (either a buy or sell, but not both)."
                    single_side_filled[sym] = False
                    bid_ask_spread = ask_price - bid_price
                    # sell at the current ask
                    sell_price = ask_price
                    # buy at the current bid
                    buy_price = bid_price
                    if(bid_ask_spread >= SPREAD):
                        # execute trade
                        buy_sell(s, sell_price, buy_price, sym)
                        sleep(SPEEDBUMP)

                # else, when there is an open order for the current security
                else:
                    # check if there is any sell price info from the current open order
                    if len(sell_prices) > 0:
                        # sets sell price to the first sell price order (lowest sell)
                        sell_price = sell_prices[0]
                    # check if there is any buy price info from the current open order
                    if len(buy_prices) > 0:
                        # sets buy price to the first buy price order (highest buy)
                        buy_price = buy_prices[0]
                    
                    # if a single side of the order has been filled for the current security
                    if (not single_side_filled[sym] and (open_buys_volume == 0 or open_sells_volume == 0)):
                        single_side_filled[sym] = True
                        single_side_transaction_time[sym] = tick

                    # if there is no open sell orders
                    if (open_sells_volume == 0):
                        # if the best buy price from the open orders is equal to the best bid price in the market, then continue
                        if (buy_price == bid_price):
                            continue
                    
                        # enter elif if NO continue. If at least 3 ticks have passed since a single side of an order was filled
                        elif(tick - single_side_transaction_time[sym] >= 2):
                            # best current bid price + 1 cent higher
                            next_buy_price = bid_price + .01
                            # potential profit if it buys 1 cent over the current bid and sell at the current ask minus a transaction cost of 2 cents
                            potential_profit = sell_price - next_buy_price - .02
                            # if potential profit is at least 1 cent, or if at least 6 ticks have passed since a single side of an order was filled
                            if(potential_profit >= .01 or tick - single_side_transaction_time[sym] >= 3):
                                #buy at the current bid
                                action = 'BUY'
                                number_of_orders = len(buy_ids)
                                buy_price = bid_price + .01
                                price = buy_price
                                ids = buy_ids
                                volumes = buy_volumes
                                volumes_filled = volume_filled_buys
                                re_order(s, number_of_orders, ids, volumes_filled, volumes, price, action, sym)
                                sleep (SPEEDBUMP)

                    elif(open_buys_volume == 0):
                        if (sell_price == ask_price):
                            continue # next iteration of 100p

                        elif(tick - single_side_transaction_time[sym] >= 2):
                            next_sell_price = ask_price - .01
                            potential_profit = next_sell_price - buy_price - .02
                            if(potential_profit >= .01 or tick - single_side_transaction_time[sym] >= 3):
                                action = 'SELL'
                                number_of_orders = len(sell_ids)
                                sell_price = ask_price - .01
                                price = sell_price
                                ids = sell_ids
                                volumes = sell_volumes
                                volumes_filled = volume_filled_sells
                                re_order(s, number_of_orders, ids, volumes_filled, volumes, price, action, sym)
                                sleep (SPEEDBUMP)
            tick = get_tick(s)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()
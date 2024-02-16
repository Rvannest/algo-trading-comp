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


SPEEDBUMP = 0.001
MAX_VOLUME = {'HAWK': 2000, 'DOVE': 2000}

MAX_ORDERS = 1

SPREAD = .08


#profits = {'HAWK': 0, 'DOVE': 0}



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



def ticker_bid_ask_with_liquidity(session, ticker):
    # Fetches all securities data
    resp = session.get('http://localhost:9999/v1/securities')
    if resp.ok:
        securities = resp.json()
        # Find the security that matches the provided ticker
        for security in securities:
            if security['ticker'] == ticker:
                # Extract the bid and ask prices and sizes
                #bid_price = security['bid']
                #ask_price = security['ask']
                bid_size = security['bid_size']
                ask_size = security['ask_size']
                return bid_size, ask_size
        # If the ticker was not found in the list of securities
        raise ApiException(f'Ticker {ticker} not found.')
    else:
        raise ApiException('Authorization error. Please check API key.')




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


# # Places buy and sell orders at specified prices.
# def buy_sell(session, sell_price, buy_price, sym):
#     for i in range (MAX_ORDERS):
#         session.post('http://localhost:9999/v1/orders', params = {'ticker': sym, 'type': 'LIMIT', 'quantity': MAX_VOLUME[sym], 'price': sell_price, 'action': 'SELL'})
#         session.post('http://localhost:9999/v1/orders', params = {'ticker': sym, 'type': 'LIMIT', 'quantity': MAX_VOLUME[sym], 'price': buy_price, 'action': 'BUY'})


# Global dictionary to track order placement times
order_placement_times = {}

def buy_sell(session, sell_price, buy_price, sym, current_tick):
    for i in range(MAX_ORDERS):
        # Place sell order
        sell_response = session.post('http://localhost:9999/v1/orders', params={'ticker': sym, 'type': 'LIMIT', 'quantity': MAX_VOLUME[sym], 'price': sell_price, 'action': 'SELL'})
        if sell_response.ok:
            sell_order_id = sell_response.json()['order_id']
            order_placement_times[sell_order_id] = current_tick

        # Place buy order
        buy_response = session.post('http://localhost:9999/v1/orders', params={'ticker': sym, 'type': 'LIMIT', 'quantity': MAX_VOLUME[sym], 'price': buy_price, 'action': 'BUY'})
        if buy_response.ok:
            buy_order_id = buy_response.json()['order_id']
            order_placement_times[buy_order_id] = current_tick




# def cancel_old_orders(session, current_tick):
#     # Fetch all open orders
#     resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
#     if resp.ok:
#         open_orders = resp.json()
#         for order in open_orders:
#             order_id = order['order_id']
#             if order_id in order_placement_times:
#                 # Check if the order has been open for more than 10 ticks
#                 if current_tick - order_placement_times[order_id] > 100:
#                     # Cancel the order
#                     session.delete(f'http://localhost:9999/v1/orders/{order_id}')
#                     #print(f"Cancelled order {order_id} that was open for more than 2 ticks.")
#                     # Remove the order from the tracking dictionary
#                     del order_placement_times[order_id]

def cancel_old_orders(session, current_tick, symbols):
    for sym in symbols:
        # Fetch current top bid and ask to determine competitiveness
        _, _, _, _, top_bid_id, top_ask_id = ticker_bid_ask_with_liquidity(session, sym)

        # Fetch all open orders
        resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
        if resp.ok:
            open_orders = resp.json()
            for order in open_orders:
                order_id = order['order_id']
                if order['ticker'] == sym and order_id in order_placement_times:
                    # Check for competitiveness or if the order has been open too long
                    too_old = current_tick - order_placement_times[order_id] > 5
                    not_top = (order['action'] == 'SELL' and order_id != top_ask_id) or \
                              (order['action'] == 'BUY' and order_id != top_bid_id)
                    
                    if too_old or not_top:
                        # Cancel the order
                        session.delete(f'http://localhost:9999/v1/orders/{order_id}')
                        print(f"Cancelled order {order_id} due to {'age' if too_old else 'position'}.")
                        # Remove the order from the tracking dictionary
                        del order_placement_times[order_id]






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




# # Function to fetch filled orders and update profit
# def update_profit(session, sym):
#     resp = session.get('http://localhost:9999/v1/orders?status=FILLED')
#     if resp.ok:
#         filled_orders = resp.json()
#         for order in filled_orders:
#             if order['ticker'] == sym:
#                 # Assuming 'price' is the fill price and 'quantity_filled' is the quantity filled
#                 fill_price = order['price']
#                 quantity_filled = order['quantity_filled']
#                 action = order['action']
                
#                 # If it's a buy order, we subtract the cost, and if it's a sell order, we add the profit
#                 if action == 'BUY':
#                     # Update profit by subtracting cost (buy price + transaction cost)
#                     profits[sym] -= fill_price * quantity_filled + 0.02 * quantity_filled
#                 elif action == 'SELL':
#                     # Update profit by adding revenue (sell price - transaction cost)
#                     profits[sym] += fill_price * quantity_filled - 0.02 * quantity_filled




# the algorithm enters a loop where it checks for opportunities to place new orders or adjust existing ones based on the market conditions and its own order status.
def main():
    single_side_transaction_time = {'HAWK': 0, 'DOVE': 0}
    # dictionary that tracks whether a single side of MM transaction has been filled for each symbol
    single_side_filled = {'HAWK': False, 'DOVE': False}

    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)

        while tick > 0 and tick < 295 and not shutdown:
            cancel_old_orders(s, tick, ['HAWK', 'DOVE'])
            for sym in ['HAWK', 'DOVE']:
                # see respective functions to understand the functionality
                volume_filled_sells, open_sells_volume, sell_ids, sell_prices, sell_volumes = open_sells(s, sym)
                volume_filled_buys, open_buys_volume, buy_ids, buy_prices, buy_volumes = open_buys(s, sym)
                bid_price, ask_price = ticker_bid_ask(s, sym)

                # if there is no open order for the current security
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
                        buy_sell(s, sell_price, buy_price, sym, tick)
                        sleep(SPEEDBUMP)

                # else, when there IS an open order for the current security
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
                        elif(tick - single_side_transaction_time[sym] >= 1):
                            # best current bid price + 1 cent higher
                            next_buy_price = bid_price + .01
                            # potential profit if it buys 1 cent over the current bid and sell at the current ask minus a transaction cost of 2 cents
                            potential_profit = sell_price - next_buy_price - .02
                            
                            # if potential profit is at least 1 cent, or if at least 2 ticks have passed since a single side of an order was filled
                            if(potential_profit >= .04 or tick - single_side_transaction_time[sym] >= 1):
                                print(potential_profit, "Potential Profit for Buys\n")
                                #print(tick - single_side_transaction_time[sym], " (Buys) 2 ticks have passed with a single side order\n")
                                #buy at the current bid
                                action = 'BUY'
                                number_of_orders = len(buy_ids)
                                buy_price = bid_price + .02
                                price = buy_price
                                ids = buy_ids
                                volumes = buy_volumes
                                volumes_filled = volume_filled_buys
                                re_order(s, number_of_orders, ids, volumes_filled, volumes, price, action, sym)
                                sleep (SPEEDBUMP)

                    elif(open_buys_volume == 0):
                        if (sell_price == ask_price):
                            continue # next iteration of 100p

                        elif(tick - single_side_transaction_time[sym] >= 1):
                            next_sell_price = ask_price - .01
                            potential_profit = next_sell_price - buy_price - .02
                            
                            if(potential_profit >= .04 or tick - single_side_transaction_time[sym] >= 1):
                                print(potential_profit, "Potential Profit for Sells\n")
                                #print(tick - single_side_transaction_time[sym], " (Sells) 2 ticks have passed with a single side order\n")

                                action = 'SELL'
                                number_of_orders = len(sell_ids)
                                sell_price = ask_price - .02
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
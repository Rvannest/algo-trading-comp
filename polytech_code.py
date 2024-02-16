#from Starter_code import api_get, api_delete, api_post
import requests
import json
from time import sleep
import numpy as np
import sys
import signal
import requests

class ApiException(Exception):
    pass

# handles shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True

# set API key to authenticate to the RIT client
API_KEY = {'X-API-key': 'K4P0T6H7'}
shutdown = False

# SETTINGS
SPEEDBUMP = 0.5
MAX_VOLUME = 5000
MAX_ORDERS = 5
SPREAD = 0.5

# returns the current 'tick' of the running case
def get_tick(session):
    resp = session.get('http://localhost:9999/v1/case')
    if resp.ok():
        case = resp.json()
        return case['tick']
    raise ApiException('Authorization error Please check API key.')

# returns bid and ask first row for a given sec
def ticker_bid_ask(sessions, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['price'], book['asks'][0]['price']
    raise ApiException('Authorization error Please Check API Key')

def ticker_bid(sessions, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['price']
    raise ApiException('Authorization error Please Check API Key')

def ticker_ask(sessions, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['asks'][0]['price']
    raise ApiException('Authorization error Please Check API Key')

# returns info about all open sell orders
def open_sells(session):
    resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
    if resp.ok:
        open_sells_volume = 0
        ids = []
        prices = []
        order_volumes = []
        volume_filled = []

        open_orders = resp.json()
        for order in open_orders:
            if order['action'] == 'SELL':
                volume_filled.append(order['quantity_filled'])
                order_volumes.append(order['quantity'])
                open_sells_volume = open_sells_volume + order['quantity']
                prices.append(order['price'])
                ids.append(order['order_id'])
    return volume_filled, open_sells_volume, ids, prices, order_volumes

# returns info about all open buy orders
def open_buys(session):
    resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
    if resp.ok:
        open_buys_volume = 0
        ids = []
        prices = []
        order_volumes = []
        volume_filled = []

        open_orders = resp.json()
        for order in open_orders:
            if order['action'] == 'BUY':
                volume_filled.append(order['quantity_filled'])
                order_volumes.append(order['quantity'])
                open_buys_volume = open_buys_volume + order['quantity']
                prices.append(order['price'])
                ids.append(order['order_id'])
    return volume_filled, open_buys_volume, ids, prices, order_volumes

# buys and sells maximum number of shares
def buy_sell(session, sell_price, buy_price):
    for i in range(MAX_ORDERS):
        session.post('http://localhost:9999/v1/orders', params = {'ticker': sym,
        'type': 'LIMIT', 'quantity': MAX_VOLUME, 'price': sell_price, 'action': 'SELL'})
        session.post('http://localhost:9999/v1/orders', params = {'ticker': sym,
        'type': 'LIMIT', 'quantity': MAX_VOLUME, 'price': buy_price, 'action': 'BUY'})

# buys/sells a specified quantity of shares of a specified ticker
def submit_order(session, ticker, type_, quantity, action, price):
    if type_ == 'MARKET':
        mkt_params = {'ticker': ticker, 'type': type_, 'quantity': quantity, 'action': action}
        resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
        if resp.ok:
            mkt_order = resp.json()
            id = mkt_order['order_id']
            print(f'The market {action} order was submitted and has ID: {id}')
            return id
        else:
            print('The order was not successfully submitted!')
            return None
    elif type_ == 'LIMIT':
        mkt_params = {'ticker': ticker, 'type': type_, 'quantity': quantity, 'price': price, 'action': action}
        resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
        if resp.ok:
            mkt_order = resp.json()
            id = mkt_order['order_id']
            print(f'The limit {action} order was submitted and has ID: {id}')
            return id
        else:
            print('The order was not successfully submitted!')
            return None

def delete_order(session, order_id):
    resp = session.delete('http://localhost:9999/v1/orders/{}'.format(order_id))
    if resp.ok:
        status = resp.json()
        success = status['success']
        print('The order was successfully cancelled: ' + str(success))
    else:
        print('The order was unsuxxessfully cancelled.')

# method re-orders all open buys or sells
def re_order(session, number_of_orders, ids, volumes_filled, volumes, price, action):
    for i in range(number_of_orders):
        id = ids[i]
        volume = volumes[i]
        volume_filled = volumes_filled[i]
        #if order is partially filled
        if volume_filled != 0:
            volume = MAX_VOLUME - volume_filled
        
        # delete then re-purchase
        deleted = session.delete('http://localhost:9999/v1/orders/{}'.format(id))
        if deleted.ok:
            session.post('http://localhost:9999/v1/orders', params = {'ticker': sym, 'type': 'LIMIT', 'quantity': volume, 'price': price, 'action': action})

LAST_MINUTE_THRESHOLD = 60
LIQUIDITY_RATIO_THRESHOLD = 100
VOLUME_RATIO_THRESHOLD = 1.0
MAX_SPREAD = 0.2
TICKS_PER_PERIOD = 300
ORDER_BOOK_SIZE = 10000

def last_minute_action(session, action, tender_id, ticker):
    potential_profit = 0
    shares_accounte_for = 0
    prices = 0
    index = 0
    if action == 'BUY':
        prices = api.get(session, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
    elif action == 'SELL':
        prices = api.get(session, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
    while shares_accounted_for < quantity_offered:
        shares_accounted_for += prices[index]["quantity"] - prices[index]["quantity_filled"]
        if shares_accounted_for > quantity_offered:
            potential_profit += prices[index]["price"] * (quantity_offered - shares_accounted_for + prices[index]["quantity"] - prices[index]["quantity_filled"])
        else:
            potential_profit += prices[index]["price"] * (prices[index]["quantity"] - prices[index]["quantity_filled"])
        index += 1
    if potential_profit > value_of_offer:
        decision = api.post(session, "tenders", kwargs={id: tender_id})
        order_id = submit_order(session, ticker, 'MARKET', 10000, 'SELL', None)
        return "acepted", order_id, tender_id
    else:
        decision = api.delete(session, "tenders", kwargs={id: tender_id})
        return "rejected", None, None

def not_last_minute_action(session, action, tender_id, ticker):
    spread = 100*(api.get(s,"securities",ticker=ticker)[0]["ask"] / api.get(s,"securities",ticker=ticker)[0]["bid"]-1)
    if spread < MAX_SPREAD:
        bids = api.get(s,"securities/book",ticker=ticker,limit=ORDER_BOOK_SIZE)['bids']
        shares_accounted_for = 0
        bid_index = 0
        while shares_accounted_for < quantity_offered:
            shares_accounted_for += bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"]
            bid_index += 1
        sell_price = bids[bid_index - 1]["price"]
        if sell_price > price_offered:
            decision = api.post(session,"tenders",kwargs={"id":tender_id})
            return "accepted", tender_id
        else:
            decision = api.delete(session,"tenders",kwargs={"id":tender_id})
            return "rejected", False
    else:
        decision = api.delete(session,"tenders",kwargs={"id":tender_id})
        return "rejected", False

def unload(session, tender_id, ticker):
    spread = 100*(api.get(s,"securities",ticker=ticker)[0]["ask"]/api.get(s,"securities",ticker=ticker)[0]["bid"]-1)
    if spread < MAX_SPREAD:
        order_id = submit_order(session, ticker, 'MARKET', 10000, 'SELL', None) 
        return True

def tender_model(session, tender_id, ticker):
    tender : dict = {}

    for t in api.get(session, "tenders"):
        if t["tender_id"] == tender_id:
            tender = t
            break
    
    if tender == {}:
        return False
    
    tick = int(tender["tick"])
    ticker = tender["ticker"]
    price_offered = float(tender["price"])
    quantity_offered = int(tender["quantity"])
    action = tender["action"]
    value_of_offer = price_offered * quantity_offered

    net_positions = api.get(session, "limits")[0]['net']
    gross_positions = api.get(session, "limits")[0]['gross']

    if action == "BUY":
        if net_positions + quantity_offered < api.get(session, "limits")[0]['net_limit'] and gross_positions + quantity_offered < api.get(session, "limits")[0]['gross_limit']:
            if TICKS_PER_PERIOD - tick < LAST_MINUTE_THRESHOLD:
                decision, order_id, tender_id = last_minute_action(session, "BUY", tender_id, ticker)
                return "accepted", None
            else:
                decision, tender_id = not_last_minute_action(session, "BUY", tender_id, ticker)
                return "accepted", tender_id
        else:
            decision = api.delete(session,"tenders",kwargs={"id":tender_id})
            return "rejected", False
    else:
        action == "SELL"
        decision = api.post(session,"tenders",kwargs={"id":tender_id})
        return "accepted", False
    
    """
    elif action == "SELL":
        if gross_positions + quantity_filled < api.get(session, "limits")[0]['gross_limit']:
            current_position = api.get(session, "securities", ticker = ticker)[0]["position"]
            shares_to_be_shorted = 0

            if 0 <= current_position < quantity_offered:
                shares_to_be_shorted = quantity_offered - current_position
            elif current_position < 0:
                shares_to_be_shorted = quantity_offered
            
            shares_to_sell_instantly = quantity_offered - shares_to_be_shorted
            value_of_shorted = shares_to_be_shorted * price_offered
            instant_profit_from_sell = shares_to_sell_instantly * (price_offered - api.get(session, "securities", ticker = ticker)[0]["vwap"])
            potential_profit = 0

            if shares_to_be_shorted > 0:
                if 600 - tick < LAST_MINUTE_THRESHOLD:
                    asks = api.get(session, "securities/book", ticker = ticker, limit = 10000)['asks']
                    shares_accounted_for = 0
                    ask_index = 0

                    while shares_accounted_for < shares_to_be_shorted:
                        shares_accounted_for += asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"]
                        if shares_accoutned_for > quantity_offered:
                            potential_profit += asks[ask_index]["price"] * (quantity_offered - shares_accounted_for + asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"])
                        else:
                            potential_profit += asks[ask_index]["price"] * (asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"])
                        ask_index += 1
                    potential_profit = value_of_shorted - potential_profit
                    if potential_profit + instant_profit_from_sell > 0:
                        decision = "accept"
                        unload = "yes"
                        return
                    else:
                        decision = "reject"
                        return     
                else:
                    liquidity_ratio = shares_to_be_shorted / api.get(session, "securities", ticker = ticker)[0]["total_volume"]
                    if liquidity_ratio < LIQUIDITY_RATIO_THRESHOLD:
                        bids_and_asks
    """

def main():
    # instantiate variables about all the open buy orders
    buy_ids = []                # order ids
    buy_prices = []             # order prices
    buy_volumes = []            # order volumes
    volume_filled_buys = []     # amount of volume filled for each order
    open_buys_volume = 0        # combined volume from all open buy orders

    # instantiate variables about all the open sell orders
    sell_ids = []
    sell_prices = []
    sell_volumes = []
    volume_filled_sells = []
    open_sells_volume = 0

    # instantiated variables when just one side of the book has been completely filled
    single_side_filled = False
    single_side_transaction_time = 0

    # creates a session to manage connections and requests to the RIT Client
    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)

        held_tenders_list = []

        # while the time is between 5 and 295, do the following
        while tick > 0 and tick < 295 and not shutdown:
            for sym in ['HAWK', 'DOVE']:
                # update information about the case
                volume_filled_sells, open_sells_volumne, sell_ids, sell_prices, sell_volumes = open_sells(s)
                volume_filled_buys, open_buys_volume, buy_ids, buy_prices, buy_volumes = open_buys(s)
                bid_price, ask_price = ticker_bid_ask(s, sym) # NEED TO CHANGE TICKER

                tenders = api.get(s,"tenders")
                for tender in tenders:
                    if tender["tender_id"] not in held_tenders_list:
                        decision, tender_id = tender_model(s,tender["tender_id"], "RIT_C")
                        if decision == "accepted" and not tender_id is None:
                            held_tenders_list.append(tender_id)
                for tender in held_tenders_list:
                    resp = unload(session, tender["tender_id"], "RIT_C")

                # check if you have 0 open orders
                if open_sells_volume == 0 and open_buys_volume == 0:
                    # both sides are filled now
                    single_side_filled = False

                    # calculate the spread between the bid and ask prices
                    bid_ask_spread = ask_price - bid_price

                    # set the prices
                    sell_price = ask_price
                    buy_price = bid_price

                    # the calculated spread is greater or equal to our set spread
                    if bid_ask_spread >= SPREAD:
                        # buy and sell the maximum number of shares
                        buy_sell(s, sell_price, buy_price)
                        sleep(SPEEDBUMP)
                
                # there are outstanding open orders
                else:
                    # one side of the book has no open orders
                    if not single_side_filled and (open_buys_volume == 0 or open_sells_volume == 0):
                        single_side_filled = True
                        single_side_transaction_time = tick
                    
                    # ask side has been completely filled
                    if open_sells_volume == 0:
                        # current buy orders are at the top of the book
                        if buy_price == bid_price:
                            continue # next iteration of loop
                        
                        # its been more than 3 seconds since a single side has been completely filled
                        elif tick - single_side_transaction_time >= 3:
                            # calculate the potential profits you can make
                            next_buy_price = bid_price + 0.01
                            potential_profit = sell_price - next_buy_price - 0.02

                            # potential profit is greater than or equal to a cent or its been more than 6 seconds
                            if potential_profit >= 0.01 or tick - single_side_transaction_time >= 6:
                                action = 'BUY'
                                number_of_orders = len(buy_ids) # NEED TO CHANGE
                                buy_price = bid_price + 0.01
                                price = buy_price
                                ids = buy_ids
                                volumes = buy_volumes
                                volumes_filled = volume_filled_buys
                            
                                # delete buys and re-buy
                                re_order(s, number_of_orders, ids, volumes_filled, volumes, price, action)
                                sleep(SPEEDBUMP)
                            
                    # bid side has been completely filled
                    elif open_buys_volume == 0:
                        # current sell orders are at the top of the book
                        if sell_price == ask_price:
                            continue # next iteration of loop
                        
                        # its been more than 3 seconds since a single side has been completely filled
                        elif tick - single_side_transaction_time >= 3:
                            # calculate the potential profit you can make
                            next_sell_price = ask_price - 0.01
                            potential_profit = next_sell_price - buy_price - 0.02

                            # potential profit is greater than or equal to a cent or its been more than 6 seconds
                            if potential_profit >= 0.01 or tick - single_side_transaction_time >= 6:
                                action = 'SELL'
                                number_of_orders = len(sells_ids) # NEED TO CHANGE
                                sell_price = ask_price - 0.01
                                price = sell_price
                                ids = sell_ids
                                volumes = sell_volumes
                                volumes_filled = volume_filled_sells
                            
                            # delete sells then re-sell
                            re_order(s, number_of_orders, ids, volumes_filled, volumes, price, action)
                            sleep(SPEEDBUMP)
                
                # refresh the case time
                tick = get_tick(s)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()
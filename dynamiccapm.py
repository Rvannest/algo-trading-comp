"""
CAPM Beta Algorithmic Trading Case
Rotman BMO Finance Research and Trading Lab, Uniersity of Toronto (C) All rights reserved.

Preamble:
-> Code will have a small start up period; however, trades should only be executed once forward market price is available,
hence there should not be any issue caused.

-> Code only runs effectively if the News articles are formatted as they are now. The only way to get the required new data is by parsing the text.
"""

import signal
import requests
from time import sleep
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

#to store prices
historical_prices = {}

CAPM_vals = {}
expected_return = {}

#to filter and store the beta values
beta_vals = {k: v for k, v in CAPM_vals.items() if 'Beta - ' in k}

# class that passes error message, ends the program
class ApiException(Exception):
    pass

# code that lets us shut down if CTRL C is pressed
def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True

API_KEY = {'X-API-Key': 'K4P0T6H7'}
shutdown = False
session = requests.Session()
session.headers.update(API_KEY)

#code that gets the current tick
def get_tick(session):
    resp = session.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick']
    raise ApiException('fail - cant get tick')

#code that parses the first and latest news instances for forward market predictions and the risk free rate
#Important: this code only works if the only '%' character is in front of the RISK FREE RATE and the onle '$' character is in front of the forward price suggestions
def get_news(session):
    news = session.get('http://localhost:9999/v1/news')    
    if news.ok:
        newsbook = news.json()
        for i in range(len(newsbook[-1]['body'])):
            if newsbook[-1]['body'][i] == '%':
                #parses the risk free rate. stored in Rf
                CAPM_vals['%Rf'] = round(float(newsbook[-1]['body'][i - 4:i])/100, 4)               
        latest_news = newsbook[0]
        if len(newsbook) > 1:
            for j in range(len(latest_news['body']) - 1, 1, -1):    
                while latest_news['body'][j] != '$':
                    j -= 1
            CAPM_vals['forward'] = float(latest_news['body'][j + 1:-1])
        return CAPM_vals
    raise ApiException('timeout')



#modified get news with a change that will fix the program from crashing when the risk free rate is 0%
def modified_get_news(session):
    news = session.get('http://localhost:9999/v1/news')    
    if news.ok:
        newsbook = news.json()
        for i in range(len(newsbook[-1]['body'])):
            if newsbook[-1]['body'][i] == '%':
                # Attempt to find and parse the risk-free rate more robustly
                try:
                    # Search backwards from the '%' symbol for the start of the number
                    start = i
                    while newsbook[-1]['body'][start - 1].isdigit() or newsbook[-1]['body'][start - 1] in '.-':
                        start -= 1
                    # Parse the risk-free rate
                    CAPM_vals['%Rf'] = round(float(newsbook[-1]['body'][start:i])/100, 4)
                except ValueError:
                    # Handle cases where conversion to float fails
                    print(f"Error parsing risk-free rate from text: {newsbook[-1]['body'][start:i]}")
                break  # Assuming only one risk-free rate per news item
        
        latest_news = newsbook[0]
        CAPM_vals['latest_news_tick'] = latest_news['tick']

        if len(newsbook) > 1:
            for j in range(len(latest_news['body']) - 1, 1, -1):    
                while latest_news['body'][j] != '$':
                    j -= 1
            CAPM_vals['forward'] = float(latest_news['body'][j + 1:-1])
        
        # Additional step to extract 'at tick' value
        tick_phrase = 'at tick'
        if tick_phrase in latest_news['body']:
            start_index = latest_news['body'].find(tick_phrase) + len(tick_phrase)
            end_index = latest_news['body'].find(',', start_index)  # Assuming the tick number is followed by a comma
            tick_str = latest_news['body'][start_index:end_index].strip()
            try:
                # Extract and store the tick number
                CAPM_vals['tick_from_body'] = int(tick_str)
            except ValueError:
                # Handle cases where conversion to int fails
                print("Error converting tick number to int")

        return CAPM_vals
    else:
        raise ApiException('timeout')



# #MODIFIED get news
# def modified_get_news(session):
#     news = session.get('http://localhost:9999/v1/news')    
#     if news.ok:
#         newsbook = news.json()
#         for i in range(len(newsbook[-1]['body'])):
#             if newsbook[-1]['body'][i] == '%':
#                 #parses the risk free rate. stored in Rf
#                 CAPM_vals['%Rf'] = round(float(newsbook[-1]['body'][i - 4:i])/100, 4)
        
#         latest_news = newsbook[0]
#         CAPM_vals['latest_news_tick'] = latest_news['tick']

#         if len(newsbook) > 1:
#             for j in range(len(latest_news['body']) - 1, 1, -1):    
#                 while latest_news['body'][j] != '$':
#                     j -= 1
#             CAPM_vals['forward'] = float(latest_news['body'][j + 1:-1])
        
#         # Additional step to extract 'at tick' value
#         tick_phrase = 'at tick'
#         if tick_phrase in latest_news['body']:
#             start_index = latest_news['body'].find(tick_phrase) + len(tick_phrase)
#             end_index = latest_news['body'].find(',', start_index)  # Assuming the tick number is followed by a comma
#             tick_str = latest_news['body'][start_index:end_index].strip()
#             try:
#                 # Extract and store the tick number
#                 CAPM_vals['tick_from_body'] = int(tick_str)
#             except ValueError:
#                 # Handle cases where conversion to int fails
#                 print("Error converting tick number to int")

#         return CAPM_vals
#     raise ApiException('timeout')

# #gets all the price data for all securities and store prices in a list
# def pop_prices_and_store_in_list(session):
#     price_act = session.get('http://localhost:9999/v1/securities')
#     if price_act.ok:
#         current_prices = price_act.json()
#         # Iterate over the securities and add their prices to the historical prices list
#         for security in current_prices:
#             ticker = security['ticker']
#             price = security['last']  # Assuming 'last' is the key for the last price in the response
            
#             # If the ticker is not yet in the historical_prices dictionary, add it
#             if ticker not in historical_prices:
#                 historical_prices[ticker] = []
            
#             # Append the current price to the list for this ticker
#             historical_prices[ticker].append(price)
        
#         return historical_prices
#     else:
#         raise ApiException('fail - cant get securities')


#OG one, Used in the dataframes
def pop_prices(session):
    price_act = session.get('http://localhost:9999/v1/securities')
    if price_act.ok:
        prices = price_act.json()
        return prices
    raise ApiException('fail - cant get securities')
      
# def pop_prices(session):
#     price_act = session.get('http://localhost:9999/v1/securities')
#     if price_act.ok:
#         securities = price_act.json()
#         # Transforming the list of securities into a more useful format
#         prices_and_positions = {security['ticker']: {'price': security['last'], 'position': security['position']} for security in securities}
#         return prices_and_positions
#     else:
#         raise ApiException('fail - cant get securities')



# # #from splitting pop prices
# def get_prices(session):
#     price_act = session.get('http://localhost:9999/v1/securities')
#     if price_act.ok:
#         securities = price_act.json()
#         prices = {security['ticker']: security['last'] for security in securities}
#         return prices
#     else:
#         raise ApiException('fail - cant get securities')

# #from splitting pop prices
# def get_positions(session):
#     position_act = session.get('http://localhost:9999/v1/securities')
#     if position_act.ok:
#         securities = position_act.json()
#         positions = {security['ticker']: security['position'] for security in securities}
#         return positions
#     else:
#         raise ApiException('fail - cant get securities')

#combining get positions and get positions
def new_get_positions_and_prices(session):
    response = session.get('http://localhost:9999/v1/securities')
    if response.ok:
        securities = response.json()
        positions = {security['ticker']: security['position'] for security in securities}
        last_ticker_prices = {security['ticker']: security['last'] for security in securities}
        return positions, last_ticker_prices  # Return both positions and prices as a tuple
    else:
        raise ApiException('fail - cant get securities')



# def generate_shock_within_one_std(ticker):
#     # Check if there are enough prices to calculate a standard deviation
#     if ticker in historical_prices and len(historical_prices[ticker]) > 1:
#         # Calculate the standard deviation of the historical prices for the ticker
#         std_dev = np.std(historical_prices[ticker], ddof=1)  # ddof=1 for sample standard deviation
        
#         # Generate a shock within one standard deviation
#         shock = np.random.normal(0, std_dev)
#     else:
#         # Default to a small shock if not enough data is available
#         shock = np.random.normal(0, 0.1)
    
#     return shock


def close_position(session):
    positions, last_ticker_prices = new_get_positions_and_prices(session)

    for ticker, position in positions.items():
        if int(positions[ticker]) > 0:
            session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'SELL'})
            # could do this too according to gpt: 'quantity': abs(int(position))
            print(f"selling to close")
        if int(positions[ticker]) < 0:
            session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'BUY'})
            print(f"buying to close")



def buy_or_sell(session, expected_return, risk_free_rate, expected_market_return, highest_beta_ticker, lowest_beta_ticker, highest_beta_value, lowest_beta_value):    
# def buy_or_sell(session, expected_return, risk_free_rate, expected_market_return):
#def buy_or_sell(session, adjusted_return):
    #prices = get_prices(session)  # Assuming you need current prices for some logic not shown here
    positions, last_ticker_prices = new_get_positions_and_prices(session)
    #modified_news_data = modified_get_news(session)
    #percentage_diff = ((float(forecasted_price_for_RITM) - float(last_price_for_RITM)) /float(last_price_for_RITM)) * 100


    for ticker, exp_return in expected_return.items():
        if float(exp_return)*100 > float(expected_market_return)*100 and float(expected_market_return)*100 > 0 and float(exp_return)*100 > float(risk_free_rate)*100 and highest_beta_value > 1:
            session.post('http://localhost:9999/v1/orders', params={'ticker': highest_beta_ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'BUY'})
            print(f"buy to open")
            print(f"bought...{highest_beta_ticker}")
            #print(f"exp return: {exp_return*100} > percent diff: {percentage_diff+0.1} and > {risk_free_rate*100+0.1}")

        # elif float(exp_return)*100 > float(expected_market_return)*100 and 0 < float(expected_market_return)*100 < 0.25 and float(exp_return)*100 > float(risk_free_rate)*100:
        #     session.post('http://localhost:9999/v1/orders', params={'ticker': lowest_beta_ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'BUY'})


        # elif float(exp_return)*100 < float(expected_market_return)*100 and -0.25 < float(expected_market_return)*100 < 0 and float(exp_return)*100 < float(risk_free_rate)*100:
        #     session.post('http://localhost:9999/v1/orders', params={'ticker': lowest_beta_ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'SELL'})

        elif float(exp_return)*100 < float(expected_market_return)*100 and float(expected_market_return)*100 < 0 and float(exp_return)*100 < float(risk_free_rate)*100 and highest_beta_value > 1:
            session.post('http://localhost:9999/v1/orders', params={'ticker': highest_beta_ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'SELL'})
            print(f"sell to open")
            print(f"sold...{highest_beta_ticker}")
            #print(f"exp return: {exp_return*100} < percent diff: {percentage_diff-0.1} and < {risk_free_rate*100-0.1}")

    print(f"exp return: {exp_return*100}...percent diff: {expected_market_return*100}...risk free: {risk_free_rate*100}...{get_tick(session)}")









    # for ticker, exp_return in expected_return.items():
    #     if float(exp_return)*100 > float(percentage_diff)+0.1 and float(percentage_diff) > 0 and float(exp_return)*100 > float(risk_free_rate)*100 + 0.1:
    #         session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'BUY'})
    #         print(f"buy to open")
    #         print(f"bought...{ticker}")
    #         print(f"exp return: {exp_return*100} > percent diff: {percentage_diff+0.1} and > {risk_free_rate*100+0.1}")

    #     # if float(exp_return)*100 < float(percentage_diff) and 

    #     elif float(exp_return)*100 < float(percentage_diff)-0.1 and float(percentage_diff) < 0 and float(exp_return)*100 < float(risk_free_rate)*100  - 0.1:
    #         session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'SELL'})
    #         print(f"sell to open")
    #         print(f"sold...{ticker}")
    #         print(f"exp return: {exp_return*100} < percent diff: {percentage_diff-0.1} and < {risk_free_rate*100-0.1}")

    # print(f"exp return: {exp_return*100}...percent diff: {percentage_diff}...risk free: {risk_free_rate*100}...forecasted price RITM: {forecasted_price_for_RITM}...last price RITM: {last_price_for_RITM}...{get_tick(session)}")








    # for ticker, exp_return in expected_return.items():
    #     if float(exp_return)*100 > float(percentage_diff) and float(percentage_diff) > 0.25:
    #         session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'BUY'})
    #         print(f"buy to open")
    #         print(f"bought...{ticker}")
    #         print(f"exp return: {exp_return*100} > percent diff: {percentage_diff}")
    #     elif float(exp_return)*100 < float(percentage_diff) and float(percentage_diff) < -0.25:
    #         session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'SELL'})
    #         print(f"sell to open")
    #         print(f"sold...{ticker}")
    #         print(f"exp return: {exp_return*100} < percent diff: {percentage_diff}")

    # print(f"forecasted price RITM: {forecasted_price_for_RITM}...last price RITM: {last_price_for_RITM}...percentage diff: {percentage_diff}...{get_tick(session)}")



    # if percentage_diff > 0.30 and highest_beta_value > 0.50:
    #     session.post('http://localhost:9999/v1/orders', params={'ticker': highest_beta_ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'BUY'})
    #     print(f"buy to open")
    #     print(f"bought...{highest_beta_ticker}")
    #     print(f"percentage diff positive: {percentage_diff}")
    # elif percentage_diff < -0.30 and highest_beta_value > 0.50:
    #     session.post('http://localhost:9999/v1/orders', params={'ticker': highest_beta_ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'SELL'})
    #     print(f"sell to open")
    #     print(f"sold...{highest_beta_ticker}")
    #     print(f"percentage diff negative: {percentage_diff}")


    
    #expected is 3%, stock goes up 3% close the position. or recalculate when there is new
    # input: tick number, need the tick from when the headline was announced, get the tick from the analyst price prediction. can only place trade between the headline tick and the analyst tick

    # place the trade at the tick +1 of when we get the news article (News N) based on if the CAPM exp return is positive or negative,
    #   close out the trade tick (News 2) before the expected analyst price in News N+1
    # from 33 to 84

    #now i need to figure out a way to retrieve the forecasted price of next articles nad use that numnber to close my position.

    # for ticker, adj_return in adjusted_return.items():
    #         if float(adj_return) > 0.25 and positions[ticker] < 0:
    #             session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': (positions[ticker]*-1), 'action': 'BUY'})
    #             session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 10000, 'action': 'BUY'})
    #             print(f" {adjusted_return}, BUY... + exp return...long position...quantity to buy: {positions[ticker]*-1}...{ticker}")

    #         elif float(adj_return) < -0.25 and positions[ticker] > 0:
    #             session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': (positions[ticker]), 'action': 'SELL'})
    #             session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 10000, 'action': 'SELL'})
    #             print(f" {adjusted_return}, SELL... - exp return...short position...quantity to sell: {positions[ticker]}...{ticker}")
            
    #         elif float(adj_return) > 0.25 and positions[ticker] == 0:
    #             session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 10000, 'action': 'BUY'})
    #             print(f"{adjusted_return}, BUY...quick long...{ticker}")
            
    #         elif float(adj_return) < -0.25 and positions[ticker] == 0:
    #             session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 10000, 'action': 'SELL'})
    #             print(f"{adjusted_return}, SELL...quick short...{ticker}")          

    # for ticker, exp_return in expected_return.items():
    #     if float(exp_return) > 0.025:
    #         # If expected return is greater than 2%, submit a buy order
    #         session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 1000, 'action': 'BUY'})
        
    #     elif float(exp_return) < 0 and positions[ticker] > 0:
    #         # If expected return is greater than 1% and we hold a position, submit a sell order
    #         session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': positions[ticker], 'action': 'SELL'})
        
    #     elif float(exp_return) < -0.025:
    #         # If expected return is less than -2%, submit a sell order
    #         session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 1000, 'action': 'SELL'})
            
        
        # elif float(exp_return) > 0 and positions[ticker] < 0:
        #     # If expected return is greater than 1% and we hold a position, submit a sell order
        #     session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': positions[ticker], 'action': 'BUY'})
        #     #print(f"Buy...{ticker}...Between -0.01 and 0: {exp_return}...Current position - : {positions[ticker]}")





# def open_sells(session, sym):
#     resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
#     if resp.ok:
#         open_sells_volume = 0
#         ids = []
#         prices = []
#         order_volumes = []
#         volume_filled = []
#         open_orders = resp.json()
#         for order in open_orders:
#             if order['action'] == 'SELL' and order['ticker'] == sym:
#                 volume_filled.append(order['quantity_filled'])
#                 order_volumes.append(order['quantity'])
#                 open_sells_volume += order['quantity']
#                 prices.append(order['price'])
#                 ids.append(order['order_id'])
#         return {'volume_filled': volume_filled, 'open_volume': open_sells_volume, 'ids': ids, 'prices': prices, 'order_volumes': order_volumes}
#     else:
#         raise ApiException('Failed to retrieve open sell orders.')

# def open_buys(session, sym):
#     resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
#     if resp.ok:
#         open_buys_volume = 0
#         ids = []
#         prices = []
#         order_volumes = []
#         volume_filled = []
#         open_orders = resp.json()
#         for order in open_orders:
#             if order['action'] == 'BUY' and order['ticker'] == sym:
#                 volume_filled.append(order['quantity_filled'])
#                 order_volumes.append(order['quantity'])
#                 open_buys_volume += order['quantity']
#                 prices.append(order['price'])
#                 ids.append(order['order_id'])
#         return {'volume_filled': volume_filled, 'open_volume': open_buys_volume, 'ids': ids, 'prices': prices, 'order_volumes': order_volumes}
#     else:
#         raise ApiException('Failed to retrieve open buy orders.')



# def check_order_performance(session, expected_return):
#     # Retrieve current positions for all tickers
#     current_positions = {security['ticker']: security['position'] for security in pop_prices(session)}
    
#     for ticker, exp_return in expected_return.items():
#         # Assume get_current_price function exists and retrieves the latest price for the ticker
#         current_price = get_current_price(session, ticker)
        
#         # Retrieve open buy and sell orders
#         buys_info = open_buys(session, ticker)
#         sells_info = open_sells(session, ticker)
        
#         # Check and potentially close open buy orders based on expected return
#         for i, buy_price in enumerate(buys_info['prices']):
#             price_diff_percentage = (current_price - buy_price) / buy_price
#             if price_diff_percentage >= exp_return:
#                 # Close the position by selling
#                 session.post('http://localhost:9999/v1/orders', 
#                              params={'ticker': ticker, 'type': 'MARKET', 'quantity': buys_info['order_volumes'][i], 'action': 'SELL'})
        
#         # Check and potentially close open sell orders based on expected return
#         for i, sell_price in enumerate(sells_info['prices']):
#             price_diff_percentage = (sell_price - current_price) / sell_price
#             if price_diff_percentage <= exp_return:
#                 # Close the position by buying, if not exceeding current positions
#                 if current_positions[ticker] < 0:  # Assuming negative position indicates short selling
#                     session.post('http://localhost:9999/v1/orders', 
#                                  params={'ticker': ticker, 'type': 'MARKET', 'quantity': sells_info['order_volumes'][i], 'action': 'BUY'})


def main():
    with requests.Session() as session:
        session.headers.update(API_KEY)
        ritm = pd.DataFrame(columns= ['RITM','BID', 'ASK', 'LAST', '%Rm'])
        alpha = pd.DataFrame(columns= ['ALPHA','BID', 'ASK', 'LAST', '%Ri', '%Rm'])
        gamma = pd.DataFrame(columns= ['GAMMA','BID', 'ASK', 'LAST', '%Ri', '%Rm'])
        theta = pd.DataFrame(columns= ['THETA','BID', 'ASK', 'LAST', '%Ri', '%Rm'])
        
        while get_tick(session) < 599 and not shutdown:
            #update the forward market price and rf rate
            #get_news(session)
            #modified_news_data = modified_get_news(session)
            positions, last_ticker_prices = new_get_positions_and_prices(session)

            forward_number_found = False
            while not forward_number_found:
                try:
                    # Attempt to fetch or update data before accessing 'forward'
                    # Assuming modified_get_news(session) updates CAPM_vals
                    modified_get_news(session)  # Fetch/update the data
                    
                    # Now attempt to use the 'forward' key
                    forecasted_price_for_RITM = CAPM_vals['forward']
                    #print(f"forecasted price for RITM: {forecasted_price_for_RITM}")
                    forward_number_found = True  # Exit loop if successful
                except KeyError:
                    # 'forward' number not available, wait and try again
                    print("'forward' number not available yet, retrying...")
                    sleep(0.01)  # Wait for some time before retrying


            #print(f"AAAAAAAAAA{modified_get_news(session)} ... {get_tick(session)}")
            #print(f"Tick from most recent article: {CAPM_vals['latest_news_tick']}...Current forecast: {CAPM_vals['forward']}...Forecasted Tick: {modified_news_data['tick_from_body']}")



            ##update RITM bid-ask dataframe
            pdt_RITM = pd.DataFrame(pop_prices(session)[0])
            ritmp = pd.DataFrame({'RITM': '', 'BID': pdt_RITM['bid'],'ASK': pdt_RITM['ask'], 'LAST': pdt_RITM['last'], '%Rm': ''})
            if ritm['BID'].empty or ritmp['LAST'].iloc[0] != ritm['LAST'].iloc[0]:
                ritm = pd.concat([ritmp, ritm.loc[:]]).reset_index(drop=True)
                ritm['%Rm'] = (ritm['LAST']/ritm['LAST'].shift(-1)) - 1
                #print(f"RITM last price: {ritm['LAST']}...Ritm 2nd last price: {ritm['LAST'].shift(-1)}")

                if ritm.shape[0] >= 31:
                    ritm = ritm.iloc[:30]
            
            #expected market return paramter
            if 'forward' in CAPM_vals.keys():
                CAPM_vals['%RM'] = (CAPM_vals['forward']-ritm['LAST'].iloc[0])/ritm['LAST'].iloc[0]
                print(f" Expected MARKET return: {CAPM_vals['%RM']*100:.2f}%, Forward (News): {CAPM_vals['forward']}, RITM LAST: {ritm['LAST'].iloc[0]}")
            else:
                CAPM_vals['%RM'] = ''
                
              
            ##update ALPHA bid-ask dataframe
            pdt_ALPHA = pd.DataFrame(pop_prices(session)[1])
            alphap = pd.DataFrame({'ALPHA': '', 'BID': pdt_ALPHA['bid'],'ASK': pdt_ALPHA['ask'], 'LAST': pdt_ALPHA['last'], '%Ri': '', '%Rm': ''})
            if alpha['BID'].empty or alphap['LAST'].iloc[0] != alpha['LAST'].iloc[0]:
                alpha = pd.concat([alphap, alpha.loc[:]]).reset_index(drop=True)
                alpha['%Ri'] = (alpha['LAST']/alpha['LAST'].shift(-1)) - 1
                alpha['%Rm'] = (ritm['LAST']/ritm['LAST'].shift(-1)) - 1
                if alpha.shape[0] >= 31:
                    alpha = alpha.iloc[:30]
              
            ##update GAMMA bid-ask dataframe
            pdt_GAMMA = pd.DataFrame(pop_prices(session)[2])
            gammap = pd.DataFrame({'GAMMA': '', 'BID': pdt_GAMMA['bid'],'ASK': pdt_GAMMA['ask'], 'LAST': pdt_GAMMA['last'], '%Ri': '', '%Rm': ''})
            if gamma['BID'].empty or gammap['LAST'].iloc[0] != gamma['LAST'].iloc[0]:
                gamma = pd.concat([gammap, gamma.loc[:]]).reset_index(drop=True)
                gamma['%Ri'] = (gamma['LAST']/gamma['LAST'].shift(-1)) - 1
                gamma['%Rm'] = (ritm['LAST']/ritm['LAST'].shift(-1)) - 1
                if gamma.shape[0] >= 31:
                    gamma = gamma.iloc[:30]            
            
            ##update THETA bid-ask dataframe
            pdt_THETA = pd.DataFrame(pop_prices(session)[3])
            thetap = pd.DataFrame({'THETA': '', 'BID': pdt_THETA['bid'],'ASK': pdt_THETA['ask'], 'LAST': pdt_THETA['last'], '%Ri': '', '%Rm': ''})
            if theta['BID'].empty or thetap['LAST'].iloc[0] != theta['LAST'].iloc[0]:     
                theta = pd.concat([thetap, theta.loc[:]]).reset_index(drop=True)
                theta['%Ri'] = (theta['LAST']/theta['LAST'].shift(-1)) - 1
                theta['%Rm'] = (ritm['LAST']/ritm['LAST'].shift(-1)) - 1
                if theta.shape[0] >= 31:
                    theta = theta.iloc[:30]
            
            #calculates the beta of the stocks
            beta_alpha = (alpha['%Ri'].cov(ritm['%Rm']))/(ritm['%Rm'].var())
            beta_gamma = (gamma['%Ri'].cov(ritm['%Rm']))/(ritm['%Rm'].var())
            beta_theta = (theta['%Ri'].cov(ritm['%Rm']))/(ritm['%Rm'].var()) 
            
            CAPM_vals['Beta - ALPHA'] = beta_alpha
            CAPM_vals['Beta - GAMMA'] = beta_gamma
            CAPM_vals['Beta - THETA'] = beta_theta


            # # adjusted capm values
            # #if CAPM_vals['%Rm'] != '':
            # shock_alpha = generate_shock_within_one_std()
            # shock_gamma = generate_shock_within_one_std()
            # shock_theta = generate_shock_within_one_std()
            
            #Calculating capm values
            if CAPM_vals['%RM'] != '':
                er_alpha = CAPM_vals['%Rf'] + CAPM_vals['Beta - ALPHA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])
                #print(f"Expected Return: {er_alpha *100:.2f}%  Risk free rate: {CAPM_vals['%Rf'] *100:.2f}%, Beta: {CAPM_vals['Beta - ALPHA'] *100:.2f}%, M.R Premium: {CAPM_vals['%RM'] - CAPM_vals['%Rf'] *100:.2f}% ")
                er_gamma = CAPM_vals['%Rf'] + CAPM_vals['Beta - GAMMA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])
                er_theta = CAPM_vals['%Rf'] + CAPM_vals['Beta - THETA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])
                
                # print(f"{er_alpha}...ALPHA...{get_tick(session)}")
                # print(f"{er_gamma}...GAMMA...{get_tick(session)}")
                # print(f"{er_theta}...THETA...{get_tick(session)}")

            # if CAPM_vals['%RM'] != '':
            #     er_alpha = (CAPM_vals['%Rf'] + CAPM_vals['Beta - ALPHA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])) + shock_alpha
            #     er_gamma = (CAPM_vals['%Rf'] + CAPM_vals['Beta - GAMMA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])) + shock_gamma
            #     er_theta = (CAPM_vals['%Rf'] + CAPM_vals['Beta - THETA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])) + shock_theta

            #     adjusted_returns = {'ALPHA': er_alpha, 'GAMMA': er_gamma, 'THETA': er_theta}
            else:
                er_alpha = 'Wait for market forward price'
                er_gamma = 'Wait for market forward price'
                er_theta = 'Wait for market forward price'
                
            expected_return['ALPHA'] = er_alpha
            expected_return['GAMMA'] = er_gamma
            expected_return['THETA'] = er_theta
            
            


            beta_values = {
                'ALPHA': beta_alpha,
                'GAMMA': beta_gamma,
                'THETA': beta_theta
            }

            highest_beta_ticker = max(beta_values, key=beta_values.get)
            #print(f"highest_beta_ticker: {highest_beta_ticker}")
            highest_beta_value = beta_values[highest_beta_ticker]
            #print(f"highest_beta_value: {highest_beta_value}...{highest_beta_ticker}")

            lowest_beta_ticker = min(beta_values, key=beta_values.get)
            lowest_beta_value = beta_values[lowest_beta_ticker]

            last_price_for_RITM = ritm['LAST'].iloc[0]
            #print(f"last price for RITM: {last_price_for_RITM}")

            forecasted_price_for_RITM = CAPM_vals['forward']
            #print(f"forecasted price for ritm: {forecasted_price_for_RITM}")

            risk_free_rate = CAPM_vals['%Rf']
            print(f"risk free rate: {risk_free_rate}")

            expected_market_return = CAPM_vals['%RM']
            print(f"expected market return: {expected_market_return}")
            
            #Uncomment this string to enable Buy/Sell


            #if int(get_tick(session)) < int(CAPM_vals['latest_news_tick'] + 2):
            #print(f"Tick Range to open position: {(CAPM_vals['latest_news_tick'] + 2)}...{CAPM_vals['latest_news_tick'] + 4}")
            buy_or_sell(session, expected_return, risk_free_rate, expected_market_return, highest_beta_ticker, lowest_beta_ticker, highest_beta_value, lowest_beta_value)

            #if int(get_tick(session)) >=  int(CAPM_vals['tick_from_body'] - 1) or int(last_price_for_RITM) == int(forecasted_price_for_RITM):
                #print(f"Tick range to close: {(CAPM_vals['latest_news_tick'] - 2)}...{(CAPM_vals['latest_news_tick'] + 1)}")
            #close_position(session)



            # if int(get_tick(session)) < int(CAPM_vals['latest_news_tick'] + 3):
            #     #print(f"Tick Range to open position: {(CAPM_vals['latest_news_tick'] + 2)}...{CAPM_vals['latest_news_tick'] + 4}")
            #     buy_or_sell(session, highest_beta_ticker, highest_beta_value, last_price_for_RITM, forecasted_price_for_RITM)

            # if  int(get_tick(session)) >=  int(CAPM_vals['tick_from_body'] - 1):
            #     #print(f"Tick range to close: {(CAPM_vals['latest_news_tick'] - 2)}...{(CAPM_vals['latest_news_tick'] + 1)}")
            #     close_position(session)


            # if int(CAPM_vals['latest_news_tick'] + 2) < int(get_tick(session)) < int(CAPM_vals['latest_news_tick'] + 4):
            #     print(f"Tick Range to open position: {(CAPM_vals['latest_news_tick'] + 2)}...{CAPM_vals['latest_news_tick'] + 4}")
            #     buy_or_sell(session, expected_return)

            # if  int(CAPM_vals['latest_news_tick'] - 2) <= int(get_tick(session)) <= int(CAPM_vals['latest_news_tick'] + 1):
            #     print(f"Tick range to close: {(CAPM_vals['latest_news_tick'] - 2)}...{(CAPM_vals['latest_news_tick'] + 1)}")
            #     close_position(session)
            
            
            #buy_or_sell(session, adjusted_returns)
            
            #print statement (print, expected_return function, any of the tickers, or CAPM_vals dictionary)
            # for i in range(0,2):
            #     if i == 1:     
            #         print(expected_return)
            #         sleep(0.5)
            
        
if __name__ == '__main__':
    main()  
    

            
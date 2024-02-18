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
        #print(newsbook)
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

# #gets all the price data for all securities and store prices in a list
# def pop_prices_and_store_in_list(session):
#     price_act = session.get('http://localhost:9999/v1/securities')
#     if price_act.ok:
#         current_prices = price_act.json()
#         # Iterate over the securities and add their prices to the historical prices list
#         for security in current_prices:
#             ticker = security['ticker']
#             price = security['last']  # Assuming 'last' is the key for the last price in the response
#             print(f"{price}...current price")
            
#             # If the ticker is not yet in the historical_prices dictionary, add it
#             if ticker not in historical_prices:
#                 historical_prices[ticker] = []
            
#             # Append the current price to the list for this ticker
#             historical_prices[ticker].append(price)
        
#         return historical_prices
#     else:
#         raise ApiException('fail - cant get securities')


#OG one
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

#from splitting pop prices
def get_prices(session):
    price_act = session.get('http://localhost:9999/v1/securities')
    if price_act.ok:
        securities = price_act.json()
        prices = {security['ticker']: security['last'] for security in securities}
        return prices
    else:
        raise ApiException('fail - cant get securities')

#from splitting pop prices
def get_positions(session):
    position_act = session.get('http://localhost:9999/v1/securities')
    if position_act.ok:
        securities = position_act.json()
        positions = {security['ticker']: security['position'] for security in securities}
        return positions
    else:
        raise ApiException('fail - cant get securities')



# def generate_min_max_within_one_std(ticker):
#     if ticker in historical_prices and len(historical_prices[ticker]) > 1:
#         # Calculate the mean and standard deviation of the historical prices for the ticker
#         mean_price = np.mean(historical_prices[ticker])
#         std_dev = np.std(historical_prices[ticker], ddof=1)  # ddof=1 for sample standard deviation
        
#         # Calculate the min and max within one standard deviation
#         min_within_std = mean_price - std_dev
#         max_within_std = mean_price + std_dev
#     else:
#         # Default to some predefined min and max if not enough data is available
#         # This could be adjusted based on your requirements
#         min_within_std = -0.1  # Example default value
#         max_within_std = 0.1   # Example default value
    
#     return min_within_std, max_within_std

    
def buy_or_sell(session, expected_return):
#def buy_or_sell(session, adjusted_return):
    #prices = get_prices(session)  # Assuming you need current prices for some logic not shown here
    positions = get_positions(session)
    current_prices = get_prices(session)
    forward_price = CAPM_vals.get('forward', None)

        # Iterate through each ticker for which we have a CAPM return
    for ticker, capm_return in expected_return.items():
        if ticker == "RITM":
            current_price = current_prices.get(ticker, None)
            forward_price = CAPM_vals.get('forward', None)  # Directly using the forward price

            if current_price and forward_price:
                # Calculate the Analyst Expected Return for RITM
                analyst_expected_return = (forward_price - current_price) / current_price
                print(f"Expected Analyst return: {analyst_expected_return} for {ticker}")
            else:
                print(f"Information missing for {ticker}")

        # If the CAPM expected return is greater than the Analyst expected return, then buy
    if capm_return > 0 and analyst_expected_return > 0:
        session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'BUY'})
        print(f"Buying {ticker} based on CAPM return being greater than Analyst return.")

    # elif capm_return > 0 and analyst_expected_return > 0:
    #     session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': positions[ticker], 'action': 'SELL'})
    #     print(f"Selling {ticker} based on CAPM return being less than Analyst return...closing long position")

    elif capm_return < 0 and analyst_expected_return < 0:
        session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'SELL'})
        print(f"Selling {ticker} based on CAPM return being less than Analyst return")

    # elif capm_return < 0 and analyst_expected_return < 0:
    #     session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': positions[ticker], 'action': 'BUY'})
    #     print(f"Buying {ticker} based on CAPM return being higher than Analyst return...closing short position")



    
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


        # if float(exp_return) > 0.025:
        #     # If expected return is greater than 2%, submit a buy order
        #     session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 1000, 'action': 'BUY'})
        #     print(f"Buy...{ticker}...Above 0.025: {exp_return}")
        
        # elif float(exp_return) < 0 and positions[ticker] > 0:
        #     # If expected return is greater than 1% and we hold a position, submit a sell order
        #     session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': positions[ticker], 'action': 'SELL'})
        #     print(f"Sell...{ticker}...Between 0 and 0.01: {exp_return}...Current position +: {positions[ticker]}")
        
        # elif float(exp_return) < -0.025:
        #     # If expected return is less than -2%, submit a sell order
        #     session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 1000, 'action': 'SELL'})
        #     print(f"Buy...{ticker}...Below -0.025: {exp_return}")
        
        # elif float(exp_return) > 0 and positions[ticker] < 0:
        #     # If expected return is greater than 1% and we hold a position, submit a sell order
        #     session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': positions[ticker], 'action': 'BUY'})
        #     print(f"Sell...{ticker}...Between -0.01 and 0: {exp_return}...Current position - : {positions[ticker]}")


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
            get_news(session)
            
            ##update RITM bid-ask dataframe
            pdt_RITM = pd.DataFrame(pop_prices(session)[0])
            ritmp = pd.DataFrame({'RITM': '', 'BID': pdt_RITM['bid'],'ASK': pdt_RITM['ask'], 'LAST': pdt_RITM['last'], '%Rm': ''})
            if ritm['BID'].empty or ritmp['LAST'].iloc[0] != ritm['LAST'].iloc[0]:
                ritm = pd.concat([ritmp, ritm.loc[:]]).reset_index(drop=True)
                ritm['%Rm'] = (ritm['LAST']/ritm['LAST'].shift(-1)) - 1
                if ritm.shape[0] >= 31:
                    ritm = ritm.iloc[:30]
            
            #expected market return paramter
            if 'forward' in CAPM_vals.keys():
                CAPM_vals['%RM'] = (CAPM_vals['forward']-ritm['LAST'].iloc[0])/ritm['LAST'].iloc[0]
                #print(f" Expected MARKET return: {CAPM_vals['%RM']*100:.2f}%, Forward (News): {CAPM_vals['forward']}, RITM LAST: {ritm['LAST'].iloc[0]}")
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

            # # caculation for adjusted capm values
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
            # print(f"{expected_return['ALPHA']}...expected return of Alpha")
            # print(f"{expected_return['GAMMA']}...expected return of Gamma")
            # print(f"{expected_return['THETA']}...expected return of Theta")
            
            #Uncomment this string to enable Buy/Sell
            buy_or_sell(session, expected_return)
            #buy_or_sell(session, adjusted_returns)
            
            #print statement (print, expected_return function, any of the tickers, or CAPM_vals dictionary)
            #print(expected_return)
            
        
if __name__ == '__main__':
    main()  
    

            
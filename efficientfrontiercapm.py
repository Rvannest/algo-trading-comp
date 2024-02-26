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
from scipy.optimize import minimize

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

# #code that parses the first and latest news instances for forward market predictions and the risk free rate
# #Important: this code only works if the only '%' character is in front of the RISK FREE RATE and the onle '$' character is in front of the forward price suggestions
# def get_news(session):
#     news = session.get('http://localhost:9999/v1/news')    
#     if news.ok:
#         newsbook = news.json()
#         for i in range(len(newsbook[-1]['body'])):
#             if newsbook[-1]['body'][i] == '%':
#                 #parses the risk free rate. stored in Rf
#                 CAPM_vals['%Rf'] = round(float(newsbook[-1]['body'][i - 4:i])/100, 4)               
#         latest_news = newsbook[0]
#         if len(newsbook) > 1:
#             for j in range(len(latest_news['body']) - 1, 1, -1):    
#                 while latest_news['body'][j] != '$':
#                     j -= 1
#             CAPM_vals['forward'] = float(latest_news['body'][j + 1:-1])
#         return CAPM_vals
#     raise ApiException('timeout')



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


#OG one, Used in the dataframes
def pop_prices(session):
    price_act = session.get('http://localhost:9999/v1/securities')
    if price_act.ok:
        prices = price_act.json()
        return prices
    raise ApiException('fail - cant get securities')



def new_get_positions_and_prices(session):
    response = session.get('http://localhost:9999/v1/securities')
    if response.ok:
        securities = response.json()
        positions = {}
        last_ticker_prices = {}
        for security in securities:
            ticker = security['ticker']
            last_price = security['last']
            position = security['position']
            
            # Store position and last price in their respective dictionaries
            positions[ticker] = position
            last_ticker_prices[ticker] = last_price
            
            # Update historical prices
            if ticker in historical_prices:
                historical_prices[ticker].append(last_price)
            else:
                historical_prices[ticker] = [last_price]
                
        # Returns both positions and last ticker prices, historical_prices gets updated globally
        return positions, last_ticker_prices
    else:
        raise ApiException('fail - cant get securities')




def objective(weights, expected_returns_ef, risk_free_rate, cov_matrix):
    return weights.dot(cov_matrix).dot(weights.T)


# def close_position(session):
#     positions, last_ticker_prices = new_get_positions_and_prices(session)

#     for ticker, position in positions.items():
#         if int(positions[ticker]) > 0:
#             session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'SELL'})
#             # could do this too according to gpt: 'quantity': abs(int(position))
#             print(f"selling to close")
#         if int(positions[ticker]) < 0:
#             session.post('http://localhost:9999/v1/orders', params={'ticker': ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'BUY'})
#             print(f"buying to close")




def buy_or_sell_optimized(session, optimal_weights, tradeable_tickers):
    net_limit = 90000  # Your net trading limit for total shares
    positions, last_ticker_prices = new_get_positions_and_prices(session)
    
    # Convert optimal weights to desired number of shares for each stock
    desired_shares = {ticker: int(weight * net_limit) for ticker, weight in zip(tradeable_tickers, optimal_weights)}
    
    for ticker, desired_share in desired_shares.items():
        current_position = positions.get(ticker, 0)
        difference = desired_share - current_position
        
        # If you need to buy shares
        if difference > 0:
            print(f"Buying {abs(difference)} shares of {ticker}")
            session.post('http://localhost:9999/v1/orders', params={
                'ticker': ticker, 'type': 'MARKET', 'quantity': abs(difference), 'action': 'BUY'
            })
        
        # If you need to sell shares
        elif difference < 0:
            print(f"Selling {abs(difference)} shares of {ticker}")
            session.post('http://localhost:9999/v1/orders', params={
                'ticker': ticker, 'type': 'MARKET', 'quantity': abs(difference), 'action': 'SELL'
            })



def buy_or_sell(session, expected_return, risk_free_rate, expected_market_return, highest_beta_ticker, lowest_beta_ticker, highest_beta_value, lowest_beta_value):    
    positions, last_ticker_prices = new_get_positions_and_prices(session)
    #modified_news_data = modified_get_news(session)
    #percentage_diff = ((float(forecasted_price_for_RITM) - float(last_price_for_RITM)) /float(last_price_for_RITM)) * 100


    for ticker, exp_return in expected_return.items():
        if float(exp_return)*100 > float(expected_market_return)*100 and float(expected_market_return)*100 > 0 and float(exp_return)*100 > float(risk_free_rate)*100 and highest_beta_value > 1:
            session.post('http://localhost:9999/v1/orders', params={'ticker': highest_beta_ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'BUY'})
            # print(f"buy to open")
            # print(f"bought...{highest_beta_ticker}")
            #print(f"exp return: {exp_return*100} > percent diff: {percentage_diff+0.1} and > {risk_free_rate*100+0.1}")

        elif float(exp_return)*100 < float(expected_market_return)*100 and float(expected_market_return)*100 < 0 and float(exp_return)*100 < float(risk_free_rate)*100 and highest_beta_value > 1:
            session.post('http://localhost:9999/v1/orders', params={'ticker': highest_beta_ticker, 'type': 'MARKET', 'quantity': 5000, 'action': 'SELL'})
            # print(f"sell to open")
            # print(f"sold...{highest_beta_ticker}")
            #print(f"exp return: {exp_return*100} < percent diff: {percentage_diff-0.1} and < {risk_free_rate*100-0.1}")

    # print(f"exp return: {exp_return*100}...percent diff: {expected_market_return*100}...risk free: {risk_free_rate*100}...{get_tick(session)}")


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

            
            #Calculating capm values
            if CAPM_vals['%RM'] != '':
                er_alpha = CAPM_vals['%Rf'] + CAPM_vals['Beta - ALPHA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])
                #print(f"Expected Return: {er_alpha *100:.2f}%  Risk free rate: {CAPM_vals['%Rf'] *100:.2f}%, Beta: {CAPM_vals['Beta - ALPHA'] *100:.2f}%, M.R Premium: {CAPM_vals['%RM'] - CAPM_vals['%Rf'] *100:.2f}% ")
                er_gamma = CAPM_vals['%Rf'] + CAPM_vals['Beta - GAMMA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])
                er_theta = CAPM_vals['%Rf'] + CAPM_vals['Beta - THETA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])
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
            #print(f"risk free rate: {risk_free_rate}")

            expected_market_return = CAPM_vals['%RM']
            print(f"expected market return: {expected_market_return}")


            #attempting to create an efficient frontier, also some covariance matrix calculations
            price_data = pd.DataFrame(historical_prices)
            returns = price_data.pct_change().dropna()
            covariance_matrix = returns.cov()

            tradeable_tickers = ['ALPHA', 'GAMMA', 'THETA']  # List of tickers you're interested in trading
            covariance_matrix_tradeable = covariance_matrix.loc[tradeable_tickers, tradeable_tickers]

            expected_returns_ef = np.array([er_alpha, er_gamma, er_theta])

            cov_matrix = covariance_matrix_tradeable.values
            num_assets = len(expected_returns_ef)

            constraints = [
            {'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1}  # Ensures leverage does not exceed 100%
            ]

            bounds = [(-1, 1) for _ in range(len(expected_returns_ef))]
            initial_guess = 1/3, 1/3, 1/3

            opt_result = minimize(objective, initial_guess, args=(expected_returns_ef, risk_free_rate, cov_matrix), method='L-BFGS-B', bounds=bounds, constraints=constraints)
            optimal_weights = opt_result.x

            print("Optimal weights for each stock:")
            for ticker, weight in zip(tradeable_tickers, optimal_weights):
                print(f"{ticker}: {weight:.2%}")

            # Calculate the expected portfolio return and volatility
            expected_portfolio_return = np.sum(optimal_weights * expected_returns_ef)
            portfolio_volatility = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))

            print(f"\nExpected Portfolio Return: {expected_portfolio_return:.2%}")
            print(f"Portfolio Volatility: {portfolio_volatility:.2%}")

            
            #Uncomment this string to enable Buy/Sell

            buy_or_sell_optimized(session, optimal_weights, tradeable_tickers)


            #if int(get_tick(session)) < int(CAPM_vals['latest_news_tick'] + 2):
            #print(f"Tick Range to open position: {(CAPM_vals['latest_news_tick'] + 2)}...{CAPM_vals['latest_news_tick'] + 4}")
            
            # buy_or_sell(session, expected_return, risk_free_rate, expected_market_return, highest_beta_ticker, lowest_beta_ticker, highest_beta_value, lowest_beta_value)

            #if int(get_tick(session)) >=  int(CAPM_vals['tick_from_body'] - 1) or int(last_price_for_RITM) == int(forecasted_price_for_RITM):
                #print(f"Tick range to close: {(CAPM_vals['latest_news_tick'] - 2)}...{(CAPM_vals['latest_news_tick'] + 1)}")
            #close_position(session)
            
            #print statement (print, expected_return function, any of the tickers, or CAPM_vals dictionary)
            # for i in range(0,2):
            #     if i == 1:     
            #         print(expected_return)
            #         sleep(0.5)
            
        
if __name__ == '__main__':
    main()
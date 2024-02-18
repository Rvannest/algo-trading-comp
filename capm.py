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

#gets all the price data for all securities        
def pop_prices(session):
    price_act = session.get('http://localhost:9999/v1/securities')
    if price_act.ok:
        securities = price_act.json()
        # Transforming the list of securities into a more useful format
        prices_and_positions = {security['ticker']: {'price': security['last'], 'position': security['position']} for security in securities}
        return prices_and_positions
    raise ApiException('fail - cant get securities')

    
#Buy or Sell function, put in your own parameters
def buy_or_sell(session, expected_return):
    for i in expected_return.keys():
        if float(expected_return[i]) > 0.02:
            session.post('http://localhost:9999/v1/orders', params = {'ticker': i, 'type': 'MARKET', 'quantity': 10000, 'action': 'BUY'})
        elif float(expected_return[i]) < -0.02:
            session.post('http://localhost:9999/v1/orders', params = {'ticker': i, 'type': 'MARKET', 'quantity': 10000, 'action': 'SELL'})


def open_sells(session, sym):
    resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
    if resp.ok:
        open_sells_volume = 0
        ids = []
        prices = []
        order_volumes = []
        volume_filled = []
        open_orders = resp.json()
        for order in open_orders:
            if order['action'] == 'SELL' and order['ticker'] == sym:
                volume_filled.append(order['quantity_filled'])
                order_volumes.append(order['quantity'])
                open_sells_volume += order['quantity']
                prices.append(order['price'])
                ids.append(order['order_id'])
        return {'volume_filled': volume_filled, 'open_volume': open_sells_volume, 'ids': ids, 'prices': prices, 'order_volumes': order_volumes}
    else:
        raise ApiException('Failed to retrieve open sell orders.')

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
                volume_filled.append(order['quantity_filled'])
                order_volumes.append(order['quantity'])
                open_buys_volume += order['quantity']
                prices.append(order['price'])
                ids.append(order['order_id'])
        return {'volume_filled': volume_filled, 'open_volume': open_buys_volume, 'ids': ids, 'prices': prices, 'order_volumes': order_volumes}
    else:
        raise ApiException('Failed to retrieve open buy orders.')



def check_order_performance(session, expected_return):
    # Retrieve current positions for all tickers
    current_positions = {security['ticker']: security['position'] for security in pop_prices(session)}
    
    for ticker, exp_return in expected_return.items():
        # Assume get_current_price function exists and retrieves the latest price for the ticker
        current_price = get_current_price(session, ticker)
        
        # Retrieve open buy and sell orders
        buys_info = open_buys(session, ticker)
        sells_info = open_sells(session, ticker)
        
        # Check and potentially close open buy orders based on expected return
        for i, buy_price in enumerate(buys_info['prices']):
            price_diff_percentage = (current_price - buy_price) / buy_price
            if price_diff_percentage >= exp_return:
                # Close the position by selling
                session.post('http://localhost:9999/v1/orders', 
                             params={'ticker': ticker, 'type': 'MARKET', 'quantity': buys_info['order_volumes'][i], 'action': 'SELL'})
        
        # Check and potentially close open sell orders based on expected return
        for i, sell_price in enumerate(sells_info['prices']):
            price_diff_percentage = (sell_price - current_price) / sell_price
            if price_diff_percentage <= exp_return:
                # Close the position by buying, if not exceeding current positions
                if current_positions[ticker] < 0:  # Assuming negative position indicates short selling
                    session.post('http://localhost:9999/v1/orders', 
                                 params={'ticker': ticker, 'type': 'MARKET', 'quantity': sells_info['order_volumes'][i], 'action': 'BUY'})


def main():
    with requests.Session() as session:
        session.headers.update(API_KEY)
        ritm = pd.DataFrame(columns= ['RITM','BID', 'ASK', 'LAST', '%Rm'])
        alpha = pd.DataFrame(columns= ['ALPHA','BID', 'ASK', 'LAST', '%Ri', '%Rm'])
        gamma = pd.DataFrame(columns= ['GAMMA','BID', 'ASK', 'LAST', '%Ri', '%Rm'])
        theta = pd.DataFrame(columns= ['THETA','BID', 'ASK', 'LAST', '%Ri', '%Rm'])
        while get_tick(session) < 600 and not shutdown:
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
            
            #Calculating capm values
            if CAPM_vals['%RM'] != '':
                er_alpha = CAPM_vals['%Rf'] + CAPM_vals['Beta - ALPHA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])
                print(f"Expected Return: {er_alpha *100:.2f}%  Risk free rate: {CAPM_vals['%Rf'] *100:.2f}%, Beta: {CAPM_vals['Beta - ALPHA'] *100:.2f}%, M.R Premium: {CAPM_vals['%RM'] - CAPM_vals['%Rf'] *100:.2f}% ")
                er_gamma = CAPM_vals['%Rf'] + CAPM_vals['Beta - GAMMA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])
                er_theta = CAPM_vals['%Rf'] + CAPM_vals['Beta - THETA'] * (CAPM_vals['%RM'] - CAPM_vals['%Rf'])
            else:
                er_alpha = 'Wait for market forward price'
                er_gamma = 'Wait for market forward price'
                er_theta = 'Wait for market forward price'
                
            expected_return['ALPHA'] = er_alpha
            expected_return['GAMMA'] = er_gamma
            expected_return['THETA'] = er_theta
            
            #Uncomment this string to enable Buy/Sell
            buy_or_sell(session, expected_return)
            
            #print statement (print, expected_return function, any of the tickers, or CAPM_vals dictionary)
            #print(expected_return)
            
        
if __name__ == '__main__':
    main()  
    

            
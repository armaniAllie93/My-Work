import pandas as pd
import ta
import datetime
import math
import numpy as np
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import dash_core_components as dcc
import dash_html_components as html
import dash
from dash.dependencies import Input, Output

#initiates Kucoin account
from kucoin.client import Client
client = Client("CLIENTKEY", "SECRETKEY", "PASSPHRASE")

#GMail Credentials
MY_ADDRESS = ''
PASSWORD = ''
s = smtplib.SMTP(host='smtp.gmail.com', port=587)
s.starttls()
s.login(MY_ADDRESS, PASSWORD)

#initiates emails
msg = MIMEMultipart()
msg['From']=MY_ADDRESS
msg['To']=MY_ADDRESS
msg['Subject']= "KuCoin Trading Bot"
#exception module
from kucoin.exceptions import KucoinAPIException

#KuCoin API constants
buy_order = client.SIDE_BUY
sell_order = client.SIDE_SELL
stop_loss = client.STOP_LOSS

#retrieves account information and buying power in trading account
accounts = client.get_accounts()
account = pd.DataFrame(accounts)
account = account[(account.type == 'trade')]
trade_hist = client.get_trade_histories('MTV-USDT')
trade_hist = pd.DataFrame(trade_hist)
start_balance = 200.00

#Trade USDT account
buypower = account.loc[account['currency']=='USDT','available'].values[0]
print(account)
#converts buying power to float and divides by 2 to represent buy size
buypow = float(buypower)
buypowT = buypow/1.01
buypowT = "{:.2f}".format(buypowT)
#converts buy size back to str for create_market_order
buysize = str(buypowT)
print(buysize)

#checks for starting balance
if buypow > 100.00:
	curr_balance = buypow
	bal = curr_balance - start_balance
	bal_pl = bal / curr_balance
	bal_diff = bal_pl * 100
	print("net profit/loss: " + str("%.2f" % bal_diff)+ "%")
else:
	print("starting balance: $" + str(start_balance) + " funds are in long positions")

#sets beginning and ending timestamp
now = datetime.datetime.now()
nowtime = now.timestamp()
start = now - datetime.timedelta(days=2)
starttime = start.timestamp()
start72 = now - datetime.timedelta(days=3)
starttime72 = start72.timestamp()
endTime = math.floor(nowtime)
beginTime = math.floor(starttime)
beginTime72 = math.floor(starttime72)



#first list that runs through selection of swing trading coins
c = ['ARPA-USDT','BEPRO-USDT','ONE-USDT','DAPPT-USDT']
#brings in OHLC Data for percent change metrics
for i in c:
    kline48 = client.get_kline_data(i,'1day',beginTime72,endTime)
    kline1h = client.get_kline_data(i,'1hour',beginTime,endTime)
    data1h = pd.DataFrame(kline1h)
    data1h = data1h[[0,2]]
    data1h[0] = pd.to_datetime(data1h[0],unit='s',origin='unix')
    data1h[2] = data1h[2].astype(float)
    data1h = data1h.reindex(index=data1h.index[::-1])
    closeprice = data1h[2]
    data48 = pd.DataFrame(kline48)
    data48 = data48[[0,2]]
    data48[0] = pd.to_datetime(data48[0],unit='s',origin='unix')
    data48[2] = data48[2].astype(float)
    data48 = data48.reindex(index=data48.index[::-1])
    price48 = data48[2]
    thirdDay = price48.iloc[0]
    secondDay = price48.iloc[1]
    firstDay = price48.iloc[2]

    #creates day percent change

    PC1 = secondDay - thirdDay
    PC1 = PC1 / secondDay
    PC1 = PC1 * 100
    PC2 = firstDay - secondDay
    PC2 = PC2 / firstDay
    PC2 = PC2 * 100
    print(str(i) + str(PC1))
    ema = ta.trend.ema_indicator(closeprice,n=25,fillna=True)
    lastEMA = ema.iloc[-1]

    #creates boolean instance which detects downtrend
    trend2 = (ema - closeprice) / closeprice
    trend24 = trend2.iloc[-24:]
    booltrend = trend24 > -0.02
    trendresult = booltrend.all()
    cstr = ''.join(str(x) for x in i)
    for acc in account['currency']:
        if cstr.startswith(acc):
            sellsize = account.loc[account['currency'] == acc, 'available'].values[0]
            sellsize = float(sellsize)
    if sellsize < 2.00:
        if PC1 > 10.00 or PC2 > 10.00:
            try:
                c.remove(i)
            except ValueError as ve:
                print(ve + "Coin not in list")
        if trendresult == True:
            try:
                c.remove(i)
            except ValueError as ve:
                print(ve + "Coin not in list")
        if PC1 < -5.00:
            try:
                c.remove(i)
            except ValueError as ve:
                print(ve + "Coin not in list")
print(c)
price_result = []

#second loop that initiates trading bot
for i in c:
    try:
        kline = client.get_kline_data(i,'1hour',beginTime,endTime)
    except KucoinAPIException as e:
        print(e.response)
        print(e.message)
    #price data for tech indicators
    data = pd.DataFrame(kline)
    openprice = data[1]
    openprice = openprice.astype(float)
    closeprice = data[[0,2]]
    closeprice[0] = pd.to_datetime(closeprice[0],unit='s',origin='unix')
    closeprice[2] = closeprice[2].astype(float)
    closeprice = closeprice.reindex(index=closeprice.index[::-1])
    close = closeprice[2]
    #initiates price action instances
    lastClose = close.iloc[-1]
    secondClose = close.iloc[-2]
    lastopen = openprice.iloc[0]
    secondopen = openprice.iloc[1]
    PA = lastClose - secondClose
    PAdiff = PA / lastClose
    PAdiff = PAdiff * 100
    autocorr = np.corrcoef(np.array([close[:-4], close[4:]]))

    ema = ta.trend.ema_indicator(close,n=35,fillna=True)
    lastEMA = ema.iloc[-1]
    rsi = ta.momentum.rsi(close=closeprice[2], n=14)
    lastRSI = rsi.iloc[-1]
    secondRSI = rsi.iloc[-2]

    trend = (ema - close) / close
    lastTrend = trend.iloc[-1]
    secondTrend = trend.iloc[-2]
    thirdTrend = trend.iloc[-3]
    fourthTrend = trend.iloc[-4]
    lastTrendP = lastTrend * 100
    trend24 = trend.iloc[-24:]
    booltrend = trend24 > -0.02
    trendresult = booltrend.all()

    def getsellsize():
        cstr = ''.join(str(x) for x in i)
        for s in account['currency']:
            if cstr.startswith(s):
                sellsize = account.loc[account['currency'] == s, 'available'].values[0]
                sellsize = float(sellsize)
                sellsize = sellsize/1.01
                sellsize = "{:.2f}".format(sellsize)
                return sellsize
    getsellsize()
    def getcurr_price():
        cstr = ''.join(str(x) for x in i)
        for s in account['currency']:
            if cstr.startswith(s):
                sellsize = account.loc[account['currency'] == s, 'available'].values[0]
                sellsize_ft = float(sellsize)
                if sellsize_ft > 2.0:
                    orders = client.get_fills(symbol=i,side='buy')
                    orders = pd.DataFrame(orders)
                    orders = orders['items']
                    print(orders)
                    try:
                        orders = pd.concat(orders.apply(lambda y: pd.DataFrame({m:[n]for m,n in y.items()})).values).reset_index(drop=True)
                    except ValueError as ve:
                        print(ve + str(i) + "Coin price not available?")
                        break
                    orders = orders[['symbol', 'side', 'price', 'size', 'funds', 'fee']]
                    orders = orders.head(1)
                    print(orders)
                    for o in orders['price']:
                        buyprice = o
                        print(str(i) + "buy price " + buyprice)
                        buyprice = float(buyprice)
                        PL = lastClose - buyprice
                        PL_diff = PL / lastClose
                        PL_diffP = PL_diff * 100
                        PL_diffP = str("%.2f" % PL_diffP + "%")
                        return PL_diffP
    print(getcurr_price())
    price_result.append((i,getcurr_price()))
    price_resultDF = pd.DataFrame(price_result)
    print("last trend : " + str(lastTrend) + "& second Trend : " + str(secondTrend))
    print("last RSI : " + str(lastRSI))

    #retrieves right decimal to create orders
    symbols = client.get_symbols()
    symbols = pd.DataFrame(symbols)
    sell_increment = symbols.loc[symbols['symbol'] == i, 'baseIncrement'].values[0]
    sell_increment = str(sell_increment)
    sell_increment_len = sell_increment[::-1].find('.')
    print(sell_increment_len)
    print(sell_increment)
    precision = sell_increment_len
    try:
        sellsize = account.loc[account['currency'] == i[:-5], 'available'].values[0]
        sellsize = float(sellsize)
        sellsize = "{:.{}f}".format(sellsize,precision)
        sellsizeT = str(sellsize)
    except IndexError:
        print("No funds in long position for " + str(i))
    try:
        sellsize = account.loc[account['currency'] == i[:-5], 'available'].values[0]
        sellsize = float(sellsize)
        sellsize = sellsize/2
        sellsize = "{:.{}f}".format(sellsize,precision)
        sellsizeT2 = str(sellsize)
    except IndexError:
        print("No funds in long position for " + str(i))


    if PC1 < -7.00 or PC2 > -5.00:
        if lastRSI < 30:
            try:
                market_buy = client.create_market_order(i,buy_order, funds=buysize)
                print(market_buy)
                message = str(str(i) + " buy order made at low RSI after downtrend " + getcurr_price())
                msg.attach(MIMEText(message, 'plain'))
                s.send_message(msg)
            except KucoinAPIException as e:
                print(str(i) + " buy order not complete because " + e.message)
        if PAdiff < -3.00:
            boolDF = account['currency'].isin([i[:-5]])
            sell_result = boolDF.any()
            if sell_result:
                try:
                    market_sell = client.create_market_order(i,sell_order, funds=sellsizeT2)
                    print(market_sell)
                    message = str(str(i) + " sell order made off downtrend at " + getcurr_price())
                    msg.attach(MIMEText(message, 'plain'))
                    s.send_message(msg)
                except KucoinAPIException as e:
                    print(str(i) + " sell not complete because " + e.message)

    if lastRSI > 70:
        boolDF = account['currency'].isin([i[:-5]])
        sell_result = boolDF.any()
        if sell_result:
            try:
                market_sell = client.create_market_order(i,sell_order, funds=sellsizeT2)
                print(market_sell)
                message = str(str(i) + " sell order made off downtrend at " + getcurr_price())
                msg.attach(MIMEText(message, 'plain'))
                s.send_message(msg)
            except KucoinAPIException as e:
                print(str(i) + " sell not complete because " + e.message)



    #sells off trend
    if lastTrend < -0.03:
	    if PAdiff < -3.00 or lastTrend > thirdTrend:
	        boolDF = account['currency'].isin([i[:-5]])
	        sell_result = boolDF.any()
	        if sell_result:
	            try:
	                market_sell = client.create_market_order(i,sell_order, funds=sellsize)
	                print(market_sell)
	                message = str(str(i) + " sell order made off trend dip/price action loss " + getcurr_price())
	                msg.attach(MIMEText(message, 'plain'))
	                s.send_message(msg)
	            except KucoinAPIException as e:
	                print(str(i) + " sell not complete because " + e.message)
    if lastTrend < 0.00 and secondTrend > 0.00:
        try:
            market_buy = client.create_market_order(i,buy_order, funds=buysize)
            print(market_buy)
            message = str(str(i) + " buy order made at trend crossover at " + getcurr_price())
            msg.attach(MIMEText(message, 'plain'))
            s.send_message(msg)
        except KucoinAPIException as e:
            print(str(i) + " buy order not complete because " + e.message)
    else:
        print("no market orders for :" + str(i))

print(price_resultDF)
##WEB APP
app = dash.Dash(
    __name__, meta_tags=[{"name": "webapp", "content": "width=device-width"}]
)

server = app.server

def make_dash_table(df):
    """ Return a dash definition of an HTML table for a Pandas dataframe """
    table = []
    for index, row in df.iterrows():
        html_row = []
        for i in range(len(row)):
            html_row.append(html.Td([row[i]]))
        table.append(html.Tr(html_row))
    return table

app.layout = html.Div(
    [
        html.Div(
            [html.Table(make_dash_table(price_resultDF))],
            id="current-price",
            className="mini_container",
        ),
    ],
    id="main-container",
    className="output-display",
)

from rest_framework.response import Response
from rest_framework.decorators import api_view
import tweepy
from textblob import TextBlob
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
import requests
import re
import json
import datetime as dt
from prophet import Prophet


def analyse(input_hashtag, n):
    auth = tweepy.OAuthHandler(
        "I9US6V0tecaipw1PwVuvixJM7", "JcCFA5XLVRdAfa50fD4LrJr8MVOGF1HSGiLFx5xGpb1tUhy16J")
    auth.set_access_token("1487078600863993874-Rv0rVuvNIarXiyzQkr2aad84xcwXwW",
                          "CtbZGroQH4tRonLSDI7ZwWRIb06G8eRjf74fFfS28OeYK")
    api = tweepy.API(auth)
    N = n  # Number of Tweets
    Tweets = tweepy.Cursor(
        api.search_tweets, q=f'{input_hashtag} stocks').items(N)
    neg = 0.0
    pos = 0.0
    neg_count = 0
    neutral_count = 0
    pos_count = 0
    # print(secrets.consumer_key)
    for tweet in Tweets:
        # print(tweet)
        blob = TextBlob(tweet.text)
        pol = blob.sentiment.polarity
        print(blob, pol)
        if pol < 0:
            neg += pol
            neg_count += 1
        elif pol == 0:
            neutral_count += 1
        else:
            pos += pol
            pos_count += 1
    print(pos, neg)

    # print "Total tweets",N
    # print "Positive ",float(pos_count/N)*100,"%"
    # print "Negative ",float(neg_count/N)*100,"%"
    # print "Neutral ",float(neutral_count/N)*100,"%"
    return {'total_count': N, 'positive_count': pos_count, 'negative_count': neg_count, 'neutral_count': neutral_count}


def scrape_ticker(name):
    tokenTable = (f'http://finance.yahoo.com/lookup/equity?s={name}')
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36"}
    response = requests.get(tokenTable, headers=headers)

    soup = BeautifulSoup(response.text, 'html.parser')
    pattern = re.compile(r'\s--\sData\s--\s')
    script_data = soup.find('script', text=pattern).contents[0]

    start = script_data.find("context")-2
    json_data = json.loads(script_data[start:-12])

    li = []
    for i in json_data['context']['dispatcher']['stores']['SimilarSymbolsStore']['lookupData']['documents']:
        # print(i['exchange'])
        if i['exchange'] in ['NSI', 'BSE', 'NMS']:
            di = {}
            di['shortName'] = i['shortName'] or ''
            di['symbol'] = i['symbol']
            di['regularMarketPrice'] = i['regularMarketPrice']['fmt']
            di['exchange'] = i['exchange']
            di['regularMarketChange'] = float(i['regularMarketChange']['fmt'])
            di['regularMarketPercentChange'] = float(
                i['regularMarketPercentChange']['fmt'][:-1])
            li.append(di)
    return li


@api_view(['GET'])
def sentiment(request, s, n):
    print(s, n)
    sentiment_response = analyse(s, n)
    data = {'sentiment': sentiment_response}
    return Response(data)


@api_view(['GET'])
def ticker(request):
    st = request.query_params['search']
    ticker_list = scrape_ticker(st)
    data = {'ticker_list': ticker_list}
    return Response(data)


def scrape_top(link):
    top = requests.get(link).text
    topSoup = BeautifulSoup(top, 'html.parser')
    topData = topSoup.find('table')
    topList = []
    for row in topData.find_all("tr")[1:]:
        x = [td.get_text() for td in row.find_all("td")]
        topList.append(x)
    return topList


@api_view(['GET'])
def top_w_l(request):
    print(request)
    winners_data = scrape_top('https://ticker.finology.in/market/top-gainers')
    losers_data = scrape_top('https://ticker.finology.in/market/top-losers')
    data = {'winners_data': winners_data, 'losers_data': losers_data}
    return Response(data)


def getHistData(ticker):
    GetStockData = yf.Ticker(ticker)
    StockData = pd.DataFrame()
    StockData["ds"] = GetStockData.history(period="5y").index
    StockData["y"] = GetStockData.history(period="5y")["Close"].values
    StockData['ds'] = StockData['ds'].apply(
        lambda x: dt.datetime.strftime(x, '%Y-%m-%d'))

    # print(len(res['data']))
    model = Prophet(daily_seasonality=False)
    model.fit(StockData)
    future = model.make_future_dataframe(365, freq='D')
    forecast = model.predict(future)
    prediction = forecast[['ds', 'yhat']][-365:]
    prediction['ds'] = prediction['ds'].apply(
        lambda x: dt.datetime.strftime(x, '%Y-%m-%d'))

    res = {
        'historical':
        {
            'label': StockData['ds'].to_list(),
            'data': StockData['y'].to_list()
        },
        'prediction':
        {
            'label': prediction['ds'].to_list(),
            'data': prediction['yhat'].to_list()
        }
    }
    return res


def getCurrentData(tick):
    stock = yf.Ticker("ABEV3.SA")
    price = stock.info
    print(price)
    return price


@api_view(['GET'])
def historical(request):
    ticker = request.query_params['ticker']
    hist_data = getHistData(ticker)
    current_data = getCurrentData(ticker)
    return Response(hist_data)

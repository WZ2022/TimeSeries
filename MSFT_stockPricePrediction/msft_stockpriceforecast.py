# -*- coding: utf-8 -*-
"""MSFT_StockPriceForecast.ipynb

# Part 0: Set up environment and load data
"""

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials

from tabulate import tabulate
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import statsmodels.api as sm
import seaborn as sns
from pylab import rcParams
from statsmodels.tsa.arima_model import ARMA

import itertools
import warnings
from statsmodels.stats.diagnostic import acorr_ljungbox
from sklearn import preprocessing
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.layers import Dropout
from keras.layers import *
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from keras.callbacks import EarlyStopping

auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
drive = GoogleDrive(gauth)

"""Data could be downloaded from Yahoo.com"""

link = 'https://drive.google.com/open?id='


fluff, id = link.split('=')
file = drive.CreateFile({'id':id}) 
file.GetContentFile('MSFT_Stock.csv') 
#read in data, take date as the index
microsoft  = pd.read_csv('MSFT_Stock.csv', index_col='Date', parse_dates=['Date'])
microsoft.head()

len(microsoft)

TS_Monthly_df   = pd.read_csv('MSFT_Stock.csv')
TS_df = microsoft

"""# Part 1: Data Exploration

# Part 1.1 Raw Dataset
"""

TS_df.info()

TS_df.nunique()

TS_df.isnull().sum()

"""# Part 1.2 EDA"""

TS_df['2015':'2021'].plot(subplots=True, figsize=(10,12))
plt.title('MSFT stock attributes from 2015 to 2021')

"""There's an upward trend of open, high, low, close price."""

#shift the high price by one day
TS_df['Change'] = TS_df.High.div(TS_df.High.shift())
TS_df['Change'].plot(figsize=(20,8))
plt.title("Changes over time")

""""Return on investment (ROI) is an approximate measure of an investment's profitability.ROI is calculated by subtracting the initial value of the investment from the final value of the investment (which equals the net return), then dividing this new number (the net return) by the cost of the investment, then finally, multiplying it by 100.""""

TS_df['Return'] = TS_df.Change.sub(1).mul(100)
TS_df['Return'].plot(figsize=(20,8))
plt.title("ROI over time")

"""Apply window functions"""

rolling_MSFT = TS_df.High.rolling('90D').mean() #mean of high price within 90 days
# rolling_MSFT
TS_df.High.plot(figsize=(20,8))
rolling_MSFT.plot()

plt.legend(['High','Rolling Mean'])

rolling_MSFT_low = TS_df.Low.rolling('30D').mean() #mean of low price within 90 days
TS_df.Low.plot(figsize=(20,8))
rolling_MSFT_low.plot()

plt.legend(['Low','Rolling Mean'])

microsoft_mean = TS_df.High.expanding().mean()
microsoft_std = TS_df.High.expanding().std()
TS_df.High.plot(figsize=(20,8))
microsoft_mean.plot()
microsoft_std.plot()
plt.legend(['High','Expanding Mean','Expanding Standard Deviation'])

"""Check acf and pacf plots"""

plot_acf(TS_df.High,lags=75,title="ACF: MSFT High")

plot_pacf(TS_df.High,lags=75,title="PACF: MSFT High")

plot_pacf(TS_df["Close"],lags=50,title="ACF: MSFT Close")

TS_Monthly_df['dateN']=pd.to_datetime(TS_Monthly_df['Date'])
TS_Monthly_df.set_index('dateN',inplace=True)
TS_Monthly_df.head()

"""plot the mean of each year's close price"""

TS_Monthly_df['Close'].resample('Y').mean().plot(figsize=(15,8), grid = True)

TS_Monthly_df.describe()

"""# Part 2: Data Cleaning and Feature Preprocessing"""

sns.pairplot(data=TS_Monthly_df, height=1.5)

"""Open, High, Low, Close have positive relationships between each two.

Conduct a seasonal decomposition on close price by yearly frequence, to get rid of trend and seasonality.
"""

rcParams['figure.figsize'] = 12, 8
pred_df_sim1_new = sm.tsa.seasonal_decompose(TS_Monthly_df.Close, model='additive', freq=360)
pred_df_sim2_full = TS_Monthly_df.Close
figure = pred_df_sim1_new.plot()
plt.show()

"""Get rid of missing value"""

len(pred_df_sim1_new.resid)
#pred_df_sim1_new.resid.isnull().sum() #360

sim1=pred_df_sim1_new.resid.dropna()
sim2 = pred_df_sim2_full.dropna()

"""# Part 3: Modeling"""

plt.plot(sim1)

plot_acf(sim1, lags = 25)

plot_pacf(sim1, lags=25)

"""PACF?????????ACF?????????AR????????????PACF????????????p=2."""

#fit an AR(2) model
model = ARMA(sim1, order=(2,0))
result = model.fit()

# Predicting simulated AR(2) model 
result.plot_predict(start=1000, end=1200) #Plot forecasts
plt.show()

"""The forecast line stayed close to the 'Close' price"""

plt.plot(sim2)

plot_pacf(sim2, lags=25)

plot_acf(sim2, lags=25)

model_s = sm.tsa.statespace.SARIMAX(sim2, order=(2, 3, 3),)
MSFTresults = model_s.fit()
print(MSFTresults.summary().tables[1])

MSFTresults.aic

MSFTresults.bic

# model_s = sm.tsa.statespace.SARIMAX(sim2, order=(2, 3, 2),)
# MSFTresults = model_s.fit()
# MSFTresults.aic, MSFTresults.aic

MSFTresults.plot_diagnostics(figsize=(15, 12))
plt.show()

print(acorr_ljungbox(MSFTresults.resid, lags=6))

"""<0.05:not white noise"""

pred = MSFTresults.get_prediction(start=1400, dynamic=False)

"""dynamic=False???????????????????????????????????????????????????????????????????????????"""

pred_ci = pred.conf_int() #Returns the confidence interval of the fitted parameters. 
pred_ci

ax = sim2['2020':].plot(label='observed')
pred.predicted_mean.plot(ax=ax, label='Forecast', alpha=.6)
ax.fill_between(pred_ci.index, pred_ci.iloc[:, 0], pred_ci.iloc[:, 1], color='k', alpha=.2)
ax.set_xlabel('Date')
ax.set_ylabel('MSFT price')
plt.legend()
plt.show()

"""# Part 4: Model Evaluation & Tuning parameters"""

y_forecasted = pred.predicted_mean
y_truth1 = TS_df.Close['2020-10-21 16:00:00':]

# Compute the mean square error
mse = ((y_forecasted - y_truth1) ** 2).mean()
print('The Mean Squared Error of our forecast 1 is {}'.format(round(mse, 2)))

"""Use AIC&BIC to choose the best parameters"""

p_min=0
d_min=0
q_min=0
p_max=4
d_max=4
q_max=4
 
# Initialize a DataFrame to store the results
results_bic = pd.DataFrame(index=['AR{}'.format(i) for i in range(p_min,p_max+1)],
                           columns=['MA{}'.format(i) for i in range(q_min,q_max+1)])
# get the results of different combination of p,d,q
for p,d,q in itertools.product(range(p_min,p_max+1),
                               range(d_min,d_max+1),
                               range(q_min,q_max+1)):
    if p==0 and d==0 and q==0:
        results_bic.loc['AR{}'.format(p), 'MA{}'.format(q)] = np.nan
        continue 
    try:
        model = sm.tsa.SARIMAX(sim2, order=(p, d, q),
                               #enforce_stationarity=False,
                               #enforce_invertibility=False,
                              )
        results = model.fit() 
## print(model_results.summary())
## print(model_results.summary().tables[1])
        # print("results.bic",results.bic)
        # print("results.aic",results.aic)
        results_bic.loc['AR{}'.format(p), 'MA{}'.format(q)] = results.bic
    except:
        continue
results_bic = results_bic[results_bic.columns].astype(float)

results_bic

fig, ax = plt.subplots(figsize=(10, 8))
ax = sns.heatmap(results_bic,
                 mask=results_bic.isnull(),
                 cmap=sns.diverging_palette(6000, 12000, n=200),
                 ax=ax,
                 annot=True,
                 fmt='.2f',
                 );
ax.set_title('BIC');

"""ARMA(1,,3) gives the lowest BIC."""

# Initialize a DataFrame to store the results
results_aic = pd.DataFrame(index=['AR{}'.format(i) for i in range(p_min,p_max+1)],
                           columns=['MA{}'.format(i) for i in range(q_min,q_max+1)])
# get the results of different combination of p,d,q
for p,d,q in itertools.product(range(p_min,p_max+1),
                               range(d_min,d_max+1),
                               range(q_min,q_max+1)):
    if p==0 and d==0 and q==0:
        results_aic.loc['AR{}'.format(p), 'MA{}'.format(q)] = np.nan
        continue 
    try:
        model = sm.tsa.SARIMAX(sim2, order=(p, d, q),
                               #enforce_stationarity=False,
                               #enforce_invertibility=False,
                              )
        results = model.fit() 
## print(model_results.summary())
## print(model_results.summary().tables[1])
        # print("results.bic",results.bic)
        # print("results.aic",results.aic)
        results_aic.loc['AR{}'.format(p), 'MA{}'.format(q)] = results.aic
    except:
        continue
results_aic = results_aic[results_aic.columns].astype(float)

fig, ax = plt.subplots(figsize=(10, 8))
ax = sns.heatmap(results_aic,
                 mask=results_aic.isnull(),
                 #cmap=sns.diverging_palette(6000, 12000, n=200),
                 ax=ax,
                 annot=True,
                 fmt='.2f',
                 );
ax.set_title('AIC');

"""ARMA(3,,4) gives the smallest aic.

Try modelling ARMA(1,3,3)
"""

model1 = sm.tsa.statespace.SARIMAX(sim2, order=(1, 3, 3),)
result1 = model1.fit()
print(result1.summary().tables[1])

pred1 = result1.get_prediction(start=1400, dynamic=True)
pred1_ci = pred1.conf_int()
ax = sim2['2020':].plot(label='observed')
pred1.predicted_mean.plot(ax=ax, label='Forecast', alpha=.6)
ax.fill_between(pred1_ci.index, pred1_ci.iloc[:, 0], pred1_ci.iloc[:, 1], color='k', alpha=.2)
ax.set_xlabel('Date')
ax.set_ylabel('MSFT price')
plt.legend()
plt.show()

y_forecasted1 = pred1.predicted_mean
mse = ((y_forecasted1 - y_truth1) ** 2).mean()
mse

"""ARMA(3,3,4)"""

model2 = sm.tsa.statespace.SARIMAX(sim2, order=(3, 3, 4),)
result2 = model2.fit()
print(result2.summary().tables[1])

pred2 = result2.get_prediction(start=1400, dynamic=True)
pred2_ci = pred2.conf_int()
ax = sim2['2020':].plot(label='observed')
pred1.predicted_mean.plot(ax=ax, label='Forecast', alpha=.6)
ax.fill_between(pred2_ci.index, pred2_ci.iloc[:, 0], pred2_ci.iloc[:, 1], color='k', alpha=.2)
ax.set_xlabel('Date')
ax.set_ylabel('MSFT price')
plt.legend()
plt.show()

y_forecasted2 = pred2.predicted_mean
mse = ((y_forecasted2 - y_truth1) ** 2).mean()
mse

"""# Part 5: Improvement

Use LSTM

# Part 5.1: Data Preprocessing
"""

MSFT_df = pd.read_csv('MSFT_Stock.csv')

MSFT_df.head()

"""Split training and testing set"""

train = MSFT_df.iloc[:1000, 4:5].values
test = MSFT_df.iloc[1000:, 4:5].values

train.shape, test.shape

"""Normalization: scale the feature into range (0,1)"""

scaler = MinMaxScaler(feature_range=(0,1))
train_scaled = scaler.fit_transform(train)

train_scaled.shape

"""Separate training set into training data and labels: 60 time-steps corresponding to 1 output"""

x_train, y_train = [], []
for i in range(60,1000):
  x_train.append(train_scaled[i-60:i, 0])
  y_train.append(train_scaled[i, 0])

x_train, y_train = np.array(x_train), np.array(y_train)

x_train.shape, y_train.shape

x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))

"""# Part 5.2: Modeling

build LSTM with 50 neurons and 4 hidden layers
"""

model = Sequential()
#setting return sequences to True to access the hidden state output for each input time step.
model.add(LSTM(units = 50, return_sequences = True, input_shape = (x_train.shape[1], 1)))
model.add(Dropout(0.2))
model.add(LSTM(units = 50, return_sequences = True))
model.add(Dropout(0.2))
model.add(LSTM(units = 50, return_sequences = True))
model.add(Dropout(0.2))
model.add(Dense(units = 1))

model.compile(optimizer = 'adam', loss = 'mean_squared_error')

model.fit(x_train, y_train, epochs = 100, batch_size = 32)

"""Prepare testing set"""

test_scaled = scaler.fit_transform(test)
test_scaled.shape

# dataset_train = MSFT_df.iloc[:1000, 4:5]
# dataset_test = MSFT_df.iloc[1000:, 4:5]
# dataset_total = pd.concat((dataset_train, dataset_test), axis = 0)
# dataset_total

# inputs = dataset_total[len(dataset_total) - len(dataset_test) - 60:].values
# inputs = inputs.reshape(-1,1)
# inputs = scaler.transform(inputs)
# inputs[:10]

# x_test = []
# for i in range(60, 571):
#     x_test.append(inputs[i-60:i, 0])
# x_test = np.array(x_test)
# x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))
# x_test.shape

#test = test.reshape(-1, 1)
# test_scaled = scaler.fit_transform(test)
# test_scaled.shape

# test_scaled[:10]

# x_test = []
# for i in range(60, 511):
#   x_test.append(test_scaled[i-60:i, 0])

# x_test = np.array(x_test)
# x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))
# x_test.shape

"""Make predictions using the test set"""

y_pred = model.predict(test_scaled)
y_pred.shape

y_pred[:5]

y_pred = y_pred.reshape((-1,1))
y_pred.shape

y_pred[:5]

predicted_close_price = scaler.inverse_transform(y_pred)

predicted_close_price.shape

predicted_close_price[:5]

"""Visualize the results"""

plt.figure(figsize=(20, 8))
plt.plot(test, color = 'red', label = 'Real MSFT Close Price')
plt.plot(predicted_close_price, color = 'blue', label = 'Predicted MSFT Close Price')
plt.xticks(np.arange(0,510,100))
plt.title('MSFT Close Price Prediction')
plt.xlabel('Time')
plt.ylabel('MSFT Close Price')
plt.legend()
plt.show()

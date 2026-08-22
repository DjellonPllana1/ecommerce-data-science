"""Leakage-safe autoregressive feature construction and recursion."""
from __future__ import annotations
import numpy as np
import pandas as pd
FEATURES=["lag_1","lag_2","lag_3","lag_7","lag_14","lag_28","rolling_mean_7","rolling_mean_14","rolling_mean_28","rolling_std_7","rolling_std_28","day_of_week","day_of_month","month","quarter","week_of_year","is_weekend","time_index"]
def make_features(series:pd.Series)->pd.DataFrame:
    frame=pd.DataFrame(index=series.index)
    for lag in [1,2,3,7,14,28]: frame[f"lag_{lag}"]=series.shift(lag)
    shifted=series.shift(1)
    for window in [7,14,28]: frame[f"rolling_mean_{window}"]=shifted.rolling(window).mean()
    for window in [7,28]: frame[f"rolling_std_{window}"]=shifted.rolling(window).std()
    frame["day_of_week"]=frame.index.dayofweek; frame["day_of_month"]=frame.index.day; frame["month"]=frame.index.month; frame["quarter"]=frame.index.quarter; frame["week_of_year"]=frame.index.isocalendar().week.astype(int); frame["is_weekend"]=(frame.index.dayofweek>=5).astype(int); frame["time_index"]=(frame.index-series.index.min()).days
    frame["target"]=series; return frame.dropna()
def next_feature_row(history:pd.Series,date:pd.Timestamp,origin:pd.Timestamp)->pd.DataFrame:
    values={f"lag_{lag}":history.iloc[-lag] for lag in [1,2,3,7,14,28]}
    for window in [7,14,28]: values[f"rolling_mean_{window}"]=history.iloc[-window:].mean()
    for window in [7,28]: values[f"rolling_std_{window}"]=history.iloc[-window:].std()
    values.update(day_of_week=date.dayofweek,day_of_month=date.day,month=date.month,quarter=date.quarter,week_of_year=int(date.isocalendar().week),is_weekend=int(date.dayofweek>=5),time_index=(date-origin).days)
    return pd.DataFrame([values],index=[date])[FEATURES]
def recursive_model_forecast(model,history:pd.Series,horizon:int)->pd.Series:
    working=history.copy(); origin=history.index.min(); predictions=[]
    for date in pd.date_range(history.index.max()+pd.Timedelta(days=1),periods=horizon,freq="D"):
        value=max(0,float(model.predict(next_feature_row(working,date,origin))[0])); predictions.append(value); working.loc[date]=value
    return pd.Series(predictions,index=pd.date_range(history.index.max()+pd.Timedelta(days=1),periods=horizon,freq="D"))

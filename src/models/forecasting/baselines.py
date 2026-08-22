"""Meaningful recursive daily forecasting baselines."""
from __future__ import annotations
import pandas as pd
def baseline_forecast(name:str,history:pd.Series,horizon:int)->pd.Series:
    working=history.copy(); values=[]; dates=pd.date_range(history.index.max()+pd.Timedelta(days=1),periods=horizon,freq="D")
    for date in dates:
        if name=="NaiveLastValue": value=working.iloc[-1]
        elif name=="HistoricalMean": value=history.mean()
        elif name=="SeasonalNaive7": value=working.iloc[-7]
        elif name=="RollingMean7": value=working.iloc[-7:].mean()
        else: raise ValueError(f"Unknown baseline: {name}")
        values.append(max(0,float(value))); working.loc[date]=values[-1]
    return pd.Series(values,index=dates)
BASELINES=["NaiveLastValue","HistoricalMean","SeasonalNaive7","RollingMean7"]

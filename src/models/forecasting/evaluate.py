"""Walk-forward evaluation and residual metrics."""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error,mean_squared_error
from .baselines import BASELINES,baseline_forecast
from .features import FEATURES,make_features,recursive_model_forecast
def metrics(actual,predicted):
    actual=np.asarray(actual); predicted=np.asarray(predicted); nonzero=actual!=0
    return {"mae":mean_absolute_error(actual,predicted),"rmse":mean_squared_error(actual,predicted)**.5,"mape":np.mean(np.abs((actual[nonzero]-predicted[nonzero])/actual[nonzero]))*100 if nonzero.any() else np.nan,"smape":np.mean(200*np.abs(actual-predicted)/np.where(np.abs(actual)+np.abs(predicted)==0,np.nan,np.abs(actual)+np.abs(predicted)))}
def folds(series:pd.Series,holdout_days=30,fold_days=30,fold_count=3):
    end=len(series)-holdout_days; result=[]
    for i in range(fold_count,0,-1):
        validation_start=end-i*fold_days; validation_end=validation_start+fold_days; result.append((series.iloc[:validation_start],series.iloc[validation_start:validation_end]))
    return result
def evaluate_candidates(series,model_factories):
    rows=[]; prediction_rows=[]
    for fold_id,(train,valid) in enumerate(folds(series),1):
        for name in BASELINES:
            pred=baseline_forecast(name,train,len(valid)); rows.append({"model":name,"fold":fold_id,**metrics(valid,pred)}); prediction_rows.extend({"date":d,"actual":a,"predicted":p,"model":name,"fold":fold_id} for d,a,p in zip(valid.index,valid,pred))
        training=make_features(train)
        for name,factory in model_factories.items():
            model=factory(); model.fit(training[FEATURES],training.target); pred=recursive_model_forecast(model,train,len(valid)); rows.append({"model":name,"fold":fold_id,**metrics(valid,pred)}); prediction_rows.extend({"date":d,"actual":a,"predicted":p,"model":name,"fold":fold_id} for d,a,p in zip(valid.index,valid,pred))
    return pd.DataFrame(rows),pd.DataFrame(prediction_rows)

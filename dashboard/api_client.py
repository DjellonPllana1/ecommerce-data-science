import os
import requests

BASE_URL=os.getenv('API_BASE_URL','http://127.0.0.1:8000')
class APIError(RuntimeError): pass
def request(method,path,**kwargs):
    try:
        response=requests.request(method,f'{BASE_URL}{path}',timeout=30,**kwargs); response.raise_for_status(); return response.json()
    except requests.RequestException as exc: raise APIError(f'Application service unavailable: {exc}') from exc
def get(path,**params): return request('GET',path,params=params)
def post(path,payload): return request('POST',path,json=payload)

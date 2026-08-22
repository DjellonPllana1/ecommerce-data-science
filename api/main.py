from contextlib import asynccontextmanager
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from api.config import settings
from api.dependencies import model_bundle
from api.routers import analytics,customers,delivery,forecasting,health

@asynccontextmanager
async def lifespan(_app: FastAPI):
    model_bundle()
    yield

app=FastAPI(title=settings.title,version=settings.version,description='Read-only analytics and persisted-model inference for the Olist portfolio project.',lifespan=lifespan)
for router in (health.router,analytics.router,delivery.router,customers.router,forecasting.router): app.include_router(router)
@app.exception_handler(RuntimeError)
def runtime_error(_request:Request,exc:RuntimeError): return JSONResponse(status_code=503,content={'detail':str(exc)})
@app.get('/',include_in_schema=False)
def root(): return {'name':settings.title,'docs':'/docs','health':'/health'}

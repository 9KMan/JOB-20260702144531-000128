"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import ingest, health
from lib.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Starting Looker Studio Data Pipeline API')
    yield
    logger.info('Shutting down Looker Studio Data Pipeline API')


app = FastAPI(
    title='Looker Studio Data Pipeline API',
    description='Ingest text data from APIs, webhooks, and scrapers into the pipeline.',
    version='1.0.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(health.router, prefix='', tags=['health'])
app.include_router(ingest.router, prefix='', tags=['ingest'])


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('api.main:app', host='0.0.0.0', port=settings.API_PORT, reload=False)

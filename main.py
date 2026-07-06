import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.router import router
from db.connection import engine as db_engine, Base
from db.seed import run_seed


def init_db():
    for attempt in range(10):
        try:
            Base.metadata.create_all(bind=db_engine)
            run_seed()
            return
        except Exception:
            if attempt < 9:
                time.sleep(2)
            else:
                raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Nodexa", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}

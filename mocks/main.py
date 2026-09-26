import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from synthetic_data import generate_synthetic_data
from nsp.router import router as nsp_router
from sfmp.router import router as sfmp_router
from nos.router import router as nos_router
from digilocker.router import router as digilocker_router
from uidai.router import router as uidai_router
from aishe.router import router as aishe_router
from udise.router import router as udise_router
from apaar.router import router as apaar_router
from edistrict.router import router as edistrict_router
from nta.router import router as nta_router
from pfms.router import router as pfms_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    generate_synthetic_data()
    yield

app = FastAPI(title="ScholarSetu Mocks", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nsp_router, prefix="/nsp", tags=["NSP"])
app.include_router(sfmp_router, prefix="/sfmp", tags=["SFMP"])
app.include_router(nos_router, prefix="/nos", tags=["NOS"])
app.include_router(digilocker_router, prefix="/digilocker", tags=["DigiLocker"])
app.include_router(uidai_router, prefix="/uidai", tags=["UIDAI"])
app.include_router(aishe_router, prefix="/aishe", tags=["AISHE"])
app.include_router(udise_router, prefix="/udise", tags=["UDISE"])
app.include_router(apaar_router, prefix="/apaar", tags=["APAAR"])
app.include_router(edistrict_router, prefix="/edistrict", tags=["eDistrict"])
app.include_router(nta_router, prefix="/nta", tags=["NTA"])
app.include_router(pfms_router, prefix="/pfms", tags=["PFMS"])

@app.get("/health")
def health_check():
    return {"status": "ok"}

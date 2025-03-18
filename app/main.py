"""
This file is part of Giswater
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
import os
from . import config

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import features, hydraulic_engine_ud, hydraulic_engine_ws, mincut, water_balance

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
if config.get_bool("api", "features"):
    app.include_router(features.router)
if config.get_bool("api", "mincut"):
    app.include_router(mincut.router)
if config.get_bool("api", "water_balance"):
    app.include_router(water_balance.router)
if config.get_bool("hydraulic_engine", "enabled"):
    if config.get_bool("hydraulic_engine", "ud"):
        app.include_router(hydraulic_engine_ud.router)
    if config.get_bool("hydraulic_engine", "ws"):
        app.include_router(hydraulic_engine_ws.router)

@app.get("/")
async def root():
    return {"message": "FastAPI Application"}

# Favicon endpoint
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join("app", "static", "favicon.ico")
    return FileResponse(favicon_path)

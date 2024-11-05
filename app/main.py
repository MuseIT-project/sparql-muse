# app/main.py
from fastapi import FastAPI, Response
from utils import buildgraph
import json
from fastapi import Query
app = FastAPI()

@app.get("/")
async def root(q: str = Query(None)):
    thistopic = '"coin/coin-related"@en'
    return Response(json.dumps(buildgraph(thistopic, q), indent=4), media_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    #return {"message": "Hello, FastAPI with Docker!"}


# app/main.py
from fastapi import FastAPI, Response
from utils import buildgraph
import json
from fastapi import Query
app = FastAPI()

@app.get("/")
async def root(thisfilter: str = Query(None)):
    q = '"coin/coin-related"@en'
    return Response(json.dumps(buildgraph(q, thisfilter), indent=4), media_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
    #return {"message": "Hello, FastAPI with Docker!"}


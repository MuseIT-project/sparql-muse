# app/main.py
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from utils import buildgraph, autosuggest
import json
from fastapi import Query
app = FastAPI()

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

@app.get("/")
async def root(
    q: str = Query(default=None),
    subject: str = Query(default=None, description="Subject of the triple"),
    predicate: str = Query(default=None, description="Predicate of the triple"),
    object: str = Query(default=None, description="Object of the triple"),
    suggest: str = Query(default=None, description="Use autosuggest instead of graph")
):
    thistopic = '"coin/coin-related"@en'
    inputparams = {
        "topic": thistopic,
        "q": q,
        "subject": subject,
        "predicate": predicate,
        "object": object,
    }
    if suggest:
        inputparams["suggest"] = suggest
    if suggest is not None:
        return Response(
            json.dumps(autosuggest(inputparams), indent=4),
            media_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    return Response(
        json.dumps(buildgraph(inputparams), indent=4),
        media_type="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )


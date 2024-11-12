import requests
import csv
import io
import re
import json
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get MIN_AMOUNT from environment variables, default to 1 if not set
MIN_AMOUNT = int(os.getenv("MIN_AMOUNT", 1))

def getdates(entity):
    pattern = r"\b(\d{4})-(\d{4})\b"

    # Find all dates in the specified range
    dates = re.findall(pattern, entity)
    return dates

def autosuggest(inputparams):
    if not inputparams.get("suggest"):
        return []
        
    query = f"""
    SELECT ?object (COUNT(?subject) AS ?frequency)
    WHERE {{
      {{
        ?subject <https://schema.org/keywords> ?object .
        FILTER(CONTAINS(LCASE(STR(?subject)), "{inputparams['suggest'].lower()}"))
      }}
      UNION
      {{
        ?subject <https://schema.org/keywords> ?object .
        FILTER(CONTAINS(LCASE(STR(?object)), "{inputparams['suggest'].lower()}"))
      }}
    }}
    GROUP BY ?object
    HAVING(?frequency > 0)
    ORDER BY DESC(?frequency)
    """

    headers = {
        "Accept": "text/tab-separated-values",
        "Content-type": "application/sparql-query"
    }

    url = os.environ.get('SPARQL_ENDPOINT')
    response = requests.post(url, headers=headers, data=query)
    
    suggestions = []
    if response.status_code == 200:
        tsv_data = io.StringIO(response.text)
        reader = csv.DictReader(tsv_data, delimiter='\t')
        for row in reader:
            suggestions.append({
                "value": row["?object"],
                "frequency": int(row["?frequency"])
            })
            
    return suggestions

def buildgraph(inputparams):
    # SPARQL endpoint URL
    extra = ''
    customquery = ''
    topicsparql = ''
    if inputparams.get("q"):
        customquery = f"FILTER(CONTAINS(STR(?relatedKeyword1), \"{inputparams['q']}\"))"
    
    # Add additional filters for subject, predicate, object if they exist
    if inputparams.get("subject") is not None and inputparams["subject"]:
        extra += f"\nFILTER(CONTAINS(STR(?s), \"{inputparams['subject']}\"))"
    if inputparams.get("predicate") is not None and inputparams["predicate"]:
        extra += f"\nFILTER(CONTAINS(STR(?p), \"{inputparams['predicate']}\"))"
    if inputparams.get("object") is not None and inputparams["object"]:
        extra += f"\nFILTER(CONTAINS(STR(?o), \"{inputparams['object']}\"))"
    if extra: # and not customquery:
        topicsparql = ''
    else:
        if 'topic' in inputparams:
            topicsparql = f"?s ?p {inputparams['topic']} ."
        if customquery:
            topicsparql += f"\nFILTER(CONTAINS(STR(?relatedKeyword1), \"{inputparams['q']}\"))" 
    
    logging.error(f"Input parameters: {inputparams}")
    # Build field filters, using schema.org/keywords as default
    field_filters = ""
    if inputparams.get("field"):
        field_conditions = []
        for field in inputparams["field"]:
            field_conditions.append(f"?p = {field}")
        if field_conditions:
            field_filters = f"FILTER({' || '.join(field_conditions)})"
    else:
        # Default to schema.org/keywords if no fields specified
        field_filters = "FILTER(?p = <https://schema.org/keywords>)"
    
    dans_query = f"""
    SELECT ?relatedKeyword1 ?relatedKeyword2 (COUNT(*) AS ?amount) WHERE {{
    ?s ?p ?relatedKeyword1 .
    ?s ?p ?relatedKeyword2 .
    {topicsparql}
    FILTER(?relatedKeyword1 != ?relatedKeyword2) 
    FILTER(CONTAINS(STR(?relatedKeyword1), "(")) 
    FILTER(CONTAINS(STR(?relatedKeyword2), "("))
    {field_filters}
    {extra}
    }} 
    GROUP BY ?relatedKeyword1 ?relatedKeyword2 
    ORDER BY DESC(?amount)
    """

    harvard_query = f"""SELECT ?relatedKeyword1 ?relatedKeyword2 (COUNT(*) AS ?amount)
    WHERE {{
    ?subject ?p "{inputparams['q']}"@en .
    ?subject ?p ?relatedKeyword1 .
    
    # Find all other terms associated with those subjects
    ?subject ?p ?relatedKeyword2 .
    
    # Exclude the search term itself from results and ensure terms are different
    FILTER(?relatedKeyword2 != "{inputparams['q']}"@en)
    FILTER(?relatedKeyword1 != "{inputparams['q']}"@en)
    FILTER(?relatedKeyword2 != ?relatedKeyword1)
    {field_filters}
    }}
    GROUP BY ?relatedKeyword1 ?relatedKeyword2 
    ORDER BY DESC(?amount)"""
        
    if 'SOURCE' in os.environ:
        if 'dans' in os.environ.get('SOURCE'):
            query = dans_query
    else:
        query = harvard_query
    
    print(query)
    #

    # HTTP headers
    headers = {
        "Accept": "text/tab-separated-values",
        "Content-type": "application/sparql-query"
    }

    # Send the request
    url = os.environ.get('SPARQL_ENDPOINT')
    response = requests.post(url, headers=headers, data=query)
    #print(response.text)
    # Check if the request was successful
    nodes = []
    links = []
    pairs = {}
    if response.status_code == 200:
        # Parse the TSV response into JSON-like structure
        data = []
        tsv_data = io.StringIO(response.text)
        reader = csv.DictReader(tsv_data, delimiter='\t')
        
        for row in reader:
    #        print(row["relatedKeyword1"])
            try:
                thisgroup = 1
                name = ''
                if getdates(row["?relatedKeyword1"]):
                    thisgroup = 2
                    name = row["?relatedKeyword1"]
                else:
                    name = row["?relatedKeyword1"]
                data.append({
                    "relatedKeyword1": row["?relatedKeyword1"],
                    "relatedKeyword2": row["?relatedKeyword2"],
                    "amount": int(row["?amount"]),
                    "group": thisgroup,
                    "name": name
                })
            except:
                skip = True
        
        known = {}
        # Print or process the data
        for item in data:
            if not str(item) in known:
                pair1 = "%s-%s" % (item["relatedKeyword1"], item["relatedKeyword2"])
                pair2 = "%s-%s" % (item["relatedKeyword2"], item["relatedKeyword1"])
                if not pair1 in pairs and not pair2 in pairs:
                    pairs[pair1] = True
                    pairs[pair2] = True
                    if item['amount'] >= MIN_AMOUNT:
                        if not {"source": item["relatedKeyword1"], "target": item["relatedKeyword2"], "value": item['amount'] } in links:
                            links.append( {"source": item["relatedKeyword1"], "target": item["relatedKeyword2"], "value": item['amount'] })

                        if pair1:
                            if getdates(item['relatedKeyword1']):
                                group = 2
                            else:
                                group = 1
                        if not {"id": item['relatedKeyword1'], "group": group } in nodes:
                            nodes.append( {"id": item['relatedKeyword1'], "group": group })
                        if pair1:
                            if getdates(item['relatedKeyword2']):
                                group = 2
                            else:
                                group = 1
                        if not {"id": item['relatedKeyword2'], "group": group } in nodes:
                            nodes.append( {"id": item['relatedKeyword2'], "group": group })
            known[str(item)] = True
    #    print(data)
    else:
        print("Error:", response.status_code, response.text)
    finaldata = { "nodes": nodes, "links": links }
    return finaldata
    #print(json.dumps(finaldata))

def getpredicates():
    query = """SELECT DISTINCT ?predicate
    WHERE {
      ?subject ?predicate ?object.
    }
    LIMIT 100
    """

    headers = {
        "Accept": "text/tab-separated-values",
        "Content-type": "application/sparql-query"
    }

    url = os.environ.get('SPARQL_ENDPOINT')
    response = requests.post(url, headers=headers, data=query)
    
    predicates = []
    if response.status_code == 200:
        tsv_data = io.StringIO(response.text)
        reader = csv.DictReader(tsv_data, delimiter='\t')
        for row in reader:
            predicates.append(row["?predicate"])
            
    return predicates

import requests
import csv
import io
import re
import json
import os
def getdates(entity):
    pattern = r"\b(\d{4})-(\d{4})\b"

    # Find all dates in the specified range
    dates = re.findall(pattern, entity)
    return dates

def buildgraph(inputparams):
    # SPARQL endpoint URL
    extra = ''
    customquery = ''
    if inputparams.get("q"):
        customquery = f"FILTER(CONTAINS(STR(?relatedKeyword1), \"{inputparams['q']}\"))"
    
    # Add additional filters for subject, predicate, object if they exist
    if inputparams.get("subject"):
        extra += f"\nFILTER(CONTAINS(STR(?s), \"{inputparams['subject']}\"))"
    if inputparams.get("predicate"):
        extra += f"\nFILTER(CONTAINS(STR(?p), \"{inputparams['predicate']}\"))"
    if inputparams.get("object"):
        extra += f"\nFILTER(CONTAINS(STR(?o), \"{inputparams['object']}\"))"
    if extra and not customquery:
        topicsparql = ''
    else:
        topicsparql = f"?s ?p {inputparams['topic']} ."
    
    query = f"""
    SELECT ?relatedKeyword1 ?relatedKeyword2 (COUNT(*) AS ?amount) WHERE {{
    ?s ?p ?relatedKeyword1 .
    ?s ?p ?relatedKeyword2 .
    {topicsparql}
    FILTER(?relatedKeyword1 != ?relatedKeyword2) 
    FILTER(CONTAINS(STR(?relatedKeyword1), "(")) 
    FILTER(CONTAINS(STR(?relatedKeyword2), "("))
    {extra}
    }} 
    GROUP BY ?relatedKeyword1 ?relatedKeyword2 
    ORDER BY DESC(?amount)
    """
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
                    #if item['name']:
                    #    if item['amount'] > 1:
                    #        if not {"id": item['name'], "group": item["group"] } in nodes:
                    #            nodes.append( {"id": item['name'], "group": item["group"] })
                    if item['amount'] > 1:
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

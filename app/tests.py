from LinkedOpenData import LinkedOpenData
import json
import asyncio
import requests
import os
import sys
import json

# Example usage
wiki_gpt = LinkedOpenData("Albert Einstein, a theoretical physicist who developed the theory of relativity.")
wiki_gpt.switch_debug(True)
#wiki_gpt.build_graph()
wikipedia_data = wiki_gpt.lookup_wikipedia_concept('developed', 'property')
print(json.dumps(wikipedia_data, indent=4))  # This will print the search results

# Example Usage for getting Wikipedia URI
wikidata_id = "Q42"  # Douglas Adams
language = "en"
wikipedia_uri = wiki_gpt.get_wikipedia_uri_from_api(wikidata_id, language)
print(wikipedia_uri)  # This will print the Wikipedia link for Douglas Adams

async def main():
    q = "Artificial intelligence"
    q = "Albert Einstein"
    result = await wiki_gpt.get_wikipedia_intro('en', q)
    return result

# Run the main function
result = asyncio.run(main())

# New example usage for looking up sentences
long_text = "Albert Einstein was a theoretical physicist. He developed the theory of relativity. Albert Einstein was born in Germany and invented the theory of relativity in 1905."
#long_text = "Albert Einstein, a theoretical physicist who developed the theory of relativity."
long_text = result
wikipedia_data = wiki_gpt.lookup_sentences(long_text, 'property')
#print(json.dumps(wikipedia_data, indent=4))  # This will print the search results for each sentence
#print(wiki_gpt.termgraph.serialize(format='turtle'))  # Print the graph in Turtle format
#print(wiki_gpt.termgraph.serialize(format='json-ld'))  # Print the graph in Turtle format

term = "Albert" # Einstein"
datadir = "data/"
entity = "PERSON"
persons = wiki_gpt.get_persons_with_context(entity="PERSON") #term)
subgraph = wiki_gpt.get_graph_entities(entity=entity)
export = wiki_gpt.export_graph(subgraph, format='turtle', filename=datadir + entity + "_graph.ttl")
#print(json.dumps(persons, indent=4))  # This will print the search results for each sentence

#print(wiki_gpt.relationships)
#print(wiki_gpt.dependencies)
wiki_gpt.export_dependencies(wiki_gpt.dependencies, filename=datadir + entity + "_dependencies.json")
wiki_gpt.export_relationships(wiki_gpt.relationships, filename=datadir + entity + "_relationships.json")

WIKI = False
if WIKI:
    property = None
    term = "Albert Einstein"
    context = "physicist"
    context = "school" #scientist"
    context = "painting"

    term = "formative assessment"
    context = "teachers learning"

    term = "knowledge graph"
    context = "graph database repository artificial intelligence"

    term = "Hitler Adolf"
    term = "Adolf Hitler"
    context = "Ninja Turtles" #Nazi Germany"

    term = "think"
    context = "thinking"
    property = "property"
    wikipedia_data = wiki_gpt.lookup_wikipedia_concept(term, property)
    if wikipedia_data:
        embedded_query = f"{term} {context}"
        results = wiki_gpt.get_sentence_embedding(embedded_query, wikipedia_data)
        print(json.dumps(results, indent=4))

SKOSMOS = False
if SKOSMOS:
    term = "amsterdam"
    context = "thinking"
    vocab = "yso-paikat"
    host = "https://api.finto.fi"
    property = None
    term = "Kyiv"
    results = wiki_gpt.lookup_skosmos_concept(host, term, vocab)
    print(json.dumps(results, indent=4))
    if results:
        wikipedia_data = wiki_gpt.lookup_wikipedia_concept(term, property)
        embedded_query = f"{term} {results['context']}"
        results = wiki_gpt.get_sentence_embedding(embedded_query, wikipedia_data)
        print(json.dumps(results, indent=4))
#        print(results['context'])

GETTY = True
if GETTY:
    query = "van gogh"
    #results = wiki_gpt.run_sparql_getty(query)
    results = wiki_gpt.run_sparql_getty(query, format="context")
    print(json.dumps(results, indent=4))
#    print(json.dumps(results, indent=4))

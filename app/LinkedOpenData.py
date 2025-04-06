import spacy
import rdflib
from rdflib import URIRef, Literal, Namespace, BNode
import requests
import re
import json
import aiohttp
from urllib.parse import urlencode
import asyncio
from nltk.tokenize import sent_tokenize
from labels import nlp_labels
from sentence_transformers import SentenceTransformer, InputExample, losses, util
#from transformers.modeling_utils import no_init_weights, init_empty_weights  # Ensure this import is included
from torch.utils.data import DataLoader
import pandas as pd
from utils import search_entities_with_sparql
from urllib.parse import urlencode
from langdetect import detect, DetectorFactory
import os

# Ensure consistent results
DetectorFactory.seed = 0
# Load the spaCy model
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer(os.environ.get('SENTENCE_TRANSFORMER_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'))

class LinkedOpenData:
    def __init__(self, sentence=None, SPARQL_COLLECTION_DIR='sparql'):
        # Store the sentence
        self.DEBUG = False
        self.SPARQL_COLLECTION_DIR = SPARQL_COLLECTION_DIR
        self.sentenceID = 0
        self.TOKENABSNUM = -1
        self.nlp_labels = rdflib.Graph()
        self.link_wikidata = False
        # Process the sentence with spaCy
        if sentence:
            self.doc = nlp(sentence)
        # Create an RDF graph
        self.init_graphs()

    def concept_stats(self, conceptIDs, is_sparql=True):
        stats = {}
        for conceptID in conceptIDs.split(','):
            sparql_query = """
            SELECT (COUNT(*) AS ?refCount)
            WHERE {
            ?subject ?predicate wd:""" + conceptID + """ 
            }
            """
            if is_sparql:
                url = 'https://query.wikidata.org/sparql'
                headers = {
                    'Accept': 'application/json'
                }
                response = requests.get(url, headers=headers, params={'query': sparql_query})
            else:
                url = 'https://www.wikidata.org/w/api.php?action=wbgetentities&ids=' + conceptID + '&format=json'
                response = requests.get(url)

            try:
                result = response.json()
                stats[conceptID] = result['results']['bindings'][0]['refCount']['value']
            except Exception as e:
                print(e)
                stats[conceptID] = 0
        return stats

    def switch_debug(self, debug=False):
        self.DEBUG = debug  # True or False

    def switch_link_wikidata(self, link_wikidata=False):
        self.link_wikidata = link_wikidata  # True or False

    def init_graphs(self, namespace="https://i.org/"):
        self.g = rdflib.Graph()
        self.labels = {}
        self.relationships = {}
        self.dependencies = {}
        self.termgraph = rdflib.Graph()
        self.gpt_graph_ent = rdflib.Graph()
        self.labels_dict = self.load_labels(nlp_labels)
        # Define a base URI for the RDF graph
        self.base_uri = namespace
        self.term_uri = Namespace(namespace + "term/")
        self.sentence_uri = Namespace(namespace + "sentence/")
        self.action_uri = Namespace(namespace + "action/")
        self.labels_uri = Namespace(namespace + "labels/")
        self.prev_uri = Namespace(namespace + "prev/")
        self.next_uri = Namespace(namespace + "next/")
        self.entity_type = Namespace(namespace + "entity/")
        self.gpt_uri = Namespace(namespace + "gpt/")
        self.termgraph.bind("term", self.term_uri)
        self.gpt_graph_ent.bind("gpt", self.gpt_uri)
        self.termgraph.bind("sentence", self.sentence_uri)
        self.termgraph.bind("action", self.action_uri)
        self.termgraph.bind("label", self.labels_uri)
        self.termgraph.bind("prev", self.prev_uri)
        self.termgraph.bind("next", self.next_uri)
        self.termgraph.bind("base", self.base_uri)
        self.wikidata_api_url = "https://www.wikidata.org/w/api.php"  # Added URL as an instance variable
        self.gptram = {}

    def load_labels(self, json_ld_data):
        # Load JSON-LD data from a file
        self.labels = {}
        # Manually add triples to the graph to preserve order
        for item in json_ld_data['@graph']:
            #subject = URIRef(item.get('label'))  # Get the subject URI
            self.labels[item.get('label')] = item.get('description')
#        print(json.dumps(self.labels, indent=4))
        return self.labels

    # Extract entities and their relationships
    def extract_relationships(self, doc, sentenceID=None):
        print(self.labels_dict)
        relationships = []
        dependencies = []
        for tokenID in range(0, len(doc)):
            self.TOKENABSNUM += 1
            self.gptram = {}
            self.chain = {}
            self.uri_chain = {}
            self.positions = {}
            token = doc[tokenID]

            if sentenceID:
                self.positions[tokenID] = "%s-%s" % (sentenceID, tokenID)

            # Build a chain of tokens for GPT in both directions
            self.chain['token'] = token
            self.uri_chain['token'] = URIRef(self.term_uri[token.text.replace(" ", "_")])
            if tokenID < len(doc) - 1:
                self.chain['next'] = doc[tokenID + 1]
                self.uri_chain['next'] = URIRef(self.term_uri[doc[tokenID + 1].text.replace(" ", "_")])
            if tokenID > 0:
                self.chain['prev'] = doc[tokenID - 1]
                self.uri_chain['prev'] = URIRef(self.term_uri[doc[tokenID - 1].text.replace(" ", "_")])
            if 'next' in self.chain:
                if self.chain['token'].ent_type_ == self.chain['next'].ent_type_:
                    self.gpt_graph_ent.add((URIRef(self.uri_chain['token']), URIRef(self.uri_chain['next']), Literal(self.chain['token'].ent_type_)))
            if 'next' in self.chain and 'prev' in self.chain:
                #self.gpt_graph_ent.add((URIRef(self.uri_chain['prev']), URIRef(self.uri_chain['token']), URIRef(self.uri_chain['next'])))
#                self.gpt_graph_ent.add((URIRef(self.uri_chain['token']), URIRef(self.prev_uri), URIRef(self.uri_chain['prev'])))
                #self.gpt_graph_ent.add((URIRef(self.uri_chain['token']), URIRef(self.next_uri), URIRef(self.uri_chain['next'])))
#                self.gpt_graph_ent.add((URIRef(self.uri_chain['token']), URIRef(self.urnext_uri), Literal(self.TOKENABSNUM)))
                self.positions[tokenID] = "%s-%s" % (sentenceID, tokenID)
            # Position of the token in the sentence
            self.gpt_graph_ent.add((URIRef(self.uri_chain['token']), URIRef(self.term_uri['wordpos']), Literal(self.TOKENABSNUM)))
            #self.gpt_graph_ent.add((URIRef(self.uri_chain['token']), URIRef(self.term_uri['wordpos']), Literal(tokenID)))

            token_type = token.ent_type_
            dependencies.append({'token': token.text, 'dep': token.dep_, 'type': token_type})
            # Look for subjects (nsubj) and objects (dobj, attr, etc.)
            if token.dep_:  # in ("nsubj", "dobj", "attr"):
                entity = token.text
                entity_uri = URIRef(self.term_uri[entity.replace(" ", "_")])
                if token_type:
                    self.termgraph.add((entity_uri, URIRef(self.entity_type), Literal(token_type)))
                    #self.gptgraph.add((entity_uri, URIRef(self.entity_type), Literal(token_type)))
                if tokenID < len(doc) - 1:
                    next_entity = doc[tokenID + 1].text
                    next_entity_type = doc[tokenID + 1].ent_type_
                    next_entity_dep = doc[tokenID + 1].dep_
                    next_uri = URIRef(self.term_uri[next_entity.replace(" ", "_")])
                else:
                    next_uri = None
                if tokenID > 0:
                    prev_entity = doc[tokenID - 1].text
                    prev_entity_type = doc[tokenID - 1].ent_type_
                    prev_entity_dep = doc[tokenID - 1].dep_
                    prev_uri = URIRef(self.term_uri[prev_entity.replace(" ", "_")])
                else:
                    prev_uri = None
                #print("[%s] %s %s" % (entity, token.dep_, self.labels[token.dep_]))
                # Find verbs or actions associated with the entity
                for child in token.head.children:
                    if child.dep_ == "relcl":  # Relative clauses
                        action = child.text
                        related_entities = [
                            child_ent.text
                            for child_ent in child.subtree
                            if child_ent.ent_type_ or child_ent.pos_ in ("NOUN", "PROPN")
                        ]
                        # Create a URI for the entity
                        entity_uri = URIRef(self.term_uri[entity.replace(" ", "_")])  # Replace spaces with underscores for URI

                        # Add a triple to the graph: (entity, dependency, value)
                        self.termgraph.add((entity_uri, URIRef(self.term_uri.dep), Literal(token.dep_)))  # Add dependency relation
                        if token.dep_ in self.labels:
                            self.termgraph.add((entity_uri, URIRef(self.labels_uri.dep), Literal(self.labels[token.dep_])))  # Add dependency relation
                        relationships.append((entity, action, related_entities))
                    else:
                        action = token.head.text
                        related_entities = [
                            child_ent.text
                            for child_ent in token.subtree
                            if child_ent.ent_type_ or child_ent.pos_ in ("NOUN", "PROPN")
                        ]
                        # Create a URI for the entity
                        entity_uri = URIRef(self.term_uri[entity.replace(" ", "_")])
                        self.termgraph.add((entity_uri, URIRef(self.action_uri.dep), Literal(token.dep_)))  # Add dependency relation
                        if token.dep_ in self.labels:
                            self.termgraph.add((entity_uri, URIRef(self.labels_uri.dep), Literal(self.labels[token.dep_])))  # Add dependency relation
                        self.termgraph.add((entity_uri, URIRef(self.action_uri.dep), Literal(tokenID)))  # Add dependency relation

                # Next and previous entities
                if 'next' in self.chain:
                    #next_uri = self.chain['next']
                    #self.termgraph.add((entity_uri, URIRef(self.next_uri.next), next_uri))  # Add dependency relation
                    ###self.gptgraph.add((entity_uri, URIRef(self.next_uri), next_uri))  # Add dependency relation
                    ###self.gptgraph.add((entity_uri, URIRef("%s%s" % (self.next_uri, self.chain['next'].dep_)), next_uri))  # Add dependency relation
                    if not next_uri in self.gptram: 
                        bnode = BNode() 
                        self.termgraph.add((bnode, URIRef(self.sentence_uri), Literal(self.sentenceID)))
                        #self.termgraph.add((bnode, next_uri, Literal(tokenID + 1)))  # Add dependency relation
                        if next_entity_dep:
                            self.termgraph.add((bnode, next_uri, URIRef(next_entity_dep)))  # Add dependency relation
                        if next_entity_type:
                            self.termgraph.add((bnode, next_uri, URIRef(next_entity_type)))  # Add dependency relation
                        self.termgraph.add((entity_uri, URIRef(self.next_uri), bnode))  # Add dependency relation
                        self.gptram[next_uri] = bnode
                    else:
                        self.termgraph.add((entity_uri, URIRef(self.next_uri), self.gptram[next_uri]))  # Add dependency relation
                if prev_uri:
                    #self.termgraph.add((entity_uri, URIRef(self.prev_uri.prev), prev_uri))  # Add dependency relation
                    if not prev_uri in self.gptram:
                        bnode = BNode()
                        self.termgraph.add((bnode, URIRef(self.sentence_uri), Literal(self.sentenceID)))
                        if prev_entity_dep:
                            self.termgraph.add((bnode, URIRef(prev_entity_dep), prev_uri))  # Add dependency relation
                        if prev_entity_type:
                            self.termgraph.add((bnode, URIRef(prev_entity_type), prev_uri))  # Add dependency relation
                        self.termgraph.add((entity_uri, URIRef(self.prev_uri), bnode))  # Add dependency relation
                        self.gptram[prev_uri] = bnode
                    else:
                        self.termgraph.add((entity_uri, URIRef(self.prev_uri), self.gptram[prev_uri]))  # Add dependency relation
            self.sentenceID += 1

            if relationships and sentenceID:
                self.relationships[sentenceID] = relationships
            else:
                self.relationships[0] = relationships
            if dependencies and sentenceID:
                self.dependencies[sentenceID] = dependencies
            else:
                self.dependencies[0] = dependencies
        return relationships

    def query_graph(self, query, graphtype=None):
        if self.DEBUG:
            print("[DEBUG query_graph] query: %s" % query)
        if not graphtype:
            return self.termgraph.query(query)
        elif graphtype == "gpt":
            return self.gpt_graph_ent.query(query)
        else:
            return self.termgraph.query(query)

    def export_graph(self, triples, format='turtle', filename=None):
        try:
            # Create a new RDF Graph
            output_graph = rdflib.Graph()

            for row in triples:
                # Add triples to the graph
                if self.DEBUG:
                    print("[DEBUG export_graph] row: %s" % str(row))
                output_graph.add((row.s, row.p, row.o))
            output_graph.serialize(destination=filename, format=format)
            return True
        except Exception as e:
            print(e)
            return False

    def export_dependencies(self, dependencies, filename=None):
        try:
            with open(filename, 'w') as f:
                f.write(json.dumps(dependencies, indent=4))
            return True
        except Exception as e:
            print(e)
            return False

    def export_relationships(self, relationships, filename=None):
        try:
            with open(filename, 'w') as f:
                f.write(json.dumps(relationships, indent=4))
            return True
        except Exception as e:
            print(e)
            return False

    # Define a function to build the concept "the United States"
    def build_concept(self, graph):
        # Initialize an empty set to store parts of the concept
        concept_parts = set()
        concepts = set()

        # Iterate over triples in the graph
        for subject, predicate, wordpos in graph:
            concept_parts = set()
            if self.DEBUG:
                print("[DEBUG build_concept] subject: %s, predicate: %s, wordpos: %s" % (subject, predicate, wordpos))
            # Check if the object is a literal 'GPE'
            if isinstance(wordpos, Literal): # and obj == Literal('GPE'):
                # Add subject and predicate to the concept parts
                concept_parts.add(subject)
                concept_parts.add(predicate)
                concept = " ".join([part.split('/')[-1] for part in concept_parts if isinstance(part, URIRef)])
                concepts.add(concept)
        if self.DEBUG:
            print("[DEBUG build_concept] concepts: %s" % concepts)
            for concept in concepts:
                if self.link_wikidata:
                    wikidata = self.lookup_wikipedia_concept(concept) #, 'property')
                    if self.DEBUG:
                        print("[DEBUG build_concept] wikidata: %s" % wikidata)
        return concepts

    def get_graph_entities(self, term=None, entity=None):
        # Define the SPARQL query to get persons with the same sentence
        if term:
            self.query_sentence = term
            self.query_sentence_uri = URIRef(self.term_uri + self.query_sentence.replace(" ", "_"))
            self.query_sentence_url = self.term_uri + self.query_sentence.replace(" ", "_")
            print(self.query_sentence_uri)

            # SPARQL query to get persons with their "prev" and "next" context
            query = f"""
            PREFIX ex: <{self.base_uri}>
            SELECT ?sentence ?prev ?next ?bnode
            WHERE {{
                ?sentence ?prev ?bnode .
                ?sentence ?next ?bnode .
                FILTER(?sentence = <{self.query_sentence_uri}>)
            }}
            """
            query = f"""
            PREFIX ex: <{self.base_uri}>
            SELECT ?s ?p ?o
            WHERE {{
                ?s ?p ?o
            }}
            """
        else:
            query = f"""
            PREFIX ex: <{self.base_uri}>
            SELECT ?s ?p ?o
            WHERE {{
#                ?s <{self.next_uri}> ?o .
                ?s ?p ?o .
#                ?s <{self.term_uri.wordpos}> ?wordpos .
#                ?o <{self.term_uri.wordpos}> ?wordpos .
                FILTER(?o = "{entity}")
            }}
            ORDER BY ?wordpos 
            """ 
        if self.DEBUG:
            print("[DEBUG get_graph_entities] query: %s" % query)
        results = self.query_graph(query, "gpt")  # Execute the query
        concepts = self.build_concept(results)
        return results  # Return the list of persons with their context

    def get_persons_with_context(self, term=None, entity=None):
        # Define the SPARQL query to get persons with the same sentence
        if term:
            self.query_sentence = term
            self.query_sentence_uri = URIRef(self.term_uri + self.query_sentence.replace(" ", "_"))
            self.query_sentence_url = self.term_uri + self.query_sentence.replace(" ", "_")
            print(self.query_sentence_uri)

            # SPARQL query to get persons with their "prev" and "next" context
            query = f"""
            PREFIX ex: <{self.base_uri}>
            SELECT ?sentence ?prev ?next ?bnode
            WHERE {{
                ?sentence ?prev ?bnode .
                ?sentence ?next ?bnode .
                FILTER(?sentence = <{self.query_sentence_uri}>)
            }}
            """
            query = f"""
            PREFIX ex: <{self.base_uri}>
            SELECT ?s ?p ?o
            WHERE {{
                ?s ?p ?o
            }}
            """
        else:
            query = f"""
            PREFIX ex: <{self.base_uri}>
            SELECT ?s ?p ?o
            WHERE {{
#                ?s <{self.next_uri}> ?o .
                ?s ?p ?o .
#                ?s <{self.term_uri.wordpos}> ?wordpos .
#                ?o <{self.term_uri.wordpos}> ?wordpos .
                FILTER(?o = "{entity}")
            }}
            ORDER BY ?wordpos 
            """ 
        results = self.query_graph(query, "gpt")  # Execute the query
        if self.DEBUG:
            print("[DEBUG get_persons_with_context] results: %s" % results)
        concepts = self.build_concept(results)
        persons = []

        # Process the results
        #print(results)
        if results:
            for row in results:
                person = None
                prev = None
                next = None
                bnode = None
                print(row)
                persons.append({
                    'bnode': str(bnode)
                })

        return persons  # Return the list of persons with their context

    def build_graph(self, doc):
        # Extract and display relationships
        relationships = self.extract_relationships(doc)
        for entity, action, related_entities in relationships:
            print(f"Entity: {entity}, Action: {action}, Related Entities: {', '.join(related_entities)}")
            # Add triples to the RDF graph
            for related_entity in related_entities:
                self.g.add((rdflib.URIRef(self.base_uri + entity.replace(" ", "_")),
                             rdflib.URIRef(self.base_uri + action.replace(" ", "_")),
                             rdflib.URIRef(self.base_uri + related_entity.replace(" ", "_")))
                )

        # Optionally, serialize the graph to a file or print it
        self.g.serialize(destination='relationships.rdf', format='xml')

    def wiki_json_to_text(self, wikidata_records):
        records = []
        self.forbidden_sentences = ["thesis by", "book chapter", "case study", "article published", "Conference Series", "Electronic Journal",  "(,"]
        for json_record in wikidata_records['search']:
            # Extract relevant fields from the JSON record
            title = json_record.get("title", "No Title")
            description = json_record.get("description", json_record.get("label").lower())
            label = json_record.get("label", "No Label")
            wikidata_id = json_record.get("id", "No Wikidata ID")
            concept_uri = json_record.get("concepturi", "No Concept URI")
            url = json_record.get("url", "No URL")
            if any(sentence.lower() in description.lower() for sentence in self.forbidden_sentences):
                continue
            # Create a formatted text output
            text_output = (
                f"Title: {title} "
                f"Label: {label} "
                f"Description: {description} "
                f"Concept URI: {concept_uri} "
                f"URL: {url} "
                f"Wikidata ID: {wikidata_id} "
                f"Connections: {self.concept_stats(wikidata_id)[wikidata_id]} "
            )
            records.append(text_output)
        return records

    def lookup_wikipedia_concept(self, term, propertytype=None, language='en', source=None):
        url = f"{self.wikidata_api_url}?action=wbsearchentities&search={term}&format=json&language={language}"
        if propertytype:
            url = "%s&type=%s" % (url, propertytype)
        response = requests.get(url)
        if response.status_code == 200:
            return self.wiki_json_to_text(response.json())
            #return response.json()
        else:
            print("Error fetching data from Wikidata")
            return None

    def getty_json_to_text(self, getty_records):
        results = {}
        for binding in getty_records["results"]["bindings"]:
            result_strings = []
            artist_uri = binding["artist"]["value"]
            artist_type = binding["artist"]["type"]
            name_value = binding["name"]["value"]
            name_type = binding["name"]["type"]
            #http://vocab.getty.edu/page/ulan/500698764
            result_strings.append(f"Artist URI: {artist_uri}")
            result_strings.append(f"Artist Page: {artist_uri.replace('/ulan/','/page/ulan/')}")
            result_strings.append(f"Name: {name_value}")
            results[artist_uri] = "\n ".join(result_strings)
        return results

    def run_sparql_query(self, query: str, sparql_endpoint: str="http://vocab.getty.edu/sparql"):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json"
        }
        data = {
            "query": query,
            "format": "json"
        }
        response = requests.post(sparql_endpoint, headers=headers, data=data) #, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None

    def run_sparql_getty(self, query, format="json", limit=str(10)):
        # SPARQL Query Example
        sparql_query = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX gvp: <http://vocab.getty.edu/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?artist ?name ?birthDate ?deathDate
        WHERE {
            ?artist rdf:type gvp:PersonConcept .
            ?artist skos:prefLabel ?name .
            OPTIONAL { ?artist gvp:birthDate ?birthDate . }
            OPTIONAL { ?artist gvp:deathDate ?deathDate . }
            FILTER(CONTAINS(LCASE(?name), "%s"))
        }
        LIMIT %s""" % (query.lower(), limit)

        # Run the query
        try:
            results = self.run_sparql_query(sparql_query)
        except Exception as e:
            print(e)
            return None
        if format == "json":    
            return results
        else:
            return self.getty_json_to_text(results)

    def skosmos_to_context(self, skosmos_data, language='en'):
        result_lines = []
        maincontext = []
        if 'graph' in skosmos_data:
            output_lines = []

            for record in skosmos_data['graph']:
                # Extract the URI
                uri = record.get("uri", "No URI")
                if uri:
                    output_lines.append(f"URI: {uri}")

                # Extract subPropertyOf if it exists
                sub_property = record.get("rdfs:subPropertyOf", {}).get("uri", "No SubProperty")
                if sub_property and sub_property != 'No SubProperty':
                    output_lines.append(f"SubProperty: {sub_property}")

                # Extract labels and preferred labels
                labels = record.get("label", [])
                pref_labels = record.get("prefLabel", [])

                # Filter labels by language
                filtered_labels = [label['value'] for label in labels if label['lang'] == language]
                filtered_pref_labels = [pref_label['value'] for pref_label in pref_labels if pref_label['lang'] == language]

                # Add filtered labels to output
                if filtered_labels:
                    output_lines.append(f"Labels ({language}): {', '.join(filtered_labels)}")
                #else:
                #    output_lines.append(f"Labels ({language}): No labels found")

                if filtered_pref_labels:
                    output_lines.append(f"Preferred Labels ({language}): {', '.join(filtered_pref_labels)}")
                    maincontext.append(", ".join(filtered_pref_labels))
                #else:
                #    output_lines.append(f"Preferred Labels ({language}): No preferred labels found")

                output_lines.append("")  # Add a blank line for separation

                result_lines.append("\n".join(output_lines))
        return ', '.join(maincontext)

    def get_skosmos_concept(self, skosmos_host, vocab, skosmos_uri):
        url = f"{skosmos_host}/rest/v1/{vocab}/data?uri={skosmos_uri}&format=application/ld%2Bjson"
        print(url)
        response = requests.get(url)
        if response.status_code == 200:
            return self.skosmos_to_context(response.json())
            #return response.json()
        else:
            print("Error fetching data from Skosmos")
            return None

    def lookup_skosmos_concept(self, skosmos_host, term, vocab=None, language='en'):
        results = {}
        if language == "en":
            # Check if the term is in English (you can define your own logic for this check)
            if not term.isascii():  # Example check: if the term contains non-ASCII characters
                detected_language = detect(term)
                if detected_language != "en":
                    language = detected_language
            
        url = f"{skosmos_host}/rest/v1/search?query={term}&lang={language}"
        if vocab:
            url = f"{url}&vocab={vocab}"
        print(url)
        response = requests.get(url)
        if 'results' in response.json():
            for record in response.json()['results']:
                skosmos_uri = record['uri']
                print(skosmos_uri)
                skosmos_data = self.get_skosmos_concept(skosmos_host, vocab, skosmos_uri)
                if skosmos_data:
                    #print(json.dumps(skosmos_data['graph'], indent=4))
                    results['concept'] = response.json()
                    results['context'] = skosmos_data
        return results

    def get_wikipedia_uri_from_api(self, wikidata_id, language='en'):
        url = self.wikidata_api_url
        params = {
            "action": "wbgetentities",
            "ids": wikidata_id,
            "format": "json",
            "props": "sitelinks",
        }
        response = requests.get(url, params=params)
        data = response.json()
        try:
            sitelinks = data['entities'][wikidata_id]['sitelinks']
            title = sitelinks.get(f"{language}wiki", {}).get("title")
            if title:
                wikipedia_link = f"https://{language}.wikipedia.org/wiki/{title.replace(' ', '_')}"
                return wikipedia_link
            return None
        except KeyError:
            return None

    async def get_wikipedia_section(self, lang, title, section_name):
        query = {
            'format': 'json',
            'action': 'parse',
            'page': title,
            'prop': 'sections',
        }
        url = f"https://{lang}.wikipedia.org/w/api.php?{urlencode(query)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                body = await response.json()
                if 'parse' in body and 'sections' in body['parse']:
                    # Find the section matching the desired section name
                    for section in body['parse']['sections']:
                        print(section)
                        if section_name.lower() in section['line'].lower():
                            section_index = section['index']
                            break
                    else:
                        return f"Section '{section_name}' not found."

            # Fetch the content of the matched section
            section_query = {
                'format': 'json',
                'action': 'parse',
                'page': title,
                'prop': 'text',
                'section': section_index,
            }
            section_url = f"https://{lang}.wikipedia.org/w/api.php?{urlencode(section_query)}"
            async with session.get(section_url) as section_response:
                section_body = await section_response.json()
                if 'parse' in section_body and 'text' in section_body['parse']:
                    return section_body['parse']['text']['*']

    async def get_wikipedia_intro(self, lang, title):
        query = {
            'format': 'json',
            'action': 'query',
            'titles': title,
            'prop': 'extracts',
            'explaintext': 'true',
            'exintro': 'true',
        }
        url = f"https://{lang}.wikipedia.org/w/api.php?{urlencode(query)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                body = await response.json()
                print(body)
                if 'query' in body and 'pages' in body['query']:
                    return next(iter(body['query']['pages'].values()))['extract']

    def lookup_sentences(self, text, propertytype=None, language='en'):
        sentences = sent_tokenize(text)
        results = {}
        for sentenceID in range(0, len(sentences)):
            sentence = sentences[sentenceID]

            #result = self.lookup_wikipedia_concept(sentence, propertytype, language)
            sentence = sentence.replace("\"", "")
            doc = nlp(sentence)
            result = self.extract_relationships(doc, sentenceID)
            results[sentenceID] = result

        return results

    def tokenize_and_align_labels(self, examples):
        # Print for debugging
        print("Examples structure:", examples)
        
        # Ensure we have valid input
        if 'tokens' not in examples:
            raise ValueError("No 'tokens' field found in examples")
        
        # Convert batch of tokens into a format the tokenizer can handle
        batch_tokens = []
        for tokens in examples['tokens']:
            if isinstance(tokens, str):
                # If tokens is a string, split it into words
                tokens = tokens.split()
            if not tokens:  # If tokens is empty
                tokens = ['[PAD]']  # Add a padding token to prevent empty sequences
            batch_tokens.append(tokens)
        
        # Tokenize with proper handling
        tokenized_inputs = self.tokenizer(
            batch_tokens,
            truncation=True,
            padding=True,
            is_split_into_words=True
        )
        
        return tokenized_inputs

    def train(self, train_file, output_dir):
        # Load dataset
        dataset = load_dataset('text', data_files={'train': train_file})
        
        # Preprocess and tokenize
        tokenized_dataset = dataset['train'].map(
            self.tokenize_and_align_labels,
            batched=True,
            remove_columns=dataset['train'].column_names  # Remove original columns
        )
        
        # Continue with training...

    def get_sentence_embedding(self, query, sources):
        self.similarities = {}
        # Compute sentence embeddings
        sentences = sources

        if len(sources) == 1:
            return sources
        sentences = [sentence.replace("(", "").replace(")", "").replace("\-", "") for sentence in sentences]
        embeddings = model.encode(sentences)

        # Compute cosine similarities of the first embedding to all others
        #ranks = []
        #for i in range(1, len(embeddings)):  # Start from the second embedding
        #    cos_sim = util.cos_sim(embeddings[0], embeddings[i])  # Similarity between the first embedding and the i-th embedding
        #    print(f"Cosine Similarity with embedding {i}: {cos_sim.item()}")  # Output similarity score
        #    ranks.append(cos_sim.item())
        # Generate embedding for the keyword
        #keyword_embedding = model.encode(query)

        # Compute cosine similarities
        print(query)
        keyword_embedding = model.encode(query)
        similarities = util.cos_sim(keyword_embedding, embeddings)

        # Rank sentences by similarity
        sorted_indices = similarities.argsort(descending=True)
        print("Top matching sentences:")
        print("\t %s " % similarities)
        self.topcandidate = None
        self.topconnections = []
        self.topcandidates = []
        self.scores = []
        for idx in sorted_indices[0]:
            connections = re.search(r'Connections: (\d+)', sentences[idx])
            if connections:
                connections = int(connections.group(1))
            else:
                connections = 0
#            print(f"Sentence: {sentences[idx]} - Similarity: {similarities[0][idx].item():.4f} - Connections: {connections}")
            self.scores.append(similarities[0][idx].item())
            if not self.topcandidate:
                self.topcandidate = sentences[idx]
            self.topcandidates.append(sentences[idx])
            self.topconnections.append(connections)

        self.THRESHOLD = float(os.environ.get('THRESHOLD', 0.2))
        self.CANDIDATE_MAX = int(os.environ.get('CANDIDATE_MAX', 3))
        the_most_popular = self.topcandidates[self.topconnections.index(max(self.topconnections))]

        # Check distance between first, second and third candidates
        print(self.scores)
        distance = float(self.scores[0]) - float(self.scores[1])
        print(f"Distance: {distance}")
        print(self.topcandidates[0])
        print(self.topcandidates[1])
        #return self.topcandidates[0]
        if abs(distance) > self.THRESHOLD:
            return self.topcandidates[0]
        else:
            # Find the index of the maximum value in topconnections
            max_index = self.topconnections.index(max(self.topconnections))  # Get the index of the highest connection value
            self.topcandidate = self.topcandidates[max_index]  # Set the top candidate based on the highest connection value
            
            # Get the ID of the most popular candidate
            most_popular_id = self.topcandidates[max_index].split(" - ")[-1]  # Assuming the ID is the last part of the candidate string
            print(f"Most Popular Candidate ID: {most_popular_id}")  # Print or store the ID as needed
            return self.topcandidate

import requests
import rdflib
import csv
from io import StringIO
from rdflib import URIRef, RDF, OWL
import re
import os
from langdetect import detect  # Import the language detection library

class LLMtoGraph:
    def __init__(self):
        self.DEBUG = False
        self.ENTITY_OLLAMA_URL = "http://10.147.18.198:8093/api/generate"
        self.ENTITY_MODEL_NAME = "gemma3:4b"
        self.enrich_entities = []
        self.enrich_labels = []
        self.generic_instance_names = []
        self.g = rdflib.Graph()

    def get_wikidata_info(self, term, context="OECD", language="en"):
        """
        Get Wikidata information for a given term using the sparqlmuse wikilink service.
        """
        base_url = "https://sparqlmuse.now.museum/wikilink/"
        params = {
            "term": term,
            "context": context,
            "language": language,
            "format": "txt"
        }
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                    return response.text
            return None
        except Exception as e:
            print(f"Error fetching wikidata info: {e}")
            return None

    def llm_entities(self, query, language="en", DEBUG=False):
    # Define Ollama endpoint & model
        ENTITY_OLLAMA_URL = self.ENTITY_OLLAMA_URL
        ENTITY_MODEL_NAME = self.ENTITY_MODEL_NAME  # Change model if needed (e.g., llama, gemma)

        openfile = open("./csv_prompt.txt", "r")
        prompt = openfile.read()
        openfile.close()
        if self.DEBUG:
            print(prompt)
        prompt = prompt.replace("{{query}}", query)
        if language != "en":
            prompt+= f"\n\nPlease don't translate the entities from {language}. in English."
        print(prompt)
        # Prepare Ollama request payload
        payload = {
            "model": ENTITY_MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }

        # Send request to Ollama API
        if self.DEBUG:
            print(payload)
        response = requests.post(ENTITY_OLLAMA_URL, json=payload)

        # Handle response
        if response.status_code == 200:
            result = response.json().get("response", "No response")
            if self.DEBUG:
                print("\n🔹 Ollama Response:\n", result)
            
            # Extract CSV data from the response
            entities = self.extract_csv_from_response(result)
            
            # Enrich entities with Wikidata information
            for entity in entities:
                entity_info = self.get_wikidata_info(entity['Value'], entity['Type'], language)
                if entity_info:
                    entity['wikidata_info'] = entity_info
                    entity['wikidata_url'] = None
                    entity['concept_uri'] = None
                    entity['concept_description'] = None
                    entity['concept_label'] = None
                    if 'http' in entity_info:
                        # Enhanced URL recognition
                        urls = re.findall(r'(https?://[^\s]+)', entity_info)
                        entity['wikidata_url'] = urls[0] if urls else None
                        
                    # Extract concept URI if present
                    concept_uri_match = re.search(r'Concept URI: (http[^\s]+)', entity_info)
                    if concept_uri_match:
                        entity['concept_uri'] = concept_uri_match.group(1)

                    # Update regex to capture the new format of the debug output
                    print(entity_info)
                    concept_info_match = re.search(r'Title: (.*?) Label: (.*?) Description: (.*?) Concept URI: (.*?) URL: (.*?)', entity_info)
                    if concept_info_match:
                        entity['concept_label'] = concept_info_match.group(2)
                        entity['concept_description'] = concept_info_match.group(3)  # Description
                        entity['concept_uri'] = concept_info_match.group(4)
                        entity['wikidata_url'] = concept_info_match.group(4)  # URL
                        self.enrich_labels.append(entity['concept_label'])
                        self.generic_instance_names.append(entity['Value'])
                    if self.DEBUG:
                        print(entity)
                    
                self.enrich_entities.append(entity)
            
            return self.enrich_entities
        
        return []

    def extract_csv_from_response(self, response_text, DEBUG=False):
        """
        Extract CSV data from the LLM response text and convert to a list of dictionaries.
        """
        if self.DEBUG:
            print("\nDebug - Original response:", response_text)
        
        # Find CSV content in the response (between possible markdown code blocks)
        csv_content = response_text.strip()
        
        # Check if the response is wrapped in markdown code blocks
        if "```csv" in response_text:
            start_idx = response_text.find("```csv") + 6
            end_idx = response_text.find("```", start_idx)
            if end_idx != -1:
                csv_content = response_text[start_idx:end_idx].strip()
        elif "```" in response_text:
            start_idx = response_text.find("```") + 3
            end_idx = response_text.find("```", start_idx)
            if end_idx != -1:
                csv_content = response_text[start_idx:end_idx].strip()
        if self.DEBUG:
            print("\nDebug - CSV content after extraction:", csv_content)
        
        # Parse CSV data
        entities = []
        try:
            # Simple line-by-line parsing
            lines = [line.strip() for line in csv_content.split('\n') if line.strip()]
            
            # If first line doesn't contain header, add it
            if lines and not ('Type' in lines[0] and 'Value' in lines[0]):
                lines.insert(0, "Type,Value")
            
            # Parse each line manually
            header = lines[0].split(',')
            for line in lines[1:]:
                parts = line.split(',', 1)  # Split only on first comma
                if len(parts) == 2:
                    entities.append({
                        'Type': parts[0].strip(),
                        'Value': parts[1].strip()
                    })
            
            print("\nDebug - Parsed entities:", entities)
            
        except Exception as e:
            if self.DEBUG:
                print(f"Error parsing: {e}")
        
        return entities

    def question_entities(self, query):
        query = query.replace("/", " ") #.replace(":", " ").replace("(", " ").replace(")", " ")
        lang_detect = detect(query)  # Detect the language of the query
        if self.DEBUG:
            print(f"Detected language: {lang_detect}")  # Print the detected language
        primary_entities = self.llm_entities(query, lang_detect)
        entities = primary_entities
        
        # Define some namespaces
        SCHEMA = rdflib.Namespace("http://schema.org/")
        self.g.bind("schema", SCHEMA)
        
        if self.DEBUG:
            print("\n🔹 Extracted Entities:")
        for entity in entities:
            if self.DEBUG:
                print(f"\n  - {entity['Type']}: {entity['Value']}")
            if 'wikidata_info' in entity:
                if self.DEBUG:
                    print(f"  DEBUG  WikiData: {entity['wikidata_info']} WikiData URL: {entity['wikidata_url']}")
                
                if entity['wikidata_url']:
                    # Create proper RDF terms
                    subject = URIRef(entity['wikidata_url'])
                    type_uri = URIRef(SCHEMA + entity['Type'].replace(' ', ''))
                    label = rdflib.Literal(entity['Value'])
                    
                    # Create a language-specific label
                    language_label = rdflib.Literal(label, lang=lang_detect)  # Set the language tag
                    self.g.add((subject, SCHEMA.name, label))  # Add the label without language
                    self.g.add((subject, SCHEMA.name, language_label))  # Add the label with language
                    
                    if 'concept_description' in entity:
                        self.g.add((subject, SCHEMA.description, rdflib.Literal(entity['concept_description'])))
                    if 'concept_label' in entity:
                        self.g.add((subject, SCHEMA.label, rdflib.Literal(entity['concept_label'])))
                    
                    if 'concept_uri' in entity:
                        self.g.add((subject, SCHEMA.sameAs, URIRef(entity['concept_uri'])))
        
        if self.DEBUG:
            print("\nGenerated RDF:")
            print(self.g.serialize(format="turtle"))
        return self.g



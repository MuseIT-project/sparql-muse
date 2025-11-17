#!/usr/bin/env python3
"""
CLI tool to test all endpoints in app/main.py
Usage: python cli.py [command] [options]
"""

import argparse
import requests
import json
import sys
from typing import Optional

# Default base URL for the API
DEFAULT_BASE_URL = "http://localhost:8000"


def test_root(base_url: str, q: Optional[str] = None, subject: Optional[str] = None, 
              predicate: Optional[str] = None, obj: Optional[str] = None,
              suggest: Optional[str] = None):
    """Test the root endpoint GET /"""
    params = {}
    if q:
        params['q'] = q
    if subject:
        params['subject'] = subject
    if predicate:
        params['predicate'] = predicate
    if obj:
        params['object'] = obj
    if suggest:
        params['suggest'] = suggest
    
    print(f"\n🔹 Testing GET / with params: {params}")
    response = requests.get(f"{base_url}/", params=params)
    print(f"Status: {response.status_code}")
    print(f"Response:\n{response.text[:500]}...")
    return response


def test_wikistats(base_url: str, concept_id: str):
    """Test the wikistats endpoint GET /wikistats/"""
    print(f"\n🔹 Testing GET /wikistats/ with conceptID: {concept_id}")
    params = {'conceptID': concept_id}
    response = requests.get(f"{base_url}/wikistats/", params=params)
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    return response


def test_nerc(base_url: str, query: str, context: Optional[str] = None, 
              format: str = "txt", rankingweights: Optional[str] = None):
    """Test the NERC endpoint GET /nerc/"""
    params = {'query': query, 'format': format}
    if context:
        params['context'] = context
    if rankingweights:
        params['rankingweights'] = rankingweights
    
    print(f"\n🔹 Testing GET /nerc/ with params: {params}")
    response = requests.get(f"{base_url}/nerc/", params=params)
    print(f"Status: {response.status_code}")
    if format == "json":
        try:
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response:\n{response.text[:500]}")
    else:
        print(f"Response:\n{response.text[:500]}...")
    return response


def test_wikilink(base_url: str, term: str, context: str, property: Optional[str] = None,
                  language: str = "en", source: Optional[str] = None,
                  rankingweights: Optional[str] = None, format: str = "txt"):
    """Test the wikilink endpoint GET /wikilink/"""
    params = {
        'term': term,
        'context': context,
        'language': language,
        'format': format
    }
    if property:
        params['property'] = property
    if source:
        params['source'] = source
    if rankingweights:
        params['rankingweights'] = rankingweights
    
    print(f"\n🔹 Testing GET /wikilink/ with params: {params}")
    response = requests.get(f"{base_url}/wikilink/", params=params)
    print(f"Status: {response.status_code}")
    if format == "json":
        try:
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response:\n{response.text[:500]}")
    else:
        print(f"Response:\n{response.text[:500]}...")
    return response


def test_ontoportal(base_url: str, term: str, context: str, language: str = "en", 
                    format: str = "txt"):
    """Test the ontoportal endpoint GET /ontoportal/"""
    params = {
        'term': term,
        'context': context,
        'language': language,
        'format': format
    }
    
    print(f"\n🔹 Testing GET /ontoportal/ with params: {params}")
    response = requests.get(f"{base_url}/ontoportal/", params=params)
    print(f"Status: {response.status_code}")
    if format == "json":
        try:
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response:\n{response.text[:500]}")
    else:
        print(f"Response:\n{response.text[:500]}...")
    return response


def test_graph_get(base_url: str, query: str, format: str = "turtle"):
    """Test the graph GET endpoint GET /graph/"""
    params = {'query': query, 'format': format}
    
    print(f"\n🔹 Testing GET /graph/ with params: {params}")
    response = requests.get(f"{base_url}/graph/", params=params)
    print(f"Status: {response.status_code}")
    print(f"Response:\n{response.text[:500]}...")
    return response


def test_graph_post(base_url: str, query: str):
    """Test the graph POST endpoint POST /graph/"""
    params = {'query': query}
    
    print(f"\n🔹 Testing POST /graph/ with query: {query}")
    response = requests.post(f"{base_url}/graph/", params=params)
    print(f"Status: {response.status_code}")
    print(f"Response:\n{response.text[:500]}...")
    return response


def test_sparql(base_url: str, query: str):
    """Test the SPARQL endpoint GET /sparql/"""
    params = {'query': query}
    
    print(f"\n🔹 Testing GET /sparql/ with query: {query}")
    response = requests.get(f"{base_url}/sparql/", params=params)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response:\n{response.text[:500]}")
    return response


def test_predicates(base_url: str):
    """Test the predicates endpoint GET /predicate"""
    print(f"\n🔹 Testing GET /predicate")
    response = requests.get(f"{base_url}/predicate")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response:\n{response.text[:500]}")
    return response


def test_auth_token(base_url: str, email: str, google_token: str):
    """Test the auth token endpoint POST /auth/token"""
    data = {
        'email': email,
        'google_token': google_token,
        'token_type': 'Bearer'
    }
    
    print(f"\n🔹 Testing POST /auth/token with email: {email}")
    response = requests.post(f"{base_url}/auth/token", json=data)
    print(f"Status: {response.status_code}")
    try:
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response:\n{response.text}")
    return response


def test_all(base_url: str):
    """Run all tests with sample data"""
    print("=" * 60)
    print(f"Running all endpoint tests against {base_url}")
    print("=" * 60)
    
    # Test root
    test_root(base_url, q="test query")
    
    # Test wikistats
    test_wikistats(base_url, "Q42")  # Douglas Adams
    
    # Test NERC
    test_nerc(base_url, "ocean", context="marine biology", format="txt")
    
    # Test wikilink
    test_wikilink(base_url, "Einstein", "physicist", language="en", format="txt")
    
    # Test ontoportal
    test_ontoportal(base_url, "protein", "biology", language="en", format="txt")
    
    # Test graph GET
    test_graph_get(base_url, "Albert Einstein physicist", format="turtle")
    
    # Test graph POST
    test_graph_post(base_url, "Marie Curie scientist")
    
    # Test SPARQL
    test_sparql(base_url, "picasso")
    
    # Test predicates
    test_predicates(base_url)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="CLI tool to test sparql-muse API endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all endpoints (default: http://localhost:8000)
  python cli.py all
  
  # Test with custom base URL
  python cli.py --base-url https://api.example.com all
  python cli.py -u http://192.168.1.100:8080 nerc --query "ocean" --context "marine biology"
  
  # Test specific endpoints
  python cli.py root --q "test query"
  python cli.py wikistats --concept-id Q42
  python cli.py nerc --query "ocean" --context "marine biology"
  python cli.py wikilink --term "Einstein" --context "physicist"
  python cli.py ontoportal --term "protein" --context "biology"
  python cli.py graph-get --query "Albert Einstein" --format turtle
  python cli.py graph-post --query "Marie Curie"
  python cli.py sparql --query "picasso"
  python cli.py predicates
  python cli.py auth --email "test@example.com" --token "fake-token"
        """
    )
    
    # Add global base-url argument
    parser.add_argument(
        '--base-url', '-u',
        default=DEFAULT_BASE_URL,
        help=f'Base URL of the API (default: {DEFAULT_BASE_URL})'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # All tests
    subparsers.add_parser('all', help='Run all tests')
    
    # Root endpoint
    root_parser = subparsers.add_parser('root', help='Test root endpoint')
    root_parser.add_argument('--q', help='Query string')
    root_parser.add_argument('--subject', help='Subject')
    root_parser.add_argument('--predicate', help='Predicate')
    root_parser.add_argument('--object', help='Object')
    root_parser.add_argument('--suggest', help='Suggest mode')
    
    # Wikistats
    wikistats_parser = subparsers.add_parser('wikistats', help='Test wikistats endpoint')
    wikistats_parser.add_argument('--concept-id', required=True, help='Wikidata concept ID')
    
    # NERC
    nerc_parser = subparsers.add_parser('nerc', help='Test NERC endpoint')
    nerc_parser.add_argument('--query', required=True, help='Search query')
    nerc_parser.add_argument('--context', help='Context for ranking')
    nerc_parser.add_argument('--format', default='txt', choices=['txt', 'json'], help='Output format')
    nerc_parser.add_argument('--rankingweights', help='Ranking weights (e.g., "popularity")')
    
    # Wikilink
    wikilink_parser = subparsers.add_parser('wikilink', help='Test wikilink endpoint')
    wikilink_parser.add_argument('--term', required=True, help='Search term')
    wikilink_parser.add_argument('--context', required=True, help='Context')
    wikilink_parser.add_argument('--property', help='Property type')
    wikilink_parser.add_argument('--language', default='en', help='Language code')
    wikilink_parser.add_argument('--source', help='Source')
    wikilink_parser.add_argument('--rankingweights', help='Ranking weights')
    wikilink_parser.add_argument('--format', default='txt', choices=['txt', 'json'], help='Output format')
    
    # Ontoportal
    ontoportal_parser = subparsers.add_parser('ontoportal', help='Test ontoportal endpoint')
    ontoportal_parser.add_argument('--term', required=True, help='Search term')
    ontoportal_parser.add_argument('--context', required=True, help='Context')
    ontoportal_parser.add_argument('--language', default='en', help='Language code')
    ontoportal_parser.add_argument('--format', default='txt', choices=['txt', 'json'], help='Output format')
    
    # Graph GET
    graph_get_parser = subparsers.add_parser('graph-get', help='Test graph GET endpoint')
    graph_get_parser.add_argument('--query', required=True, help='Query string')
    graph_get_parser.add_argument('--format', default='turtle', choices=['turtle', 'ttl', 'json-ld'], help='Output format')
    
    # Graph POST
    graph_post_parser = subparsers.add_parser('graph-post', help='Test graph POST endpoint')
    graph_post_parser.add_argument('--query', required=True, help='Query string')
    
    # SPARQL
    sparql_parser = subparsers.add_parser('sparql', help='Test SPARQL endpoint')
    sparql_parser.add_argument('--query', required=True, help='SPARQL query')
    
    # Predicates
    subparsers.add_parser('predicates', help='Test predicates endpoint')
    
    # Auth token
    auth_parser = subparsers.add_parser('auth', help='Test auth token endpoint')
    auth_parser.add_argument('--email', required=True, help='Email address')
    auth_parser.add_argument('--token', required=True, help='Google token')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        base_url = args.base_url
        
        if args.command == 'all':
            test_all(base_url)
        elif args.command == 'root':
            test_root(base_url, args.q, args.subject, args.predicate, args.object, args.suggest)
        elif args.command == 'wikistats':
            test_wikistats(base_url, args.concept_id)
        elif args.command == 'nerc':
            test_nerc(base_url, args.query, args.context, args.format, args.rankingweights)
        elif args.command == 'wikilink':
            test_wikilink(base_url, args.term, args.context, args.property, args.language, 
                         args.source, args.rankingweights, args.format)
        elif args.command == 'ontoportal':
            test_ontoportal(base_url, args.term, args.context, args.language, args.format)
        elif args.command == 'graph-get':
            test_graph_get(base_url, args.query, args.format)
        elif args.command == 'graph-post':
            test_graph_post(base_url, args.query)
        elif args.command == 'sparql':
            test_sparql(base_url, args.query)
        elif args.command == 'predicates':
            test_predicates(base_url)
        elif args.command == 'auth':
            test_auth_token(base_url, args.email, args.token)
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Error: Could not connect to {base_url}")
        print("Make sure the server is running with:")
        print("  uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


import rdflib
from rdflib import Graph, Literal, BNode, Namespace, RDF, RDFS
from loguru import logger

class Cortex:
    """
    The Cortex represents the Logic Layer of the Exocortex.
    It manages the Semantic Knowledge Graph and enforces ontological consistency.
    """
    def __init__(self):
        self.graph = Graph()
        self.namespace = Namespace("http://exocortex.local/ontology#")
        logger.info("Cortex Logic Layer initialized.")

    def ingest_fact(self, subject: str, predicate: str, object_: str):
        """
        Ingests a semantic triple into the Knowledge Graph.
        """
        try:
            s = self.namespace[subject]
            p = self.namespace[predicate]
            o = Literal(object_) # Simplified for initial skeleton
            
            self.graph.add((s, p, o))
            logger.debug(f"Ingested fact: {subject} {predicate} {object_}")
        except Exception as e:
            logger.error(f"Failed to ingest fact: {e}")

    def query(self, sparql_query: str):
        """
        Executes a SPARQL query against the Knowledge Graph.
        """
        return self.graph.query(sparql_query)

cortex = Cortex()

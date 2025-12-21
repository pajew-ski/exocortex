from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD
import json
from datetime import datetime

# 1. Ontologische Definitionen (The Logic Layer)
# Wir definieren den Namensraum unseres Exocortex.
EXOCORTEX = Namespace("http://pajew.ski/ontology#")
SOSA = Namespace("http://www.w3.org/ns/sosa/") # Sensor, Observation, Sample, and Actuator

def create_knowledge_graph():
    """Initialisiert den lokalen semantischen Graphen."""
    g = Graph()
    g.bind("exocortex", EXOCORTEX)
    g.bind("sosa", SOSA)
    return g

# 2. Der Transmutator (JSON -> RDF)
def transmute_state(graph, entity_id, raw_state, attributes):
    """
    Transformiert einen flüchtigen JSON-Zustand in ein persistentes semantisches Faktum.
    
    Args:
        graph (rdflib.Graph): Der aktive Wissensgraph.
        entity_id (str): Die ID aus der physischen Ebene (z.B. 'sensor.living_room_temp').
        raw_state (str): Der rohe Messwert/Zustand.
        attributes (dict): Metadaten des Sensors.
    """
    
    # Erzeugung der URI-Referenz für die Entität (Reifizierung)
    # Wir heben den String 'sensor.xyz' auf die Ebene eines Web-Objekts.
    subject_uri = URIRef(f"http://pajew.ski/resource/{entity_id}")
    
    # Typisierung: Ist es ein Sensor oder ein Aktor?
    # Implizite Didaktik: Wir nutzen Standard-Vokabulare (SOSA) für Interoperabilität.
    graph.add((subject_uri, RDF.type, SOSA.Sensor))
    
    # Extraktion des aktuellen Werts als Observation
    observation_uri = URIRef(f"http://pajew.ski/observation/{entity_id}_{int(datetime.now().timestamp())}")
    graph.add((observation_uri, RDF.type, SOSA.Observation))
    graph.add((observation_uri, SOSA.madeBySensor, subject_uri))
    
    # Zuweisung des Werts (mit Datentyp-Explikation)
    # Hier entscheidet der Orchestrator über die physikalische Dimension (Unit of Measurement).
    try:
        # Versuch der numerischen Konvertierung für metrische Auswertbarkeit
        value_literal = Literal(float(raw_state), datatype=XSD.double)
    except ValueError:
        # Fallback auf String für diskrete Zustände (z.B. 'on'/'off')
        value_literal = Literal(raw_state, datatype=XSD.string)
        
    graph.add((observation_uri, SOSA.hasSimpleResult, value_literal))
    
    # Timestamping für temporale Kausalitätsanalysen
    timestamp = Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
    graph.add((observation_uri, SOSA.resultTime, timestamp))

    return graph

# 3. Simulations-Lauf (Orchestration)
if __name__ == "__main__":
    # Simulierter Payload vom Home Assistant Websocket
    ha_payload = {
        "entity_id": "sensor.bio_monitor_heartrate",
        "state": "62",
        "attributes": {"unit_of_measurement": "bpm", "friendly_name": "Michael's Heartrate"}
    }
    
    knowledge_base = create_knowledge_graph()
    
    # Injektion in den Cortex
    knowledge_base = transmute_state(
        knowledge_base, 
        ha_payload["entity_id"], 
        ha_payload["state"], 
        ha_payload["attributes"]
    )
    
    # Serialisierung zur Überprüfung (Turtle-Format)
    print(knowledge_base.serialize(format="turtle"))
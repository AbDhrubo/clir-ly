"""
Knowledge Graph Visualization
Generates interactive HTML graph using PyVis.
"""

import json
import logging
from pathlib import Path
import networkx as nx
from pyvis.network import Network

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Colors for entity types
COLORS = {
    "PERSON": "#FF9999",  # Red-ish
    "ORG": "#99CCFF",     # Blue-ish
    "LOC": "#99FF99",     # Green-ish
    "MISC": "#FFFF99",    # Yellow-ish
    "UNKNOWN": "#CCCCCC"  # Grey
}

def visualize_graph(
    gexf_path: str = "data/processed/knowledge_graph/knowledge_graph.gexf",
    output_path: str = "data/processed/knowledge_graph/interactive_graph.html",
    top_n: int = 500
):
    """
    Visualize top N connected entities in the graph.
    """
    logger.info("="*60)
    logger.info(f"GRAPH VISUALIZATION (Top {top_n})")
    logger.info("="*60)
    
    # Load graph
    logger.info(f"Loading graph from {gexf_path}...")
    try:
        G = nx.read_gexf(gexf_path)
    except Exception as e:
        logger.error(f"Failed to load GEXF: {e}")
        return
        
    logger.info(f"Loaded {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # Filter for top entities by degree
    logger.info("Filtering for top entities...")
    degrees = dict(G.degree())
    top_nodes = sorted(degrees.items(), key=lambda x: -x[1])[:top_n]
    top_node_ids = {n for n, d in top_nodes}
    
    # Create subgraph with edges between top nodes
    subgraph = G.subgraph(top_node_ids).copy()
    
    logger.info(f"Subgraph: {subgraph.number_of_nodes()} nodes, {subgraph.number_of_edges()} edges")
    
    # Initialize PyVis network
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white")
    
    # Add nodes with formatting
    for node_id in subgraph.nodes():
        node = subgraph.nodes[node_id]
        
        # Determine label and title
        label_en = node.get("label_en", "")
        label_bn = node.get("label_bn", "")
        etype = node.get("entity_type", "UNKNOWN")
        mentions = node.get("mentions", 0)
        
        label = label_en if label_en else label_bn
        if not label:
            label = node_id
            
        title = f"ID: {node_id}\nType: {etype}\nMentions: {mentions}\nEN: {label_en}\nBN: {label_bn}"
        
        # Size based on degree
        size = 10 + (degrees[node_id] * 0.5)
        size = min(size, 50)  # Cap size
        
        net.add_node(
            node_id,
            label=label,
            title=title,
            color=COLORS.get(etype, COLORS["UNKNOWN"]),
            size=size,
            group=etype
        )
    
    # Add edges
    for u, v, data in subgraph.edges(data=True):
        weight = data.get("weight", 1)
        # Scale width
        width = 1 + (weight * 0.2)
        width = min(width, 10)
        
        net.add_edge(u, v, value=weight, width=width, title=f"Co-occurrences: {weight}")
    
    # Set physics options for better layout
    net.set_options("""
    var options = {
      "nodes": {
        "font": {
          "size": 16
        }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": {
          "enabled": true,
          "iterations": 200
        }
      }
    }
    """)
    
    # Save
    logger.info(f"Saving to {output_path}...")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    net.save_graph(output_path)
    logger.info("Done!")
    
    return output_path

if __name__ == "__main__":
    visualize_graph()

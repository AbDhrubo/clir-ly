"""
Knowledge Graph Builder
Builds entity co-occurrence graph from articles.
"""

import json
import logging
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict, Counter
from pathlib import Path
from itertools import combinations

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Warning: networkx not installed. Install with: pip install networkx")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Entity co-occurrence knowledge graph."""
    
    def __init__(self):
        self.graph = nx.Graph() if NETWORKX_AVAILABLE else None
        self.entity_index: Dict[str, Dict] = {}
        
    def load_entity_index(self, filepath: str):
        """Load entity index from JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.entity_index = json.load(f)
        logger.info(f"Loaded {len(self.entity_index)} entities from index")
        
    def build_from_articles(
        self,
        articles: List[Dict],
        min_cooccurrence: int = 2,
        max_entities_per_article: int = 50
    ):
        """
        Build graph from article entities.
        
        Two entities are connected if they co-occur in the same article.
        Edge weight = number of articles where both appear.
        
        Args:
            articles: List of article dicts with 'named_entities'
            min_cooccurrence: Minimum co-occurrences for an edge
            max_entities_per_article: Skip articles with too many entities
        """
        if not NETWORKX_AVAILABLE:
            raise RuntimeError("networkx is required")
        
        # Count co-occurrences
        cooccurrence: Counter = Counter()
        entity_articles: Dict[str, Set[int]] = defaultdict(set)
        
        logger.info("Building co-occurrence matrix...")
        
        for article_idx, article in enumerate(articles):
            entities = article.get("entities", [])
            
            # Get unique entity IDs in this article
            entity_ids = set()
            for ent in entities:
                eid = ent.get("entity_id")
                if eid:
                    entity_ids.add(eid)
            
            # Skip articles with too many entities
            if len(entity_ids) > max_entities_per_article:
                continue
            
            # Track which articles each entity appears in
            for eid in entity_ids:
                entity_articles[eid].add(article_idx)
            
            # Count co-occurrences
            for eid1, eid2 in combinations(sorted(entity_ids), 2):
                cooccurrence[(eid1, eid2)] += 1
        
        logger.info(f"Found {len(cooccurrence)} entity pairs")
        
        # Build graph
        logger.info("Building graph...")
        
        # Add nodes (entities that appear in at least one article)
        for eid in entity_articles.keys():
            if eid in self.entity_index:
                record = self.entity_index[eid]
                self.graph.add_node(
                    eid,
                    label_en=record.get("canonical_en") or "",
                    label_bn=record.get("canonical_bn") or "",
                    entity_type=record.get("entity_type", "UNKNOWN"),
                    article_count=len(entity_articles[eid]),
                    mentions=record.get("total_mentions", 0)
                )
        
        # Add edges
        edge_count = 0
        for (eid1, eid2), weight in cooccurrence.items():
            if weight >= min_cooccurrence:
                self.graph.add_edge(eid1, eid2, weight=weight)
                edge_count += 1
        
        logger.info(f"Graph built: {self.graph.number_of_nodes()} nodes, {edge_count} edges")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        if not self.graph:
            return {}
        
        # Basic stats
        num_nodes = self.graph.number_of_nodes()
        num_edges = self.graph.number_of_edges()
        
        # Degree distribution
        degrees = [d for n, d in self.graph.degree()]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0
        max_degree = max(degrees) if degrees else 0
        
        # Top connected nodes
        degree_centrality = nx.degree_centrality(self.graph)
        top_nodes = sorted(degree_centrality.items(), key=lambda x: -x[1])[:20]
        
        top_entities = []
        for eid, centrality in top_nodes:
            record = self.entity_index.get(eid, {})
            top_entities.append({
                "entity_id": eid,
                "label_en": record.get("canonical_en"),
                "label_bn": record.get("canonical_bn"),
                "type": record.get("entity_type"),
                "degree": self.graph.degree(eid),
                "centrality": round(centrality, 4)
            })
        
        # Entity type distribution
        type_counts = Counter()
        for node in self.graph.nodes():
            etype = self.graph.nodes[node].get("entity_type", "UNKNOWN")
            type_counts[etype] += 1
        
        # Connected components
        num_components = nx.number_connected_components(self.graph)
        largest_cc = max(nx.connected_components(self.graph), key=len)
        
        return {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "avg_degree": round(avg_degree, 2),
            "max_degree": max_degree,
            "num_components": num_components,
            "largest_component_size": len(largest_cc),
            "entity_types": dict(type_counts),
            "top_entities": top_entities
        }
    
    def get_neighbors(self, entity_id: str, top_k: int = 10) -> List[Dict]:
        """Get top neighbors for an entity."""
        if entity_id not in self.graph:
            return []
        
        neighbors = []
        for neighbor in self.graph.neighbors(entity_id):
            weight = self.graph[entity_id][neighbor].get("weight", 1)
            record = self.entity_index.get(neighbor, {})
            neighbors.append({
                "entity_id": neighbor,
                "label_en": record.get("canonical_en"),
                "label_bn": record.get("canonical_bn"),
                "type": record.get("entity_type"),
                "weight": weight
            })
        
        # Sort by weight
        neighbors.sort(key=lambda x: -x["weight"])
        return neighbors[:top_k]
    
    def export_gexf(self, filepath: str):
        """Export graph to GEXF format (for Gephi)."""
        nx.write_gexf(self.graph, filepath)
        logger.info(f"Exported GEXF to {filepath}")
    
    def export_json(self, filepath: str):
        """Export graph to JSON format (for D3.js)."""
        nodes = []
        for node in self.graph.nodes():
            data = dict(self.graph.nodes[node])
            data["id"] = node
            nodes.append(data)
        
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "weight": data.get("weight", 1)
            })
        
        graph_data = {
            "nodes": nodes,
            "edges": edges
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported JSON to {filepath}")
    
    def get_subgraph(self, entity_ids: List[str], depth: int = 1) -> 'KnowledgeGraph':
        """Extract subgraph around specified entities."""
        # Get nodes within depth
        nodes = set(entity_ids)
        for _ in range(depth):
            new_nodes = set()
            for node in nodes:
                if node in self.graph:
                    new_nodes.update(self.graph.neighbors(node))
            nodes.update(new_nodes)
        
        # Create subgraph
        subgraph = KnowledgeGraph()
        subgraph.graph = self.graph.subgraph(nodes).copy()
        subgraph.entity_index = {k: v for k, v in self.entity_index.items() if k in nodes}
        
        return subgraph


def build_knowledge_graph(
    articles_path: str = "data/processed/articles_enhanced.jsonl",
    entity_index_path: str = "data/processed/entity_index_linked.json",
    output_dir: str = "data/processed/knowledge_graph",
    min_cooccurrence: int = 2
):
    """Build knowledge graph from articles."""
    
    logger.info("="*60)
    logger.info("KNOWLEDGE GRAPH BUILDER")
    logger.info("="*60)
    
    # Load data
    logger.info(f"Loading articles from {articles_path}...")
    articles = []
    with open(articles_path, 'r', encoding='utf-8') as f:
        for line in f:
            articles.append(json.loads(line))
    logger.info(f"Loaded {len(articles)} articles")
    
    # Build graph
    kg = KnowledgeGraph()
    kg.load_entity_index(entity_index_path)
    kg.build_from_articles(articles, min_cooccurrence=min_cooccurrence)
    
    # Get stats
    stats = kg.get_stats()
    
    logger.info("\n" + "="*60)
    logger.info("GRAPH STATISTICS")
    logger.info("="*60)
    logger.info(f"Nodes: {stats['num_nodes']}")
    logger.info(f"Edges: {stats['num_edges']}")
    logger.info(f"Avg degree: {stats['avg_degree']}")
    logger.info(f"Max degree: {stats['max_degree']}")
    logger.info(f"Connected components: {stats['num_components']}")
    logger.info(f"Largest component: {stats['largest_component_size']} nodes")
    logger.info(f"Entity types: {stats['entity_types']}")
    
    logger.info("\nTop 10 most connected entities:")
    for i, ent in enumerate(stats['top_entities'][:10], 1):
        label = ent['label_en'] or ent['label_bn']
        logger.info(f"  {i}. {label} ({ent['type']}) - degree: {ent['degree']}")
    
    # Export
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    kg.export_json(f"{output_dir}/knowledge_graph.json")
    kg.export_gexf(f"{output_dir}/knowledge_graph.gexf")
    
    # Save stats
    stats_path = f"{output_dir}/graph_stats.json"
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved stats to {stats_path}")
    
    logger.info("\n" + "="*60)
    logger.info("KNOWLEDGE GRAPH COMPLETE")
    logger.info("="*60)
    
    return kg, stats


if __name__ == "__main__":
    build_knowledge_graph()

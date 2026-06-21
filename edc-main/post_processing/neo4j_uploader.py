#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
neo4j_uploader.py — Uploads packed graph JSON to a Neo4j Database instance.

Loads canon_kg_debated_packed.json, establishes a connection to Neo4j,
creates database constraints/indexes, and performs batch Cypher imports.

Usage:
  python post_processing/neo4j_uploader.py \
      --input_json_path output/Medication_for_Diabetes_Mellitus_Treatment/debated_results/canon_kg_debated_packed.json \
      --uri bolt://localhost:7687 \
      --username neo4j \
      --password your_password \
      --database neo4j \
      [--clear]
"""

import os
import json
import time
import logging
from argparse import ArgumentParser
from typing import Dict, List, Any
from neo4j import GraphDatabase, Driver

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("Neo4jUploader")

# Try loading .env variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Neo4jUploader:
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Driver = None

    def connect(self):
        """Establishes connection to the Neo4j instance."""
        try:
            logger.info(f"Connecting to Neo4j at {self.uri} (database: {self.database})...")
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j database!")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j database: {e}")
            raise

    def close(self):
        """Closes the driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver connection closed.")

    def clear_database(self):
        """Wipes all nodes and relationships in the active database."""
        logger.warning(f"CLEAR DATABASE requested! Detaching and deleting all nodes in database: {self.database}")
        query = "MATCH (n) DETACH DELETE n"
        
        start_time = time.monotonic()
        with self.driver.session(database=self.database) as session:
            result = session.run(query)
            summary = result.consume()
            nodes_deleted = summary.counters.nodes_deleted
            rels_deleted = summary.counters.relationships_deleted
            logger.info(
                f"Cleared database in {time.monotonic() - start_time:.2f}s "
                f"({nodes_deleted} nodes deleted, {rels_deleted} relationships deleted)."
            )

    def create_constraints(self):
        """Creates unique constraints and indexes to optimize matching performance."""
        logger.info("Creating unique constraints and indexes on specific node labels...")
        labels_to_index = [
            "Disease", "Symptom", "Drug", "Treatment_Procedure", "Dosage_Value", 
            "Clinical_Metric", "Biomarker", "Nutrient", "Clinical_Rule", "Risk_Factor", 
            "Anatomical_Site"
        ]
        with self.driver.session(database=self.database) as session:
            for label in labels_to_index:
                constraint_query = (
                    f"CREATE CONSTRAINT unique_{label.lower()}_id IF NOT EXISTS "
                    f"FOR (c:{label}) REQUIRE c.id IS UNIQUE"
                )
                try:
                    session.run(constraint_query)
                    logger.info(f"Unique constraint on (:{label} {{id}}) verified.")
                except Exception as e:
                    logger.warning(f"Could not create constraint for label {label}: {e}")

    def upload_nodes(self, nodes: List[Dict[str, Any]], batch_size: int = 200):
        """Uploads nodes in batches, grouped by their label combinations to support multi-label Neo4j nodes."""
        logger.info(f"Importing {len(nodes)} nodes...")
        start_time = time.monotonic()
        
        # Valid labels matching Bảng 3.3
        VALID_LABELS = {
            "Disease", "Symptom", "Drug", "Treatment_Procedure", "Dosage_Value", 
            "Clinical_Metric", "Biomarker", "Nutrient", "Clinical_Rule", "Risk_Factor", 
            "Anatomical_Site"
        }
        
        # Group nodes by their labels set to batch them with specific Cypher MERGE queries
        grouped_nodes: Dict[str, List[Dict[str, Any]]] = {}
        skipped_count = 0
        
        for node in nodes:
            node_id = node.get("id")
            labels = node.get("labels", [])
            properties = node.get("properties", {})
            
            # Normalize labels (replace space/dash with underscore and match)
            normalized_labels = []
            for l in labels:
                normalized = l.strip().replace(" ", "_").replace("-", "_")
                # Normalize capitalization to match VALID_LABELS
                matched_label = None
                for val in VALID_LABELS:
                    if val.lower() == normalized.lower():
                        matched_label = val
                        break
                if matched_label:
                    normalized_labels.append(matched_label)
            
            # Filter labels to only include valid ones
            clean_labels = sorted(list(set(normalized_labels)))
            
            # If no valid labels, skip the node
            if not clean_labels:
                skipped_count += 1
                continue
            
            group_key = ":".join(clean_labels)
            if group_key not in grouped_nodes:
                grouped_nodes[group_key] = []
                
            grouped_nodes[group_key].append({
                "id": node_id,
                "properties": properties
            })

        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} nodes because they did not contain any valid labels from Table 3.3 (Concept, Device, Finding, etc. are filtered out).")

        total_imported = 0
        with self.driver.session(database=self.database) as session:
            for label_key, batch_list in grouped_nodes.items():
                logger.info(f"Uploading batch of {len(batch_list)} nodes with labels :{label_key}")
                
                # Cypher query with dynamic label string building
                # (Safe because label_key is constructed strictly from sorted alphanumeric inputs)
                query = (
                    f"UNWIND $batch AS row "
                    f"MERGE (n {{id: row.id}}) "
                    f"SET n += row.properties "
                    f"SET n:{label_key}"
                )
                
                # Sub-batching
                for i in range(0, len(batch_list), batch_size):
                    sub_batch = batch_list[i : i + batch_size]
                    session.run(query, batch=sub_batch)
                    total_imported += len(sub_batch)

        logger.info(f"Imported {total_imported} nodes in {time.monotonic() - start_time:.2f}s.")

    def upload_relationships(self, relationships: List[Dict[str, Any]], batch_size: int = 200):
        """Uploads relationships in batches, grouped by relationship type."""
        logger.info(f"Importing {len(relationships)} relationships...")
        start_time = time.monotonic()

        # Valid relationship types matching Bảng 3.4
        VALID_REL_TYPES = {
            "IS_A", "HAS_ANATOMIC_SITE", "CAUSE_OF", "HAS_FINDING", "HAS_BIOMARKER",
            "CO_OCCURS_WITH", "TREATED_BY", "HAS_ADVERSE_EFFECT", "CONTRAINDICATED_WITH",
            "PREFERRED_OVER", "HAS_EVALUATION", "HAS_TITRATION_RULE", "INCREASES_RISK_OF",
            "ADMINISTERED_VIA", "DISPENSES"
        }

        # Group relationships by their relationship type
        grouped_rels: Dict[str, List[Dict[str, Any]]] = {}
        skipped_count = 0
        
        for rel in relationships:
            rel_type = rel.get("type", "RELATED_TO").upper().strip().replace(" ", "_")
            
            # Filter relationship types to only include valid ones
            if rel_type not in VALID_REL_TYPES:
                skipped_count += 1
                continue
                
            if rel_type not in grouped_rels:
                grouped_rels[rel_type] = []
                
            grouped_rels[rel_type].append({
                "start": rel.get("start"),
                "end": rel.get("end"),
                "properties": rel.get("properties", {})
            })

        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} relationships because they were not in the 15 types of Table 3.4 (DECREASES, RELATION, etc. are filtered out).")

        total_imported = 0
        with self.driver.session(database=self.database) as session:
            for rel_type, batch_list in grouped_rels.items():
                logger.info(f"Uploading batch of {len(batch_list)} relationships of type {rel_type}")
                
                # Match start and end nodes (label-less MATCH uses all indexed labels for fast lookups) and merge edge
                query = (
                    f"UNWIND $batch AS row "
                    f"MATCH (a {{id: row.start}}) "
                    f"MATCH (b {{id: row.end}}) "
                    f"MERGE (a)-[r:{rel_type}]->(b) "
                    f"SET r += row.properties"
                )

                # Sub-batching
                for i in range(0, len(batch_list), batch_size):
                    sub_batch = batch_list[i : i + batch_size]
                    session.run(query, batch=sub_batch)
                    total_imported += len(sub_batch)

        logger.info(f"Imported {total_imported} relationships in {time.monotonic() - start_time:.2f}s.")


def main():
    parser = ArgumentParser(description="Uploads canonical packed knowledge graph to Neo4j.")
    parser.add_argument(
        "--input_json_path",
        required=True,
        help="Path to canon_kg_debated_packed.json file generated by property_packer.py"
    )
    parser.add_argument(
        "--uri",
        default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j Connection URI (default: bolt://localhost:7687 or NEO4J_URI env var)"
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("NEO4J_USERNAME", "neo4j"),
        help="Neo4j Username (default: neo4j or NEO4J_USERNAME env var)"
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("NEO4J_PASSWORD", ""),
        help="Neo4j Password (default: from NEO4J_PASSWORD env var)"
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("NEO4J_DATABASE", "neo4j"),
        help="Target database name (default: neo4j)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Wipe the target database before importing new nodes/relationships."
    )

    args = parser.parse_args()

    # Load JSON file
    if not os.path.exists(args.input_json_path):
        logger.error(f"Input file not found at: {args.input_json_path}")
        return

    logger.info(f"Loading packed graph file: {args.input_json_path}")
    with open(args.input_json_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    nodes = graph_data.get("nodes", [])
    relationships = graph_data.get("relationships", [])

    if not nodes:
        logger.warning("No nodes found in graph JSON. Aborting import.")
        return

    # Check for password
    password = args.password
    if not password:
        logger.warning(
            "Neo4j password not provided via argument or env var! "
            "Attempting connection with empty password."
        )

    # Initialize Uploader
    uploader = Neo4jUploader(
        uri=args.uri,
        username=args.username,
        password=password,
        database=args.database
    )

    try:
        uploader.connect()
        
        # Optional database wipe
        if args.clear:
            uploader.clear_database()
            
        # Create indexing constraints
        uploader.create_constraints()
        
        # Perform batches import
        uploader.upload_nodes(nodes)
        uploader.upload_relationships(relationships)
        
        logger.info(
            f"\n"
            f"╔══════════════════════════════════════════════════════════╗\n"
            f"║          NEO4J DATABASE IMPORT SUCCESSFUL!               ║\n"
            f"╠══════════════════════════════════════════════════════════╣\n"
            f"║  Imported Nodes:        {len(nodes):>5}                           ║\n"
            f"║  Imported Relationships:{len(relationships):>5}                           ║\n"
            f"║  Target Database:       {args.database:<14}                   ║\n"
            f"║  Graph URI:             {args.uri:<30} 🚀 ║\n"
            f"╚══════════════════════════════════════════════════════════╝"
        )

    except Exception as e:
        logger.error(f"Import process failed: {e}")
    finally:
        uploader.close()


if __name__ == "__main__":
    main()

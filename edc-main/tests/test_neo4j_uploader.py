"""
Unit tests for the Neo4j Graph Database Uploader module.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure the package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from post_processing.neo4j_uploader import Neo4jUploader


class TestNeo4jUploader(unittest.TestCase):
    def setUp(self):
        self.uri = "bolt://localhost:7687"
        self.username = "neo4j"
        self.password = "password"
        self.database = "neo4j"
        self.uploader = Neo4jUploader(self.uri, self.username, self.password, self.database)

    @patch("post_processing.neo4j_uploader.GraphDatabase")
    def test_connect(self, mock_graph_db):
        """Verify driver connectivity is established and verified."""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        
        self.uploader.connect()
        
        mock_graph_db.driver.assert_called_once_with(self.uri, auth=(self.username, self.password))
        mock_driver.verify_connectivity.assert_called_once()
        self.assertEqual(self.uploader.driver, mock_driver)

    @patch("post_processing.neo4j_uploader.GraphDatabase")
    def test_clear_database(self, mock_graph_db):
        """Verify Cypher query to detach and delete all nodes is executed."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_summary = MagicMock()
        
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.return_value = mock_result
        mock_result.consume.return_value = mock_summary
        mock_summary.counters.nodes_deleted = 10
        mock_summary.counters.relationships_deleted = 5
        
        self.uploader.driver = mock_driver
        self.uploader.clear_database()
        
        mock_session.run.assert_called_once_with("MATCH (n) DETACH DELETE n")

    @patch("post_processing.neo4j_uploader.GraphDatabase")
    def test_upload_nodes_grouping(self, mock_graph_db):
        """Verify nodes are batched correctly by their exact label combinations."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        nodes = [
            {"id": "N1", "labels": ["Concept", "Disease"], "properties": {"name": "T2DM"}},
            {"id": "N2", "labels": ["Concept", "Drug"], "properties": {"name": "Metformin"}},
            {"id": "N3", "labels": ["Concept", "Disease"], "properties": {"name": "T1DM"}},
        ]
        
        self.uploader.driver = mock_driver
        self.uploader.upload_nodes(nodes)
        
        # Should call session.run twice (one for :Concept:Disease, one for :Concept:Drug)
        self.assertEqual(mock_session.run.call_count, 2)
        
        # Verify the queries were structured correctly
        calls = mock_session.run.call_args_list
        queries = [call[0][0] for call in calls]
        
        # Check label combinations
        self.assertTrue(any("Concept:Disease" in q for q in queries))
        self.assertTrue(any("Concept:Drug" in q for q in queries))

    @patch("post_processing.neo4j_uploader.GraphDatabase")
    def test_upload_relationships_grouping(self, mock_graph_db):
        """Verify relationships are batched correctly by their relationship types."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        relationships = [
            {"start": "N1", "end": "N2", "type": "treated_by", "properties": {"confidence": 0.9}},
            {"start": "N2", "end": "N3", "type": "decreases", "properties": {"confidence": 0.85}},
            {"start": "N3", "end": "N4", "type": "treated_by", "properties": {}},
        ]
        
        self.uploader.driver = mock_driver
        self.uploader.upload_relationships(relationships)
        
        # Should call session.run twice (one for treated_by, one for decreases)
        self.assertEqual(mock_session.run.call_count, 2)
        
        calls = mock_session.run.call_args_list
        queries = [call[0][0] for call in calls]
        
        self.assertTrue(any("[r:TREATED_BY]" in q or "[r:treated_by]" in q.lower() for q in queries))
        self.assertTrue(any("[r:DECREASES]" in q or "[r:decreases]" in q.lower() for q in queries))


if __name__ == "__main__":
    unittest.main()

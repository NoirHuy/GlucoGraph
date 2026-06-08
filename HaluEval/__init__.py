# -*- coding: utf-8 -*-
"""
HaluEval — Adversarial Hallucination Evaluation Framework
==========================================================
Module for benchmarking the Knowledge Graph verification pipeline
against synthetically fabricated adversarial medical triples in
the Diabetes domain.

Attack Types Covered:
  1. Semantic Inversion   — causality fully reversed
  2. Ontology Violation   — domain/range constraint breach
  3. Entity Boundary Flaw — non-atomic, padded entity spans
  4. Out-of-Schema Hallucination — out-of-domain concept injection

Usage:
    python HaluEval/run_halueval.py

Author: AI Red-Teamer & Clinical Knowledge Engineer
"""

__version__ = "1.0.0"
__all__ = ["run_halueval", "evaluate_pipeline_rejection", "load_adversarial_dataset"]

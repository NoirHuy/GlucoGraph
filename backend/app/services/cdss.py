import sys
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import json
import re
import os
import httpx
import time
from groq import Groq
from app.config import settings
from app.database import get_db_driver
from app.services.graph_query import (
    get_all_cdss_nodes,
    get_contraindications_direct,
    get_bfs_hop1,
    get_bfs_hop2,
    RELATION_WEIGHTS,
)

# Initialize Groq client (if key present)
_groq_client = None
_groq_cooldown_8b = 0.0
_groq_cooldown_70b = 0.0

try:
    if settings.GROQ_API_KEY:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
except Exception as e:
    print(f"❌ Error configuring Groq AI for CDSS: {e}")


# COMMON_TRANSLATIONS maps common Neo4j node IDs to Vietnamese medical terms
COMMON_TRANSLATIONS = {
    "diabetes mellitus": "Bệnh đái tháo đường",
    "diabetes mellitus, non-insulin-dependent": "Bệnh Đái tháo đường tuýp 2",
    "diabetes mellitus, insulin-dependent": "Bệnh Đái tháo đường tuýp 1",
    "metformin": "Metformin",
    "liraglutide": "Liraglutide",
    "pioglitazone": "Pioglitazone",
    "insulin": "Insulin",
    "chronic kidney disease": "Suy thận mạn",
    "end-stage renal disease": "Suy thận giai đoạn cuối",
    "diabetic nephropathy": "Bệnh thận đái tháo đường",
    "patients at risk of acidemia": "Bệnh nhân có nguy cơ nhiễm toan",
    "acidosis, lactic": "Nhiễm toan lactic",
    "vitamin b12 malabsorption": "Kém hấp thu vitamin B12",
    "obesity": "Béo phì",
    "heart failure": "Suy tim",
    "lisinopril": "Lisinopril",
    "valsartan": "Valsartan",
    "carvedilol": "Carvedilol",
    "insulin resistance": "Đề kháng Insulin",
    "polyuria": "Tiểu nhiều",
    "polydipsia": "Khát nhiều",
    "hypoglycemia": "Hạ đường huyết",
    "hyperglycemia": "Tăng đường huyết",
    "pregnancy": "Thai kỳ",
    "pregnancy, 1st trimester": "Thai kỳ 3 tháng đầu",
    "hyperthyroidism": "Cường giáp",
    "gout": "Bệnh Gout",
    "peptic ulcer": "Loét dạ dày tá tràng",
    "nsaids": "Thuốc chống viêm không steroid (NSAIDs)",
    "colchicine": "Colchicine",
    "tirzepatide": "Tirzepatide"
}

_translation_cache = {}

def translate_node_id(node_id: str) -> str:
    if not node_id:
        return ""
    node_id_clean = str(node_id).strip()
    node_id_lower = node_id_clean.lower()
    
    # 1. Check COMMON_TRANSLATIONS first
    if node_id_lower in COMMON_TRANSLATIONS:
        return COMMON_TRANSLATIONS[node_id_lower]
        
    # 2. Check global cache next
    if node_id_lower in _translation_cache:
        return _translation_cache[node_id_lower]
        
    # Fast translation prompt using Llama
    prompt = f"Bạn là trợ lý dịch thuật thuật ngữ y khoa Việt - Anh chuyên nghiệp. Hãy dịch thuật ngữ y khoa tiếng Anh sau đây sang tiếng Việt chuẩn y văn Việt Nam, dịch thật ngắn gọn, chỉ trả về đúng kết quả dịch (từ 1 đến 5 từ), không thêm bất kỳ giải thích, dấu ngoặc hay dấu chấm câu nào khác:\n\nThuật ngữ: \"{node_id_clean}\""
    
    try:
        # Call model to get dynamic accurate translation using fast 8b model
        translated = call_llm_api(prompt, system_prompt="Dịch thuật ngữ y khoa ngắn gọn sang tiếng Việt.", model_size="8b", force_groq=True)
        cleaned = translated.replace('"', '').replace("'", "").strip()
        # Fallback to capitalize first letter
        if cleaned and not cleaned.lower().startswith("error") and len(cleaned) < 60:
            _translation_cache[node_id_lower] = cleaned
            return cleaned
    except Exception as e:
        print(f"⚠️ Dynamic LLM translation failed for '{node_id_clean}': {e}")
        
    _translation_cache[node_id_lower] = node_id_clean
    return node_id_clean


def translate_multiple_terms(terms: list[str]) -> dict[str, str]:
    """Translates a list of medical terms to Vietnamese in a single batched LLM call."""
    results = {}
    to_translate = []
    
    for term in terms:
        if not term:
            continue
        term_clean = str(term).strip()
        term_lower = term_clean.lower()
        
        if term_lower in COMMON_TRANSLATIONS:
            results[term_lower] = COMMON_TRANSLATIONS[term_lower]
        elif term_lower in _translation_cache:
            results[term_lower] = _translation_cache[term_lower]
        else:
            to_translate.append(term_clean)
            
    if not to_translate:
        return results
        
    # Translate all remaining terms in a single prompt!
    prompt = (
        "Bạn là trợ lý dịch thuật thuật ngữ y khoa Việt - Anh chuyên nghiệp. Hãy dịch danh sách thuật ngữ y khoa tiếng Anh sau đây sang tiếng Việt chuẩn y văn Việt Nam.\n"
        "Hãy dịch thật ngắn gọn (từ 1 đến 5 từ), không thêm giải thích. Trả về kết quả dưới dạng JSON object với key là thuật ngữ tiếng Anh gốc và value là từ đã dịch sang tiếng Việt.\n\n"
        f"Danh sách thuật ngữ: {json.dumps(to_translate, ensure_ascii=False)}"
    )
    
    try:
        # Use fast 8b model on Groq for json output translation
        response = call_llm_api(prompt, system_prompt="Dịch thuật ngữ y khoa ngắn gọn sang tiếng Việt.", response_format="json", model_size="8b", force_groq=True)
        translated_dict = json.loads(response)
        if isinstance(translated_dict, dict):
            for k, v in translated_dict.items():
                k_lower = k.lower()
                cleaned_v = str(v).replace('"', '').replace("'", "").strip()
                _translation_cache[k_lower] = cleaned_v
                results[k_lower] = cleaned_v
    except Exception as e:
        print(f"⚠️ Batched LLM translation failed: {e}")
        # Fallback will occur automatically in subsequent translate_node_id calls
            
    return results


# ─────────────────────────────────────────────────────────────────────────────
# LLM API CALLER — Groq primary, OpenRouter rotation fallback
# ─────────────────────────────────────────────────────────────────────────────

def call_llm_api(prompt: str, system_prompt: str = "", response_format: str = "text", model_size: str = "70b", force_groq: bool = False) -> str:
    """Unified LLM API caller supporting Groq primary (with Qwen 32B reasoning) and OpenRouter failover rotation."""
    global _groq_cooldown_8b, _groq_cooldown_70b

    # Helper to clean reasoning tags from output
    def clean_thinking_tags(text: str) -> str:
        if not text:
            return ""
        # Remove standard <think>...</think> tags
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Remove any stray unclosed <think> or </think> tags
        text = re.sub(r'<think>.*', '', text, flags=re.DOTALL)
        text = text.replace("</think>", "")
        return text.strip()

    # Define provider-specific models
    openrouter_model = "qwen/qwen3.5-flash-02-23"
    
    # Select fast 8b model or reasoning qwen/qwen3-32b model on Groq
    if model_size == "8b":
        groq_model = "llama-3.1-8b-instant"
    else:
        groq_model = "qwen/qwen3-32b"

    errors = []

    # 1. Try Groq first (extremely fast and supports qwen/qwen3-32b)
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key:
        cooldown = _groq_cooldown_8b if model_size == "8b" else _groq_cooldown_70b
        if time.time() > cooldown:
            try:
                print(f"  [LLM API] Trying Groq model {groq_model}...")
                g_client = Groq(api_key=groq_key, max_retries=0)
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                kwargs = {
                    "model": groq_model,
                    "messages": messages,
                    "temperature": 0.1 if response_format == "json" else 0.0,
                }
                if response_format == "json":
                    kwargs["response_format"] = {"type": "json_object"}
                
                response = g_client.chat.completions.create(**kwargs)
                msg = response.choices[0].message
                if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                    print(f"  [LLM THINKING] {msg.reasoning_content.strip()}")
                return clean_thinking_tags(msg.content)
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str or "limit reached" in err_str:
                    if model_size == "8b":
                        _groq_cooldown_8b = time.time() + 300.0
                    else:
                        _groq_cooldown_70b = time.time() + 300.0
                    print(f"⚠️ Groq rate limit hit for {groq_model}. Entering 5-minute cooldown.")
                err_msg = f"Groq primary failed: {e}"
                print(f"⚠️ {err_msg}")
                errors.append(err_msg)

    # 2. Try OpenRouter as fallback
    if not force_groq:
        openrouter_keys = []
        for i in range(1, 21):
            key_name = f"OPENROUTER_API_KEY_{i}" if i > 1 else "OPENROUTER_API_KEY"
            key_val = os.environ.get(key_name, "").strip()
            if key_val and key_val not in openrouter_keys:
                openrouter_keys.append(key_val)
        for k in os.environ:
            if k.startswith("OPENROUTER_API_KEY"):
                val = os.environ[k].strip()
                if val and val not in openrouter_keys:
                    openrouter_keys.append(val)

        print(f"  [LLM API] Fallback to OpenRouter. Total keys: {len(openrouter_keys)}")
        if openrouter_keys:
            for idx, api_key in enumerate(openrouter_keys):
                try:
                    print(f"  [LLM API] Trying OpenRouter key {idx+1}/{len(openrouter_keys)} for model {openrouter_model}")
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost",
                        "X-Title": "CDSS GraphRAG Engine",
                    }
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})
                    payload = {
                        "model": openrouter_model,
                        "messages": messages,
                        "temperature": 0.1 if response_format == "json" else 0.0,
                        "max_tokens": 2500,
                    }
                    if response_format == "json":
                        payload["response_format"] = {"type": "json_object"}
                    with httpx.Client(timeout=45.0) as http_client:
                        r = http_client.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers=headers,
                            json=payload,
                        )
                        if r.status_code == 200:
                            return clean_thinking_tags(r.json()["choices"][0]["message"]["content"])
                        else:
                            raise Exception(f"OpenRouter returned {r.status_code}: {r.text[:150]}")
                except Exception as e:
                    err_msg = f"OpenRouter fallback key {idx+1} failed: {e}"
                    print(f"⚠️ {err_msg}")
                    errors.append(err_msg)

    err_details = " | ".join(errors) if errors else "No keys configured."
    raise Exception(f"All LLM APIs failed. ({err_details})")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — Chunked Entity Linking
# ─────────────────────────────────────────────────────────────────────────────

def chunk_match_entities(clinical_text: str, kg_nodes: list[dict], chunk_size: int = 100) -> tuple[list[str], list[str]]:
    """
    Map clinical text to KG node IDs using a two-stage approach:
    1. Extract English medical concepts from the clinical text using LLM.
    2. Filter the 391 KG nodes down to a small list of candidate nodes.
    3. Perform entity linking on the candidates.
    Returns a tuple: (matched_nodes_list, extracted_terms_list)
    """
    if not kg_nodes:
        return [], []

    print(f"  [Stage 1] Starting two-stage entity matching for: {clinical_text[:60]}...")

    # Stage 1a: Extract English medical terms from clinical text
    extraction_prompt = f"""You are a medical translation assistant. Extract all clinical concepts, symptoms, diseases, drugs, and key patient states mentioned in the clinical scenario below and translate them into standard English medical terms.

CRITICAL MAPPING & STATUS MODIFIER RULES:
1. Pay extremely close attention to status modifiers of clinical measurements or symptoms (e.g., normal, normal range, stable, controlled vs high, increased, low, decreased).
2. If a measurement is explicitly stated as normal, stable, or controlled (e.g., "đường huyết đói bình thường", "huyết áp ổn định"), do NOT extract pathologically high or low states. Instead, translate it to its normal equivalent (e.g., "normal fasting glucose", "normal blood pressure") or do not extract it if it has no clinical relevance.
3. If a measurement is high or increased (e.g., "đường huyết cao", "tăng đường huyết"), map it to its corresponding pathologically high state.
4. If a measurement is low or decreased (e.g., "hạ đường huyết"), map it to its corresponding pathologically low state.
5. Do NOT extract any terms that are not mentioned or implied in the clinical scenario. Do not copy examples from these rules.

Clinical scenario: "{clinical_text}"

Return ONLY a valid JSON list of objects representing these English medical terms, each with a "term" and a "type" (which must be either "Disease", "Drug", "Symptom", or "Concept").
Example: [[{{"term": "Diabetes Mellitus", "type": "Disease"}}, {{"term": "Metformin", "type": "Drug"}}, {{"term": "Nocturia", "type": "Symptom"}}]]
Do not include any other text or markdown formatting.
"""
    try:
        raw_extraction = call_llm_api(extraction_prompt, response_format="text", model_size="8b")
        bracket_match = re.search(r'\[.*?\]', raw_extraction, re.DOTALL)
        if not bracket_match:
            print("  ⚠️ Stage 1a failed to parse extraction output:", raw_extraction)
            extracted_terms = []
        else:
            extracted_terms = json.loads(bracket_match.group())
            print("  [Stage 1a] Extracted English terms:", extracted_terms)
    except Exception as e:
        print("  ⚠️ Stage 1a extraction error:", e)
        extracted_terms = []

    if not extracted_terms:
        return [], []

    # Stage 1b: Filter KG nodes to candidates based on keyword overlap
    candidates = set()
    for term in extracted_terms:
        term_str = term.get("term", "") if isinstance(term, dict) else str(term)
        term_lower = term_str.lower().strip()
        term_words_clean = set(re.findall(r'\w+', term_lower))
        
        for node_entry in kg_nodes:
            node_id = node_entry["id"]
            node_aliases = node_entry.get("aliases", [])
            
            # 1. Substring matching on ID
            id_lower = node_id.lower().strip()
            if term_lower in id_lower or id_lower in term_lower:
                candidates.add(node_id)
                continue
                
            # 2. Substring matching on Aliases
            alias_matched = False
            for alias in node_aliases:
                alias_lower = alias.lower().strip()
                if term_lower in alias_lower or alias_lower in term_lower:
                    candidates.add(node_id)
                    alias_matched = True
                    break
            if alias_matched:
                continue
                
            # 3. Word boundary overlap matching on ID
            id_words_clean = set(re.findall(r'\w+', id_lower))
            overlap = term_words_clean.intersection(id_words_clean)
            overlap = {w for w in overlap if w not in {"disease", "diseases", "mellitus", "type", "in", "of", "and", "or", "patients", "with"}}
            if len(overlap) >= 2:
                candidates.add(node_id)
                continue
                
            # 4. Word boundary overlap matching on Aliases
            for alias in node_aliases:
                alias_words_clean = set(re.findall(r'\w+', alias.lower().strip()))
                overlap = term_words_clean.intersection(alias_words_clean)
                overlap = {w for w in overlap if w not in {"disease", "diseases", "mellitus", "type", "in", "of", "and", "or", "patients", "with"}}
                if len(overlap) >= 2:
                    candidates.add(node_id)
                    break

    candidate_list = list(candidates)
    print(f"  [Stage 1b] Filtered to {len(candidate_list)} candidate nodes")

    if not candidate_list:
        return [], extracted_terms

    # Stage 1c: Perform linking using LLM on the small candidate list
    nodes_str = ", ".join(f'"{n}"' for n in candidate_list)
    linking_prompt = f"""You are an expert clinical entity linker. Identify which entities from the provided "Knowledge Graph entities" list are mentioned or clearly implied in the "Clinical scenario".

Knowledge Graph entities (English):
[{nodes_str}]

Clinical scenario (Vietnamese/English): "{clinical_text}"

CRITICAL RULES:
1. Map the Vietnamese concepts in the clinical scenario to their correct English equivalents in the list.
2. Status Modifier Safeguard: If the clinical scenario says a measurement or condition is normal, stable, or controlled, do NOT link it to pathological entities in the list (e.g., do not link normal blood glucose to pathologically high or low states).
3. Return ONLY a valid JSON list containing the matched entity names EXACTLY as they appear in the list.
4. STRICT MATCHING: If none of the candidate entities in the list are mentioned or clearly implied in the clinical scenario, you MUST return an empty list: []. Do not match unrelated entities.
"""
    try:
        raw_linking = call_llm_api(linking_prompt, response_format="text", model_size="8b")
        bracket_match = re.search(r'\[.*?\]', raw_linking, re.DOTALL)
        if bracket_match:
            matched = json.loads(bracket_match.group())
            # Double check that they actually exist in the candidate list
            cand_lower = {c.lower(): c for c in candidate_list}
            result = []
            for m in matched:
                if isinstance(m, str):
                    canon = cand_lower.get(m.strip().lower())
                    if canon:
                        result.append(canon)
            print(f"  [Stage 1c] Matched {len(result)} entities: {result}")
            return result, extracted_terms
    except Exception as e:
        print("  ⚠️ Stage 1c linking error:", e)

    return [], extracted_terms


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — BFS Multi-hop Graph Traversal
# ─────────────────────────────────────────────────────────────────────────────

def bfs_multi_hop_traversal(seed_nodes: list[str]) -> list[dict]:
    """
    Execute 2-hop BFS graph traversal over Neo4j, plus a dedicated
    CONTRAINDICATED_WITH query for Circuit Breaker detection.
    Returns a flat list of triples with 'hop' markers.
    """
    if not seed_nodes:
        return []

    print(f"  [Stage 2] BFS traversal from seeds: {seed_nodes}")

    # Priority: always fetch contraindications first
    contraindication_triples = get_contraindications_direct(seed_nodes)
    print(f"  [Stage 2] CONTRAINDICATED_WITH triples: {len(contraindication_triples)}")

    # Hop 1
    hop1_triples = get_bfs_hop1(seed_nodes, limit=60)
    print(f"  [Stage 2] Hop-1 triples: {len(hop1_triples)}")

    # Hop 2 (expand from hop-1 targets)
    hop2_triples = get_bfs_hop2(hop1_triples, seed_nodes, limit=60)
    print(f"  [Stage 2] Hop-2 triples: {len(hop2_triples)}")

    # Merge, dedup by (subject, relation, object)
    all_triples = []
    seen = set()
    for triple in contraindication_triples + hop1_triples + hop2_triples:
        key = (triple["subject"], triple["relation"], triple["object"])
        if key not in seen:
            seen.add(key)
            all_triples.append(triple)

    print(f"  [Stage 2] Total unique triples after merge: {len(all_triples)}")
    return all_triples


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — Priority Scoring & Pruning
# ─────────────────────────────────────────────────────────────────────────────

def score_and_prune_triples(all_triples: list[dict], max_triples: int = 50) -> list[dict]:
    """
    Score each triple by relation type priority weight (from RELATION_WEIGHTS).
    Triples from hop-1 get a +2 bonus. Triples from CONTRAINDICATED_WITH
    always go first (sorted by weight desc), then pruned to max_triples.
    Multiplies by relation confidence score from the database.
    """
    def score(triple: dict) -> float:
        rel = triple.get("relation", "").upper()
        weight = RELATION_WEIGHTS.get(rel, 1)
        hop_bonus = 2 if triple.get("hop", 1) == 1 else 0
        db_confidence = triple.get("confidence", 100.0) / 100.0
        # CONTRAINDICATED_WITH always gets top score regardless
        if rel == "CONTRAINDICATED_WITH":
            return (100 + hop_bonus) * db_confidence
        return (weight + hop_bonus) * db_confidence

    scored = sorted(all_triples, key=score, reverse=True)
    pruned = scored[:max_triples]
    print(f"  [Stage 3] Pruned to {len(pruned)} triples (from {len(all_triples)})")
    return pruned


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3b — Structured Context Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_rich_graph_context(scored_triples: list[dict], seed_nodes: list[str]) -> str:
    """
    Organise scored triples into 3 structured sections for the LLM:
      1. CIRCUIT BREAKER — CONTRAINDICATED_WITH edges
      2. TREATMENT RELATIONS — TREATED_BY, HAS_ADVERSE_EFFECT, PREFERRED_OVER, DECREASES
      3. EVIDENCE CHAINS — HAS_FINDING, CAUSE_OF, INCREASES_RISK_OF, etc.
    """
    TREATMENT_RELS = {"TREATED_BY", "HAS_ADVERSE_EFFECT", "PREFERRED_OVER", "DECREASES"}
    CIRCUIT_RELS   = {"CONTRAINDICATED_WITH"}

    circuit_lines    = []
    treatment_lines  = []
    evidence_lines   = []

    for t in scored_triples:
        rel_upper = t["relation"].upper()
        conf_str = f", confidence={t.get('confidence', 100.0):.1f}%"
        line = f"  [{t.get('subject_type','?')}] {t['subject']} --({t['relation']}, hop={t.get('hop',1)}{conf_str})--> [{t.get('object_type','?')}] {t['object']}"
        if rel_upper in CIRCUIT_RELS:
            circuit_lines.append(line)
        elif rel_upper in TREATMENT_RELS:
            treatment_lines.append(line)
        else:
            evidence_lines.append(line)

    sections = []
    if circuit_lines:
        sections.append(
            "🚨 CIRCUIT BREAKER — CONTRAINDICATED_WITH (HIGHEST PRIORITY):\n" +
            "\n".join(circuit_lines)
        )
    if treatment_lines:
        sections.append(
            "💊 TREATMENT RELATIONS — TREATED_BY / HAS_ADVERSE_EFFECT / PREFERRED_OVER:\n" +
            "\n".join(treatment_lines)
        )
    if evidence_lines:
        sections.append(
            "🔬 EVIDENCE CHAINS — HAS_FINDING / CAUSE_OF / INCREASES_RISK_OF / IS_A / …:\n" +
            "\n".join(evidence_lines)
        )

    if not sections:
        return "=== NO MATCHING GRAPH DATA FOUND IN NEO4J ===\n"

    header = (
        f"=== KNOWLEDGE GRAPH DATA RETRIEVED FROM NEO4J ===\n"
        f"Seed entities identified: {', '.join(seed_nodes)}\n"
        f"Total triples retrieved: {len(scored_triples)}\n\n"
    )
    return header + "\n\n".join(sections)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — Graph-Grounded LLM Inference
# ─────────────────────────────────────────────────────────────────────────────

def check_term_coverage(term: str) -> bool:
    """Helper to check if a specific term exists in Neo4j database."""
    driver = get_db_driver()
    if not driver:
        return False
    query = """
    MATCH (n)
    WHERE toLower(n.id) CONTAINS toLower($term)
       OR toLower($term) CONTAINS toLower(n.id)
       OR (n.aliases IS NOT NULL AND any(a in n.aliases WHERE toLower(a) CONTAINS toLower($term) OR toLower($term) CONTAINS toLower(a)))
    RETURN count(n) > 0 as found
    """
    try:
        with driver.session() as session:
            res = session.run(query, term=term)
            rec = res.single()
            return rec["found"] if rec else False
    except Exception:
        return False


def is_term_covered_by_matched_nodes(term: str, matched_nodes: list[str]) -> bool:
    """Uses LLM to verify if a missing term is already synonymously covered by matched Neo4j entities."""
    if not matched_nodes:
        return False
    
    system_prompt = (
        "You are a medical vocabulary expert. Verify if a given medical term is synonymously or category-wise "
        "covered by a list of already matched database concepts. "
        "For example, 'Renal Insufficiency' or 'Kidney Disease' is covered if the list contains 'Chronic Kidney Diseases'. "
        "Respond with ONLY 'YES' or 'NO'."
    )
    prompt = f"Term to verify: \"{term}\"\nMatched nodes:\n{json.dumps(matched_nodes, ensure_ascii=False)}"
    
    try:
        response = call_llm_api(prompt, system_prompt=system_prompt, model_size="70b")
        ans = response.strip().upper()
        if "YES" in ans:
            return True
    except Exception as e:
        print(f"⚠️ Error verifying term coverage: {e}")
    return False


def get_no_data_response(missing_str: str, matched_nodes: list[str], pipeline_logs: list[str]) -> dict:
    """Helper to return a clean 'No database data' fallback structure when relevant data is missing."""
    alert_msg = f"Bệnh lý/thuốc '{missing_str}' chưa được nạp vào cơ sở dữ liệu Neo4j."
    return {
        "matched_entities": matched_nodes,
        "alert": {
            "active": False,
            "title": "⚠️ KHÔNG CÓ DỮ LIỆU ĐỒ THỊ",
            "rule": alert_msg,
        },
        "differential_diagnosis": {
            "condition_a": "Không có dữ liệu",
            "condition_b": "Không có dữ liệu",
            "prose_a": f"Hệ thống CDSS hiện tại chưa có dữ liệu đồ thị tri thức về bệnh lý '{missing_str}' trong ca lâm sàng này. Vui lòng nạp thêm dữ liệu y văn.",
            "prose_b": f"Hệ thống CDSS hiện tại chưa có dữ liệu đồ thị tri thức về bệnh lý '{missing_str}' trong ca lâm sàng này. Vui lòng nạp thêm dữ liệu y văn.",
            "distinguishing_factor": "Không có dữ liệu đối chiếu trong đồ thị tri thức hiện tại."
        },
        "graph_path": [],
        "evidence_triples": [],
        "recommendations": [
            {
                "type": "recommend",
                "title": "Cập nhật dữ liệu đồ thị Neo4j",
                "desc": f"Vui lòng chuẩn hóa và nạp thêm dữ liệu y văn liên quan đến '{missing_str}' thông qua neo4j_uploader.py.",
                "relation": "SYSTEM_ACTION"
            }
        ],
        "logs": pipeline_logs
    }


def check_is_valid_clinical_case(text: str) -> tuple[str, str]:
    """
    Evaluates if the input text is suitable for the CDSS system.
    Returns a tuple (status, message).
    status can be:
      - "valid": It is a valid clinical case scenario related to diabetes/metabolic diseases.
      - "invalid_format": It is not a clinical case description (e.g. greeting, chat, or generic question).
      - "out_of_scope": It is a clinical text/case, but completely unrelated to diabetes/metabolic disorders.
    """
    if not text or len(text.strip()) < 15:
        return "invalid_format", "Vui lòng nhập đầy đủ thông tin ca lâm sàng (tối thiểu 15 ký tự) để hệ thống CDSS tiến hành phân tích."

    prompt = (
        "Bạn là trợ lý y khoa chuyên phân loại và đánh giá tính hợp lệ của văn bản lâm sàng nhập vào hệ thống CDSS hỗ trợ điều trị ĐÁI THÁO ĐƯỜNG.\n"
        "Nhiệm vụ: Phân tích đoạn văn bản đầu vào của người dùng và xác định trạng thái của nó:\n"
        "1. Nếu văn bản là câu hỏi trò chuyện thông thường, lời chào, hoặc câu hỏi ngoài lĩnh vực y khoa, hãy phân loại là \"invalid_format\".\n"
        "2. Nếu văn bản mô tả ca bệnh lâm sàng hoặc hỏi về điều trị bệnh, nhưng hoàn toàn KHÔNG liên quan đến Đái tháo đường (Diabetes), các biến chứng đái tháo đường (bệnh thận, võng mạc, tim mạch liên quan), hoặc các thuốc tiểu đường, hãy phân loại là \"out_of_scope\".\n"
        "3. Nếu văn bản mô tả ca lâm sàng hợp lệ và CÓ liên quan đến Đái tháo đường hoặc các tình trạng đi kèm của bệnh nhân đái tháo đường, hãy phân loại là \"valid\".\n\n"
        "Văn bản đầu vào:\n"
        f"\"{text}\"\n\n"
        "Hãy trả về kết quả dưới dạng JSON object với 2 trường:\n"
        "1. \"status\": \"valid\", \"invalid_format\" hoặc \"out_of_scope\"\n"
        "2. \"reason\": Giải thích lý do bằng tiếng Việt ngắn gọn:\n"
        "   - Nếu \"invalid_format\": Giải thích ngắn gọn tại sao không phải ca lâm sàng.\n"
        "   - Nếu \"out_of_scope\": Tạo một câu phản hồi chuẩn theo mẫu: \"Hệ thống hiện tại chỉ hỗ trợ tra cứu và quyết định lâm sàng trong phạm vi bệnh Đái tháo đường. Thông tin về [tên bệnh lý cụ thể] và [tên thuốc cụ thể] nằm ngoài phạm vi cơ sở dữ liệu tri thức của hệ thống.\" (hãy điền đúng tên bệnh và thuốc xuất hiện trong văn bản của người dùng vào các chỗ ngoặc vuông, ví dụ: 'bệnh hen phế quản và thuốc Salbutamol').\n"
        "   - Nếu \"valid\": Để trống."
    )
    try:
        # Call fast 8b model on Groq
        response = call_llm_api(prompt, system_prompt="Phân loại phạm vi ca lâm sàng.", response_format="json", model_size="8b", force_groq=True)
        res_dict = json.loads(response)
        if isinstance(res_dict, dict):
            status = str(res_dict.get("status", "valid")).strip().lower()
            reason = str(res_dict.get("reason", "")).strip()
            if status not in {"valid", "invalid_format", "out_of_scope"}:
                status = "valid"
            return status, reason
    except Exception as e:
        print(f"⚠️ Error checking clinical case validity: {e}")
    
    # Fallback to valid if check fails to avoid blocking valid scenarios
    return "valid", ""


def get_invalid_case_response(warning_msg: str, pipeline_logs: list[str]) -> dict:
    """Helper to return a warning response when the input text is not a valid clinical case."""
    return {
        "matched_entities": [],
        "alert": {
            "active": True,
            "title": "⚠️ HỆ THỐNG CDSS: YÊU CẦU NHẬP CA LÂM SÀNG",
            "rule": warning_msg,
        },
        "differential_diagnosis": {
            "condition_a": "Không có dữ liệu",
            "condition_b": "Không có dữ liệu",
            "prose_a": "Vui lòng nhập mô tả ca lâm sàng thực tế của bệnh nhân (ví dụ: tuổi, giới tính, triệu chứng, tiền sử bệnh, hoặc đề xuất kê đơn thuốc) để hệ thống CDSS tiến hành phân tích đối chiếu đồ thị tri thức.",
            "prose_b": "Hệ thống hỗ trợ ra quyết định lâm sàng (CDSS) yêu cầu thông tin đầu vào là hồ sơ/ca bệnh cụ thể, không hỗ trợ trả lời các câu hỏi trò chuyện thông thường hoặc hỏi đáp lý thuyết.",
            "distinguishing_factor": "Đầu vào không đủ dữ kiện lâm sàng để phân tích đối chiếu."
        },
        "graph_path": [],
        "evidence_triples": [],
        "recommendations": [
            {
                "type": "exclude",
                "title": "Yêu cầu nhập lại ca lâm sàng",
                "desc": "Vui lòng nhập văn bản mô tả cụ thể tình trạng bệnh nhân và thuốc đang cân nhắc điều trị.",
                "relation": "SYSTEM_ACTION"
            }
        ],
        "logs": pipeline_logs
    }


def get_out_of_scope_response(warning_msg: str, pipeline_logs: list[str]) -> dict:
    """Helper to return an out-of-scope response when the topic is unrelated to Diabetes."""
    return {
        "matched_entities": [],
        "alert": {
            "active": True,
            "title": "⚠️ HỆ THỐNG CDSS: NGOÀI PHẠM VI HỖ TRỢ",
            "rule": warning_msg,
        },
        "differential_diagnosis": {
            "condition_a": "Ngoài phạm vi hỗ trợ",
            "condition_b": "Ngoài phạm vi hỗ trợ",
            "prose_a": warning_msg,
            "prose_b": "Hệ thống hỗ trợ ra quyết định lâm sàng (CDSS) này chỉ được nạp dữ liệu tri thức chuyên biệt cho bệnh Đái tháo đường (Diabetes Mellitus) và các biến chỉ định liên quan.",
            "distinguishing_factor": "Bệnh lý hoặc thuốc đang truy vấn không nằm trong cơ sở dữ liệu Neo4j của hệ thống."
        },
        "graph_path": [],
        "evidence_triples": [],
        "recommendations": [
            {
                "type": "exclude",
                "title": "Bệnh lý ngoài danh mục",
                "desc": warning_msg,
                "relation": "SYSTEM_ACTION"
            }
        ],
        "logs": pipeline_logs
    }


def generate_medical_decision(clinical_text: str, patient_id: str) -> dict:
    """
    4-Stage GraphRAG CDSS pipeline:
      Stage 1: Chunked entity linking over all 391 KG nodes
      Stage 2: BFS 2-hop traversal + priority CONTRAINDICATED_WITH query
      Stage 3: Relation-priority scoring, pruning to top-40 triples
      Stage 4: Graph-grounded LLM inference → structured JSON decision (with strict hallucination blocker)
    """
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    
    # ── Check input validity and scope ──
    status, warning_msg = check_is_valid_clinical_case(clinical_text)
    if status == "invalid_format":
        pipeline_logs = [f"[{ts} WARNING] Ca lâm sàng không hợp lệ: {warning_msg}"]
        return get_invalid_case_response(warning_msg, pipeline_logs)
    elif status == "out_of_scope":
        pipeline_logs = [f"[{ts} WARNING] Ngoài phạm vi hỗ trợ: {warning_msg}"]
        return get_out_of_scope_response(warning_msg, pipeline_logs)

    pipeline_logs = [
        f"[{ts} INFO] Stage 1: Fetching all KG nodes from Neo4j...",
    ]

    # ── Stage 1: Entity Linking ──────────────────────────────────────────────
    kg_nodes = get_all_cdss_nodes()
    pipeline_logs.append(f"[{ts} INFO] Stage 1: {len(kg_nodes)} nodes fetched. Running chunked LLM entity matching...")
    matched_nodes, extracted_terms = chunk_match_entities(clinical_text, kg_nodes, chunk_size=100)
    pipeline_logs.append(f"[{ts} INFO] Stage 1 complete: matched {len(matched_nodes)} entities → {matched_nodes}")

    # Check database coverage: Do the matched entities contain at least one Disease or Drug node in Neo4j?
    has_coverage = False
    if matched_nodes:
        driver = get_db_driver()
        if driver:
            try:
                with driver.session() as session:
                    res = session.run(
                        "MATCH (n) WHERE n.id IN $nodes AND ('Disease' IN labels(n) OR 'Drug' IN labels(n) OR 'Symptom' IN labels(n)) RETURN count(n) > 0 as ok",
                        nodes=matched_nodes
                    )
                    record = res.single()
                    has_coverage = record["ok"] if record else False
            except Exception as db_err:
                print(f"⚠️ Neo4j coverage check error: {db_err}")
                has_coverage = False

    # Check which extracted terms are missing from the database
    missing_terms = []
    for term in extracted_terms:
        if isinstance(term, dict):
            term_str = term.get("term", "").strip()
            term_type = term.get("type", "").strip().lower()
        else:
            term_str = str(term).strip()
            term_type = "disease"  # Default fallback if type info is missing

        # Only strictly block if type is "disease" or "drug"
        if term_type in {"disease", "drug"}:
            if len(term_str) > 3 and term_str.lower() not in {
                "pregnancy", "patient", "male", "female", "years", "old", "onset", 
                "acute", "chronic", "history", "stable", "normal", "range", "controlled",
                "controlled clinical trial", "finding", "findings", "symptom", "symptoms"
            }:
                if not check_term_coverage(term_str):
                    if not is_term_covered_by_matched_nodes(term_str, matched_nodes):
                        missing_terms.append(term_str)

    if not has_coverage or missing_terms:
        missing_str = ", ".join(missing_terms) if missing_terms else "bệnh lý liên quan"
        pipeline_logs.append(f"[{ts} WARNING] Thiếu dữ liệu đồ thị cho các thực thể quan trọng: '{missing_str}'. Bỏ qua suy luận để chống ảo giác.")
        return get_no_data_response(missing_str, matched_nodes, pipeline_logs)

    # ── Stage 2: BFS Graph Traversal ────────────────────────────────────────
    pipeline_logs.append(f"[{ts} INFO] Stage 2: BFS 2-hop traversal from seed nodes...")
    all_triples = bfs_multi_hop_traversal(matched_nodes)
    has_contraindication = any(
        t["relation"].upper() == "CONTRAINDICATED_WITH" for t in all_triples
    )
    pipeline_logs.append(
        f"[{ts} {'WARNING' if has_contraindication else 'INFO'}] "
        f"Stage 2 complete: {len(all_triples)} triples. "
        f"{'⚠️ CONTRAINDICATED_WITH edge found!' if has_contraindication else 'No contraindication edges.'}"
    )

    # ── Stage 3: Scoring & Context Building ─────────────────────────────────
    pipeline_logs.append(f"[{ts} INFO] Stage 3: Scoring and pruning triples (max 50)...")
    scored_triples = score_and_prune_triples(all_triples, max_triples=50)
    graph_context = build_rich_graph_context(scored_triples, matched_nodes)
    pipeline_logs.append(f"[{ts} INFO] Stage 3 complete: {len(scored_triples)} triples in context.")

    # ── Stage 4: Graph-grounded LLM Inference ───────────────────────────────
    pipeline_logs.append(f"[{ts} INFO] Stage 4: Calling LLM with graph-grounded context...")

    system_prompt = f"""You are a Clinical Decision Support System (CDSS) powered by a Medical Knowledge Graph (Neo4j).

Your ONLY source of truth for clinical reasoning is the graph data provided below.
You MUST NOT invent clinical rules or contraindications that are not supported by the graph data.

{graph_context}

CRITICAL TRANSLATION & REFERENCE INSTRUCTIONS:
- Translate all English concept/node names in graph_path.title and evidence_triples.subject/object to standard, commonly used Vietnamese medical terms.
- Keep the `original_id` and `original_subject_id`/`original_object_id` fields EXACTLY as they appear in the English graph data.
- STRICT RELATION MATCHING & ANTI-HALLUCINATION SAFEGUARDS:
  1. Use ONLY relations and connections explicitly present in the graph data.
  2. START PATH WITH CONNECTED NODES only.
  3. NO INVERTED CONNECTIONS unless explicitly shown.

REASONING INSTRUCTIONS:
1. CIRCUIT BREAKER: If ANY triple with relation CONTRAINDICATED_WITH exists above, activate the alert with the exact drug/condition pair from that triple.

2. BIỆN LUẬN CHẨN ĐOÁN (DIAGNOSTIC REASONING): Đối chiếu các triệu chứng lâm sàng của bệnh nhân với các bộ ba tri thức Neo4j được cung cấp ở trên để lập luận chẩn đoán:
   - `condition_a`: **BẮT BUỘC** điền tên một bệnh/tình trạng lâm sàng CÓ MẶT trong ca lâm sàng này — trích từ ca lâm sàng hoặc từ các thực thể đã khớp trong đồ thị. KHÔNG BAO GIỜ được điền "Không có dữ liệu".
   - `prose_a`: Viết 2-3 câu tiếng Việt giải thích tại sao chẩn đoán CÓ bệnh này, dựa trên các bộ ba tri thức cụ thể khớp với triệu chứng thực tế của bệnh nhân làm bằng chứng. Nếu không có triple chẩn đoán trong đồ thị, hãy suy luận dựa trên thông tin lâm sàng được cung cấp trong ca lâm sàng.
   - `condition_b`: **BẮT BUỘC** điền tên một bệnh cần biện luận loại trừ — có thể là bệnh đồng mắc, biến chứng hoặc chẩn đoán thay thế dựa trên bối cảnh lâm sàng. KHÔNG BAO GIỜ được điền "Không có dữ liệu".
   - `prose_b`: Viết 2-3 câu tiếng Việt giải thích tại sao KHÔNG nghĩ đến bệnh này hoặc cần theo dõi thêm, dựa trên việc thiếu các bằng chứng bộ ba tri thức hoặc các dấu hiệu lâm sàng không khớp.
   - `distinguishing_factor`: Viết một câu ngắn kết luận chẩn đoán xác định bệnh nào và loại trừ bệnh nào dựa trên bằng chứng đồ thị cốt lõi.
   - **LƯU Ý ĐẶC BIỆT**: Nếu Circuit Breaker đã kích hoạt (có CONTRAINDICATED_WITH), hãy dùng các bệnh lý và thuốc trong triple CCĐ làm chủ đề chẩn đoán phân biệt. Ví dụ: condition_a = bệnh nền của bệnh nhân, condition_b = tình trạng cần loại trừ hoặc biến chứng tiềm ẩn.

3. GRAPH PATH (linear chain): Trace symptom → disease → treatment using ONLY concepts and connections from the graph data above.
   - "title" field: ALWAYS translate to standard Vietnamese medical terms.
   - "original_id" field: Keep the EXACT original English node ID as retrieved from the graph data above.
   - "edge" field: Keep the EXACT relation type in UPPERCASE English as it appears in the graph data (e.g. "TREATED_BY", "HAS_FINDING", "DECREASES").
   - Include node_type and hop for each node.

4. EVIDENCE TRIPLES: Select up to 5 triples from graph data that best SUPPORT THE DIAGNOSIS, and up to 5 triples that best SUPPORT THE TREATMENT.
   - "subject" and "object" fields: ALWAYS translate to standard Vietnamese medical terms.
   - "original_subject_id" and "original_object_id" fields: Keep the EXACT original English subject/object IDs as retrieved from the graph data above.
   - "relation" field: Keep the EXACT relation type in UPPERCASE English as it appears in the graph data.
   - Use group="diagnosis" or group="treatment".

5. RECOMMENDATIONS: From TREATED_BY, PREFERRED_OVER, HAS_ADVERSE_EFFECT, CONTRAINDICATED_WITH, DECREASES triples only.

CRITICAL OUTPUT RULES:
- Output ONLY valid JSON. No markdown, no code blocks.
- All narrative text (prose_a, prose_b, distinguishing_factor, title, desc) must be in Vietnamese.
- Relation types (edge, relation fields) stay in UPPERCASE English.
- EXACT structure:

{{
  "matched_entities": ["entity1", "entity2"],
  "alert": {{
    "active": true,
    "title": "🛑 KÍCH HOẠT NGẮT MẠCH: Chống chỉ định dùng [Tên thuốc]",
    "rule": "[Bệnh lý] → (CONTRAINDICATED_WITH) → [Thuốc]"
  }},
  "differential_diagnosis": {{
    "condition_a": "Tên bệnh chẩn đoán CÓ mắc",
    "condition_b": "Tên bệnh chẩn đoán KHÔNG mắc (hoặc loại trừ)",
    "prose_a": "Đoạn văn 2-3 câu biện luận tại sao bệnh nhân CÓ mắc bệnh A dựa trên việc triệu chứng khớp với các bộ ba tri thức cụ thể trong đồ thị (nêu rõ các bộ ba làm bằng chứng)...",
    "prose_b": "Đoạn văn 2-3 câu biện luận tại sao loại trừ hoặc chẩn đoán KHÔNG mắc bệnh B dựa trên sự thiếu hụt bằng chứng bộ ba tri thức hoặc các đặc điểm lâm sàng không phù hợp...",
    "distinguishing_factor": "Kết luận chẩn đoán xác định và loại trừ dựa trên bằng chứng đồ thị cốt lõi."
  }},
  "graph_path": [
    {{ "title": "Tên Node", "original_id": "Original English Node ID", "node_type": "Disease|Drug|Symptom|Anatomy|Concept", "hop": 0 }},
    {{ "edge": "RELATION_TYPE_FROM_GRAPH" }},
    {{ "title": "Tên Node", "original_id": "Original English Node ID", "node_type": "Disease|Drug|Symptom|Anatomy|Concept", "hop": 1 }},
    {{ "edge": "RELATION_TYPE_FROM_GRAPH" }},
    {{ "title": "Tên Node", "original_id": "Original English Node ID", "node_type": "Disease|Drug|Symptom|Anatomy|Concept", "hop": 2 }}
  ],
  "evidence_triples": [
    {{ "group": "diagnosis", "subject": "Tên node", "original_subject_id": "Original English Subject ID", "relation": "RELATION", "object": "Tên node", "original_object_id": "Original English Object ID", "subject_type": "Symptom", "object_type": "Disease" }},
    {{ "group": "treatment", "subject": "Tên bệnh", "original_subject_id": "Original English Subject ID", "relation": "TREATED_BY", "object": "Tên thuốc", "original_object_id": "Original English Object ID", "subject_type": "Disease", "object_type": "Drug" }}
  ],
  "recommendations": [
    {{
      "type": "recommend",
      "title": "Tên thuốc / Liệu pháp",
      "desc": "Lý do khuyến nghị từ dữ liệu đồ thị.",
      "relation": "TREATED_BY"
    }}
  ],
  "logs": {json.dumps(pipeline_logs, ensure_ascii=False)}
}}
"""

    raw_response = None
    try:
        raw_response = call_llm_api(
            prompt=f"Analyse the following clinical scenario for patient '{patient_id}': {clinical_text}",
            system_prompt=system_prompt,
            response_format="json",
        )
        # Robust JSON extraction: find first '{' and last '}'
        cleaned = raw_response.strip()
        start = cleaned.find('{')
        end   = cleaned.rfind('}')
        if start != -1 and end != -1 and start < end:
            cleaned = cleaned[start:end + 1]

        result = json.loads(cleaned)

        # Inject pipeline logs if LLM didn't include them properly
        if not result.get("logs"):
            result["logs"] = pipeline_logs

        # ALWAYS overwrite matched_entities with the pipeline's verified matches
        # (prevents LLM from hallucinating unverified entity names into this field)
        result["matched_entities"] = matched_nodes

        # ── Strict Hallucination Blocker ─────────────────────────────────────
        # Build an ID resolver from lowercase IDs and aliases to canonical IDs
        id_resolver = {}
        for node in kg_nodes:
            canon_id = node["id"]
            id_resolver[canon_id.lower().strip()] = canon_id
            for alias in node.get("aliases", []):
                id_resolver[alias.lower().strip()] = canon_id

        # Verify that all returned node names and relationships exist in scored_triples or matched_nodes.
        valid_node_ids = {n.lower() for n in matched_nodes}
        valid_triples = set()
        for t in scored_triples:
            s_id = t["subject"].lower().strip()
            r_id = t["relation"].lower().strip()
            o_id = t["object"].lower().strip()
            valid_node_ids.add(s_id)
            valid_node_ids.add(o_id)
            valid_triples.add((s_id, r_id, o_id))
            valid_triples.add((o_id, r_id, s_id)) # Direction-agnostic verification for safety

        def resolve_id(user_provided_id: str) -> str:
            if not user_provided_id:
                return None
            cleaned = str(user_provided_id).strip().lower()
            # 1. Exact or alias match
            if cleaned in id_resolver:
                return id_resolver[cleaned]
            # 2. Fuzzy match using Jaccard similarity at the word level
            words_cleaned = set(cleaned.split())
            if not words_cleaned:
                return None
            best_score = 0.0
            best_canon = None
            for k, canon in id_resolver.items():
                words_k = set(k.split())
                if not words_k:
                    continue
                intersection = words_cleaned.intersection(words_k)
                union = words_cleaned.union(words_k)
                jaccard = len(intersection) / len(union)
                # Boost score if cleaned is a contiguous substring of k or vice versa
                if cleaned in k or k in cleaned:
                    jaccard += 0.1
                if jaccard > best_score:
                    best_score = jaccard
                    best_canon = canon
            if best_score >= 0.4:
                return best_canon
            return None


        # Build a lookup dictionary for confidence scores: (s_id, rel, o_id) -> confidence
        conf_lookup = {}
        for t in scored_triples:
            s_id = t["subject"].lower().strip()
            r_id = t["relation"].lower().strip()
            o_id = t["object"].lower().strip()
            conf_lookup[(s_id, r_id, o_id)] = t.get("confidence", 100.0)
            conf_lookup[(o_id, r_id, s_id)] = t.get("confidence", 100.0)

        def find_valid_triple(s_prov: str, r_prov: str, o_prov: str):
            s_resolved = resolve_id(s_prov)
            o_resolved = resolve_id(o_prov)
            
            if not s_resolved or not o_resolved:
                return None
                
            s_resolved_lower = s_resolved.lower()
            o_resolved_lower = o_resolved.lower()
            r_prov_lower = r_prov.lower().strip()
            
            # 1. Try direct match
            if (s_resolved_lower, r_prov_lower, o_resolved_lower) in valid_triples:
                return s_resolved, o_resolved
                
            # 2. Try partial/fuzzy match on nodes in valid_triples
            for s_cand, r_cand, o_cand in valid_triples:
                if r_cand == r_prov_lower:
                    # Check subject match (exact, or candidate starts with the resolved ID followed by a comma or space)
                    s_match = (s_cand == s_resolved_lower or 
                               s_cand.startswith(s_resolved_lower + ",") or 
                               s_cand.startswith(s_resolved_lower + " "))
                    # Check object match (exact, or candidate starts with the resolved ID followed by a comma or space)
                    o_match = (o_cand == o_resolved_lower or 
                               o_cand.startswith(o_resolved_lower + ",") or 
                               o_cand.startswith(o_resolved_lower + " "))
                    if s_match and o_match:
                        # Return the canonical casing from id_resolver
                        return id_resolver.get(s_cand, s_cand), id_resolver.get(o_cand, o_cand)
            return None

        has_hallucination = False
        hallucinated_elements = []

        # Validate and clean graph_path
        cleaned_graph_path = []
        if "graph_path" in result and isinstance(result["graph_path"], list):
            path_items = result["graph_path"]
            nodes_in_path = []
            edges_in_path = []
            for item in path_items:
                if "edge" in item:
                    edges_in_path.append(item)
                else:
                    nodes_in_path.append(item)
            
            # Resolve nodes
            resolved_nodes = []
            for node in nodes_in_path:
                orig_id = str(node.get("original_id", "")).strip()
                title = str(node.get("title", "")).strip()
                
                resolved_id = resolve_id(orig_id) if orig_id else resolve_id(title)
                if not resolved_id or resolved_id.lower() not in valid_node_ids:
                    resolved_nodes.append(None)
                else:
                    resolved_nodes.append(node)
                    node["original_id"] = resolved_id
            
            # Reconstruct the path by keeping only valid hops
            if len(resolved_nodes) == len(edges_in_path) + 1:
                if resolved_nodes[0]:
                    cleaned_graph_path.append(resolved_nodes[0])
                
                edge_idx = 0
                for i in range(len(path_items)):
                    if "edge" in path_items[i]:
                        n1 = resolved_nodes[edge_idx]
                        n2 = resolved_nodes[edge_idx+1]
                        edge_rel = str(path_items[i].get("edge", "")).strip().lower()
                        
                        if n1 and n2 and edge_rel:
                            matched_triple = find_valid_triple(n1["original_id"], edge_rel, n2["original_id"])
                            if matched_triple:
                                canon_n1, canon_n2 = matched_triple
                                n1["original_id"] = canon_n1
                                n2["original_id"] = canon_n2
                                confidence = conf_lookup.get((canon_n1.lower(), edge_rel, canon_n2.lower()), 100.0)
                                cleaned_graph_path.append({"edge": path_items[i]["edge"].upper(), "confidence": confidence})
                                cleaned_graph_path.append(n2)
                        edge_idx += 1

        # Rebuild a fallback graph_path from scored_triples if it's empty
        if not cleaned_graph_path and scored_triples:
            t = scored_triples[0]
            cleaned_graph_path = [
                {"title": t["subject"], "original_id": t["subject"], "node_type": t.get("subject_type", "Concept"), "hop": 1},
                {"edge": t["relation"].upper(), "confidence": t.get("confidence", 100.0)},
                {"title": t["object"], "original_id": t["object"], "node_type": t.get("object_type", "Concept"), "hop": 2}
            ]
        result["graph_path"] = cleaned_graph_path

        # Validate and clean evidence_triples (ensure they are strictly from Neo4j)
        cleaned_evidence_triples = []
        if "evidence_triples" in result and isinstance(result["evidence_triples"], list):
            for t in result["evidence_triples"]:
                sub = str(t.get("subject", "")).strip()
                obj = str(t.get("object", "")).strip()
                rel = str(t.get("relation", "")).strip().lower()
                orig_sub = str(t.get("original_subject_id", "")).strip()
                orig_obj = str(t.get("original_object_id", "")).strip()
                
                matched_triple = find_valid_triple(orig_sub if orig_sub else sub, rel, orig_obj if orig_obj else obj)
                if matched_triple:
                    canon_sub, canon_obj = matched_triple
                    t["original_subject_id"] = canon_sub
                    t["original_object_id"] = canon_obj
                    t["relation"] = rel.upper()
                    t["confidence"] = conf_lookup.get((canon_sub.lower(), rel, canon_obj.lower()), 100.0)
                    cleaned_evidence_triples.append(t)
                else:
                    hallucinated_elements.append(f"Connection '{t.get('subject')} -[{t.get('relation')}]-> {t.get('object')}' not in graph")

        # Backfill evidence_triples from scored_triples to ensure we always have valid ones
        existing_keys = {(t["original_subject_id"].lower(), t["relation"].lower(), t["original_object_id"].lower()) for t in cleaned_evidence_triples}
        for t in scored_triples:
            if len(cleaned_evidence_triples) >= 6:
                break
            s_lower = t["subject"].lower()
            r_lower = t["relation"].lower()
            o_lower = t["object"].lower()
            if (s_lower, r_lower, o_lower) not in existing_keys:
                group = "treatment" if r_lower in {"treated_by", "has_adverse_effect", "preferred_over", "decreases"} else "diagnosis"
                cleaned_evidence_triples.append({
                    "group": group,
                    "subject": t["subject"],
                    "original_subject_id": t["subject"],
                    "relation": t["relation"].upper(),
                    "object": t["object"],
                    "original_object_id": t["object"],
                    "subject_type": t.get("subject_type", "Concept"),
                    "object_type": t.get("object_type", "Concept"),
                    "confidence": t.get("confidence", 100.0)
                })
                existing_keys.add((s_lower, r_lower, o_lower))
        result["evidence_triples"] = cleaned_evidence_triples

        # Collect all unique terms that will need translation to pre-fetch them in a single batch
        terms_to_translate = set()
        for mn in matched_nodes:
            terms_to_translate.add(mn)
        for t in scored_triples:
            terms_to_translate.add(t["subject"])
            terms_to_translate.add(t["object"])
        if "graph_path" in result and isinstance(result["graph_path"], list):
            for node in result["graph_path"]:
                if "edge" not in node:
                    orig_id = node.get("original_id", "")
                    if orig_id:
                        terms_to_translate.add(orig_id)
        if "evidence_triples" in result and isinstance(result["evidence_triples"], list):
            for t in result["evidence_triples"]:
                orig_sub = t.get("original_subject_id", "")
                orig_obj = t.get("original_object_id", "")
                if orig_sub:
                    terms_to_translate.add(orig_sub)
                if orig_obj:
                    terms_to_translate.add(orig_obj)
        
        # Batch translate everything at once! (Puts them in _translation_cache)
        if terms_to_translate:
            translate_multiple_terms(list(terms_to_translate))

        # ── Validate recommendations: flag (not delete) entries that can't be grounded in the graph ──
        # The LLM writes Vietnamese display names which often don't directly match English Neo4j node IDs.
        # We add a _verified flag for transparency but NEVER delete recommendations.
        if "recommendations" in result and isinstance(result["recommendations"], list):
            for rec in result["recommendations"]:
                rec_title = str(rec.get("title", "")).strip()
                rec_drug  = str(rec.get("drug", "")).strip()
                resolved_title = resolve_id(rec_title)
                resolved_drug  = resolve_id(rec_drug) if rec_drug else None
                if resolved_title or resolved_drug:
                    rec["_verified"] = True
                    if resolved_title:
                        rec["_verified_node"] = resolved_title
                else:
                    rec["_verified"] = False
                    hallucinated_elements.append(f"Recommendation '{rec_title}' not found in Neo4j graph nodes (kept, flagged)")

        # ── Validate differential_diagnosis: flag conditions not verifiable in the graph ──
        # Content is NEVER removed — this is LLM clinical reasoning, not graph facts.
        # We only annotate with a verified flag so the frontend can show an informational badge.
        if "differential_diagnosis" in result and isinstance(result["differential_diagnosis"], dict):
            dd = result["differential_diagnosis"]
            condition_a = str(dd.get("condition_a", "")).strip()
            condition_b = str(dd.get("condition_b", "")).strip()

            # Pre-translate all matched nodes to Vietnamese (only at most 5-7 nodes, so very fast)
            ground_truth_vietnamese = []
            for mn in matched_nodes:
                ground_truth_vietnamese.append(mn.lower())
                translated = translate_node_id(mn)
                if translated:
                    ground_truth_vietnamese.append(translated.lower())

            # For scored triples, only use instant lookups (COMMON_TRANSLATIONS and _translation_cache)
            # NEVER call the dynamic LLM translator inside a 50+ item loop.
            def safe_translate_lookup(term: str) -> str:
                t_lower = term.lower().strip()
                if t_lower in COMMON_TRANSLATIONS:
                    return COMMON_TRANSLATIONS[t_lower]
                if t_lower in _translation_cache:
                    return _translation_cache[t_lower]
                return None

            for t in scored_triples:
                sub = t["subject"].lower()
                obj = t["object"].lower()
                ground_truth_vietnamese.extend([sub, obj])
                
                # Check instant lookups
                trans_sub = safe_translate_lookup(t["subject"])
                trans_obj = safe_translate_lookup(t["object"])
                if trans_sub:
                    ground_truth_vietnamese.append(trans_sub.lower())
                if trans_obj:
                    ground_truth_vietnamese.append(trans_obj.lower())

            # De-duplicate
            ground_truth_vietnamese = list(set(ground_truth_vietnamese))

            def is_condition_grounded(name: str) -> bool:
                if not name or name in {"Không có dữ liệu", "N/A", ""}:
                    return False
                if resolve_id(name):
                    return True
                
                # Jaccard overlap check at the word level for maximum robustness with Vietnamese phrases
                name_words = set(name.lower().replace(",", " ").replace("(", " ").replace(")", " ").split())
                if not name_words:
                    return False
                
                for gt in ground_truth_vietnamese:
                    gt_words = set(gt.replace(",", " ").replace("(", " ").replace(")", " ").split())
                    if not gt_words:
                        continue
                    intersection = name_words.intersection(gt_words)
                    union = name_words.union(gt_words)
                    jaccard = len(intersection) / len(union)
                    if jaccard >= 0.35:
                        return True
                return False

            dd["condition_a_verified"] = is_condition_grounded(condition_a)
            dd["condition_b_verified"] = is_condition_grounded(condition_b)
            if not dd["condition_a_verified"]:
                hallucinated_elements.append(f"Differential condition_a '{condition_a}' not verifiable in Neo4j (kept, flagged)")
            if not dd["condition_b_verified"]:
                hallucinated_elements.append(f"Differential condition_b '{condition_b}' not verifiable in Neo4j (kept, flagged)")

        if hallucinated_elements:
            print(f"⚠️ Hallucination detected and filtered/corrected in LLM response: {hallucinated_elements}")
            pipeline_logs.append(f"[{ts} WARNING] Trình chặn ảo giác phát hiện và làm sạch các liên kết không có trong đồ thị: {', '.join(hallucinated_elements)}.")

        # Post-process translations and normalize alert
        # 1. Translate empty or English fields in graph_path
        if "graph_path" in result and isinstance(result["graph_path"], list):
            for node in result["graph_path"]:
                if "edge" not in node:
                    node_title = node.get("title", "")
                    orig_id = node.get("original_id", "")
                    if not node_title or node_title.lower() == orig_id.lower():
                        node["title"] = translate_node_id(orig_id)

        # 2. Translate empty or English fields in evidence_triples
        if "evidence_triples" in result and isinstance(result["evidence_triples"], list):
            for t in result["evidence_triples"]:
                sub = t.get("subject", "")
                orig_sub = t.get("original_subject_id", "")
                obj = t.get("object", "")
                orig_obj = t.get("original_object_id", "")
                
                if not sub or sub.lower() == orig_sub.lower():
                    t["subject"] = translate_node_id(orig_sub)
                if not obj or obj.lower() == orig_obj.lower():
                    t["object"] = translate_node_id(orig_obj)

        # 3. Normalize alert title and rule to fix LLM typos/hallucinations (e.g. "NGWṬ MẬCh", "NGẬT MẬCH" or similar placeholders)
        # ── HARD GUARD: Force alert.active = False if no CONTRAINDICATED_WITH triple is in Neo4j scored_triples ──
        # The LLM may hallucinate a contraindication from its training data even when the drug does NOT exist in our graph.
        # We never trust alert.active = true from the LLM alone — we validate against the ground-truth scored_triples.
        real_contraindication_triples = [
            t for t in scored_triples
            if t.get("relation", "").upper() == "CONTRAINDICATED_WITH"
        ]
        if "alert" in result and isinstance(result["alert"], dict):
            if result["alert"].get("active") and not real_contraindication_triples:
                # LLM hallucinated a contraindication that has no backing triple in Neo4j — suppress it
                result["alert"]["active"] = False
                result["alert"]["title"] = "ℹ️ Không phát hiện chống chỉ định trong cơ sở tri thức"
                result["alert"]["rule"] = "Không tìm thấy cạnh CONTRAINDICATED_WITH nào liên quan đến các thực thể được nhận dạng trong đồ thị Neo4j. Hệ thống không thể xác nhận chống chỉ định này."
                pipeline_logs.append(f"[{ts} WARNING] LLM hallucinated alert.active=true but NO CONTRAINDICATED_WITH triple found in scored_triples. Alert suppressed.")
                print(f"⛔ Alert suppressed: LLM claimed contraindication but no matching Neo4j triple found in {len(scored_triples)} scored triples.")

        if "alert" in result and isinstance(result["alert"], dict) and result["alert"].get("active"):
            title = result["alert"].get("title", "")
            rule = result["alert"].get("rule", "")
            
            def clean_spelling(text: str) -> str:
                if not isinstance(text, str):
                    return text
                text = text.replace("NGẬT MẠCH", "NGẮT MẠCH")
                text = text.replace("NGẬT MẬCH", "NGẮT MẠCH")
                text = text.replace("NGẬT MẬCh", "NGẮT MẠCH")
                text = text.replace("NGWṬ MẬCh", "NGẮT MẠCH")
                text = text.replace("ngật mạch", "ngắt mạch")
                text = text.replace("ngật mập", "ngắt mạch")
                text = text.replace("ngắt mập", "ngắt mạch")
                text = text.replace("Chống chỉ dùng", "Chống chỉ định dùng")
                text = re.sub(r'^[←\-\s⚠🛑]+', '🛑 ', text)
                return text

            # ── Anti-Hallucination: Override alert with ground-truth from Neo4j triples ──
            # The LLM may generalize a specific drug (e.g. "pioglitazone") to its drug class
            # (e.g. "Thiazolidinediones"). We always re-derive alert content from verified scored_triples.
            contraindication_triples = [
                t for t in scored_triples
                if t.get("relation", "").upper() == "CONTRAINDICATED_WITH"
            ]
            if contraindication_triples:
                ct = contraindication_triples[0]
                drug_name = ct["object"] if ct.get("object_type", "").lower() in {"drug", "treatment_procedure"} else ct["subject"]
                disease_name = ct["subject"] if ct.get("subject_type", "").lower() in {"disease", "clinical_finding", "symptom"} else ct["object"]

                # If LLM used a different name (e.g. drug class), show both for UX clarity
                llm_drug_mention = title.split(":", 1)[1].strip().lstrip("🛑 ").strip() if ":" in title else ""
                # Clean up LLM phrasing so we only extract the actual drug class name or drug name
                llm_drug_mention_clean = llm_drug_mention.replace("Chống chỉ định dùng", "").replace("chống chỉ định dùng", "").strip()
                llm_drug_mention_clean = re.sub(r'^[🛑⚠️\s\-→\(\)]+', '', llm_drug_mention_clean).strip(" ()")

                if (llm_drug_mention_clean
                        and llm_drug_mention_clean.lower() != drug_name.lower()
                        and len(llm_drug_mention_clean) < 60
                        and not any(c in llm_drug_mention_clean for c in ["{", "}", "[", "]"])):
                    display_name = f"{drug_name} ({llm_drug_mention_clean})"
                else:
                    display_name = drug_name

                result["alert"]["title"] = f"🛑 KÍCH HOẠT NGẮT MẠCH: Chống chỉ định dùng {display_name}"
                result["alert"]["rule"] = f"[{disease_name}] → (CONTRAINDICATED_WITH) → [{drug_name}]"
            else:
                result["alert"]["title"] = clean_spelling(title)
                if rule:
                    rule = rule.replace("->", "→").replace("-->", "→").replace("→→", "→")
                    result["alert"]["rule"] = clean_spelling(rule)

        # 4. Recursively clean common LLM-generated Vietnamese spelling typos in the entire result JSON
        def clean_vietnamese_typos(text: str) -> str:
            if not isinstance(text, str):
                return text
            typos = {
                "Chần đoạn": "Chẩn đoán",
                "chần đoạn": "chẩn đoán",
                "đải thảo đượng": "đái tháo đường",
                "Đải thảo đượng": "Đái tháo đường",
                "đải thảo": "đái tháo",
                "Đải thảo": "Đái tháo",
                "đượng": "đường",
                "ại thảo": "nhiễm toan",
                "nguy cấu": "nguy cơ",
                "Nguy cấu": "Nguy cơ",
                "lỗc": "lọc",
                "thần": "thận",
                "thập thập": "thấp",
                "thập": "thấp",
                "đực": "được",
                "khắp": "khớp",
                "tuyp": "tuýp",
            }
            for typo, correction in typos.items():
                text = text.replace(typo, correction)
            return text

        def recursive_clean_typos(data):
            if isinstance(data, dict):
                return {k: recursive_clean_typos(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [recursive_clean_typos(item) for item in data]
            elif isinstance(data, str):
                return clean_vietnamese_typos(data)
            return data

        result = recursive_clean_typos(result)

        pipeline_logs.append(f"[{ts} SUCCESS] Stage 4 complete. CDSS decision generated from {len(scored_triples)} graph triples.")
        return result


    except Exception as e:
        print(f"❌ Error in Stage 4 CDSS inference: {e}")
        print(f"   Raw LLM response: {repr(raw_response)[:500] if raw_response else 'None'}")
        pipeline_logs.append(f"[{ts} ERROR] Stage 4 failed: {e}. Activating safety fallback.")
        return get_mock_fallback(patient_id, clinical_text, matched_nodes, pipeline_logs, error_message=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# SAFETY FALLBACK — only activated when ALL LLM APIs fail
# ─────────────────────────────────────────────────────────────────────────────

def get_mock_fallback(
    patient_id: str,
    clinical_text: str,
    matched_nodes: list[str] = None,
    pipeline_logs: list[str] = None,
    error_message: str = None,
) -> dict:
    """
    Last-resort safety fallback when both Neo4j and ALL LLM APIs are offline.
    Returns a generic error structure instead of misleading clinical content.
    """
    rule_msg = "Vui lòng kiểm tra kết nối API (Groq / OpenRouter) và thử lại."
    if error_message:
        rule_msg = f"Chi tiết lỗi hệ thống: {error_message}"
    return {
        "matched_entities": matched_nodes or [],
        "alert": {
            "active": False,
            "title": "⚠️ HỆ THỐNG LLM NGOẠI TUYẾN — Không thể phân tích",
            "rule": rule_msg,
        },
        "differential_diagnosis": {
            "condition_a": "Không xác định",
            "condition_b": "Không xác định",
            "features": [
                {
                    "characteristic": "Trạng thái hệ thống",
                    "val_a": "LLM API ngoại tuyến",
                    "val_b": "Cần khôi phục kết nối",
                    "relation_a": "",
                    "relation_b": "",
                }
            ],
        },
        "graph_path": [
            {"title": "Tình huống lâm sàng", "node_type": "Concept", "hop": 0},
            {"edge": "SYSTEM_ERROR"},
            {"title": "LLM API Offline", "node_type": "Concept", "hop": 1},
        ],
        "recommendations": [
            {
                "type": "recommend",
                "title": "Khởi động lại kết nối API",
                "desc": "Kiểm tra file .env và đảm bảo ít nhất một OPENROUTER_API_KEY_* còn hoạt động.",
                "relation": "SYSTEM_ACTION",
            }
        ],
        "logs": pipeline_logs or ["[ERROR] Không thể kết nối LLM API."],
    }


def consult_diabetes_graph(query_text: str) -> dict:
    """
    Diabetes QA Chatbot service using AMG-RAG Text-to-Cypher:
    Stage 1: Translate natural language query to Cypher using Llama-3.3-70B.
    Stage 2: Validate the Cypher query (guardrails for relations, labels, and safety).
    Stage 3: Execute on Neo4j. If fails, trigger fallback.
    Stage 4: Synthesize Vietnamese medical response using LLM.
    """
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    pipeline_logs = [
        f"[{ts} INFO] Nhận câu hỏi tư vấn: '{query_text}'",
    ]

    # Target metadata for validation
    VALID_RELATIONS = {
        "IS_A", "HAS_ANATOMIC_SITE", "CAUSE_OF", "HAS_FINDING", "HAS_BIOMARKER",
        "CO_OCCURS_WITH", "TREATED_BY", "HAS_ADVERSE_EFFECT", "CONTRAINDICATED_WITH",
        "PREFERRED_OVER", "HAS_EVALUATION", "HAS_TITRATION_RULE", "INCREASES_RISK_OF",
        "ADMINISTERED_VIA", "DISPENSES"
    }
    
    CYPHER_GENERATION_SYSTEM_PROMPT = """You are a Cypher query generator for a Neo4j Knowledge Graph about diabetes.
The graph has nodes representing clinical concepts and relationships between them.

Target Node Labels (Note: Node labels in the database do NOT contain spaces):
- Disease (e.g. "Diabetes Mellitus", "Diabetes Mellitus, Non-Insulin-Dependent", "Diabetic Retinopathy", "Diabetic Nephropathy", "Obesity", "Renal Impairment", "Heart failure")
- Symptom (e.g. "Polyuria", "Polydipsia", "Paresthesia", "Weight Loss", "fractures")
- Drug (e.g. "metformin", "liraglutide", "pioglitazone", "Thiazolidinediones", "insulin", "tirzepatide")
- Nutrient (e.g. "Carbohydrates", "Dietary Fiber", "Vitamin B12")
- Biomarker (e.g. "C-peptide", "GAD65 autoantibodies")
- Treatment_Procedure (e.g. "dietary management", "Subcutaneous injection of insulin")
- Dosage_Value (e.g. "500 mg")
- Clinical_Metric (e.g. "HbA1c", "eGFR")
- Clinical_Rule
- Risk_Factor (e.g. "Obesity", "Sedentary Lifestyle")
- Anatomical_Site (e.g. "Pancreatic Islet Cells")

Target Relationship Types (MUST BE UPPERCASE, e.g. [:TREATED_BY]):
- IS_A
- HAS_ANATOMIC_SITE
- CAUSE_OF
- HAS_FINDING
- HAS_BIOMARKER
- CO_OCCURS_WITH
- TREATED_BY
- HAS_ADVERSE_EFFECT
- CONTRAINDICATED_WITH
- PREFERRED_OVER
- HAS_EVALUATION
- HAS_TITRATION_RULE
- INCREASES_RISK_OF
- ADMINISTERED_VIA
- DISPENSES

Target Node Properties:
- id: Canonical English name of the node (e.g. n.id = "Diabetes Mellitus")
- aliases: Alternative names/synonyms list (e.g. n.aliases = ["DPP-4 inhibitors"])
- umls_cui: UMLS Concept Unique Identifier (CUI) code (e.g. n.umls_cui = "C0011849"). You MUST use this property if the user asks for CUI or "mã CUI" of a concept.
- description: Brief description of the concept (e.g. n.description)
- umls_semantic_type: Semantic type (e.g. n.umls_semantic_type)

CRITICAL OUTPUT INSTRUCTIONS:
1. Return ONLY the raw Cypher query, with no explanations, no prefix, and no suffix. Start the query directly with MATCH or other valid Cypher keywords. Do NOT include markdown code block formatting (do NOT wrap it in ```cypher).
2. If the user asks for CUI or "mã CUI", query and return the `umls_cui` property (e.g. `RETURN n.id, n.umls_cui`).
3. You MUST write the node ID property exactly as listed in the "Matched entities in the Knowledge Graph for this question" context if present. Do NOT change its casing (e.g. if the context says - Node ID: "pioglitazone", you must write `id: "pioglitazone"` (lowercase), not `"Pioglitazone"`).

Few-Shot Examples:
Question: "Thuốc nào chống chỉ định với bệnh suy tim?"
Cypher: MATCH (d:Drug)-[:CONTRAINDICATED_WITH]->(dis:Disease {id: "Heart failure"}) RETURN d.id AS Drug

Question: "Bệnh béo phì có quan hệ đồng mắc với những bệnh nào?"
Cypher: MATCH (d1:Disease {id: "Obesity"})-[:CO_OCCURS_WITH]-(d2:Disease) RETURN d2.id AS CoOccurringDisease

Question: "Biến chứng của tiểu đường tuýp 2 là gì?"
Cypher: MATCH (d:Disease {id: "Diabetes Mellitus, Non-Insulin-Dependent"})-[:CO_OCCURS_WITH]-(c:Disease) RETURN c.id AS Complication

Question: "Thuốc pioglitazone có tác dụng phụ gì?"
Cypher: MATCH (d:Drug {id: "pioglitazone"})-[:HAS_ADVERSE_EFFECT]->(s:Symptom) RETURN s.id AS AdverseEffect

Question: "tìm mã CUI của bệnh tiểu đường"
Cypher: MATCH (d:Disease) WHERE d.id IN ["Diabetes Mellitus", "Diabetes Mellitus, Non-Insulin-Dependent", "Diabetes Mellitus, Insulin-Dependent"] RETURN d.id AS Disease, d.umls_cui AS CUI
"""

    # Stage 0: Entity Matching to provide exact ID hints to the LLM
    pipeline_logs.append(f"[{ts} INFO] Giai đoạn 0: Nhận diện thực thể làm chỉ dẫn cho bộ dịch Cypher...")
    matched_nodes = []
    try:
        kg_nodes = get_all_cdss_nodes()
        matched_nodes, extracted_terms = chunk_match_entities(query_text, kg_nodes, chunk_size=100)
        pipeline_logs.append(f"[{ts} INFO] Các thực thể khớp được: {matched_nodes}")
    except Exception as e:
        pipeline_logs.append(f"[{ts} WARNING] Không thể đối sánh thực thể ban đầu: {str(e)}")

    matched_entities_info = ""
    if matched_nodes:
        matched_entities_info = "Matched entities in the Knowledge Graph for this question (MUST use these exact node IDs in the query):\n"
        for node_id in matched_nodes:
            matched_entities_info += f"- Node ID: \"{node_id}\"\n"

    prompt = f"Question: \"{query_text}\"\n"
    if matched_entities_info:
        prompt += f"{matched_entities_info}\n"
    prompt += "Cypher:"
    cypher_query = ""
    is_fallback = False
    graph_results = []
    
    pipeline_logs.append(f"[{ts} INFO] Giai đoạn 1: Biên dịch câu hỏi sang câu lệnh Cypher...")
    try:
        raw_cypher = call_llm_api(prompt, system_prompt=CYPHER_GENERATION_SYSTEM_PROMPT, model_size="70b")
        cypher_query = raw_cypher.strip().replace("```cypher", "").replace("```", "").strip()
        pipeline_logs.append(f"[{ts} INFO] Câu lệnh Cypher được sinh ra: {cypher_query}")
        
        # Stage 2: Guardrails & Validation
        pipeline_logs.append(f"[{ts} INFO] Giai đoạn 2: Kiểm duyệt bảo mật câu lệnh Cypher...")
        
        # Block write/destructive keywords (matching whole words only using regex word boundaries)
        blocked_keywords = ["CREATE", "MERGE", "DELETE", "REMOVE", "SET", "DROP", "APOC", "CALL", "LOAD", "CSV", "WRITE"]
        has_blocked = False
        query_upper = cypher_query.upper()
        for kw in blocked_keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', query_upper):
                has_blocked = True
                break
        
        # Extract relations and validate
        extracted_rels = re.findall(r'\[:([A-Z_]+)\]', cypher_query)
        invalid_rels = [rel for rel in extracted_rels if rel not in VALID_RELATIONS]
        
        if has_blocked:
            pipeline_logs.append(f"[{ts} WARNING] Phát hiện từ khóa bị cấm trong câu lệnh Cypher. Kích hoạt chế độ dự phòng (fallback).")
            is_fallback = True
        elif invalid_rels:
            pipeline_logs.append(f"[{ts} WARNING] Phát hiện quan hệ không hợp lệ: {invalid_rels}. Kích hoạt chế độ dự phòng (fallback).")
            is_fallback = True
        else:
            pipeline_logs.append(f"[{ts} INFO] Giai đoạn 2 thành công: Câu lệnh hợp lệ. Thực thi trên Neo4j...")
            
            # Stage 3: Neo4j Execution
            from app.services.graph_query import execute_raw_cypher
            graph_results = execute_raw_cypher(cypher_query)
            pipeline_logs.append(f"[{ts} INFO] Giai đoạn 3 thành công: Đã lấy được {len(graph_results)} kết quả từ Neo4j.")
            
            if not graph_results:
                pipeline_logs.append(f"[{ts} INFO] Câu lệnh Cypher chạy thành công nhưng không trả về kết quả. Kích hoạt chế độ dự phòng.")
                is_fallback = True
                
    except Exception as e:
        pipeline_logs.append(f"[{ts} ERROR] Lỗi khi xử lý hoặc thực thi Cypher: {str(e)}. Kích hoạt chế độ dự phòng.")
        is_fallback = True

    # Fallback Mechanism: standard GraphRAG using semantic vector search
    fallback_context_str = ""
    if is_fallback:
        pipeline_logs.append(f"[{ts} INFO] Chế độ dự phòng: Sử dụng đối sánh thực thể...")
        if not matched_nodes:
            try:
                kg_nodes = get_all_cdss_nodes()
                matched_nodes, extracted_terms = chunk_match_entities(query_text, kg_nodes, chunk_size=100)
            except Exception as e:
                pipeline_logs.append(f"[{ts} WARNING] Lỗi đối sánh thực thể dự phòng: {str(e)}")
        
        pipeline_logs.append(f"[{ts} INFO] Các thực thể đối sánh được: {matched_nodes}")
        
        if matched_nodes:
            all_triples = bfs_multi_hop_traversal(matched_nodes)
            scored_triples = score_and_prune_triples(all_triples, max_triples=20)
            fallback_context_str = build_rich_graph_context(scored_triples, matched_nodes)
            
            # Pack scored triples as graph results for the frontend view
            graph_results = [
                {
                    "subject": t["subject"],
                    "relation": t["relation"],
                    "object": t["object"],
                    "subject_type": t.get("subject_type", "Concept"),
                    "object_type": t.get("object_type", "Concept")
                }
                for t in scored_triples
            ]
            pipeline_logs.append(f"[{ts} INFO] Trích xuất được {len(scored_triples)} bộ ba làm ngữ cảnh dự phòng.")

    # Extract triples for direct Cypher queries to show as UI evidence
    graph_context_triples = []
    if is_fallback:
        graph_context_triples = graph_results
    else:
        try:
            # Collect all node ID strings from the raw cypher results
            target_ids = set()
            for row in graph_results:
                if isinstance(row, dict):
                    for val in row.values():
                        if isinstance(val, str):
                            target_ids.add(val)
                        elif isinstance(val, list):
                            for item in val:
                                if isinstance(item, str):
                                    target_ids.add(item)
                        elif hasattr(val, "get"):
                            node_id = val.get("id")
                            if isinstance(node_id, str):
                                target_ids.add(node_id)
            
            # Extract seeds from matched_nodes AND parsed from Cypher query to be robust
            extracted_seeds = set(matched_nodes)
            if cypher_query:
                # regex matches like id: "..." or id: '...'
                for m in re.finditer(r'id\s*:\s*["\']([^"\']+)["\']', cypher_query, re.IGNORECASE):
                    extracted_seeds.add(m.group(1))
                # regex matches like n.id = "..." or n.id = '...'
                for m in re.finditer(r'\.id\s*=\s*["\']([^"\']+)["\']', cypher_query, re.IGNORECASE):
                    extracted_seeds.add(m.group(1))
            
            if extracted_seeds and target_ids:
                from app.database import get_db_driver
                driver = get_db_driver()
                if driver:
                    with driver.session() as session:
                        # Bidirectional meet-in-the-middle path query of length 1 to 2
                        rel_query = """
                        MATCH p = (a)-[*1..2]-(b)
                        WHERE a.id IN $seeds AND b.id IN $targets
                        UNWIND relationships(p) AS rel
                        WITH startNode(rel) AS s, rel, endNode(rel) AS o
                        WHERE s.id IS NOT NULL AND o.id IS NOT NULL
                        RETURN s.id AS subject, type(rel) AS relation, o.id AS object,
                               labels(s)[0] AS subject_type, labels(o)[0] AS object_type
                        """
                        res = session.run(rel_query, seeds=list(extracted_seeds), targets=list(target_ids))
                        seen = set()
                        for r in res:
                            key = (r["subject"], r["relation"], r["object"])
                            if key not in seen:
                                seen.add(key)
                                graph_context_triples.append({
                                    "subject": r["subject"],
                                    "relation": r["relation"],
                                    "object": r["object"],
                                    "subject_type": r["subject_type"],
                                    "object_type": r["object_type"]
                                })
            
            # If no triples found via path search, try direct 1-hop as fallback
            if not graph_context_triples and extracted_seeds and target_ids:
                from app.database import get_db_driver
                driver = get_db_driver()
                if driver:
                    with driver.session() as session:
                        rel_query = """
                        MATCH (a)-[r]-(b)
                        WHERE a.id IN $seeds AND b.id IN $targets
                        RETURN a.id AS subject, type(r) AS relation, b.id AS object,
                               labels(a)[0] AS subject_type, labels(b)[0] AS object_type
                        """
                        res = session.run(rel_query, seeds=list(extracted_seeds), targets=list(target_ids))
                        seen = set()
                        for r in res:
                            key = (r["subject"], r["relation"], r["object"])
                            if key not in seen:
                                seen.add(key)
                                graph_context_triples.append({
                                    "subject": r["subject"],
                                    "relation": r["relation"],
                                    "object": r["object"],
                                    "subject_type": r["subject_type"],
                                    "object_type": r["object_type"]
                                })
                                
            # If still empty, construct simple pseudo-triples to prevent empty UI blocks
            if not graph_context_triples and extracted_seeds:
                # Pair seed nodes with target IDs
                for seed in extracted_seeds:
                    for target in target_ids:
                        if seed != target:
                            graph_context_triples.append({
                                "subject": seed,
                                "relation": "RETRIEVED_RELATION",
                                "object": target,
                                "subject_type": "Concept",
                                "object_type": "Concept"
                            })
                            
            pipeline_logs.append(f"[{ts} INFO] Trích xuất thành công {len(graph_context_triples)} bộ ba minh chứng cho UI.")
        except Exception as e:
            pipeline_logs.append(f"[{ts} WARNING] Lỗi trích xuất bộ ba minh chứng UI: {str(e)}")

    # Stage 4: Synthesize Vietnamese medical response
    pipeline_logs.append(f"[{ts} INFO] Giai đoạn 4: Tổng hợp câu trả lời y khoa tiếng Việt...")
    
    SYNTHESIS_SYSTEM_PROMPT = """You are a Clinical Decision Support System (CDSS) assistant specialized in diabetes.
Your task is to answer the user's clinical or general question about diabetes.

You must base your answer on the provided Neo4j Graph Database query results.
If the query results are empty or not present, you should use the fallback graph context or general medical knowledge, but inform the user about the facts retrieved from the graph.

You must translate all English concept names (e.g. "Type 2 Diabetes Mellitus" -> "Đái tháo đường tuýp 2") to standard Vietnamese medical terms.
Always output a clear, structured, and clinically sound response in Vietnamese.
"""

    synthesis_prompt = f"""User Question: "{query_text}"

"""
    if not is_fallback:
        synthesis_prompt += f"""Neo4j Cypher Query Results: {json.dumps(graph_results, ensure_ascii=False)}

Generate a response explaining these facts to the user clearly. Translate all clinical terms to Vietnamese."""
    else:
        synthesis_prompt += f"""Neo4j Fallback Graph Context:
{fallback_context_str if fallback_context_str else "No matching facts found in database."}

Generate a response to the user's question, grounding it in the fallback graph context above if possible. If no facts are matched, explain what is missing but give a helpful answer based on general medical knowledge while advising them."""

    try:
        answer = call_llm_api(synthesis_prompt, system_prompt=SYNTHESIS_SYSTEM_PROMPT, model_size="70b")
        pipeline_logs.append(f"[{ts} INFO] Tổng hợp câu trả lời hoàn tất.")
    except Exception as e:
        pipeline_logs.append(f"[{ts} ERROR] Lỗi khi gọi LLM để tổng hợp câu trả lời: {str(e)}")
        answer = "Xin lỗi, hệ thống gặp lỗi khi kết nối với LLM để tổng hợp câu trả lời. Vui lòng thử lại sau."

    return {
        "answer": answer,
        "cypher_query": "N/A" if is_fallback else cypher_query,
        "graph_context": graph_context_triples,
        "is_fallback": is_fallback,
        "logs": pipeline_logs
    }


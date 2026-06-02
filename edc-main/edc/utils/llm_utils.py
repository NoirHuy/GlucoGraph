import os
import openai
import time
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
import ast
from sentence_transformers import SentenceTransformer
from typing import List
import gc
import torch
import logging
import threading

logger = logging.getLogger(__name__)


class APIKeyPool:
    """Thread-safe and Coroutine-safe API Key rotation pool for OpenRouter."""
    def __init__(self, env_prefix: str = "OPENROUTER_API_KEY"):
        # Dynamically load .env files up to two levels of parent directories
        try:
            from dotenv import load_dotenv
            load_dotenv()                              # Current directory
            load_dotenv(dotenv_path="../.env")         # One level up (e.g. edc-main/)
            load_dotenv(dotenv_path="../../.env")      # Two levels up (root folder MyProject/)
        except ImportError:
            pass

        self.keys = []
        # 1. Primary key
        primary = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        if primary:
            self.keys.append(primary)
        
        # 2. Check indexed keys (1 to 20)
        for i in range(1, 21):
            k = os.environ.get(f"{env_prefix}_{i}") or os.environ.get(f"OPENROUTER_KEY_{i}")
            if k and k not in self.keys:
                self.keys.append(k)
        
        self.current_index = 0
        self.lock = threading.Lock()
        logger.info(f"[APIKeyPool] Initialized with {len(self.keys)} OpenRouter API keys.")

    def get_active_key(self) -> str:
        with self.lock:
            if not self.keys:
                # If no keys loaded, fallback to empty string so API call raises standard auth error
                return ""
            return self.keys[self.current_index]

    def report_failure(self, failed_key: str):
        with self.lock:
            if failed_key in self.keys:
                # Proactively mark key as expired in .env files to disable/comment it out!
                self._mark_key_expired_in_env(failed_key)
                
                idx = self.keys.index(failed_key)
                if idx == self.current_index:
                    next_idx = (self.current_index + 1) % len(self.keys)
                    logger.warning(
                        f"[APIKeyPool] Key index {self.current_index} failed/exhausted. "
                        f"Automatically rotating to key index {next_idx}."
                    )
                    self.current_index = next_idx

    def _mark_key_expired_in_env(self, failed_key: str):
        """Comments out the failed key in any loaded .env files to mark it as EXPIRED."""
        if not failed_key:
            return
            
        env_paths = [
            ".env",
            "../.env",
            "../../.env",
            "edc-main/medical_preprocessing_pipeline/.env"
        ]
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for path in env_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    modified = False
                    new_lines = []
                    for line in lines:
                        # If the key exists on this line and is NOT already commented out as EXPIRED
                        if failed_key in line and not line.strip().startswith("# [EXPIRED]"):
                            stripped_line = line.rstrip("\r\n")
                            # Disable the key by commenting it out and appending a timestamp
                            new_line = f"# [EXPIRED at {timestamp}] {stripped_line}\n"
                            new_lines.append(new_line)
                            modified = True
                        else:
                            new_lines.append(line)
                            
                    if modified:
                        with open(path, "w", encoding="utf-8") as f:
                            f.writelines(new_lines)
                        logger.info(f"[APIKeyPool] Successfully marked and commented out expired key in: {path}")
                except Exception as env_err:
                    logger.warning(f"[APIKeyPool] Failed to write expired label to {path}: {env_err}")


# Global instance of key pool
global_key_pool = APIKeyPool()



def free_model(model: AutoModelForCausalLM = None, tokenizer: AutoTokenizer = None):
    try:
        if model is not None and hasattr(model, "cpu"):
            model.cpu()
        if model is not None:
            del model
        if tokenizer is not None:
            del tokenizer
        gc.collect()
        torch.cuda.empty_cache()
    except Exception as e:
        logger.warning(e)


def get_embedding_e5mistral(model, tokenizer, sentence, task=None):
    model.eval()
    device = model.device

    if task != None:
        # It's a query to be embed
        sentence = get_detailed_instruct(task, sentence)

    sentence = [sentence]

    max_length = 4096
    # Tokenize the input texts
    batch_dict = tokenizer(
        sentence, max_length=max_length - 1, return_attention_mask=False, padding=False, truncation=True
    )
    # append eos_token_id to every input_ids
    batch_dict["input_ids"] = [input_ids + [tokenizer.eos_token_id] for input_ids in batch_dict["input_ids"]]
    batch_dict = tokenizer.pad(batch_dict, padding=True, return_attention_mask=True, return_tensors="pt")

    batch_dict.to(device)

    embeddings = model(**batch_dict).detach().cpu()

    assert len(embeddings) == 1

    return embeddings[0]


def get_detailed_instruct(task_description: str, query: str) -> str:
    return f"Instruct: {task_description}\nQuery: {query}"


def get_embedding_sts(model: SentenceTransformer, text: str, prompt_name=None, prompt=None):
    embedding = model.encode(text, prompt_name=prompt_name, prompt=prompt)
    return embedding


def parse_raw_entities(raw_entities: str):
    parsed_entities = []
    if not raw_entities:
        return parsed_entities
    try:
        left_bracket_idx = raw_entities.index("[")
        right_bracket_idx = raw_entities.index("]")
        parsed_entities = ast.literal_eval(raw_entities[left_bracket_idx : right_bracket_idx + 1])
    except ValueError:
        pass
    except Exception as e:
        pass
    logging.debug(f"Entities {raw_entities} parsed as {parsed_entities}")
    return parsed_entities


def parse_raw_triplets(raw_triplets: str):
    if not raw_triplets:
        return []
        
    # Look for enclosing brackets
    unmatched_left_bracket_indices = []
    matched_bracket_pairs = []

    collected_triples = []
    for c_idx, c in enumerate(raw_triplets):
        if c == "[":
            unmatched_left_bracket_indices.append(c_idx)
        if c == "]":
            if len(unmatched_left_bracket_indices) == 0:
                continue
            # Found a right bracket, match to the last found left bracket
            matched_left_bracket_idx = unmatched_left_bracket_indices.pop()
            matched_bracket_pairs.append((matched_left_bracket_idx, c_idx))
    for l, r in matched_bracket_pairs:
        bracketed_str = raw_triplets[l : r + 1]
        try:
            import ast
            parsed_triple = ast.literal_eval(bracketed_str)
            if not isinstance(parsed_triple, (list, tuple)):
                continue
            if len(parsed_triple) == 3:
                # Convert any nested lists to comma-separated strings
                for e_idx, e in enumerate(parsed_triple):
                    if isinstance(e, list):
                        parsed_triple[e_idx] = ", ".join([str(item) for item in e])
                
                # Ensure all elements are indeed clean strings and not Ellipsis (...) or other objects
                if all(isinstance(t, str) for t in parsed_triple):
                    cleaned_triple = [t.strip() for t in parsed_triple]
                    if all(e != "" and e != "_" and e != "..." for e in cleaned_triple):
                        collected_triples.append(cleaned_triple)
        except Exception as e:
            pass
    logger.debug(f"Triplets {raw_triplets} parsed as {collected_triples}")
    return collected_triples


def parse_relation_definition(raw_definitions: str):
    if not raw_definitions:
        return {}
    descriptions = raw_definitions.split("\n")
    relation_definition_dict = {}

    for description in descriptions:
        if ":" not in description:
            continue
        index_of_colon = description.index(":")
        relation = description[:index_of_colon].strip()
        
        # Strip common markdown formatting (like **relation**) or quotes
        relation = relation.strip("*_`\"' ")

        relation_description = description[index_of_colon + 1 :].strip()

        if relation == "Answer":
            continue

        relation_definition_dict[relation] = relation_description
    logger.debug(f"Relation Definitions {raw_definitions} parsed as {relation_definition_dict}")
    return relation_definition_dict


def is_model_openai(model_name):
    """Returns True if the model should be called via an OpenAI-compatible API."""
    model_lower = model_name.lower()
    prefixes = ["xiaomi/", "openrouter/", "google/", "gemini/", "openai/", "groq/"]
    if any(model_lower.startswith(p) for p in prefixes):
        return True
    if "gpt" in model_lower or "/" in model_lower:
        return True
    if "gemini" in model_lower or "mimo" in model_lower or "xiaomi" in model_lower:
        return True
    if os.environ.get("GROQ_KEY", ""):
        return True
    return False



def generate_completion_transformers(
    input: list,
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    max_new_token=256,
    answer_prepend="",
):
    device = model.device
    tokenizer.pad_token = tokenizer.eos_token

    messages = tokenizer.apply_chat_template(input, add_generation_prompt=True, tokenize=False) + answer_prepend

    model_inputs = tokenizer(messages, return_tensors="pt", padding=True, add_special_tokens=False).to(device)

    generation_config = GenerationConfig(
        do_sample=False,
        max_new_tokens=max_new_token,
        pad_token_id=tokenizer.eos_token_id,
        return_dict_in_generate=True,
    )

    generation = model.generate(**model_inputs, generation_config=generation_config)
    sequences = generation["sequences"]
    generated_ids = sequences[:, model_inputs["input_ids"].shape[1] :]
    generated_texts = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

    logging.debug(f"Prompt:\n {messages}\n Result: {generated_texts}")
    return generated_texts


def is_model_openrouter(model_name):
    """Returns True if the model should be called via OpenRouter (has '/' prefix, e.g. 'openai/gpt-oss-120b')."""
    return "/" in model_name


def openai_chat_completion(model, system_prompt, history, temperature=0, max_tokens=512):
    """Call OpenAI Chat Completion API directly (for models like gpt-3.5-turbo, gpt-4o-mini)."""
    openai.api_key = os.environ["OPENAI_KEY"]
    response = None
    if system_prompt is not None:
        messages = [{"role": "system", "content": system_prompt}] + history
    else:
        messages = history
    while response is None:
        try:
            response = openai.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
            )
        except Exception as e:
            time.sleep(5)
    logging.debug(f"Model: {model}\nPrompt:\n {messages}\n Result: {response.choices[0].message.content}")
    return response.choices[0].message.content


def openrouter_chat_completion(model, system_prompt, history, temperature=0, max_tokens=512):
    """Call OpenRouter OR Groq API using OpenAI-compatible interface.
    - OpenRouter: set OPENROUTER_KEY env var. Supports models like 'openai/gpt-oss-120b', etc.
    - Groq: set GROQ_KEY env var. Supports models like 'llama-3.3-70b-versatile', etc.
    Detection is automatic: if GROQ_KEY is set, Groq is used.
    """
    groq_key = os.environ.get("GROQ_KEY", "")
    
    response = None
    if system_prompt is not None:
        messages = [{"role": "system", "content": system_prompt}] + history
    else:
        messages = history
        
    while response is None:
        # If the model has a '/' (like meta-llama/...), it MUST go to OpenRouter.
        # Otherwise, if GROQ_KEY is present, send to Groq.
        if "/" in model or not groq_key:
            # Use OpenRouter API with key rotation
            openrouter_key = global_key_pool.get_active_key()
            client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
            )
        else:
            # Use Groq API
            client = openai.OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
            )
            
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
            )
        except Exception as e:
            err_msg = str(e).lower()
            if "/" in model or not groq_key:
                # Detect billing, balance, quota, authentication, or rate limit issues
                is_quota_or_rate = any(x in err_msg for x in ["rate limit", "429", "quota", "balance", "insufficient", "unauthorized", "401", "invalid api key", "credit"])
                if is_quota_or_rate:
                    logger.warning(f"OpenRouter API Key failed due to: {e}. Rotating to next key...")
                    global_key_pool.report_failure(openrouter_key)
                    # Retry immediately with the next key, skipping the sleep
                    continue
                    
            logger.warning(f"API error: {e}. Retrying in 5s...")
            time.sleep(5)
            
    logging.debug(f"Model: {model}\nPrompt:\n {messages}\n Result: {response.choices[0].message.content}")
    return response.choices[0].message.content


def google_chat_completion(model, system_prompt, history, temperature=0, max_tokens=512):
    """Call Google AI Studio API via the new OpenAI-compatible format."""
    client = openai.OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )
    response = None
    if system_prompt is not None:
        messages = [{"role": "system", "content": system_prompt}] + history
    else:
        messages = history
    while response is None:
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
            )
        except Exception as e:
            logger.warning(f"Google API error: {e}. Retrying in 5s...")
            time.sleep(5)
    logging.debug(f"Model: {model}\nPrompt:\n {messages}\n Result: {response.choices[0].message.content}")
    return response.choices[0].message.content


def _extract_final_answer_from_reasoning(text: str) -> str:
    """Extract the final structured answer from a reasoning model's chain-of-thought output.
    
    MiMo writes its full thought process into content. We want only the final answer
    section (the actual triplets), not the intermediate reasoning paragraphs.
    Strategy: look for common 'conclusion' markers and take everything after the last one.
    If no marker is found, return the full text so the standard parser can still try.
    """
    if not text:
        return text
    
    # Markers that indicate the model is transitioning from reasoning to final answer
    answer_markers = [
        "Triplets:",
        "Final answer:",
        "Final Answer:",
        "FINAL ANSWER:",
        "Final triplets:",
        "Final Triplets:",
        "Output:",
        "Answer:",
        "ANSWER:",
        "So, the triples are:",
        "So, the triplets are:",
        "The triples are:",
        "The triplets are:",
        "Therefore, the triples",
        "In conclusion,",
        "To summarize,",
    ]
    
    best_pos = -1
    for marker in answer_markers:
        pos = text.rfind(marker)  # rfind = last occurrence
        if pos != -1 and pos > best_pos:
            best_pos = pos
    
    if best_pos != -1:
        return text[best_pos:]
    
    # No marker found — return the last ~600 chars where the final answer usually lives
    # This prevents feeding thousands of reasoning tokens into the bracket-scanner
    return text[-600:] if len(text) > 600 else text


def xiaomi_chat_completion(model, system_prompt, history, temperature=0, max_tokens=512):
    """Call Xiaomi MiMo API via OpenAI-compatible interface."""
    # Normalize model name for Xiaomi platform which typically expects lowercase e.g., mimo-v2.5-pro
    model_lower = model.lower()
    if "mimo" in model_lower:
        if "2.5-pro" in model_lower or "2.5_pro" in model_lower:
            model = "mimo-v2.5-pro"
        elif "2.5" in model_lower:
            model = "mimo-v2.5"
        else:
            model = "mimo-v2.5-pro"

    api_key = os.environ.get("XIAOMI_API_KEY", "")
    if not api_key:
        raise ValueError("XIAOMI_API_KEY environment variable is not set! Please set it before running.")

    client = openai.OpenAI(
        base_url="https://token-plan-sgp.xiaomimimo.com/v1",
        api_key=api_key,
    )
    response = None
    if system_prompt is not None:
        messages = [{"role": "system", "content": system_prompt}] + history
    else:
        messages = history
    
    # MiMo is a reasoning model — it writes its full chain-of-thought into content.
    # 512 tokens is far too small; the model cuts off mid-reasoning and never writes
    # the final answer. Use 4096 to give it enough room to finish.
    effective_max_tokens = max(max_tokens, 4096)
    
    while response is None:
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=effective_max_tokens
            )
        except Exception as e:
            logger.warning(f"Xiaomi MiMo API error: {e}. Retrying in 5s...")
            time.sleep(5)
            
    message_obj = response.choices[0].message
    content = message_obj.content or ""
    
    # Fallback: some API versions return output in reasoning_content instead of content
    if not content:
        reasoning_content = getattr(message_obj, "reasoning_content", None)
        if not reasoning_content and hasattr(message_obj, "model_extra"):
            reasoning_content = message_obj.model_extra.get("reasoning_content", None)
        if reasoning_content:
            logger.info("[Xiaomi Router] Using 'reasoning_content' fallback because 'content' is empty.")
            content = reasoning_content
    
    # For reasoning models: strip the chain-of-thought and return only the final answer.
    # We must SKIP this truncation if it is a debate gate call, because the agents need the full,
    # untruncated clinical/ontological reasoning to debate effectively in Rounds 2 and 3!
    is_debate = False
    for msg in messages:
        msg_content = str(msg.get("content", ""))
        if any(keyword in msg_content for keyword in ["Trạng thái:", "Clinical_Specialist", "Ontology_Inspector", "Medical_Skeptic"]):
            is_debate = True
            break
            
    if not is_debate:
        content = _extract_final_answer_from_reasoning(content)
        
    logging.debug(f"Model: {model}\nPrompt:\n {messages}\n Result: {content}")
    return content


def api_chat_completion(model, system_prompt, history, temperature=0, max_tokens=512):
    """Unified entry point: dynamically routes based on model prefix and environment variables."""
    model_lower = model.lower()
    
    # 1. Xiaomi Prefix Routing
    if model_lower.startswith("xiaomi/"):
        actual_model = model[7:]
        return xiaomi_chat_completion(actual_model, system_prompt, history, temperature, max_tokens)
        
    # 2. Google Gemini Prefix Routing
    if model_lower.startswith("google/") or model_lower.startswith("gemini/"):
        if "gemini" not in model_lower or not os.environ.get("GEMINI_API_KEY"):
            return openrouter_chat_completion(model, system_prompt, history, temperature, max_tokens)
        actual_model = model
        if model_lower.startswith("google/"):
            actual_model = model[7:]
        elif model_lower.startswith("gemini/"):
            actual_model = model[7:]
        return google_chat_completion(actual_model, system_prompt, history, temperature, max_tokens)
        
    # 3. OpenRouter Prefix Routing
    if model_lower.startswith("openrouter/"):
        actual_model = model[11:]
        return openrouter_chat_completion(actual_model, system_prompt, history, temperature, max_tokens)
        
    # 4. OpenAI Prefix Routing
    if model_lower.startswith("openai/"):
        if not os.environ.get("OPENAI_KEY") and (os.environ.get("OPENROUTER_KEY") or os.environ.get("OPENROUTER_API_KEY")):
            return openrouter_chat_completion(model, system_prompt, history, temperature, max_tokens)
        actual_model = model[7:]
        return openai_chat_completion(actual_model, system_prompt, history, temperature, max_tokens)
        
    # 5. Groq Prefix Routing
    if model_lower.startswith("groq/"):
        actual_model = model[5:]
        return openrouter_chat_completion(actual_model, system_prompt, history, temperature, max_tokens)

    # --- Environment-based Key Fallbacks ---
    if os.environ.get("XIAOMI_API_KEY", "") and ("mimo" in model_lower or "xiaomi" in model_lower):
        return xiaomi_chat_completion(model, system_prompt, history, temperature, max_tokens)
        
    elif os.environ.get("GEMINI_API_KEY", "") and "gemini" in model_lower:
        return google_chat_completion(model, system_prompt, history, temperature, max_tokens)
        
    elif "/" in model or os.environ.get("GROQ_KEY", ""):
        # Fallback to Xiaomi if OpenRouter/Groq keys are missing but Xiaomi key is present!
        if not os.environ.get("OPENROUTER_KEY", "") and not os.environ.get("GROQ_KEY", "") and os.environ.get("XIAOMI_API_KEY", ""):
            return xiaomi_chat_completion(model, system_prompt, history, temperature, max_tokens)
        return openrouter_chat_completion(model, system_prompt, history, temperature, max_tokens)
        
    else:
        return openai_chat_completion(model, system_prompt, history, temperature, max_tokens)

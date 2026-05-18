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

logger = logging.getLogger(__name__)


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
            parsed_triple = ast.literal_eval(bracketed_str)
            if len(parsed_triple) == 3 and all([isinstance(t, str) for t in parsed_triple]):
                if all([e != "" and e != "_" for e in parsed_triple]):
                    collected_triples.append(parsed_triple)
            elif not all([type(x) == type(parsed_triple[0]) for x in parsed_triple]):
                for e_idx, e in enumerate(parsed_triple):
                    if isinstance(e, list):
                        parsed_triple[e_idx] = ", ".join(e)
                collected_triples.append(parsed_triple)
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
    """Returns True if the model should be called via an OpenAI-compatible API.
    Detects: OpenAI (gpt in name), OpenRouter (/ in name), Google (gemini in name), Xiaomi (mimo in name) or Groq (GROQ_KEY is set).
    """
    if "gpt" in model_name:
        return True
    if "/" in model_name:
        return True
    if "gemini" in model_name.lower():
        return True
    if "mimo" in model_name.lower():
        return True
    # If GROQ_KEY is set, route all models through Groq API
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
    openrouter_key = os.environ.get("OPENROUTER_KEY", os.environ.get("OPENROUTER_API_KEY", ""))
    
    # If the model has a '/' (like meta-llama/...), it MUST go to OpenRouter.
    # Otherwise, if GROQ_KEY is present, send to Groq.
    if "/" in model or not groq_key:
        # Use OpenRouter API
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


def xiaomi_chat_completion(model, system_prompt, history, temperature=0, max_tokens=512):
    """Call Xiaomi MiMo API via OpenAI-compatible interface."""
    client = openai.OpenAI(
        base_url="https://token-plan-sgp.xiaomimimo.com/v1",
        api_key=os.environ["XIAOMI_API_KEY"],
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
            logger.warning(f"Xiaomi MiMo API error: {e}. Retrying in 5s...")
            time.sleep(5)
    logging.debug(f"Model: {model}\nPrompt:\n {messages}\n Result: {response.choices[0].message.content}")
    return response.choices[0].message.content


def api_chat_completion(model, system_prompt, history, temperature=0, max_tokens=512):
    """Unified entry point: routes to Google, Xiaomi, OpenRouter/Groq, or OpenAI based on model name and env vars."""
    if os.environ.get("XIAOMI_API_KEY", "") and "mimo" in model.lower():
        return xiaomi_chat_completion(model, system_prompt, history, temperature, max_tokens)
    elif os.environ.get("GEMINI_API_KEY", "") and "gemini" in model:
        return google_chat_completion(model, system_prompt, history, temperature, max_tokens)
    elif is_model_openrouter(model) or os.environ.get("GROQ_KEY", ""):
        return openrouter_chat_completion(model, system_prompt, history, temperature, max_tokens)
    else:
        return openai_chat_completion(model, system_prompt, history, temperature, max_tokens)

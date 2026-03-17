#!/usr/bin/env python3
"""批量提取节点 - 去扣子版，支持多 LLM Provider

批量处理文件，每批预过滤后调用LLM提取SOP
"""

import os
import json
import logging
import re
import sys
from pathlib import Path
from typing import List, Dict
from jinja2 import Template
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.graphs.state import ExtractFilesOutput, MergeResultsInput
from src.utils.llm_client import LLMClient
from src.utils.llm_config import get_llm_config, get_prompt_config

logger = logging.getLogger(__name__)


def log_progress(message: str):
    """打印进度信息到 stderr"""
    print(f"[PROGRESS] {message}", file=sys.stderr, flush=True)


def preprocess_file(chat_file):
    """预处理单个文件：执行质量检测、噪声过滤、敏感信息过滤"""
    try:
        from src.graphs.nodes.check_quality_node import check_quality_node
        from src.graphs.nodes.filter_noise_node import filter_noise_node
        from src.graphs.nodes.filter_sensitive_node import filter_sensitive_node
        from src.graphs.state import CheckQualityInput, FilterNoiseInput, FilterSensitiveInput

        check_input = CheckQualityInput(chat_file=chat_file)
        check_result = check_quality_node(state=check_input)

        if not check_result.quality_passed:
            logger.info(f"Quality check failed: {chat_file.url}, reason: {check_result.reason}")
            return None

        noise_input = FilterNoiseInput(chat_file=chat_file)
        noise_result = filter_noise_node(state=noise_input)

        sensitive_input = FilterSensitiveInput(filtered_content=noise_result.filtered_content)
        sensitive_result = filter_sensitive_node(state=sensitive_input)

        return {
            "file": chat_file,
            "filtered_content": sensitive_result.filtered_content
        }
    except Exception as e:
        logger.error(f"Preprocess error for {chat_file.url}: {e}")
        return None


def extract_sop_single_file(filtered_content: str) -> List[Dict]:
    """单个文件提取SOP"""
    llm_config = get_llm_config()
    prompt_config = get_prompt_config()
    
    sp = prompt_config["system"]
    up_template = prompt_config["user_template"]
    
    up_tpl = Template(up_template)
    user_prompt_content = up_tpl.render({"filtered_content": filtered_content})
    
    client = LLMClient.from_config(llm_config)
    
    messages = [
        {"role": "system", "content": sp},
        {"role": "user", "content": user_prompt_content}
    ]
    
    response_text = client.invoke(
        messages=messages,
        model=llm_config.model,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
        top_p=llm_config.top_p
    )

    logger.info(f"LLM response length: {len(response_text)}")

    sop_list = _parse_json_response(response_text)
    
    if sop_list:
        logger.info(f"Extracted {len(sop_list)} SOP(s)")
    
    return sop_list


def _parse_json_response(response_text: str) -> List[Dict]:
    """解析LLM的JSON响应"""
    if not response_text:
        return []
    
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data if isinstance(data, list) else [data]
            except:
                pass
    
    return []


def filter_contact_sop_simple(sop_list: List[Dict]) -> List[Dict]:
    """过滤引导联系客服的SOP"""
    filtered = []
    contact_keywords = ["联系客服", "找客服", "加客服", "客服微信", "客服QQ", "客服电话"]
    
    for sop in sop_list:
        response = sop.get("then", {}).get("response", "")
        if any(keyword in response for keyword in contact_keywords):
            logger.info(f"Filtered contact SOP: {sop.get('id', 'unknown')}")
            continue
        filtered.append(sop)
    
    return filtered


def batch_extract_node(state: ExtractFilesOutput) -> MergeResultsInput:
    """批量提取SOP（支持多 LLM Provider）"""
    total_files = len(state.chat_files)
    
    concurrency = int(os.getenv("SOP_CONCURRENCY", "50"))
    concurrency = min(concurrency, 100)
    batch_size = int(os.getenv("SOP_BATCH_SIZE", "10"))

    log_progress(f"Starting batch extraction: {total_files} files, concurrency={concurrency}, batch_size={batch_size}")

    all_sops = []
    total_batches = (total_files + batch_size - 1) // batch_size

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {}

        for batch_index in range(0, total_files, batch_size):
            batch = state.chat_files[batch_index:batch_index + batch_size]
            current_batch_num = (batch_index // batch_size) + 1
            
            log_progress(f"Batch {current_batch_num}/{total_batches}: Processing {len(batch)} file(s)")
            
            future = executor.submit(process_batch, batch, current_batch_num)
            futures[future] = batch_index

        completed_batches = 0
        for future in as_completed(futures):
            try:
                batch_sops = future.result(timeout=300)
                completed_batches += 1
                if batch_sops:
                    all_sops.extend(batch_sops)
                    log_progress(f"Progress: {completed_batches}/{total_batches} batches done, {len(all_sops)} SOP(s) extracted")
                else:
                    log_progress(f"Progress: {completed_batches}/{total_batches} batches done (no SOP)")
            except Exception as e:
                completed_batches += 1
                logger.error(f"Batch error: {e}")
                log_progress(f"Progress: {completed_batches}/{total_batches} batches done (error)")

    log_progress(f"Extraction complete: {len(all_sops)} SOP(s) from {total_files} files")
    return MergeResultsInput(all_sops=all_sops)


def process_batch(batch_files, batch_num):
    """处理一批文件"""
    log_progress(f"  Batch {batch_num}: Preprocessing {len(batch_files)} file(s)...")
    
    preprocessed = []
    for chat_file in batch_files:
        result = preprocess_file(chat_file)
        if result:
            preprocessed.append(result)

    if not preprocessed:
        log_progress(f"  Batch {batch_num}: No files passed preprocessing")
        return []

    log_progress(f"  Batch {batch_num}: {len(preprocessed)}/{len(batch_files)} files passed preprocessing")

    all_sops = []
    for idx, item in enumerate(preprocessed, 1):
        try:
            log_progress(f"  Batch {batch_num}: Extracting SOP from file {idx}/{len(preprocessed)}...")
            sop_list = extract_sop_single_file(item['filtered_content'])
            if not sop_list:
                continue
            
            filtered_sops = filter_contact_sop_simple(sop_list)
            if filtered_sops:
                all_sops.extend(filtered_sops)
                log_progress(f"  Batch {batch_num}: File {idx} -> {len(filtered_sops)} SOP(s)")
            else:
                log_progress(f"  Batch {batch_num}: File {idx} -> filtered out")
        except Exception as e:
            log_progress(f"  Batch {batch_num}: File {idx} error - {e}")
            continue

    log_progress(f"  Batch {batch_num}: Total {len(all_sops)} SOP(s)")
    return all_sops

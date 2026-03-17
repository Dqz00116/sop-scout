#!/usr/bin/env python3
"""批量提取节点 - 去扣子版，支持多 LLM Provider

批量处理文件，每批预过滤后调用LLM提取SOP
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict
from jinja2 import Template
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.graphs.state import ExtractFilesOutput, MergeResultsInput
from src.utils.llm_client import LLMClient
from src.utils.llm_config import get_llm_config, get_prompt_config

logger = logging.getLogger(__name__)


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
            logger.info(f"文件未通过质量检测: {chat_file.url}, 原因: {check_result.reason}")
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
        logger.error(f"预处理文件 {chat_file.url} 时出错: {str(e)}")
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

    logger.info(f"LLM原始响应（前500字符）: {response_text[:500]}")
    logger.info(f"LLM完整响应长度: {len(response_text)}")

    sop_list = _parse_json_response(response_text)
    
    if sop_list:
        logger.info(f"JSON解析成功，提取到 {len(sop_list)} 个SOP")
        if sop_list:
            logger.info(f"第一个SOP: {json.dumps(sop_list[0], ensure_ascii=False)[:500]}")
    
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
            logger.info(f"过滤引导联系客服的SOP: {sop.get('id', 'unknown')}")
            continue
        filtered.append(sop)
    
    return filtered


def batch_extract_node(state: ExtractFilesOutput) -> MergeResultsInput:
    """批量提取SOP（支持多 LLM Provider）"""
    concurrency = int(os.getenv("SOP_CONCURRENCY", 50))
    concurrency = min(concurrency, 100)
    batch_size = int(os.getenv("SOP_BATCH_SIZE", 10))

    logger.info(f"批量提取模式：批大小={batch_size}, 并发数={concurrency}, 总文件数={len(state.chat_files)}")

    all_sops = []
    total_batches = (len(state.chat_files) + batch_size - 1) // batch_size

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {}

        for batch_index in range(0, len(state.chat_files), batch_size):
            batch = state.chat_files[batch_index:batch_index + batch_size]
            current_batch_num = (batch_index // batch_size) + 1
            logger.info(f"开始处理第 {current_batch_num}/{total_batches} 批 ({len(batch)} 个文件)")
            future = executor.submit(process_batch, batch, current_batch_num)
            futures[future] = batch_index

        for future in as_completed(futures):
            try:
                batch_sops = future.result(timeout=300)
                if batch_sops:
                    all_sops.extend(batch_sops)
                    logger.info(f"批次完成，累计提取 {len(all_sops)} 个SOP")
            except Exception as e:
                logger.error(f"批次处理出错: {str(e)}")

    logger.info(f"所有批次完成，共提取 {len(all_sops)} 个SOP")
    return MergeResultsInput(all_sops=all_sops)


def process_batch(batch_files, batch_num):
    """处理一批文件"""
    preprocessed = []
    for chat_file in batch_files:
        result = preprocess_file(chat_file)
        if result:
            preprocessed.append(result)

    if not preprocessed:
        logger.info(f"批次 {batch_num} 没有文件通过预处理")
        return []

    logger.info(f"批次 {batch_num} 预处理完成，{len(preprocessed)} 个文件通过")

    all_sops = []
    for item in preprocessed:
        try:
            sop_list = extract_sop_single_file(item['filtered_content'])
            if not sop_list:
                continue
            filtered_sops = filter_contact_sop_simple(sop_list)
            if filtered_sops:
                all_sops.extend(filtered_sops)
                logger.info(f"文件 {item['file'].url} 提取到 {len(filtered_sops)} 个SOP")
        except Exception as e:
            logger.error(f"提取文件 {item['file'].url} 时出错: {str(e)}")
            continue

    logger.info(f"批次 {batch_num} 完成，共提取 {len(all_sops)} 个SOP")
    return all_sops

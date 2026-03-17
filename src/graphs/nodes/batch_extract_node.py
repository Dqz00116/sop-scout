import os
import json
import re
import logging
import asyncio
from typing import List, Dict
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage
from utils.file.file import FileOps
from graphs.state import (
    ExtractFilesOutput,
    MergeResultsInput
)
from utils.cancel_manager import cancel_manager

logger = logging.getLogger(__name__)

def preprocess_file(chat_file):
    """预处理单个文件：执行质量检测、噪声过滤、敏感信息过滤"""
    try:
        # 调用循环子图执行规则处理（但不执行extract_sop）
        # 我们需要手动执行这些规则处理节点
        from graphs.nodes.check_quality_node import check_quality_node
        from graphs.nodes.filter_noise_node import filter_noise_node
        from graphs.nodes.filter_sensitive_node import filter_sensitive_node

        # 1. 质量检测
        from graphs.state import CheckQualityInput, CheckQualityOutput
        check_input = CheckQualityInput(chat_file=chat_file)
        # 创建空的RunnableConfig和Runtime
        empty_config = RunnableConfig()
        from langgraph.runtime import Runtime
        from coze_coding_utils.runtime_ctx.context import Context
        empty_runtime = Runtime[Context]()

        check_result = check_quality_node(
            state=check_input,
            config=empty_config,
            runtime=empty_runtime
        )

        if not check_result.quality_passed:
            logger.info(f"文件未通过质量检测: {chat_file.url}, 原因: {check_result.reason}")
            return None

        # 2. 噪声过滤
        from graphs.state import FilterNoiseInput, FilterNoiseOutput
        noise_input = FilterNoiseInput(chat_file=chat_file)
        noise_result = filter_noise_node(
            state=noise_input,
            config=empty_config,
            runtime=empty_runtime
        )

        # 3. 敏感信息过滤
        from graphs.state import FilterSensitiveInput, FilterSensitiveOutput
        sensitive_input = FilterSensitiveInput(filtered_content=noise_result.filtered_content)
        sensitive_result = filter_sensitive_node(
            state=sensitive_input,
            config=empty_config,
            runtime=empty_runtime
        )

        return {
            "file": chat_file,
            "filtered_content": sensitive_result.filtered_content
        }
    except Exception as e:
        logger.error(f"预处理文件 {chat_file.url} 时出错: {str(e)}")
        return None

def extract_sop_single_file(filtered_content: str, ctx: Context) -> List[Dict]:
    """单个文件提取SOP"""
    # 读取LLM配置
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), "config/extract_sop_cfg.json")
    with open(cfg_file, 'r') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")

    # 构建用户提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"filtered_content": filtered_content})

    # 调用LLM
    client = LLMClient(ctx=ctx)
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]

    response = client.invoke(
        messages=messages,
        model=llm_config.get("model", "doubao-seed-1-8-251228"),
        temperature=llm_config.get("temperature", 0.7),
        max_completion_tokens=llm_config.get("max_completion_tokens", 32768),
        thinking=llm_config.get("thinking", "disabled")
    )

    # 解析响应
    def get_text_content(content):
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            if content and isinstance(content[0], str):
                return " ".join(content)
            else:
                return " ".join(item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text")
        return str(content)

    response_text = get_text_content(response.content)

    # 添加日志，输出LLM原始响应（前500字符）
    logger.info(f"LLM原始响应（前500字符）: {response_text[:500]}")
    logger.info(f"LLM完整响应长度: {len(response_text)}")

    try:
        sop_list = json.loads(response_text)
        if not isinstance(sop_list, list):
            sop_list = [sop_list]
        logger.info(f"JSON解析成功，提取到 {len(sop_list)} 个SOP")
        # 输出第一个SOP的详细信息
        if sop_list:
            logger.info(f"第一个SOP: {json.dumps(sop_list[0], ensure_ascii=False)[:500]}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                sop_list = json.loads(json_match.group())
                logger.info(f"正则提取JSON成功，提取到 {len(sop_list)} 个SOP")
            except Exception as e2:
                logger.error(f"正则提取JSON失败: {e2}")
                sop_list = []
        else:
            sop_list = []

    return sop_list

def batch_extract_node(state: ExtractFilesOutput, config: RunnableConfig, runtime: Runtime[Context]) -> MergeResultsInput:
    """
    title: 批量提取SOP（流水线并行 + 批量LLM调用）
    desc: 将文件分批，每批文件预过滤后批量调用LLM提取SOP，提升吞吐量
    integrations: 大语言模型
    """
    ctx = runtime.context
    run_id = ctx.run_id

    # 获取并发数配置
    import os
    concurrency = int(os.getenv("SOP_CONCURRENCY", 50))
    concurrency = min(concurrency, 100)

    # 批处理大小：每批调用LLM的文件数
    batch_size = int(os.getenv("SOP_BATCH_SIZE", 10))

    from utils.progress_manager import progress_manager
    from concurrent.futures import ThreadPoolExecutor, as_completed

    logger.info(f"批量提取模式：批大小={batch_size}, 并发数={concurrency}, 总文件数={len(state.chat_files)}")

    # 初始化进度
    total_files = len(state.chat_files)
    progress_manager.init_progress(run_id, total_files, batch_size)

    all_sops = []
    processed_count = 0
    total_batches = (len(state.chat_files) + batch_size - 1) // batch_size
    cancelled = False

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {}

        # 分批提交任务
        for batch_index in range(0, len(state.chat_files), batch_size):
            if cancel_manager.is_cancelled(run_id):
                cancelled = True
                logger.warning("检测到取消信号，停止提交新批次")
                break

            batch = state.chat_files[batch_index:batch_index + batch_size]
            current_batch_num = (batch_index // batch_size) + 1

            logger.info(f"开始处理第 {current_batch_num}/{total_batches} 批 ({len(batch)} 个文件)")

            # 提交批次任务
            future = executor.submit(process_batch, batch, current_batch_num, run_id, ctx)
            futures[future] = batch_index

        # 等待所有批次完成
        for future in as_completed(futures):
            if cancel_manager.is_cancelled(run_id):
                cancelled = True
                logger.warning("检测到取消信号，停止等待")
                break

            try:
                batch_sops = future.result(timeout=300)
                if batch_sops:
                    all_sops.extend(batch_sops)
                    processed_count += len(batch_sops)
                    logger.info(f"批次完成，累计提取 {len(all_sops)} 个SOP")
                    progress_manager.update_progress(
                        run_id=run_id,
                        processed_files=processed_count,
                        extracted_sops=len(all_sops),
                        current_batch=len(all_sops)
                    )
            except Exception as e:
                if isinstance(e, (KeyboardInterrupt, asyncio.CancelledError)):
                    cancelled = True
                    break
                logger.error(f"批次处理出错: {str(e)}")

    if cancelled:
        logger.warning(f"任务已取消，提取 {len(all_sops)} 个SOP")
        progress_manager.update_status(run_id, "cancelled")
    else:
        logger.info(f"所有批次完成，共提取 {len(all_sops)} 个SOP")
        progress_manager.update_status(run_id, "completed")

    return MergeResultsInput(all_sops=all_sops)

def process_batch(batch_files, batch_num, run_id, ctx):
    """处理一批文件：批量预过滤 + 单个文件LLM调用"""
    if cancel_manager.is_cancelled(run_id):
        return []

    # 1. 预处理所有文件（质量检测 + 噪声过滤 + 敏感信息过滤）
    preprocessed = []
    for chat_file in batch_files:
        result = preprocess_file(chat_file)
        if result:
            preprocessed.append(result)

    if not preprocessed:
        logger.info(f"批次 {batch_num} 没有文件通过预处理")
        return []

    logger.info(f"批次 {batch_num} 预处理完成，{len(preprocessed)} 个文件通过")

    # 2. 对每个通过预处理的文件单独调用LLM提取SOP
    all_sops = []
    from graphs.nodes.filter_contact_sop_node import filter_contact_sop_node
    from langchain_core.runnables import RunnableConfig
    from langgraph.runtime import Runtime
    from coze_coding_utils.runtime_ctx.context import Context
    from graphs.state import FilterContactSOPInput, FilterContactSPOutput

    for item in preprocessed:
        if cancel_manager.is_cancelled(run_id):
            break

        try:
            # 提取SOP（使用原有的extract_sop_node）
            sop_list = extract_sop_single_file(item['filtered_content'], ctx)

            if not sop_list:
                continue

            # 过滤引导联系客服的SOP
            filter_input = FilterContactSOPInput(sop_list=sop_list)
            filter_result = filter_contact_sop_node(
                state=filter_input,
                config=RunnableConfig(),
                runtime=Runtime[Context]()
            )

            if filter_result.filtered_sop_list:
                all_sops.extend(filter_result.filtered_sop_list)
                logger.info(f"文件 {item['file'].url} 提取到 {len(filter_result.filtered_sop_list)} 个SOP")

        except Exception as e:
            logger.error(f"提取文件 {item['file'].url} 时出错: {str(e)}")
            continue

    logger.info(f"批次 {batch_num} 完成，共提取 {len(all_sops)} 个SOP")
    return all_sops

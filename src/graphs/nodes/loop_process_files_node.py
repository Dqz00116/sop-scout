from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_EXCEPTION
import os
import asyncio
import logging
from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import ExtractFilesOutput, MergeResultsInput
from graphs.loop_graph import loop_graph
import json
from utils.cancel_manager import cancel_manager
from utils.progress_manager import progress_manager

logger = logging.getLogger(__name__)

def process_single_file(chat_file, run_id):
    """处理单个文件的函数（用于线程池）"""
    # 检查是否被取消
    if cancel_manager.is_cancelled(run_id):
        return []

    try:
        # 调用子图处理单个文件
        result = loop_graph.invoke({"chat_file": chat_file})

        # 再次检查是否被取消
        if cancel_manager.is_cancelled(run_id):
            return []

        # 收集SOP
        if result.get("sop_list"):
            return result["sop_list"]
        return []
    except Exception as e:
        # 如果是取消异常，静默返回
        if isinstance(e, (KeyboardInterrupt, asyncio.CancelledError)):
            return []
        logger.error(f"处理文件 {chat_file.url} 时出错: {str(e)}")
        return []

def loop_process_files_node(state: ExtractFilesOutput, config: RunnableConfig, runtime: Runtime[Context]) -> MergeResultsInput:
    """
    title: 循环处理文件（多线程并发）
    desc: 使用线程池并发处理每个聊天记录文件，提取SOP
    integrations:
    """
    ctx = runtime.context
    run_id = ctx.run_id

    # 获取并发数配置
    # 优先使用环境变量，否则默认50个并发
    concurrency = int(os.getenv("SOP_CONCURRENCY", 50))

    # 限制最大并发数，避免API限流和线程切换开销
    concurrency = min(concurrency, 100)

    # 批处理大小：每批提交的文件数
    batch_size = int(os.getenv("SOP_BATCH_SIZE", 10))

    logger.info(f"使用 {concurrency} 个并发线程处理 {len(state.chat_files)} 个文件")
    logger.info(f"批处理大小: {batch_size} 个文件/批")

    # 初始化进度
    total_files = len(state.chat_files)
    progress_manager.init_progress(run_id, total_files, batch_size)
    logger.info(f"已初始化进度跟踪，run_id: {run_id}, 总文件数: {total_files}")

    all_sops = []
    cancelled = False
    processed_count = 0
    total_batches = (len(state.chat_files) + batch_size - 1) // batch_size

    # 使用线程池并发处理
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # 分批提交任务
        for batch_index in range(0, len(state.chat_files), batch_size):
            # 检查是否被取消
            if cancel_manager.is_cancelled(run_id):
                cancelled = True
                logger.warning("检测到取消信号，停止提交新批次")
                break

            # 获取当前批次
            batch = state.chat_files[batch_index:batch_index + batch_size]
            current_batch_num = (batch_index // batch_size) + 1

            logger.info(f"开始处理第 {current_batch_num}/{total_batches} 批 ({len(batch)} 个文件)")

            # 提交当前批次的任务
            future_to_file = {
                executor.submit(process_single_file, chat_file, run_id): chat_file
                for chat_file in batch
            }

            try:
                # 等待当前批次完成
                while future_to_file:
                    # 检查是否被取消
                    if cancel_manager.is_cancelled(run_id):
                        cancelled = True
                        logger.warning("检测到取消信号，停止当前批次")
                        break

                    try:
                        # 等待下一个完成的任务，超时2秒检查一次取消状态
                        completed = next(as_completed(future_to_file, timeout=2))
                        chat_file = future_to_file[completed]

                        try:
                            # 获取结果，超时120秒
                            sop_list = completed.result(timeout=120)
                            if sop_list:
                                all_sops.extend(sop_list)
                                processed_count += 1
                                logger.info(f"已处理文件 [{processed_count}/{len(state.chat_files)}]: {chat_file.url}, 提取 {len(sop_list)} 个SOP")
                                # 更新进度
                                progress_manager.update_progress(
                                    run_id=run_id,
                                    processed_files=processed_count,
                                    extracted_sops=len(all_sops),
                                    current_batch=current_batch_num
                                )
                        except TimeoutError:
                            logger.warning(f"处理文件超时: {chat_file.url}")
                        except Exception as e:
                            if isinstance(e, (KeyboardInterrupt, asyncio.CancelledError)):
                                cancelled = True
                                logger.warning("检测到取消信号，停止当前批次")
                                break
                            logger.error(f"处理文件 {chat_file.url} 时出错: {str(e)}")

                        # 移除已完成的任务
                        del future_to_file[completed]

                    except TimeoutError:
                        # 超时后继续循环，检查取消状态
                        continue

            except (KeyboardInterrupt, asyncio.CancelledError):
                # 捕获取消信号
                logger.warning("检测到取消请求，正在停止任务...")
                cancelled = True
                break

            # 如果被取消，停止提交后续批次
            if cancelled:
                logger.warning(f"第 {current_batch_num}/{total_batches} 批被取消")
                break

            logger.info(f"第 {current_batch_num}/{total_batches} 批处理完成")

    # 如果被取消，输出统计信息
    if cancelled:
        logger.warning(f"任务已取消，已处理 {processed_count}/{len(state.chat_files)} 个文件，提取 {len(all_sops)} 个SOP")
        progress_manager.update_status(run_id, "cancelled")
    else:
        logger.info(f"所有批次处理完成，总共处理 {processed_count} 个文件，提取 {len(all_sops)} 个SOP")
        progress_manager.update_status(run_id, "completed")

    return MergeResultsInput(all_sops=all_sops)

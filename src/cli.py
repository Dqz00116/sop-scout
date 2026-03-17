#!/usr/bin/env python3
"""SOP Extractor CLI - MVP 版本"""

import argparse
import os
import asyncio
import sys
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.file.file import File
from graphs.graph import main_graph_cli
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_utils.log.loop_trace import init_run_config


async def process_zip(zip_path: str, output_dir: str, concurrency: int, verbose: bool):
    """处理单个 zip 文件"""
    
    # 确保路径绝对化
    zip_path = os.path.abspath(zip_path)
    output_dir = os.path.abspath(output_dir)
    
    # 检查输入文件
    if not os.path.exists(zip_path):
        print(f"错误: 文件不存在: {zip_path}", file=sys.stderr)
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置并发数和工作空间路径
    os.environ["SOP_CONCURRENCY"] = str(concurrency)
    os.environ.setdefault("COZE_WORKSPACE_PATH", str(Path(__file__).parent.parent))
    
    if verbose:
        print(f"处理文件: {zip_path}")
        print(f"输出目录: {output_dir}")
        print(f"并发数: {concurrency}")
    
    try:
        # 创建上下文
        ctx = new_context("cli_run")
        
        # 创建运行配置
        run_config = init_run_config(main_graph_cli, ctx)
        run_config["configurable"] = {"thread_id": ctx.run_id}
        
        # 调用工作流
        result = await main_graph_cli.ainvoke(
            {"zip_file": File(url=zip_path)},
            config=run_config,
            context=ctx
        )
        
        # 移动结果文件到输出目录
        jsonl_files = result.get("jsonl_file_urls", [])
        # 过滤掉可能的 http URL，只保留本地文件路径
        jsonl_files = [f for f in jsonl_files if f and not f.startswith('http')]
        
        if not jsonl_files:
            print("警告: 未生成任何输出文件", file=sys.stderr)
            return
        
        for src_path in jsonl_files:
            filename = os.path.basename(src_path)
            dst_path = os.path.join(output_dir, filename)
            
            # 如果目标已存在，先删除
            if os.path.exists(dst_path):
                os.remove(dst_path)
            
            shutil.move(src_path, dst_path)
            print(f"✓ {dst_path}")
        
        if verbose:
            print(f"\n完成: 共生成 {len(jsonl_files)} 个文件")
            
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="SOP 提取工具 - 从客服聊天记录中提取结构化 SOP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m src.cli 1号.zip -o ./output/
  python -m src.cli /mnt/e/data/chat.zip -o ./out/ -c 100 -v
        """
    )
    
    parser.add_argument(
        "input",
        help="输入 zip 文件路径（支持 WSL 路径如 /mnt/e/...）"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="输出目录（默认: ./output）"
    )
    
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=50,
        help="并发线程数（默认: 50）"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细日志"
    )
    
    args = parser.parse_args()
    
    # 运行异步处理
    asyncio.run(process_zip(
        zip_path=args.input,
        output_dir=args.output,
        concurrency=args.concurrency,
        verbose=args.verbose
    ))


if __name__ == "__main__":
    main()

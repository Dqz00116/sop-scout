#!/usr/bin/env python3
"""SOP Scout CLI - 面向开发者的简洁版本

极简 CLI 工具，支持 Moonshot/Kimi、豆包等多 LLM Provider
"""

import argparse
import os
import sys
import shutil
import logging
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.file.file import File
from src.utils.llm_config import get_llm_config
from src.graphs.simple_graph import simple_graph


# 配置日志（带时间戳）
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


def process_zip(zip_path: str, output_dir: str, verbose: bool):
    """处理单个 zip 文件"""
    
    # 确保路径绝对化
    zip_path = os.path.abspath(zip_path)
    output_dir = os.path.abspath(output_dir)
    
    # 检查输入文件
    if not os.path.exists(zip_path):
        print(f"Error: File not found: {zip_path}", file=sys.stderr)
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载配置
    llm_config = get_llm_config()
    concurrency = int(os.getenv("SOP_CONCURRENCY", "50"))
    
    if verbose:
        print(f"Input: {zip_path}", file=sys.stderr)
        print(f"Output: {output_dir}", file=sys.stderr)
        print(f"Model: {llm_config.model} ({llm_config.provider})", file=sys.stderr)
        print(f"Concurrency: {concurrency}", file=sys.stderr)
        print("", file=sys.stderr)
    
    try:
        # 同步调用工作流
        result = simple_graph.invoke({
            "zip_file": File(url=zip_path)
        })
        
        # 移动结果文件到输出目录
        jsonl_files = result.get("jsonl_file_urls", [])
        jsonl_files = [f for f in jsonl_files if f and not f.startswith('http')]
        
        if not jsonl_files:
            print("Warning: No output files generated", file=sys.stderr)
            sys.exit(1)
        
        moved_files = []
        for src_path in jsonl_files:
            if not os.path.exists(src_path):
                continue
            filename = os.path.basename(src_path)
            dst_path = os.path.join(output_dir, filename)
            
            if os.path.exists(dst_path):
                os.remove(dst_path)
            
            shutil.move(src_path, dst_path)
            moved_files.append(dst_path)
            print(dst_path)  # 标准输出，供脚本解析
        
        if verbose:
            print(f"\nDone: {len(moved_files)} file(s) generated", file=sys.stderr)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="SOP Scout - Extract SOP from customer service chat records",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli_simple input.zip -o ./output/
  python -m src.cli_simple input.zip -o ./output/ -v

Environment Variables:
  LLM_API_KEY / ARK_API_KEY / OPENAI_API_KEY  API key for LLM provider
  SOP_CONCURRENCY                               Concurrent threads (default: 50)
  SOP_BATCH_SIZE                                Batch size (default: 10)

Available Models:
  Run: python -c "from src.utils.llm_config import print_models; print_models()"
        """
    )
    
    parser.add_argument(
        "input",
        help="Input zip file path"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Output directory (default: ./output)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed logs"
    )
    
    args = parser.parse_args()
    
    # 检查 API key
    try:
        config = get_llm_config()
        if not config.api_key:
            raise ValueError("API key not found")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Please set environment variable:", file=sys.stderr)
        print("  export LLM_API_KEY=sk-xxx        # For Moonshot", file=sys.stderr)
        print("  export ARK_API_KEY=sk-xxx        # For Doubao", file=sys.stderr)
        print("  export OPENAI_API_KEY=sk-xxx     # For OpenAI", file=sys.stderr)
        sys.exit(1)
    
    # 运行处理
    process_zip(
        zip_path=args.input,
        output_dir=args.output,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()

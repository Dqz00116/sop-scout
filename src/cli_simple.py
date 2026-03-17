#!/usr/bin/env python3
"""SOP Scout CLI - 去扣子简化版

极简 CLI 工具，使用标准 OpenAI API（Moonshot/Kimi）
"""

import argparse
import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.file.file import File
from src.graphs.simple_graph import simple_graph


def process_zip(zip_path: str, output_dir: str, concurrency: int, verbose: bool):
    """处理单个 zip 文件"""
    
    # 确保路径绝对化
    zip_path = os.path.abspath(zip_path)
    output_dir = os.path.abspath(output_dir)
    
    # 检查输入文件
    if not os.path.exists(zip_path):
        print(f"❌ 错误: 文件不存在: {zip_path}", file=sys.stderr)
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置并发数
    os.environ["SOP_CONCURRENCY"] = str(concurrency)
    
    if verbose:
        print(f"📁 处理文件: {zip_path}")
        print(f"📂 输出目录: {output_dir}")
        print(f"⚡ 并发数: {concurrency}")
        print(f"🤖 使用模型: {os.getenv('LLM_MODEL', 'kimi-k2-0711-preview')}")
    
    try:
        # 同步调用工作流
        result = simple_graph.invoke({
            "zip_file": File(url=zip_path)
        })
        
        # 移动结果文件到输出目录
        jsonl_files = result.get("jsonl_file_urls", [])
        
        # 过滤掉可能的 http URL，只保留本地文件路径
        jsonl_files = [f for f in jsonl_files if f and not f.startswith('http')]
        
        if not jsonl_files:
            print("⚠️ 警告: 未生成任何输出文件", file=sys.stderr)
            return
        
        moved_files = []
        for src_path in jsonl_files:
            if not os.path.exists(src_path):
                continue
            filename = os.path.basename(src_path)
            dst_path = os.path.join(output_dir, filename)
            
            # 如果目标已存在，先删除
            if os.path.exists(dst_path):
                os.remove(dst_path)
            
            shutil.move(src_path, dst_path)
            moved_files.append(dst_path)
            print(f"✅ {dst_path}")
        
        if verbose:
            print(f"\n🎉 完成: 共生成 {len(moved_files)} 个文件")
            
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="SOP Scout - 从客服聊天记录中提取结构化 SOP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m src.cli_simple 1号.zip -o ./output/
  python -m src.cli_simple /mnt/e/data/chat.zip -o ./out/ -c 100 -v

环境变量:
  LLM_API_KEY       API 密钥 (必需)
  LLM_BASE_URL      API 基础 URL (默认: https://api.moonshot.cn/v1)
  SOP_CONCURRENCY   并发线程数 (默认: 50)
  SOP_BATCH_SIZE    批处理大小 (默认: 10)
        """
    )
    
    parser.add_argument(
        "input",
        help="输入 zip 文件路径"
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
    
    # 检查 API 密钥
    if not os.getenv("LLM_API_KEY"):
        print("❌ 错误: 未设置 LLM_API_KEY 环境变量", file=sys.stderr)
        print("请在 .env 文件中设置或导出环境变量:", file=sys.stderr)
        print("  export LLM_API_KEY=your_api_key", file=sys.stderr)
        sys.exit(1)
    
    # 运行处理
    process_zip(
        zip_path=args.input,
        output_dir=args.output,
        concurrency=args.concurrency,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()

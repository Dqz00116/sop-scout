import os
import zipfile
import tempfile
from typing import List
import urllib.request
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from utils.file.file import File
from graphs.state import ExtractFilesInput, ExtractFilesOutput

def extract_files_node(state: ExtractFilesInput, config: RunnableConfig, runtime: Runtime[Context]) -> ExtractFilesOutput:
    """
    title: 解压并提取聊天记录文件
    desc: 从zip文件中提取所有.txt格式的聊天记录文件
    integrations: 
    """
    ctx = runtime.context
    
    # 创建临时解压目录
    extract_dir = tempfile.mkdtemp(prefix="chat_extract_")
    
    try:
        # 下载zip文件内容
        url = state.zip_file.url
        
        if url.startswith('http://') or url.startswith('https://'):
            # 远程URL，下载文件
            with urllib.request.urlopen(url) as response:
                zip_content = response.read()
        else:
            # 本地路径，直接读取
            with open(url, 'rb') as f:
                zip_content = f.read()
        
        # 保存zip文件到临时目录
        zip_path = os.path.join(extract_dir, "chat_records.zip")
        with open(zip_path, 'wb') as f:
            f.write(zip_content)
        
        # 解压zip文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # 递归查找所有.txt文件
        txt_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    txt_files.append(file_path)
        
        # 为每个txt文件创建File对象（使用解压后的文件路径）
        chat_files = []
        for txt_file_path in txt_files:
            try:
                # 创建File对象，url为文件路径
                file_obj = File(url=txt_file_path)
                chat_files.append(file_obj)
            except Exception as e:
                print(f"创建文件对象 {txt_file_path} 时出错: {str(e)}")
                continue
        
        return ExtractFilesOutput(chat_files=chat_files)
    
    except Exception as e:
        print(f"解压zip文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return ExtractFilesOutput(chat_files=[])

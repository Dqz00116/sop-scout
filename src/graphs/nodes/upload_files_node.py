import os
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk.s3 import S3SyncStorage
from graphs.state import UploadFilesInput, UploadFilesOutput

def upload_files_node(state: UploadFilesInput, config: RunnableConfig, runtime: Runtime[Context]) -> UploadFilesOutput:
    """
    title: 上传JSONL文件
    desc: 将生成的JSONL文件上传到对象存储并返回下载URL
    integrations: 对象存储
    """
    ctx = runtime.context
    
    # 初始化对象存储客户端
    storage = S3SyncStorage(
        endpoint_url=os.getenv("COZE_BUCKET_ENDPOINT_URL"),
        access_key="",
        secret_key="",
        bucket_name=os.getenv("COZE_BUCKET_NAME"),
        region="cn-beijing",
    )
    
    jsonl_file_urls = []
    
    for file_path in state.jsonl_files:
        try:
            # 读取文件内容
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # 上传到对象存储
            file_name = os.path.basename(file_path)
            
            # 使用 stream_upload_file 上传文件
            with open(file_path, 'rb') as f:
                file_key = storage.stream_upload_file(
                    fileobj=f,
                    file_name=f"sop_extraction/{file_name}",
                    content_type="application/jsonl",
                )
            
            # 生成签名 URL
            file_url = storage.generate_presigned_url(
                key=file_key,
                expire_time=86400,  # 有效期1天
            )
            
            jsonl_file_urls.append(file_url)
        
        except Exception as e:
            print(f"上传文件 {file_path} 时出错: {str(e)}")
            continue
    
    return UploadFilesOutput(jsonl_file_urls=jsonl_file_urls)

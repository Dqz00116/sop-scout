from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from src.utils.file.file import File

class GlobalState(BaseModel):
    """全局状态定义"""
    zip_file: Optional[File] = Field(default=None, description="包含聊天记录的zip文件")
    chat_files: List[File] = Field(default=[], description="聊天记录文件列表")
    all_sops: List[dict] = Field(default=[], description="所有提取的SOP列表")
    jsonl_file_urls: List[str] = Field(default=[], description="生成的JSONL文件URL列表")

class GraphInput(BaseModel):
    """工作流的输入"""
    zip_file: File = Field(..., description="包含聊天记录的zip文件")

class GraphOutput(BaseModel):
    """工作流的输出"""
    jsonl_file_urls: List[str] = Field(..., description="生成的JSONL文件URL列表")

# 解压节点的输入
class ExtractFilesInput(BaseModel):
    """解压节点的输入"""
    zip_file: File = Field(..., description="包含聊天记录的zip文件")

# 解压节点的输出
class ExtractFilesOutput(BaseModel):
    """解压节点的输出"""
    chat_files: List[File] = Field(default=[], description="提取的聊天记录文件列表")

# 循环子图的状态（用于处理单个文件）
class LoopGlobalState(BaseModel):
    """循环子图的全局状态"""
    chat_file: File = Field(..., description="当前处理的聊天记录文件")
    sop_list: List[dict] = Field(default=[], description="提取的SOP列表")
    filtered_sop_list: List[dict] = Field(default=[], description="过滤后的SOP列表")

class LoopGraphInput(BaseModel):
    """循环子图的输入"""
    chat_file: File = Field(..., description="要处理的聊天记录文件")

class LoopGraphOutput(BaseModel):
    """循环子图的输出"""
    sop_list: List[dict] = Field(..., description="提取的SOP列表")

# 质量检测节点的输入
class CheckQualityInput(BaseModel):
    """质量检测节点的输入"""
    chat_file: File = Field(..., description="要检测的聊天记录文件")

# 质量检测节点的输出
class CheckQualityOutput(BaseModel):
    """质量检测节点的输出"""
    quality_passed: bool = Field(..., description="是否通过质量检测")
    reason: str = Field(..., description="未通过的原因")

# 噪声过滤节点的输入
class FilterNoiseInput(BaseModel):
    """噪声过滤节点的输入"""
    chat_file: File = Field(..., description="要过滤的聊天记录文件")

# 噪声过滤节点的输出
class FilterNoiseOutput(BaseModel):
    """噪声过滤节点的输出"""
    filtered_content: str = Field(..., description="过滤后的内容")

# 敏感信息过滤节点的输入
class FilterSensitiveInput(BaseModel):
    """敏感信息过滤节点的输入"""
    filtered_content: str = Field(..., description="要过滤敏感信息的内容")

# 敏感信息过滤节点的输出
class FilterSensitiveOutput(BaseModel):
    """敏感信息过滤节点的输出"""
    filtered_content: str = Field(..., description="过滤敏感信息后的内容")

# SOP提取节点的输入
class ExtractSOPInput(BaseModel):
    """SOP提取节点的输入"""
    filtered_content: str = Field(..., description="要提取SOP的内容")

# SOP提取节点的输出
class ExtractSPOutput(BaseModel):
    """SOP提取节点的输出"""
    sop_list: List[dict] = Field(default=[], description="提取的SOP列表")

# SOP过滤节点的输入
class FilterContactSOPInput(BaseModel):
    """SOP过滤节点的输入"""
    sop_list: List[dict] = Field(..., description="要过滤的SOP列表")

# SOP过滤节点的输出
class FilterContactSPOutput(BaseModel):
    """SOP过滤节点的输出"""
    filtered_sop_list: List[dict] = Field(default=[], description="过滤后的SOP列表")

# 聚合结果节点的输入
class MergeResultsInput(BaseModel):
    """聚合结果节点的输入"""
    all_sops: List[dict] = Field(..., description="所有提取的SOP列表")

# 聚合结果节点的输出
class MergeResultsOutput(BaseModel):
    """聚合结果节点的输出"""
    jsonl_file_urls: List[str] = Field(default=[], description="生成的JSONL文件本地路径列表")

# 文件上传节点的输入
class UploadFilesInput(BaseModel):
    """文件上传节点的输入"""
    jsonl_files: List[str] = Field(..., description="生成的JSONL文件本地路径列表")

# 文件上传节点的输出
class UploadFilesOutput(BaseModel):
    """文件上传节点的输出"""
    jsonl_file_urls: List[str] = Field(..., description="上传后的JSONL文件URL列表")

#!/usr/bin/env python3
"""噪声过滤节点 - 去扣子版

过滤聊天记录中的噪声段落（问候语、闲聊等无效对话）
"""

from src.utils.file.file import FileOps
from src.graphs.state import FilterNoiseInput, FilterNoiseOutput


def filter_noise_node(state: FilterNoiseInput) -> FilterNoiseOutput:
    """
    title: 噪声过滤
    desc: 过滤聊天记录中的噪声段落（问候语、闲聊等无效对话）
    """
    
    # 读取文件内容
    content = FileOps.extract_text(state.chat_file)
    
    greeting_keywords = ['在吗', '你好', '您好', '在不在', '有人吗', '哈喽', '嗨', 'hello', 'hi']
    confirmation_keywords = ['好的', '收到', 'OK', 'ok', '明白', '知道了', '了解了', '嗯', '行', '可以', '没问题']
    valid_keywords = ['无法', '不能', '错误', '异常', '问题', '失败', '报错', '闪退', '卡顿', 
                     '充值', '找回', '注册', '登录', '账号', '密码', '活动', '奖励', 
                     '外挂', '举报', '昵称', '违规', '段位', '等级', '规则', '帮助']
    
    lines = content.split('\n')
    paragraphs = []
    current_paragraph = []
    
    for line in lines:
        line = line.strip()
        if line:
            current_paragraph.append(line)
        else:
            if current_paragraph:
                paragraphs.append(current_paragraph)
                current_paragraph = []
    
    if current_paragraph:
        paragraphs.append(current_paragraph)
    
    filtered_paragraphs = []
    
    for paragraph in paragraphs:
        paragraph_text = '\n'.join(paragraph)
        
        is_greeting_only = True
        for line in paragraph:
            line_lower = line.lower()
            has_greeting = any(greeting in line for greeting in greeting_keywords)
            has_other_content = not has_greeting or len(line) > 20
            if has_other_content:
                is_greeting_only = False
                break
        
        if is_greeting_only:
            continue
        
        if len(paragraph) == 1:
            single_line = paragraph[0]
            if len(single_line) < 20:
                has_valid_keyword = any(keyword in single_line for keyword in valid_keywords)
                if not has_valid_keyword:
                    continue
        
        is_confirmation_only = True
        for line in paragraph:
            line_lower = line.lower()
            has_confirmation = any(confirmation in line for confirmation in confirmation_keywords)
            has_other_content = not has_confirmation or len(line) > 10
            if has_other_content:
                is_confirmation_only = False
                break
        
        if is_confirmation_only:
            continue
        
        has_valid_content = any(
            any(keyword in line for keyword in valid_keywords)
            for line in paragraph
        )
        
        has_role = any(
            any(role in line for role in ['客服', 'CS', 'GM', '玩家', '用户', 'Player', 'User'])
            for line in paragraph
        )
        
        has_timestamp = any(
            any(char.isdigit() for char in line) and (':' in line or '：' in line)
            for line in paragraph
        )
        
        if has_valid_content or has_role or has_timestamp:
            filtered_paragraphs.append(paragraph)
        elif len(paragraph_text) > 50:
            filtered_paragraphs.append(paragraph)
    
    filtered_content = '\n\n'.join('\n'.join(para) for para in filtered_paragraphs)
    
    if not filtered_content.strip():
        filtered_content = content
    
    return FilterNoiseOutput(filtered_content=filtered_content)

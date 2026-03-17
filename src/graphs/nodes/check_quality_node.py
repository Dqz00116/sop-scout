#!/usr/bin/env python3
"""质量检测节点 - 去扣子版

检测聊天记录的质量，判断是否包含有效的客服对话内容
"""

import re
from src.utils.file.file import FileOps
from src.graphs.state import CheckQualityInput, CheckQualityOutput


def check_quality_node(state: CheckQualityInput) -> CheckQualityOutput:
    """
    title: 质量检测
    desc: 检测聊天记录的质量，判断是否包含有效的客服对话内容
    """
    
    # 读取文件内容
    content = FileOps.extract_text(state.chat_file)
    
    # 1. 检查文件长度（至少5行）
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    if len(lines) < 5:
        return CheckQualityOutput(quality_passed=False, reason=f"聊天记录过短，只有{len(lines)}行，至少需要5行")
    
    # 2. 检查是否包含客服标识
    csr_keywords = ["客服", "技术支持", "管理员", "官方"]
    has_csr = any(keyword in content for keyword in csr_keywords)
    if not has_csr:
        return CheckQualityOutput(quality_passed=False, reason="缺少客服标识")
    
    # 3. 检查对话轮次
    customer_pattern = re.compile(r'(玩家|用户|顾客|访客)')
    customer_dialogues = [line for line in lines if customer_pattern.search(line)]
    
    csr_pattern = re.compile(r'(客服|技术支持|管理员|官方)')
    csr_dialogues = [line for line in lines if csr_pattern.search(line)]
    
    if len(customer_dialogues) < 1 or len(csr_dialogues) < 1:
        return CheckQualityOutput(quality_passed=False, reason=f"对话次数不足（玩家:{len(customer_dialogues)}, 客服:{len(csr_dialogues)}）")
    
    # 4. 检查问题关键词
    question_keywords = ["问题", "故障", "错误", "失败", "无法", "不能", "不行", "怎么", "如何", "怎么办", "登录不了", "充值不到", "闪退", "卡顿", "延迟", "账号", "密码", "bug", "BUG", "功能", "异常", "调整"]
    has_question = any(keyword in content for keyword in question_keywords)
    if not has_question:
        return CheckQualityOutput(quality_passed=False, reason="缺少问题关键词")
    
    # 5. 检查解决方案关键词
    solution_keywords = ["请", "可以", "建议", "尝试", "需要", "您", "提供", "核实", "处理", "反馈", "等待", "修复", "联系", "提交", "记录", "通知", "关注", "官方", "研发", "知晓", "消息"]
    has_solution = any(keyword in content for keyword in solution_keywords)
    if not has_solution:
        return CheckQualityOutput(quality_passed=False, reason="缺少解决方案关键词")
    
    # 6. 计算噪声占比
    noise_keywords = ["你好", "您好", "在吗", "在不在", "哈喽", "hello", "hi", "嗨", "有人吗", "收到", "好的", "明白", "谢谢", "感谢", "行", "ok", "OK"]
    noise_lines = sum(1 for line in lines if any(keyword in line for keyword in noise_keywords))
    noise_ratio = noise_lines / len(lines) if len(lines) > 0 else 0
    
    if noise_ratio >= 0.7:
        return CheckQualityOutput(quality_passed=False, reason=f"噪声占比过高（{noise_ratio:.1%}）")
    
    return CheckQualityOutput(quality_passed=True, reason="质量检测通过")

import re
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import FilterSensitiveInput, FilterSensitiveOutput

def filter_sensitive_node(state: FilterSensitiveInput, config: RunnableConfig, runtime: Runtime[Context]) -> FilterSensitiveOutput:
    """
    title: 敏感信息过滤
    desc: 过滤聊天记录中的敏感信息（电话、身份证、密码、地址、游戏账号、卡牌等级、昵称、IP等）
    integrations: 
    """
    ctx = runtime.context
    
    patterns = {
        'phone': r'1[3-9]\d{9}',
        'id_card': r'\d{17}[\dXx]',
        'password': r'(密码|Password|pwd)[：:\s]*([^\s,，。.!?！?]{4,20})',
        'address': r'[\u4e00-\u9fa5]{2,}[省市][\u4e00-\u9fa5]{1,}[区县][\u4e00-\u9fa5]{1,}[路街道][\u4e00-\u9fa50-9]{1,}[号栋楼]',
        'game_account': r'(账号|account|UID|uid)[：:\s]*[A-Za-z0-9_-]{4,20}',
        'game_id': r'(?<!\d)(\d{4,15})(?!\d)|(?<![A-Za-z])([A-Za-z0-9]{4,15})(?![A-Za-z0-9])',
        'ip_address': r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',
        'card_level': r'(Lv\.|等级|Level|level)\s*\d{1,3}',
        'nickname': r'(角色|玩家|用户|user)[：:\s]*[\u4e00-\u9fa5]{2,8}'
    }
    
    filtered_content = state.filtered_content
    
    for name, pattern in patterns.items():
        filtered_content = re.sub(pattern, '[***已过滤***]', filtered_content)
    
    return FilterSensitiveOutput(filtered_content=filtered_content)

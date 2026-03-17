#!/usr/bin/env python3
"""过滤联系客服SOP节点 - 去扣子版

过滤掉引导玩家联系客服的SOP流程
"""

from src.graphs.state import FilterContactSOPInput, FilterContactSPOutput


def filter_contact_sop_node(state: FilterContactSOPInput) -> FilterContactSPOutput:
    """
    title: 过滤联系客服SOP
    desc: 过滤掉引导玩家联系客服的SOP流程
    """
    filtered_sop_list = []
    
    contact_keywords = [
        '联系客服',
        '联系人工客服',
        '请咨询客服',
        '找客服',
        '客服咨询',
        '联系在线客服',
        '咨询人工',
        '转人工',
        '人工服务',
        '客服协助',
        '请联系我们',
        '联系官方客服',
        '客服微信',
        '客服QQ',
        '客服电话'
    ]
    
    for sop in state.sop_list:
        should_filter = False
        response_text = sop.get('then', {}).get('response', '').lower()
        
        for keyword in contact_keywords:
            if keyword in response_text:
                should_filter = True
                break
        
        if not should_filter:
            if '如不接受' in response_text or '如仍有问题' in response_text or '如无法解决' in response_text:
                should_filter = True
        
        if not should_filter:
            filtered_sop_list.append(sop)
    
    return FilterContactSPOutput(filtered_sop_list=filtered_sop_list)

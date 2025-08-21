#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实时日志功能的脚本
"""

import sys
import time
from datetime import datetime

def simulate_resume_extraction():
    """模拟简历提取过程，产生大量日志输出"""
    print("=== 开始模拟简历提取过程 ===")
    print(f"当前时间: {datetime.now()}")
    
    # 模拟创建对话
    print("正在创建新对话...")
    time.sleep(0.5)
    print(f"[2025-08-21 11:10:50.219157] 对话创建成功，对话ID: d2jftegpsf858s19bh1g")
    print("✅ 对话ID已保存到 conversation_id.json")
    print("使用对话ID: d2jftegpsf858s19bh1g")
    
    # 模拟处理多个简历查询
    queries = [
        "5.新疆大学-电子信息-常硕硕的简历情况",
        "6.北京理工大学-计算机科学-张三的简历情况",
        "7.清华大学-人工智能-李四的简历情况"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n=== 处理第{i}个简历查询 ===")
        print(f"查询: {query}")
        
        # 模拟发送消息
        print(f"发送消息: {query}")
        time.sleep(0.3)
        
        # 模拟智能体回复
        print(f"[2025-08-21 11:11:14.894762] 智能体回复:")
        print("```json")
        print("{")
        print('  "姓名": "示例姓名",')
        print('  "性别": "男",')
        print('  "最高学历": "硕士",')
        print('  "硕士专业": "示例专业",')
        print('  "硕士院校": "示例大学"')
        print("}")
        print("```")
        
        # 模拟成功提取
        print("✅ 成功提取简历信息")
        time.sleep(0.2)
    
    print("\n=== 简历提取完成 ===")
    print(f"总共处理了 {len(queries)} 个查询")
    print(f"完成时间: {datetime.now()}")

if __name__ == "__main__":
    simulate_resume_extraction()

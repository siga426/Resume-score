#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日志捕获功能的脚本
"""

import sys
import time
from datetime import datetime

def test_print_outputs():
    """测试各种print输出"""
    print("=== 开始测试日志捕获功能 ===")
    print(f"当前时间: {datetime.now()}")
    
    # 测试不同类型的输出
    print("这是一条普通信息")
    print("这是一条警告信息")
    print("这是一条错误信息")
    
    # 测试数字输出
    for i in range(5):
        print(f"处理第 {i+1} 项...")
        time.sleep(0.1)  # 模拟处理时间
    
    # 测试长文本
    print("这是一段很长的文本，用来测试日志显示区域的换行和滚动功能。")
    print("包含中文和English混合内容。")
    
    # 测试特殊字符
    print("特殊字符: !@#$%^&*()_+-=[]{}|;':\",./<>?")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_print_outputs()

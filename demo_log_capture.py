#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示日志捕获功能的Streamlit应用
"""

import streamlit as st
import sys
import time
from datetime import datetime
from contextlib import contextmanager

# 导入日志捕获器
from streamlit_app import StreamlitLogCapture, capture_logs

def demo_log_capture():
    """演示日志捕获功能"""
    st.title("🔍 日志捕获功能演示")
    st.caption("这个演示展示了如何实时捕获和显示print输出")
    
    # 创建日志容器
    log_container = st.container()
    
    # 演示按钮
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 生成测试日志"):
            with capture_logs(log_container) as log_capture:
                st.info("正在生成测试日志...")
                
                # 模拟一些print输出
                print("=== 开始生成测试日志 ===")
                print(f"当前时间: {datetime.now()}")
                
                for i in range(10):
                    print(f"处理第 {i+1} 项任务...")
                    time.sleep(0.2)  # 模拟处理时间
                
                print("生成一些中文内容...")
                print("这是一段很长的中文文本，用来测试日志显示区域的换行和滚动功能。")
                print("包含中文和English混合内容。")
                
                print("=== 测试日志生成完成 ===")
                
                # 更新显示
                log_capture.update_display()
                
                st.success("测试日志生成完成！")
    
    with col2:
        if st.button("🧹 清除所有日志"):
            st.rerun()
    
    with col3:
        if st.button("🔄 刷新页面"):
            st.rerun()
    
    # 显示说明
    st.divider()
    st.subheader("📖 功能说明")
    
    st.markdown("""
    ### 主要特性
    
    1. **实时日志捕获**: 自动捕获所有print()函数的输出
    2. **时间戳记录**: 每条日志都带有精确的时间戳
    3. **缓冲区管理**: 智能管理日志缓冲区，避免内存溢出
    4. **界面集成**: 完美集成到Streamlit界面中
    
    ### 使用方法
    
    1. 点击"📝 生成测试日志"按钮
    2. 观察日志区域的实时更新
    3. 使用日志管理功能（清除、下载、刷新）
    
    ### 技术原理
    
    - 重写sys.stdout来捕获print输出
    - 使用上下文管理器确保资源正确释放
    - Streamlit容器动态更新显示内容
    """)
    
    # 显示日志区域
    st.divider()
    st.subheader("📋 日志显示区域")
    
    # 初始化日志显示
    with log_container:
        st.info("日志区域已就绪，点击上方按钮开始演示")

if __name__ == "__main__":
    demo_log_capture()

#!/usr/bin/env python3
"""
简历信息提取系统 - Streamlit界面启动脚本
"""

import os
import sys
import subprocess
import webbrowser
import time

def main():
    """主函数"""
    print("=" * 50)
    print("📋 简历信息提取系统 - Streamlit界面")
    print("=" * 50)
    
    # 检查必要文件
    required_files = [
        "resume_extractor.py",
        "multi_round_chat.py", 
        "query_loader.py",
        "streamlit_app.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少必要文件: {', '.join(missing_files)}")
        print("请确保所有必要文件都在当前目录中")
        return
    
    print("✅ 环境检查通过")
    
    # 检查是否安装了streamlit
    try:
        import streamlit
        print(f"✅ Streamlit已安装 (版本: {streamlit.__version__})")
    except ImportError:
        print("❌ 未安装Streamlit，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
            print("✅ Streamlit安装成功")
        except subprocess.CalledProcessError:
            print("❌ Streamlit安装失败，请手动安装: pip install streamlit")
            return
    
    print("\n🚀 启动Streamlit应用...")
    print("📱 应用将在浏览器中自动打开")
    print("⏹️  按 Ctrl+C 停止应用")
    print("=" * 50)
    
    try:
        # 启动Streamlit应用
        cmd = [sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.port", "8501"]
        process = subprocess.Popen(cmd)
        
        # 等待应用启动
        print("⏳ 等待应用启动...")
        time.sleep(5)
        
        # 自动打开浏览器
        try:
            webbrowser.open("http://localhost:8501")
            print("🌐 浏览器已自动打开")
        except:
            print("📱 请在浏览器中手动访问: http://localhost:8501")
        
        # 等待进程结束
        process.wait()
        
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()

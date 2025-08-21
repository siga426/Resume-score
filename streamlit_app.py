import streamlit as st
import pandas as pd
import os
import json
import tempfile
import zipfile
from datetime import datetime
import sys
import io
from contextlib import redirect_stdout
import threading
import queue
import time

# 导入项目模块
from resume_extractor import ResumeExtractor
from query_loader import QueryLoader

# 页面配置
st.set_page_config(
    page_title="简历信息提取系统",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 全局变量
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []
if 'extraction_running' not in st.session_state:
    st.session_state.extraction_running = False

class StreamlitLogger:
    """Streamlit日志记录器，用于捕获print输出"""
    
    def __init__(self):
        self.log_queue = queue.Queue()
        self.original_stdout = sys.stdout
        self.original_print = print
        
    def start_capture(self):
        """开始捕获print输出"""
        sys.stdout = self
        # 重写print函数
        def custom_print(*args, **kwargs):
            message = ' '.join(str(arg) for arg in args)
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry = f"[{timestamp}] {message}"
            self.log_queue.put(log_entry)
            # 同时输出到原始stdout
            self.original_print(*args, **kwargs)
        
        # 替换全局print函数
        globals()['print'] = custom_print
        
    def stop_capture(self):
        """停止捕获print输出"""
        sys.stdout = self.original_stdout
        globals()['print'] = self.original_print
        
    def write(self, text):
        """重写stdout的write方法"""
        if text.strip():
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry = f"[{timestamp}] {text.strip()}"
            self.log_queue.put(log_entry)
        self.original_stdout.write(text)
        
    def flush(self):
        """重写stdout的flush方法"""
        self.original_stdout.flush()
        
    def get_logs(self):
        """获取所有日志消息"""
        logs = []
        while not self.log_queue.empty():
            try:
                logs.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        return logs

def main():
    """主函数"""
    
    # 页面标题
    st.title("📋 简历信息提取系统")
    st.markdown("智能提取简历信息，支持批量处理 - Streamlit版本")
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 系统配置")
        
        # API配置
        st.subheader("API设置")
        api_key = st.text_input("API密钥", value="d2a7gnen04uuiosfsnk0", type="password")
        base_url = st.text_input("API基础URL", value="https://aiagentplatform.cmft.com")
        user_id = st.text_input("用户ID", value="Siga")
        
        # 文件上传配置
        st.subheader("📁 文件上传")
        uploaded_file = st.file_uploader(
            "选择查询文件",
            type=['xlsx', 'xls', 'csv', 'txt'],
            help="支持Excel、CSV、TXT格式，第一列包含查询列表"
        )
        
        # 操作按钮
        st.subheader("🚀 操作控制")
        if uploaded_file is not None:
            if st.button("开始提取", type="primary", use_container_width=True):
                start_extraction(uploaded_file, api_key, base_url, user_id)
        
        # 系统状态
        st.subheader("📊 系统状态")
        if st.session_state.extraction_running:
            st.info("🔄 正在运行中...")
        else:
            st.success("✅ 系统就绪")
    
    # 主内容区域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📋 文件信息")
        if uploaded_file is not None:
            file_info = {
                "文件名": uploaded_file.name,
                "文件大小": f"{uploaded_file.size / 1024:.1f} KB",
                "文件类型": uploaded_file.type,
                "上传时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            for key, value in file_info.items():
                st.write(f"**{key}:** {value}")
            
            # 预览文件内容
            st.subheader("📖 文件内容预览")
            try:
                if uploaded_file.name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(uploaded_file)
                elif uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    # 文本文件
                    content = uploaded_file.read().decode('utf-8')
                    lines = content.split('\n')[:10]  # 只显示前10行
                    df = pd.DataFrame({'查询内容': lines})
                    uploaded_file.seek(0)  # 重置文件指针
                
                st.dataframe(df.head(10), use_container_width=True)
                if len(df) > 10:
                    st.info(f"显示前10行，共{len(df)}行数据")
                    
            except Exception as e:
                st.error(f"文件预览失败: {str(e)}")
        else:
            st.info("请上传查询文件")
    
    with col2:
        st.header("📊 提取统计")
        if 'extraction_summary' in st.session_state:
            summary = st.session_state.extraction_summary
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.metric("总数量", summary.get('total_count', 0))
                st.metric("成功", summary.get('successful_extractions', 0))
            
            with col_b:
                st.metric("失败", summary.get('failed_count', 0))
                st.metric("成功率", f"{summary.get('success_rate', 0):.1f}%")
        else:
            st.info("暂无提取数据")
    
    # 实时日志显示
    st.header("📝 实时执行日志")
    
    # 日志控制按钮
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 刷新日志", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("🗑️ 清空日志", use_container_width=True):
            st.session_state.log_messages = []
            st.rerun()
    
    with col3:
        st.info("日志会实时显示程序执行过程中的所有print输出")
    
    # 日志显示区域
    if st.session_state.log_messages:
        # 创建可滚动的日志容器
        log_text = "\n".join(st.session_state.log_messages[-100:])  # 只显示最后100条
        st.text_area("执行日志", value=log_text, height=300, disabled=True)
    else:
        st.info("暂无日志信息")
    
    # 结果显示区域
    if 'extraction_results' in st.session_state:
        st.header("📊 提取结果")
        
        results = st.session_state.extraction_results
        
        # 显示摘要信息
        if 'summary' in results:
            summary = results['summary']
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("成功提取", summary.get('successful_extractions', 0))
            
            with col2:
                st.metric("不同姓名", len(summary.get('unique_names', [])))
            
            with col3:
                st.metric("学历类型", len(summary.get('education_levels', [])))
            
            with col4:
                st.metric("涉及院校", len(summary.get('universities', [])))
        
        # 显示数据表格
        if 'data' in results and results['data']:
            st.subheader("📋 提取数据预览")
            df = pd.DataFrame(results['data'])
            st.dataframe(df.head(20), use_container_width=True)
            
            if len(df) > 20:
                st.info(f"显示前20行，共{len(df)}行数据")
        
        # 下载按钮
        if 'files' in results:
            st.subheader("📥 下载结果")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 下载Excel", use_container_width=True):
                    download_excel(results['files']['excel'])
            
            with col2:
                if st.button("📄 下载JSON", use_container_width=True):
                    download_json(results['files']['json'])
            
            with col3:
                if st.button("📦 下载所有文件", use_container_width=True):
                    download_all_files()

def start_extraction(uploaded_file, api_key, base_url, user_id):
    """开始简历提取"""
    
    if st.session_state.extraction_running:
        st.warning("提取任务正在运行中，请等待完成")
        return
    
    st.session_state.extraction_running = True
    
    # 创建日志记录器
    logger = StreamlitLogger()
    logger.start_capture()
    
    try:
        # 保存上传的文件
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 记录日志
        st.session_state.log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] 文件上传成功: {uploaded_file.name}")
        
        # 创建简历提取器
        extractor = ResumeExtractor(api_key, base_url, user_id)
        query_loader = QueryLoader()
        
        # 从文件读取查询列表
        resume_queries = query_loader.load_queries(file_path)
        
        if not resume_queries:
            st.error("无法从文件中读取查询列表")
            return
        
        st.session_state.log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] 成功加载 {len(resume_queries)} 个查询")
        
        # 执行批量提取
        extracted_data = extractor.batch_extract_resumes(resume_queries)
        
        if not extracted_data:
            st.error("没有成功提取到任何简历数据")
            return
        
        # 生成输出文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f'resume_data_{timestamp}.xlsx'
        json_filename = f'resume_data_{timestamp}.json'
        
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        excel_path = os.path.join(output_dir, excel_filename)
        json_path = os.path.join(output_dir, json_filename)
        
        # 导出文件
        extractor.export_to_excel(excel_path)
        extractor.export_to_json(json_path)
        
        # 保存失败的查询（如果有的话）
        failed_queries_file = None
        if hasattr(extractor, 'failed_queries') and extractor.failed_queries:
            failed_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            failed_filename = f'failed_queries_{failed_timestamp}.xlsx'
            failed_path = os.path.join(output_dir, failed_filename)
            extractor.save_failed_queries(failed_path)
            failed_queries_file = failed_filename
        
        # 获取提取摘要
        summary = extractor.get_extraction_summary()
        failed_summary = extractor.get_failed_queries_summary()
        
        # 保存结果到session state
        st.session_state.extraction_results = {
            'data': extracted_data,
            'summary': summary,
            'failed_summary': failed_summary,
            'files': {
                'excel': excel_filename,
                'json': json_filename,
                'failed_queries': failed_queries_file
            }
        }
        
        st.session_state.extraction_summary = {
            'total_count': len(resume_queries),
            'successful_extractions': summary.get('successful_extractions', 0),
            'failed_count': failed_summary.get('failed_count', 0) if failed_summary else 0,
            'success_rate': (summary.get('successful_extractions', 0) / len(resume_queries)) * 100 if resume_queries else 0
        }
        
        st.session_state.log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] 简历提取完成！成功提取 {len(extracted_data)} 条数据")
        
        st.success("简历提取完成！")
        
    except Exception as e:
        error_msg = f"提取失败: {str(e)}"
        st.error(error_msg)
        st.session_state.log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")
        
    finally:
        # 停止日志捕获
        logger.stop_capture()
        st.session_state.extraction_running = False
        
        # 获取剩余的日志
        remaining_logs = logger.get_logs()
        st.session_state.log_messages.extend(remaining_logs)

def download_excel(filename):
    """下载Excel文件"""
    try:
        file_path = os.path.join("outputs", filename)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                st.download_button(
                    label="点击下载Excel文件",
                    data=f.read(),
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error("文件不存在")
    except Exception as e:
        st.error(f"下载失败: {str(e)}")

def download_json(filename):
    """下载JSON文件"""
    try:
        file_path = os.path.join("outputs", filename)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                st.download_button(
                    label="点击下载JSON文件",
                    data=f.read(),
                    file_name=filename,
                    mime="application/json"
                )
        else:
            st.error("文件不存在")
    except Exception as e:
        st.error(f"下载失败: {str(e)}")

def download_all_files():
    """下载所有输出文件"""
    try:
        output_dir = "outputs"
        if not os.path.exists(output_dir):
            st.error("输出目录不存在")
            return
        
        # 创建ZIP文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'resume_extraction_{timestamp}.zip'
        zip_path = os.path.join(output_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename in os.listdir(output_dir):
                if filename.endswith(('.xlsx', '.json')):
                    filepath = os.path.join(output_dir, filename)
                    zipf.write(filepath, filename)
        
        # 提供下载
        with open(zip_path, "rb") as f:
            st.download_button(
                label="点击下载所有文件(ZIP)",
                data=f.read(),
                file_name=zip_filename,
                mime="application/zip"
            )
        
        # 删除临时ZIP文件
        os.remove(zip_path)
        
    except Exception as e:
        st.error(f"打包下载失败: {str(e)}")

if __name__ == "__main__":
    main()

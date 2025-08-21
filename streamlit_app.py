import streamlit as st
import pandas as pd
import os
import json
import tempfile
import zipfile
from datetime import datetime
from resume_extractor import ResumeExtractor
from query_loader import QueryLoader
import io

# 页面配置
st.set_page_config(
    page_title="简历信息提取系统",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 初始化session state
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'extraction_results' not in st.session_state:
    st.session_state.extraction_results = None

def main():
    # 主标题
    st.markdown('<h1 class="main-header">📄 简历信息提取系统</h1>', unsafe_allow_html=True)
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 系统配置")
        
        # API配置
        st.subheader("API设置")
        api_key = st.text_input("API密钥", value="d2a7gnen04uuiosfsnk0", type="password")
        base_url = st.text_input("基础URL", value="https://aiagentplatform.cmft.com")
        user_id = st.text_input("用户ID", value="Siga")
        
        # 文件上传设置
        st.subheader("文件设置")
        max_file_size = st.number_input("最大文件大小(MB)", min_value=1, max_value=100, value=16)
        
        st.markdown("---")
        st.markdown("### 📋 支持的文件格式")
        st.markdown("- Excel文件 (.xlsx, .xls)")
        st.markdown("- CSV文件 (.csv)")
        st.markdown("- 文本文件 (.txt)")
        
        st.markdown("---")
        st.markdown("### 🔧 使用说明")
        st.markdown("1. 上传包含查询列表的文件")
        st.markdown("2. 点击开始提取按钮")
        st.markdown("3. 等待处理完成")
        st.markdown("4. 下载结果文件")
    
    # 主界面
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📤 文件上传")
        
        # 文件上传
        uploaded_file = st.file_uploader(
            "选择包含查询列表的文件",
            type=['xlsx', 'xls', 'csv', 'txt'],
            help="支持Excel、CSV和文本格式"
        )
        
        if uploaded_file is not None:
            st.session_state.uploaded_file = uploaded_file
            
            # 显示文件信息
            file_info = {
                "文件名": uploaded_file.name,
                "文件大小": f"{uploaded_file.size / 1024 / 1024:.2f} MB",
                "文件类型": uploaded_file.type
            }
            
            st.json(file_info)
            
            # 预览文件内容
            try:
                if uploaded_file.name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(uploaded_file)
                elif uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    content = uploaded_file.read().decode('utf-8')
                    df = pd.DataFrame({'内容': content.split('\n')})
                
                st.subheader("📋 文件预览")
                st.dataframe(df.head(10), use_container_width=True)
                
                if len(df) > 10:
                    st.info(f"文件共包含 {len(df)} 行数据，仅显示前10行")
                    
            except Exception as e:
                st.error(f"文件预览失败: {str(e)}")
    
    with col2:
        st.header("🚀 操作控制")
        
        if st.session_state.uploaded_file is not None:
            if st.button("开始提取", type="primary", use_container_width=True):
                with st.spinner("正在处理文件..."):
                    try:
                        # 保存上传的文件
                        temp_dir = tempfile.mkdtemp()
                        temp_file_path = os.path.join(temp_dir, st.session_state.uploaded_file.name)
                        
                        with open(temp_file_path, 'wb') as f:
                            f.write(st.session_state.uploaded_file.getbuffer())
                        
                        # 创建简历提取器
                        extractor = ResumeExtractor(api_key, base_url, user_id)
                        query_loader = QueryLoader()
                        
                        # 读取查询列表
                        resume_queries = query_loader.load_queries(temp_file_path)
                        
                        if not resume_queries:
                            st.error("无法从文件中读取查询列表")
                            return
                        
                        # 执行批量提取
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        extracted_data = extractor.batch_extract_resumes(resume_queries)
                        
                        if not extracted_data:
                            st.error("没有成功提取到任何简历数据")
                            return
                        
                        # 生成输出文件名
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        excel_filename = f'resume_data_{timestamp}.xlsx'
                        json_filename = f'resume_data_{timestamp}.json'
                        
                        # 导出文件
                        excel_buffer = io.BytesIO()
                        json_buffer = io.BytesIO()
                        
                        extractor.export_to_excel(excel_buffer)
                        extractor.export_to_json(json_buffer)
                        
                        # 保存失败的查询
                        failed_queries_buffer = None
                        if hasattr(extractor, 'failed_queries') and extractor.failed_queries:
                            failed_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            failed_filename = f'failed_queries_{failed_timestamp}.xlsx'
                            failed_queries_buffer = io.BytesIO()
                            extractor.save_failed_queries(failed_queries_buffer)
                        
                        # 获取摘要信息
                        summary = extractor.get_extraction_summary()
                        failed_summary = extractor.get_failed_queries_summary()
                        
                        # 存储结果
                        st.session_state.extraction_results = {
                            'summary': summary,
                            'failed_summary': failed_summary,
                            'excel_buffer': excel_buffer,
                            'json_buffer': json_buffer,
                            'failed_queries_buffer': failed_queries_buffer,
                            'data_count': len(extracted_data),
                            'excel_filename': excel_filename,
                            'json_filename': json_filename,
                            'failed_filename': failed_filename if failed_queries_buffer else None
                        }
                        
                        st.success("✅ 简历提取完成！")
                        
                    except Exception as e:
                        st.error(f"提取失败: {str(e)}")
                    finally:
                        # 清理临时文件
                        if 'temp_dir' in locals():
                            import shutil
                            shutil.rmtree(temp_dir)
        else:
            st.info("请先上传文件")
    
    # 显示结果
    if st.session_state.extraction_results:
        st.header("📊 提取结果")
        
        results = st.session_state.extraction_results
        
        # 显示摘要
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("✅ 成功提取")
            st.json(results['summary'])
        
        with col2:
            if results['failed_summary']:
                st.subheader("❌ 失败查询")
                st.json(results['failed_summary'])
            else:
                st.subheader("❌ 失败查询")
                st.info("没有失败的查询")
        
        # 下载按钮
        st.subheader("📥 下载结果")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            excel_buffer = results['excel_buffer']
            excel_buffer.seek(0)
            st.download_button(
                label="📊 下载Excel文件",
                data=excel_buffer.getvalue(),
                file_name=results['excel_filename'],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            json_buffer = results['json_buffer']
            json_buffer.seek(0)
            st.download_button(
                label="📄 下载JSON文件",
                data=json_buffer.getvalue(),
                file_name=results['json_filename'],
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            if results['failed_queries_buffer']:
                failed_buffer = results['failed_queries_buffer']
                failed_buffer.seek(0)
                st.download_button(
                    label="⚠️ 下载失败查询",
                    data=failed_buffer.getvalue(),
                    file_name=results['failed_filename'],
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.info("无失败查询")
        
        # 统计信息
        st.subheader("📈 统计信息")
        st.metric("成功提取数量", results['data_count'])
        
        if results['failed_summary']:
            failed_count = results['failed_summary'].get('失败查询数量', 0)
            st.metric("失败查询数量", failed_count)
            st.metric("成功率", f"{results['data_count']/(results['data_count']+failed_count)*100:.1f}%")

if __name__ == "__main__":
    main()

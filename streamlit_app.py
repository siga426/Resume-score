import os
import io
import json
import tempfile
import sys
from datetime import datetime
from typing import List
from contextlib import contextmanager

import streamlit as st
import pandas as pd

from resume_extractor import ResumeExtractor
from query_loader import QueryLoader


# 创建日志捕获器类
class StreamlitLogCapture:
    """捕获print输出并显示在Streamlit界面上的日志捕获器"""
    
    def __init__(self, container):
        self.container = container
        self.original_stdout = sys.stdout
        self.log_buffer = []
        self.max_logs = 200  # 最大日志条数
        
    def write(self, text):
        """重写stdout的write方法"""
        if text.strip():  # 只处理非空文本
            # 保存到原始stdout
            self.original_stdout.write(text)
            self.original_stdout.flush()
            
            # 添加到日志缓冲区
            timestamp = datetime.now().strftime('%H:%M:%S')
            log_entry = f"[{timestamp}] {text.rstrip()}"
            self.log_buffer.append(log_entry)
            
            # 限制日志条数
            if len(self.log_buffer) > self.max_logs:
                self.log_buffer = self.log_buffer[-self.max_logs:]
    
    def flush(self):
        """重写stdout的flush方法"""
        self.original_stdout.flush()
    
    def update_display(self):
        """更新Streamlit日志显示"""
        try:
            # 清空容器并重新显示日志
            self.container.empty()
            with self.container:
                st.subheader("📋 实时执行日志")
                st.caption("显示程序执行过程中的print输出")
                
                # 显示日志内容
                if self.log_buffer:
                    log_text = "\n".join(self.log_buffer)
                    st.code(log_text, language="text")
                    
                    # 显示日志统计信息
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("日志条数", len(self.log_buffer))
                    with col2:
                        if self.log_buffer:
                            last_log_time = self.log_buffer[-1].split(']')[0].replace('[', '')
                            st.metric("最后更新", last_log_time)
                    with col3:
                        st.metric("缓冲区大小", f"{len(self.log_buffer)}/{self.max_logs}")
                    
                    # 添加操作按钮
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("🗑️ 清除日志", key="clear_logs"):
                            self.log_buffer.clear()
                            st.rerun()
                    with col2:
                        if st.button("📥 下载日志", key="download_logs"):
                            log_content = "\n".join(self.log_buffer)
                            st.download_button(
                                "确认下载",
                                log_content,
                                file_name=f"execution_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                mime="text/plain"
                            )
                    with col3:
                        if st.button("🔄 刷新显示", key="refresh_logs"):
                            st.rerun()
                else:
                    st.info("暂无日志输出")
        except Exception as e:
            # 如果更新失败，回退到原始stdout
            self.original_stdout.write(f"日志显示更新失败: {e}\n")
    
    def get_logs(self):
        """获取当前日志内容"""
        return self.log_buffer.copy()


@contextmanager
def capture_logs(container):
    """上下文管理器，用于捕获日志"""
    capture = StreamlitLogCapture(container)
    sys.stdout = capture
    try:
        yield capture
    finally:
        sys.stdout = capture.original_stdout


def get_api_config():
	# 从 Streamlit Secrets 读取 API 配置
	api_key = st.secrets.get('RESUME_API_KEY')
	base_url = st.secrets.get('RESUME_BASE_URL')
	user_id = st.secrets.get('RESUME_USER_ID')
	
	# 检查是否所有配置都已设置
	if not all([api_key, base_url, user_id]):
		st.error('❌ API 配置不完整，请在 Streamlit Cloud 的 Settings → Secrets 中配置以下信息：\n'
				'- RESUME_API_KEY: API 密钥\n'
				'- RESUME_BASE_URL: API 基础 URL\n'
				'- RESUME_USER_ID: 用户 ID')
		st.stop()
	
	return api_key, base_url, user_id


def strip_ext(filename: str) -> str:
	if '.' not in filename:
		return filename
	return '.'.join(filename.split('.')[:-1])


def to_excel_bytes(data: List[dict], sheet_name: str = '简历信息') -> bytes:
	if not data:
		return b''
	df = pd.DataFrame(data)
	output = io.BytesIO()
	with pd.ExcelWriter(output, engine='openpyxl') as writer:
		df.to_excel(writer, index=False, sheet_name=sheet_name)
		ws = writer.sheets[sheet_name]
		for column in ws.columns:
			max_len = 0
			col_letter = column[0].column_letter
			for cell in column:
				try:
					val_len = len(str(cell.value)) if cell.value is not None else 0
					max_len = max(max_len, val_len)
				except Exception:
					pass
			ws.column_dimensions[col_letter].width = min(max_len + 2, 50)
	output.seek(0)
	return output.read()


def to_failed_queries_excel_bytes(failed_queries: List[dict]) -> bytes:
	if not failed_queries:
		return b''
	df = pd.DataFrame(failed_queries)
	output = io.BytesIO()
	with pd.ExcelWriter(output, engine='openpyxl') as writer:
		df.to_excel(writer, index=False, sheet_name='失败查询')
	output.seek(0)
	return output.read()


def main():
	st.set_page_config(page_title='CMSR - 简历信息提取系统', layout='wide')
	st.title('📋 CMSR - 简历信息提取系统')
	st.caption('在云端运行，无需本地部署。支持单文件查询与批量文件名生成查询。')
	
	# 显示系统状态信息
	with st.sidebar:
		st.subheader("🔧 系统状态")
		st.info(f"页面加载时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
		st.success("✅ 日志系统已就绪")
		st.caption("日志系统将实时捕获程序执行过程中的所有print输出")

	# 从 Streamlit Secrets 读取 API 配置（不显示在界面上）
	api_key, base_url, user_id = get_api_config()

	# ——— 模式选择 ———
	mode = st.radio('选择上传模式：', ['📄 单文件模式', '📁 批量文件模式'], horizontal=True)
	
	# 创建日志显示区域
	log_container = st.container()
	
	# 添加日志显示区域
	with st.expander("📋 实时执行日志", expanded=False):
		st.info("日志将在开始提取时显示")
		st.caption("点击展开查看详细的执行日志信息")
	
	queries: List[str] = []

	if mode == '📄 单文件模式':
		st.subheader('📁 上传查询文件（Excel/CSV/TXT）')
		uploaded = st.file_uploader('选择一个包含查询列表的文件：', type=['xlsx', 'xls', 'csv', 'txt'])
		if uploaded is not None:
			# 将上传文件保存到临时文件，再复用现有 QueryLoader 逻辑
			with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded.name.split('.')[-1]}") as tmp:
				tmp.write(uploaded.read())
				tmp_path = tmp.name
			
			loader = QueryLoader()
			queries = loader.load_queries(tmp_path)
			st.success(f'已读取 {len(queries)} 条查询')
			if queries:
				with st.expander('查看查询预览', expanded=False):
					st.write(pd.DataFrame({'查询': queries}))

	else:
		st.subheader('📁 批量文件名生成查询')
		batch_files = st.file_uploader('选择多个任意类型文件：系统仅提取文件名', accept_multiple_files=True)
		if batch_files:
			file_names = [bf.name for bf in batch_files]
			queries = [f"{strip_ext(name)}的简历情况" for name in file_names]
			st.success(f'已从 {len(file_names)} 个文件名生成 {len(queries)} 条查询')
			with st.expander('查看生成的查询', expanded=True):
				st.write(pd.DataFrame({'文件名': file_names, '生成的查询': queries}))

	# ——— 开始提取 ———
	st.divider()
	can_run = bool(queries)
	run = st.button('🚀 开始提取', disabled=not can_run)
	if run:
		# 使用日志捕获器捕获print输出
		with capture_logs(log_container) as log_capture:
			with st.spinner('正在提取简历信息，请稍候...'):
				extractor = ResumeExtractor(api_key, base_url, user_id)
				data = extractor.batch_extract_resumes(queries)
			
			# 执行完成后更新日志显示
			log_capture.update_display()

		if not data:
			st.error('没有成功提取到任何简历数据')
			return

		# 摘要信息
		summary = extractor.get_extraction_summary()
		st.success('提取完成！下面是摘要信息：')
		col1, col2, col3, col4 = st.columns(4)
		col1.metric('总提取数量', summary.get('total_count', 0))
		col2.metric('成功提取', summary.get('successful_extractions', 0))
		col3.metric('不同姓名数', len(summary.get('unique_names', [])))
		col4.metric('学历类型数', len(summary.get('education_levels', [])))

		# 数据预览
		with st.expander('查看提取明细（前100行）', expanded=False):
			st.dataframe(pd.DataFrame(data).head(100), use_container_width=True)

		# 下载区
		st.subheader('📥 下载结果文件')
		excel_bytes = to_excel_bytes(data, sheet_name='简历信息')
		json_str = json.dumps(data, ensure_ascii=False, indent=2)
		st.download_button('📊 下载Excel', data=excel_bytes, file_name=f"resume_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
		st.download_button('📄 下载JSON', data=json_str.encode('utf-8'), file_name=f"resume_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime='application/json')

		# 失败查询
		failed = getattr(extractor, 'failed_queries', [])
		if failed:
			st.warning(f'有 {len(failed)} 条查询失败，可下载明细。')
			failed_bytes = to_failed_queries_excel_bytes(failed)
			st.download_button('⚠️ 下载失败查询（Excel）', data=failed_bytes, file_name=f"failed_queries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
	main()

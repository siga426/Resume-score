import os
import io
import json
import tempfile
import sys
import time
from datetime import datetime
from typing import List, Dict

import streamlit as st
import pandas as pd

from resume_extractor import ResumeExtractor
from query_loader import QueryLoader


# 创建字符串字典存储所有print输出
class PrintOutputCollector:
	"""收集所有print输出并存储到字典中"""
	
	def __init__(self):
		self.original_stdout = sys.stdout
		self.output_dict = {}
		self.current_key = None
		self.current_output = []
	
	def write(self, text):
		"""重写stdout的write方法"""
		if text.strip():
			# 保存到原始stdout
			self.original_stdout.write(text)
			self.original_stdout.flush()
			
			# 添加到当前输出列表
			if self.current_key:
				self.current_output.append(text.rstrip())
	
	def flush(self):
		"""重写stdout的flush方法"""
		self.original_stdout.flush()
	
	def start_collecting(self, key: str):
		"""开始收集指定键的输出"""
		self.current_key = key
		self.current_output = []
	
	def stop_collecting(self):
		"""停止收集并保存到字典"""
		if self.current_key and self.current_output:
			self.output_dict[self.current_key] = '\n'.join(self.current_output)
		self.current_key = None
		self.current_output = []
	
	def get_all_outputs(self) -> Dict[str, str]:
		"""获取所有收集的输出"""
		return self.output_dict.copy()
	
	def clear_outputs(self):
		"""清空所有输出"""
		self.output_dict.clear()


# 全局输出收集器
output_collector = PrintOutputCollector()


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


def simulate_streaming_output(text: str, container, delay: float = 0.05):
	"""模拟流式输出效果"""
	if not text:
		return
	
	# 清空容器
	container.empty()
	
	# 逐字输出
	current_text = ""
	for char in text:
		current_text += char
		with container:
			st.code(current_text, language="text")
		time.sleep(delay)
	
	# 最终显示完整文本
	with container:
		st.code(text, language="text")


def main():
	st.set_page_config(page_title='CMSR - 简历信息提取系统', layout='wide')
	st.title('📋 CMSR - 简历信息提取系统')
	st.caption('在云端运行，无需本地部署。支持单文件查询与批量文件名生成查询。')
	
	# 初始化会话状态
	if 'extraction_data' not in st.session_state:
		st.session_state.extraction_data = None
	if 'extraction_summary' not in st.session_state:
		st.session_state.extraction_summary = None
	if 'outputs' not in st.session_state:
		st.session_state.outputs = {}
	if 'error_message' not in st.session_state:
		st.session_state.error_message = None
	
	# 从 Streamlit Secrets 读取 API 配置（不显示在界面上）
	api_key, base_url, user_id = get_api_config()

	# ——— 模式选择 ———
	mode = st.radio('选择上传模式：', ['📄 单文件模式', '📁 批量文件模式'], horizontal=True)
	
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
		st.info("🚀 开始执行简历提取任务...")
		
		# 显示执行进度
		progress_bar = st.progress(0)
		status_text = st.empty()
		
		# 每次运行前清空旧结果
		st.session_state.extraction_data = None
		st.session_state.extraction_summary = None
		st.session_state.outputs = {}
		st.session_state.error_message = None
		
		# 重定向stdout到收集器并执行
		started_collect = False
		try:
			sys.stdout = output_collector
			output_collector.start_collecting("resume_extraction")
			started_collect = True
			
			with st.spinner('正在提取简历信息，请稍候...'):
				extractor = ResumeExtractor(api_key, base_url, user_id)
				data = extractor.batch_extract_resumes(queries)
				# 保存结果到会话
				st.session_state.extraction_data = data
				st.session_state.extraction_summary = extractor.get_extraction_summary()
		finally:
			# 停止收集并恢复stdout
			try:
				if started_collect:
					output_collector.stop_collecting()
				st.session_state.outputs = output_collector.get_all_outputs()
			except Exception:
				pass
			finally:
				sys.stdout = output_collector.original_stdout
		
		# 更新进度条
		progress_bar.progress(100)
		status_text.success("✅ 简历提取任务完成！")

	# ——— 持久化结果显示（避免按钮触发后的重跑导致内容消失） ———
	if st.session_state.extraction_data:
		data = st.session_state.extraction_data
		summary = st.session_state.extraction_summary or {}
		st.success('提取完成！下面是摘要信息：')
		col1, col2, col3, col4 = st.columns(4)
		col1.metric('总提取数量', summary.get('total_count', 0))
		col2.metric('成功提取', summary.get('successful_extractions', 0))
		col3.metric('不同姓名数', len(summary.get('unique_names', []) or []))
		col4.metric('学历类型数', len(summary.get('education_levels', []) or []))

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
		failed = getattr(ResumeExtractor, '__unused__', None)  # 占位，避免未定义
		failed = getattr(extractor, 'failed_queries', []) if 'extractor' in locals() else []
		if failed:
			st.warning(f'有 {len(failed)} 条查询失败，可下载明细。')
			failed_bytes = to_failed_queries_excel_bytes(failed)
			st.download_button('⚠️ 下载失败查询（Excel）', data=failed_bytes, file_name=f"failed_queries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

	# ——— 流式输出显示区域 ———
	all_outputs_state = st.session_state.outputs or output_collector.get_all_outputs()
	if all_outputs_state:
		st.divider()
		st.subheader("📺 程序输出流式显示")
		st.caption("显示程序执行过程中的所有print输出，模拟流式输出效果")
		
		# 创建流式输出容器
		streaming_container = st.container()
		
		# 显示输出键列表
		output_key = st.selectbox(
			"选择要显示的输出：",
			options=list(all_outputs_state.keys()),
			index=0
		)
		
		selected_output = all_outputs_state[output_key]
		
		# 控制按钮
		col1, col2, col3 = st.columns(3)
		with col1:
			if st.button("🎬 开始流式播放", key="start_streaming"):
				simulate_streaming_output(selected_output, streaming_container, delay=0.03)
		with col2:
			if st.button("⏸️ 暂停/继续", key="pause_streaming"):
				st.info("流式播放已暂停")
		with col3:
			if st.button("🗑️ 清空输出", key="clear_outputs"):
				output_collector.clear_outputs()
				st.session_state.outputs = {}
				st.rerun()
		
		# 显示完整输出
		with st.expander("📋 查看完整输出", expanded=False):
			st.code(selected_output, language="text")
		
		# 下载输出
		if st.button("📥 下载输出内容", key="download_output"):
			st.download_button(
				"确认下载",
				selected_output,
				file_name=f"program_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
				mime="text/plain"
			)


if __name__ == '__main__':
	main()

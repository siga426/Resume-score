import os
import io
import json
import tempfile
from datetime import datetime
from typing import List

import streamlit as st
import pandas as pd

from resume_extractor import ResumeExtractor
from resume_scorer import ResumeScorer
from query_loader import QueryLoader


def get_api_config():
	# 优先从 Streamlit Secrets 读取
	api_key = st.secrets.get('RESUME_API_KEY') if hasattr(st, 'secrets') else None
	base_url = st.secrets.get('RESUME_BASE_URL') if hasattr(st, 'secrets') else None
	user_id = st.secrets.get('RESUME_USER_ID') if hasattr(st, 'secrets') else None
	
	# 兜底：从环境变量读取
	if not api_key:
		api_key = os.getenv('RESUME_API_KEY')
	if not base_url:
		base_url = os.getenv('RESUME_BASE_URL')
	if not user_id:
		user_id = os.getenv('RESUME_USER_ID')
	
	# 最后兜底：给出清晰提示
	if not all([api_key, base_url, user_id]):
		st.error('❌ 未找到 API 配置。请按以下任一方式配置：\n\n'
				'1) 在项目根目录创建 .streamlit/secrets.toml 并填写：\n'
				'   RESUME_API_KEY = "你的API密钥"\n'
				'   RESUME_BASE_URL = "https://aiagentplatform.cmft.com"\n'
				'   RESUME_USER_ID = "Siga"\n\n'
				'2) 在系统环境变量中设置相同的键（RESUME_API_KEY/RESUME_BASE_URL/RESUME_USER_ID）。')
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

	# —— 初始化会话状态 ——
	if 'queries' not in st.session_state:
		st.session_state.queries = []
	if 'data' not in st.session_state:
		st.session_state.data = []
	if 'score_data' not in st.session_state:
		st.session_state.score_data = []
	if 'failed' not in st.session_state:
		st.session_state.failed = []
	if 'ran' not in st.session_state:
		st.session_state.ran = False

	# 从 Streamlit Secrets 读取 API 配置（不显示在界面上）
	api_key, base_url, user_id = get_api_config()

	# ——— 模式选择 ———
	mode = st.radio('选择上传模式：', ['📄 单文件模式', '📁 批量文件模式'], horizontal=True)

	queries: List[str] = st.session_state.queries

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
			st.session_state.queries = queries
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
			st.session_state.queries = queries
			st.success(f'已从 {len(file_names)} 个文件名生成 {len(queries)} 条查询')
			with st.expander('查看生成的查询', expanded=True):
				st.write(pd.DataFrame({'文件名': file_names, '生成的查询': queries}))

	# ——— 开始提取 ———
	st.divider()
	can_run = bool(st.session_state.queries)
	run = st.button('🚀 开始提取', disabled=not can_run)
	if run:
		with st.spinner('正在提取简历信息，请稍候...'):
			try:
				# 避免使用过期对话ID：删除本地对话缓存文件
				if os.path.exists('conversation_id.json'):
					os.remove('conversation_id.json')
				if os.path.exists('conversation_id_score.json'):
					os.remove('conversation_id_score.json')

				# —— 简历信息提取（带进度）——
				extractor = ResumeExtractor(api_key, base_url, user_id)
				# 创建或加载对话ID
				try:
					extractor.chat_api.create_or_load_conversation(use_existing=False)  # 强制创建新对话
					st.success("✅ 简历提取对话创建成功")
				except Exception as e:
					st.error(f"❌ 简历提取对话创建失败: {e}")
					st.stop()
				
				progress = st.progress(0)
				status_text = st.empty()
				total = len(st.session_state.queries)
				results = []
				failed = []
				for idx, q in enumerate(st.session_state.queries, start=1):
					status_text.info(f'提取简历信息 {idx}/{total}：{q[:80]}')
					try:
						info = extractor.process_resume_query(q)
						if info:
							# 处理列表类型的字段，转换为字符串
							processed_info = {}
							for key, value in info.items():
								if isinstance(value, list):
									processed_info[key] = '; '.join(str(item) for item in value)
								else:
									processed_info[key] = str(value) if value is not None else ""
							results.append(processed_info)
						else:
							failed.append({'序号': idx, '查询内容': q, '失败时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '失败原因': '提取失败或无返回数据'})
					except Exception as e:
						failed.append({'序号': idx, '查询内容': q, '失败时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '失败原因': f'处理异常: {str(e)}'})
					progress.progress(int(idx * 100 / max(total, 1)))

				# —— 简历评分（带进度）——
				score_api_key = 'd2jdmq16ht5pktrs7a10'
				scorer = ResumeScorer(score_api_key, base_url, user_id)
				# 创建或加载评分对话ID
				try:
					scorer.chat_api.create_or_load_conversation(use_existing=False)  # 强制创建新对话
					st.success("✅ 简历评分对话创建成功")
				except Exception as e:
					st.warning(f"⚠️ 简历评分对话创建失败: {e}，将跳过评分步骤")
					score_data = []
				else:
					def to_score_query(q: str) -> str:
						base = str(q).strip()
						for suf in ['的简历信息', '的简历情况', '的简历']:
							if base.endswith(suf):
								base = base[:-len(suf)]
								break
						return base + '的简历评分'
					
					score_data = []
					try:
						for idx, q in enumerate(st.session_state.queries, start=1):
							status_text.info(f'获取评分 {idx}/{total}：{q[:80]}')
							try:
								info = scorer.process_score_query(to_score_query(q))
								if info:
									# 处理列表类型的字段，转换为字符串
									processed_info = {}
									for key, value in info.items():
										if isinstance(value, list):
											processed_info[key] = '; '.join(str(item) for item in value)
										else:
											processed_info[key] = str(value) if value is not None else ""
									score_data.append(processed_info)
							except Exception as e:
								st.warning(f'第{idx}条评分查询失败: {e}')
								continue
							progress.progress(int(idx * 100 / max(total, 1)))
					except Exception as e:
						st.warning(f'评分调用失败：{e}，将不显示评分数据。')
						score_data = []

				# 保存结果到会话状态
				st.session_state.data = results
				st.session_state.score_data = score_data
				st.session_state.failed = failed
				st.session_state.ran = True
				status_text.success('处理完成 ✅')
			except Exception as e:
				st.error(f'提取失败：{e}\n请检查 API Key 是否有效、网络是否可访问，以及查询数量是否过大。')
				st.stop()

		if not st.session_state.data:
			st.error('没有成功提取到任何简历数据')
			return

	# —— 显示历史结果（即使页面因交互重跑也保留）——
	if st.session_state.ran and st.session_state.data:
		# 重新构造 extractor 以便使用现有摘要方法
		extractor = ResumeExtractor(api_key, base_url, user_id)
		extractor.extracted_data = st.session_state.data
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
			st.dataframe(pd.DataFrame(st.session_state.data).head(100), use_container_width=True)
		with st.expander('查看评分明细（前100行）', expanded=False):
			st.dataframe(pd.DataFrame(st.session_state.score_data).head(100), use_container_width=True)

		# 下载区
		st.subheader('📥 下载结果文件')
		# 合并两个Sheet导出
		combined_output = io.BytesIO()
		with pd.ExcelWriter(combined_output, engine='openpyxl') as writer:
			pd.DataFrame(st.session_state.data).to_excel(writer, index=False, sheet_name='简历信息')
			pd.DataFrame(st.session_state.score_data).to_excel(writer, index=False, sheet_name='简历评分')
		combined_output.seek(0)
		st.download_button('📒 下载合并Excel（含评分）', data=combined_output.read(), file_name=f"resume_with_scores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
		# 分别导出
		excel_bytes = to_excel_bytes(st.session_state.data, sheet_name='简历信息')
		json_str = json.dumps(st.session_state.data, ensure_ascii=False, indent=2)
		scores_json_str = json.dumps(st.session_state.score_data, ensure_ascii=False, indent=2)
		st.download_button('📊 下载简历Excel', data=excel_bytes, file_name=f"resume_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
		st.download_button('📄 下载简历JSON', data=json_str.encode('utf-8'), file_name=f"resume_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime='application/json')
		st.download_button('🏷️ 下载评分JSON', data=scores_json_str.encode('utf-8'), file_name=f"resume_scores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime='application/json')

		# 失败查询
		failed = st.session_state.failed
		if failed:
			st.warning(f'有 {len(failed)} 条查询失败，可下载明细。')
			failed_bytes = to_failed_queries_excel_bytes(failed)
			st.download_button('⚠️ 下载失败查询（Excel）', data=failed_bytes, file_name=f"failed_queries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
	main()

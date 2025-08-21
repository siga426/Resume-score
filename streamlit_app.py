import os
import io
import json
import zipfile
import tempfile
from datetime import datetime
from typing import List, Tuple

import streamlit as st
import pandas as pd

from resume_extractor import ResumeExtractor
from resume_scorer import ResumeScorer
from query_loader import QueryLoader


def get_api_config_from_secrets() -> Tuple[str, str, str]:
	api_key = st.secrets.get('RESUME_API_KEY') or st.secrets.get('API_KEY')
	base_url = st.secrets.get('RESUME_BASE_URL') or st.secrets.get('BASE_URL')
	user_id = st.secrets.get('RESUME_USER_ID') or st.secrets.get('USER_ID')
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


def build_zip_bytes(files: List[Tuple[str, bytes]]) -> bytes:
	buf = io.BytesIO()
	with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
		for name, data in files:
			zf.writestr(name, data)
	buf.seek(0)
	return buf.read()


def main():
	st.set_page_config(page_title='CMSR - 简历信息提取系统', layout='wide')
	st.title('📋 CMSR - 简历信息提取系统')

	# ——— 侧边栏：API 配置（支持 Secrets 默认 + 手动覆盖） ———
	with st.sidebar:
		st.subheader('⚙️ API 配置')
		secret_api_key, secret_base_url, secret_user_id = get_api_config_from_secrets()
		api_key = st.text_input('RESUME_API_KEY', value=secret_api_key or '', type='password')
		base_url = st.text_input('RESUME_BASE_URL', value=secret_base_url or 'https://aiagentplatform.cmft.com')
		user_id = st.text_input('RESUME_USER_ID', value=secret_user_id or 'Siga')
		st.caption('可在侧边栏直接覆盖，或在 Streamlit Secrets 中配置。')

		st.markdown('---')
		st.subheader('📌 使用提示')
		st.markdown('- 支持 Excel/CSV/TXT 三种输入方式')
		st.markdown('- 也可从文件名快速生成查询或手动粘贴查询')
		st.markdown('- 处理完成后可下载合并Excel、JSON、评分JSON、失败查询与ZIP')

	# ——— 模式选择 ———
	mode = st.radio('选择模式：', ['📄 单文件上传', '📁 从文件名生成', '📝 手动批量输入'], horizontal=True)

	queries: List[str] = []

	if mode == '📄 单文件上传':
		st.subheader('📁 上传查询文件（Excel/CSV/TXT）')
		uploaded = st.file_uploader('选择一个包含查询列表的文件：', type=['xlsx', 'xls', 'csv', 'txt'])
		if uploaded is not None:
			with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded.name.split('.')[-1]}") as tmp:
				tmp.write(uploaded.read())
				tmp_path = tmp.name
			loader = QueryLoader()
			queries = loader.load_queries(tmp_path)
			st.success(f'已读取 {len(queries)} 条查询')
			if queries:
				with st.expander('查看查询预览', expanded=False):
					st.write(pd.DataFrame({'查询': queries}))

	elif mode == '📁 从文件名生成':
		st.subheader('📁 选择多个文件，系统将基于文件名生成查询')
		batch_files = st.file_uploader('选择多个任意类型文件：仅提取文件名', accept_multiple_files=True)
		if batch_files:
			file_names = [bf.name for bf in batch_files]
			queries = [f"{strip_ext(name)}的简历情况" for name in file_names]
			st.success(f'已从 {len(file_names)} 个文件名生成 {len(queries)} 条查询')
			with st.expander('查看生成的查询', expanded=True):
				st.write(pd.DataFrame({'文件名': file_names, '生成的查询': queries}))

	else:
		st.subheader('📝 手动粘贴批量查询（每行一个）')
		text = st.text_area('在此粘贴或输入，每行一个查询（自动补齐“的简历情况/简历信息”后缀）', height=200)
		if text.strip():
			raw = [ln.strip() for ln in text.split('\n') if ln.strip()]
			queries = []
			for q in raw:
				if q.endswith('的简历信息') or q.endswith('的简历情况'):
					queries.append(q)
				else:
					queries.append(q + '的简历信息')
			st.success(f'共收集 {len(queries)} 条查询')
			with st.expander('查询列表', expanded=False):
				st.write(pd.DataFrame({'查询': queries}))
			# 生成可下载的TXT
			if queries:
				txt_buf = io.StringIO('\n'.join(queries))
				st.download_button('📝 下载查询TXT', data=txt_buf.getvalue().encode('utf-8'), file_name=f"batch_queries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", mime='text/plain')

	st.divider()
	can_run = bool(queries) and all([api_key, base_url, user_id])
	col_run, col_progress = st.columns([1, 3])
	with col_run:
		run = st.button('🚀 开始提取与评分', disabled=not can_run)
	with col_progress:
		progress_ex = st.progress(0, text='等待开始...')
		progress_sc = st.progress(0, text='等待开始...')

	if run:
		# 提取：逐条更新进度（复用同一对话）
		extractor = ResumeExtractor(api_key, base_url, user_id)
		extractor.chat_api.create_or_load_conversation(use_existing=True)
		results = []
		failed = []
		for idx, q in enumerate(queries, 1):
			info = extractor.process_resume_query(q)
			if info:
				results.append(info)
			else:
				failed.append({
					'序号': idx,
					'查询内容': q,
					'失败时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
					'失败原因': '提取失败或无返回数据或所有字段为空'
				})
			progress_ex.progress(int(idx * 100 / len(queries)), text=f'提取进度：{idx}/{len(queries)}')
		extractor.extracted_data = results
		extractor.failed_queries = failed

		# 评分：带兜底
		score_api_key = 'd2jdmq16ht5pktrs7a10'
		scorer = ResumeScorer(score_api_key, base_url, user_id)
		scorer.chat_api.create_or_load_conversation(use_existing=True)
		def to_score_query(q: str) -> str:
			base = str(q).strip()
			for suf in ['的简历信息', '的简历情况', '的简历']:
				if base.endswith(suf):
					base = base[:-len(suf)]
					break
			return base + '的简历评分'
		score_queries = [to_score_query(q) for q in queries]
		score_data = []
		score_error = None
		for idx, q in enumerate(score_queries, 1):
			try:
				info = scorer.process_score_query(q)
			except Exception as e:
				info = None
			if info is None:
				# 兜底使用简历APIKey
				try:
					scorer_fb = ResumeScorer(api_key, base_url, user_id)
					scorer_fb.chat_api.create_or_load_conversation(use_existing=True)
					info = scorer_fb.process_score_query(q)
					score_error = '评分APIKey无效，已使用简历APIKey兜底'
				except Exception as e2:
					score_error = f'评分调用失败: {e2}'
			if info:
				score_data.append(info)
			progress_sc.progress(int(idx * 100 / len(score_queries)), text=f'评分进度：{idx}/{len(score_queries)}')

		if not results:
			st.error('没有成功提取到任何简历数据')
			return

		# 摘要信息
		summary = extractor.get_extraction_summary()
		st.success('处理完成！下面是摘要信息：')
		col1, col2, col3, col4 = st.columns(4)
		col1.metric('总提取数量', summary.get('total_count', 0))
		col2.metric('成功提取', summary.get('successful_extractions', 0))
		col3.metric('不同姓名数', len(summary.get('unique_names', [])))
		col4.metric('学历类型数', len(summary.get('education_levels', [])))

		with st.expander('查看提取明细（前100行）', expanded=False):
			st.dataframe(pd.DataFrame(results).head(100), use_container_width=True)
		with st.expander('查看评分明细（前100行）', expanded=False):
			st.dataframe(pd.DataFrame(score_data).head(100), use_container_width=True)
		if score_error:
			st.info(f'评分提示：{score_error}')

		# 导出与下载
		st.subheader('📥 下载结果文件')
		timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
		combined_output = io.BytesIO()
		with pd.ExcelWriter(combined_output, engine='openpyxl') as writer:
			pd.DataFrame(results).to_excel(writer, index=False, sheet_name='简历信息')
			if score_data:
				pd.DataFrame(score_data).to_excel(writer, index=False, sheet_name='简历评分')
		combined_output.seek(0)
		st.download_button('📒 下载合并Excel（含评分）', data=combined_output.read(), file_name=f"resume_with_scores_{timestamp}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

		excel_bytes = to_excel_bytes(results, sheet_name='简历信息')
		json_bytes = json.dumps(results, ensure_ascii=False, indent=2).encode('utf-8')
		scores_json_bytes = json.dumps(score_data, ensure_ascii=False, indent=2).encode('utf-8') if score_data else b'[]'
		st.download_button('📊 下载简历Excel', data=excel_bytes, file_name=f"resume_data_{timestamp}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
		st.download_button('📄 下载简历JSON', data=json_bytes, file_name=f"resume_data_{timestamp}.json", mime='application/json')
		if score_data:
			st.download_button('🏷️ 下载评分JSON', data=scores_json_bytes, file_name=f"resume_scores_{timestamp}.json", mime='application/json')

		failed = getattr(extractor, 'failed_queries', [])
		failed_bytes = to_failed_queries_excel_bytes(failed) if failed else None
		if failed_bytes:
			st.download_button('⚠️ 下载失败查询（Excel）', data=failed_bytes, file_name=f"failed_queries_{timestamp}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

		# 打包下载 ZIP（对齐 /download-all）
		files_for_zip: List[Tuple[str, bytes]] = [
			(f'resume_with_scores_{timestamp}.xlsx', combined_output.getvalue()),
			(f'resume_data_{timestamp}.xlsx', excel_bytes),
			(f'resume_data_{timestamp}.json', json_bytes)
		]
		if score_data:
			files_for_zip.append((f'resume_scores_{timestamp}.json', scores_json_bytes))
		if failed_bytes:
			files_for_zip.append((f'failed_queries_{timestamp}.xlsx', failed_bytes))
		zip_bytes = build_zip_bytes(files_for_zip)
		st.download_button('🗜️ 下载全部（ZIP）', data=zip_bytes, file_name=f"resume_extraction_{timestamp}.zip", mime='application/zip')

		# 状态面板（对齐 /status）
		st.subheader('📊 状态面板')
		st.write({
			'upload_count': len(queries),
			'output_count': len(files_for_zip),
			'upload_files': ['(内存数据)'],
			'output_files': [name for name, _ in files_for_zip]
		})


if __name__ == '__main__':
	main()

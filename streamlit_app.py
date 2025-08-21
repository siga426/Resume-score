import os
import io
import json
import zipfile
import tempfile
import contextlib
from datetime import datetime
from typing import List, Tuple

import streamlit as st
import pandas as pd

from resume_extractor import ResumeExtractor
from resume_scorer import ResumeScorer
from query_loader import QueryLoader

# 硬编码API配置（按你的要求）
EXTRACT_API_KEY = 'd2a7gnen04uuiosfsnk0'
SCORE_API_KEY_HARDCODED = 'd2ji4jh6ht5pktrvmql0'
BASE_URL = 'https://aiagentplatform.cmft.com'
USER_ID = 'Siga'

# 运行时检查第三方平台SDK是否可用，给出更友好的提示
try:
    import aiagentplatformpy  # type: ignore
    _HAS_AIA = True
except Exception:
    _HAS_AIA = False


def get_api_config_from_secrets() -> Tuple[str, str, str]:
	# 改为返回硬编码配置，不再从 Secrets 读取
	return EXTRACT_API_KEY, BASE_URL, USER_ID


def get_score_key_from_secrets() -> str:
	# 改为返回硬编码的评分 Key，不再从 Secrets 读取
	return SCORE_API_KEY_HARDCODED


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

	# ——— 主界面配置信息 ———
	st.subheader('⚙️ 运行配置（代码内写死）')
	api_key, base_url, user_id = get_api_config_from_secrets()
	score_api_key_input = get_score_key_from_secrets()
	st.caption('本应用不使用 Secrets。')

	if not _HAS_AIA:
		st.warning('未检测到 aiagentplatformpy。若为私有库，云端无法直接安装，请使用带该库的自定义环境或私有包镜像；或联系管理员提供公共可安装版本。')

	st.markdown('---')
	st.subheader('📌 使用提示')
	st.markdown('- 支持 Excel/CSV/TXT 三种输入方式')
	st.markdown('- 也可从文件名快速生成查询或手动粘贴查询')
	st.markdown('- 处理完成后可下载合并Excel（信息+评分）、单独Excel、JSON、失败查询与ZIP')

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
			extract_queries = [f"{strip_ext(name)}的简历情况" for name in file_names]
			score_queries = [f"{strip_ext(name)}的简历评分" for name in file_names]
			queries = extract_queries  # 用于提取的查询
			st.success(f'已从 {len(file_names)} 个文件名生成 {len(queries)} 条查询')
			with st.expander('查看生成的查询', expanded=True):
				st.write(pd.DataFrame({
					'文件名': file_names, 
					'提取查询': extract_queries,
					'评分查询': score_queries
				}))

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
	can_run = bool(queries)
	run = st.button('🚀 开始提取与评分', disabled=not can_run)

	# 使用 session_state 保存阶段性结果
	if 'extracted_results' not in st.session_state:
		st.session_state.extracted_results = None
	if 'extracted_failed' not in st.session_state:
		st.session_state.extracted_failed = None
	if 'score_results' not in st.session_state:
		st.session_state.score_results = None
	if 'score_error' not in st.session_state:
		st.session_state.score_error = None
	# 初始化日志存储并常驻显示日志区域（运行结束后仍可见）
	if 'extract_logs' not in st.session_state:
		st.session_state.extract_logs = []
	if 'score_logs' not in st.session_state:
		st.session_state.score_logs = []

	# 常驻日志区域（默认展开，显示当前 session_state 日志）
	# 提取进度条
	ex_progress_placeholder = st.empty()
	
	ex_log_expander = st.expander('📜 提取日志', expanded=True)
	with ex_log_expander:
		# 显示已有的提取日志
		if st.session_state.extract_logs:
			st.text_area(
				label='提取日志内容',
				value=''.join(st.session_state.extract_logs),
				height=200,
				disabled=True,
				key='extract_log_display'
			)
		ex_log_placeholder = st.empty()

	# 评分进度条
	sc_progress_placeholder = st.empty()
	
	sc_expander = st.expander('📜 评分日志', expanded=True)
	with sc_expander:
		# 显示已有的评分日志
		if st.session_state.score_logs:
			st.text_area(
				label='评分日志内容',
				value=''.join(st.session_state.score_logs),
				height=200,
				disabled=True,
				key='score_log_display'
			)
		sc_placeholder = st.empty()

	# 提取流程与评分流程（合并按钮顺序执行）
	if run:
		with ex_progress_placeholder:
			progress_ex = st.progress(0, text='提取开始...')
		# 初始化/清空提取日志
		st.session_state['extract_logs'] = []

		class StreamlitAppendWriter(io.StringIO):
			def write(self, s: str):
				if not s:
					return
				st.session_state['extract_logs'].append(s)
				# 更新固定的日志显示区域
				ex_log_placeholder.text_area(
					label='实时提取日志',
					value=''.join(st.session_state['extract_logs']),
					height=200,
					disabled=True,
					key=f'extract_log_realtime_{len(st.session_state["extract_logs"])}'  # 动态key
				)

		extractor = ResumeExtractor(api_key, base_url, user_id)
		# 复用提取会话ID
		if st.session_state.get('extract_conversation_id'):
			extractor.chat_api.conversation_id = st.session_state['extract_conversation_id']
		else:
			conv_id = extractor.chat_api.create_or_load_conversation(use_existing=True)
			st.session_state['extract_conversation_id'] = conv_id
		results = []
		failed = []
		with contextlib.redirect_stdout(StreamlitAppendWriter()):
			for idx, q in enumerate(queries, 1):
				print(f"\n=== 处理第{idx}个简历查询 ===")
				print(f"查询: {q}")
				info = extractor.process_resume_query(q)
				if info:
					print("✅ 成功提取简历信息")
					results.append(info)
				else:
					print("❌ 提取简历信息失败")
					failed.append({
						'序号': idx,
						'查询内容': q,
						'失败时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
						'失败原因': '提取失败或无返回数据或所有字段为空'
					})
				progress_ex.progress(int(idx * 100 / len(queries)), text=f'提取进度：{idx}/{len(queries)}')
		st.session_state.extracted_results = results
		st.session_state.extracted_failed = failed

	# 评分流程
	if run:
		with sc_progress_placeholder:
			progress_sc = st.progress(0, text='评分开始...')
		# 初始化/清空评分日志
		st.session_state['score_logs'] = []

		class StreamlitScoreWriter(io.StringIO):
			def write(self, s: str):
				if not s:
					return
				st.session_state['score_logs'].append(s)
				# 更新固定的日志显示区域
				sc_placeholder.text_area(
					label='实时评分日志',
					value=''.join(st.session_state['score_logs']),
					height=200,
					disabled=True,
					key=f'score_log_realtime_{len(st.session_state["score_logs"])}'  # 动态key
				)

		# 仅使用评分Key，不使用兜底
		use_key = score_api_key_input
		scorer = ResumeScorer(use_key, base_url, user_id)
		# 复用评分会话ID
		if st.session_state.get('score_conversation_id'):
			scorer.chat_api.conversation_id = st.session_state['score_conversation_id']
		else:
			conv_id = scorer.chat_api.create_or_load_conversation(use_existing=True)
			st.session_state['score_conversation_id'] = conv_id
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
		with contextlib.redirect_stdout(StreamlitScoreWriter()):
			for idx, q in enumerate(score_queries, 1):
				print(f"\n=== 处理第{idx}个评分查询 ===")
				print(f"查询: {q}")
				try:
					info = scorer.process_score_query(q)
					if info:
						print("✅ 成功获取评分")
					else:
						print("❌ 评分返回空数据")
				except Exception as e:
					info = None
					score_error = f'评分调用失败: {e}'
					print(f"❌ 评分异常: {e}")
				if info is None and score_error is None:
					score_error = '评分调用失败或无返回数据'
				if info:
					score_data.append(info)
				progress_sc.progress(int(idx * 100 / len(score_queries)), text=f'评分进度：{idx}/{len(score_queries)}')
		st.session_state.score_results = score_data
		st.session_state.score_error = score_error

	# 展示提取结果
	if st.session_state.extracted_results is not None:
		results = st.session_state.extracted_results
		failed = st.session_state.extracted_failed or []
		if not results:
			st.error('没有成功提取到任何简历数据')
		else:
			extractor_tmp = ResumeExtractor(api_key, base_url, user_id)
			extractor_tmp.extracted_data = results
			meta = extractor_tmp.get_extraction_summary()
			st.success('提取完成！')
			col1, col2, col3, col4 = st.columns(4)
			col1.metric('总提取数量', meta.get('total_count', 0))
			col2.metric('成功提取', meta.get('successful_extractions', 0))
			col3.metric('不同姓名数', len(meta.get('unique_names', [])))
			col4.metric('学历类型数', len(meta.get('education_levels', [])))
			with st.expander('查看提取明细（前100行）', expanded=False):
				st.dataframe(pd.DataFrame(results).head(100), use_container_width=True)
			# 下载提取结果
			st.subheader('📥 下载提取结果')
			ts = datetime.now().strftime('%Y%m%d_%H%M%S')
			excel_bytes = to_excel_bytes(results, sheet_name='简历信息')
			st.download_button('📊 下载简历Excel', data=excel_bytes, file_name=f"resume_data_{ts}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
			if failed:
				failed_bytes = to_failed_queries_excel_bytes(failed)
				st.download_button('⚠️ 下载失败查询（Excel）', data=failed_bytes, file_name=f"failed_queries_{ts}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

	# 展示评分结果
	if st.session_state.score_results is not None:
		score_data = st.session_state.score_results
		score_error = st.session_state.score_error
		if score_error:
			st.info(f'评分提示：{score_error}')
		if score_data:
			# 按总得分从高到低排序
			df_scores = pd.DataFrame(score_data)
			if '总得分' in df_scores.columns:
				df_scores_sorted = df_scores.sort_values('总得分', ascending=False)
				st.success(f'评分完成！共 {len(score_data)} 条评分数据')
				
				# 提取文件名并重新排列列顺序
				if '评分查询' in df_scores_sorted.columns:
					# 从评分查询中提取文件名
					def extract_filename(query):
						if pd.isna(query) or not query:
							return ''
						# 移除"的简历评分"后缀
						query_str = str(query).strip()
						if query_str.endswith('的简历评分'):
							return query_str[:-5]  # 移除"的简历评分"
						return query_str
					
					df_scores_sorted['姓名'] = df_scores_sorted['评分查询'].apply(extract_filename)
				
				# 重新排列列顺序：文件名、总分、其他得分项
				score_columns = list(df_scores_sorted.columns)
				ordered_columns = []
				
				# 第一列：文件名
				if '姓名' in score_columns:
					ordered_columns.append('姓名')
				
				# 第二列：总分
				if '总得分' in score_columns:
					ordered_columns.append('总得分')
				
				# 其他得分列（按顺序）
				score_fields = [
					'本科院校分', '硕士院校分', '本科专业符合度分', '硕士专业符合度分', 
					'交叉学科分', '学习成绩分', '英语水平分', '编程技能分', 
					'项目实习经历分', '学生工作分', '掌握CAD类软件加分', 'AVEVA Marine软件加分'
				]
				for field in score_fields:
					if field in score_columns:
						ordered_columns.append(field)
				
				# 添加剩余列
				for col in score_columns:
					if col not in ordered_columns:
						ordered_columns.append(col)
				
				df_scores_sorted = df_scores_sorted[ordered_columns]
				
				# 显示排序后的评分明细
				with st.expander('查看评分明细（按总得分从高到低排序，前100行）', expanded=False):
					st.dataframe(df_scores_sorted.head(100), use_container_width=True)
				
				# 显示评分统计信息
				col1, col2, col3, col4 = st.columns(4)
				col1.metric('最高分', df_scores_sorted['总得分'].max())
				col2.metric('最低分', df_scores_sorted['总得分'].min())
				col3.metric('平均分', f"{df_scores_sorted['总得分'].mean():.1f}")
				col4.metric('中位数', f"{df_scores_sorted['总得分'].median():.1f}")
			else:
				# 如果没有总得分字段，按原样显示
				with st.expander('查看评分明细（前100行）', expanded=False):
					st.dataframe(pd.DataFrame(score_data).head(100), use_container_width=True)
			# 下载评分结果
			st.subheader('📥 下载评分结果')
			ts = datetime.now().strftime('%Y%m%d_%H%M%S')
			# 若有提取结果，则提供合并Excel与ZIP
			if st.session_state.extracted_results:
				# 将评分数据拼接到简历信息右侧
				df_resume = pd.DataFrame(st.session_state.extracted_results)
				df_score = pd.DataFrame(score_data)
				
				# 由于查询文件名顺序一致，直接按索引合并（更可靠）
				merged_df = pd.concat([df_resume, df_score], axis=1)
				
				# 生成合并后的Excel
				combined_output = io.BytesIO()
				with pd.ExcelWriter(combined_output, engine='openpyxl') as writer:
					merged_df.to_excel(writer, index=False, sheet_name='简历信息与评分')
				combined_output.seek(0)
				st.download_button('📒 下载合并Excel（信息+评分）', data=combined_output.read(), file_name=f"resume_with_scores_{ts}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
				# 生成评分JSON数据用于ZIP包
				scores_json_bytes = json.dumps(score_data, ensure_ascii=False, indent=2).encode('utf-8')
				files_for_zip: List[Tuple[str, bytes]] = [
					(f'resume_with_scores_{ts}.xlsx', combined_output.getvalue()),
					(f'resume_data_{ts}.xlsx', to_excel_bytes(st.session_state.extracted_results)),
					(f'resume_data_{ts}.json', json.dumps(st.session_state.extracted_results, ensure_ascii=False, indent=2).encode('utf-8')),
					(f'resume_scores_{ts}.json', scores_json_bytes)
				]
				if st.session_state.extracted_failed:
					files_for_zip.append((f'failed_queries_{ts}.xlsx', to_failed_queries_excel_bytes(st.session_state.extracted_failed)))
				zip_bytes = build_zip_bytes(files_for_zip)
				st.download_button('🗜️ 下载全部（ZIP）', data=zip_bytes, file_name=f"resume_extraction_{ts}.zip", mime='application/zip')


if __name__ == '__main__':
	main()

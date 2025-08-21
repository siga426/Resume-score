import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from multi_round_chat import MultiRoundChatAPI


class ResumeScorer:
    """简历评分器"""

    def __init__(self, api_key: str, base_url: str, user_id: str,
                 conversation_id_file: str = "conversation_id_score.json"):
        self.chat_api = MultiRoundChatAPI(
            api_key=api_key,
            base_url=base_url,
            user_id=user_id,
            conversation_id_file=conversation_id_file
        )
        self.scored_data: List[Dict[str, Any]] = []

    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """从回复中提取JSON"""
        try:
            start_marker = "```json"
            end_marker = "```"
            start_pos = response_text.find(start_marker)
            if start_pos == -1:
                return json.loads(response_text.strip())
            json_start = start_pos + len(start_marker)
            end_pos = response_text.find(end_marker, json_start)
            if end_pos == -1:
                json_text = response_text[json_start:].strip()
            else:
                json_text = response_text[json_start:end_pos].strip()
            return json.loads(json_text)
        except Exception:
            return None

    def process_score_query(self, query: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.chat_api.send_message(query)
            data = self.extract_json_from_response(response['answer'])
            if not data:
                return None
            # 附加元信息
            data['评分查询'] = query
            data['对话ID'] = response['conversation_id']
            data['时间戳'] = response['timestamp']
            return data
        except Exception:
            return None

    def batch_score(self, score_queries: List[str]) -> List[Dict[str, Any]]:
        conversation_id = self.chat_api.create_or_load_conversation(use_existing=True)
        print(f"使用评分对话ID: {conversation_id}")
        results: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []
        for idx, q in enumerate(score_queries, 1):
            print(f"\n=== 处理第{idx}个评分查询 ===\n查询: {q}")
            info = self.process_score_query(q)
            if info:
                results.append(info)
                print("✅ 成功获取评分")
            else:
                failed.append({
                    '序号': idx,
                    '查询内容': q,
                    '失败时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '失败原因': '评分失败或无返回数据'
                })
                print("❌ 获取评分失败")
        self.scored_data = results
        self.failed_scores = failed
        return results

    def export_scores_to_excel(self, filename: str = "resume_scores.xlsx") -> bool:
        if not self.scored_data:
            return False
        try:
            df = pd.DataFrame(self.scored_data)
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='简历评分', index=False)
            return True
        except Exception:
            return False

    def export_scores_to_json(self, filename: str = "resume_scores.json") -> bool:
        if not self.scored_data:
            return False
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.scored_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False



import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from multi_round_chat import MultiRoundChatAPI


class ResumeScorer:
    """简历评分器"""

    def __init__(self, api_key: str, base_url: str, user_id: str,
                 conversation_id_file: str = "conversation_id_score.json"):
        # 兼容旧版本 MultiRoundChatAPI（无 conversation_id_file 形参）
        try:
            self.chat_api = MultiRoundChatAPI(
                api_key=api_key,
                base_url=base_url,
                user_id=user_id,
                conversation_id_file=conversation_id_file
            )
        except TypeError:
            self.chat_api = MultiRoundChatAPI(
                api_key=api_key,
                base_url=base_url,
                user_id=user_id
            )
        self.scored_data: List[Dict[str, Any]] = []

    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """从回复中尽可能稳健地提取JSON（兼容多种回复格式）。"""
        try:
            # 1) 已是字典
            if isinstance(response_text, dict):
                return response_text

            text = str(response_text).strip()

            # 2) 优先解析带代码块（```json / ```JSON / ```）
            for marker in ("```json", "```JSON", "```"):
                start = text.find(marker)
                if start != -1:
                    json_start = start + len(marker)
                    end = text.find("```", json_start)
                    if end != -1:
                        candidate = text[json_start:end].strip()
                        try:
                            return json.loads(candidate)
                        except Exception:
                            pass

            # 3) 直接整体解析
            try:
                return json.loads(text)
            except Exception:
                pass

            # 4) 提取正文中第一段可能的JSON（基于花括号匹配）
            first_brace = text.find("{")
            if first_brace != -1:
                # 先尝试到最后一个右括号的切片
                last_brace = text.rfind("}")
                if last_brace != -1 and last_brace > first_brace:
                    candidate = text[first_brace:last_brace + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        pass

                # 逐字符匹配，寻找第一个完整的JSON对象
                depth = 0
                start_idx = None
                for i, ch in enumerate(text):
                    if ch == '{':
                        if depth == 0:
                            start_idx = i
                        depth += 1
                    elif ch == '}':
                        if depth > 0:
                            depth -= 1
                            if depth == 0 and start_idx is not None:
                                segment = text[start_idx:i + 1]
                                try:
                                    return json.loads(segment)
                                except Exception:
                                    # 继续尝试后续片段
                                    start_idx = None
                                    continue

            return None
        except Exception:
            return None

    def process_score_query(self, query: str) -> Optional[Dict[str, Any]]:
        try:
            print(f"发送评分查询: {query}")
            response = self.chat_api.send_message(query)
            # if SHOW_RESPONSE_DEBUG:
                # print(f"收到响应: {response}")
            
            if 'answer' not in response:
                print(f"响应中缺少answer字段: {response}")
                return None
                
            data = self.extract_json_from_response(response['answer'])
            if not data:
                print(f"无法从响应中提取JSON数据: {response['answer']}")
                return None
                
            # 附加元信息
            data['评分查询'] = query
            data['对话ID'] = response.get('conversation_id', 'unknown')
            data['时间戳'] = response.get('timestamp', datetime.now().isoformat())
            # print(f"成功提取评分数据: {data}")
            return data
        except Exception as e:
            print(f"评分查询处理异常: {e}")
            return None

    def batch_score(self, score_queries: List[str]) -> List[Dict[str, Any]]:
        conversation_id = self.chat_api.create_or_load_conversation(use_existing=True)
        # print(f"使用评分对话ID: {conversation_id}")
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



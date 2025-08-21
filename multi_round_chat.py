import json
import os
from typing import List, Dict, Any
from aiagentplatformpy.auth import TokenAuth
from aiagentplatformpy.chat import ChatEventType
from aiagentplatformpy.aiagentplatform import AsyncAiAgentPlatform, AiAgentPlatform


class MultiRoundChatAPI:
    """多轮对话API调用类"""
    
    def __init__(self, api_key: str, base_url: str, user_id: str):
        """
        初始化多轮对话API
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            user_id: 用户ID
        """
        self.api_key = api_key
        self.base_url = base_url
        self.user_id = user_id
        self.conversation_id = None
        self.chat_history = []  # 存储所有对话历史
        
        # 初始化AI智能体平台
        self.aiagentplatform = AiAgentPlatform(
            auth=TokenAuth(token=api_key),
            base_url=base_url
        )
    
    def save_conversation_id(self, conversation_id: str):
        """保存对话ID到文件"""
        data = {
            "conversation_id": conversation_id,
            "user_id": self.user_id,
            "timestamp": "2025-08-03"
        }
        with open("conversation_id.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ 对话ID已保存到 conversation_id.json")
    
    def load_conversation_id(self) -> str:
        """从文件加载对话ID"""
        try:
            if os.path.exists("conversation_id.json"):
                with open("conversation_id.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("conversation_id")
        except Exception as e:
            print(f"加载对话ID失败: {e}")
        return None
    
    def create_or_load_conversation(self, use_existing: bool = True) -> str:
        """
        创建新对话或加载已有对话
        
        Args:
            use_existing: 是否使用已有对话ID
            
        Returns:
            conversation_id: 对话ID
        """
        if use_existing:
            existing_conversation_id = self.load_conversation_id()
            if existing_conversation_id:
                print(f"找到已保存的对话ID: {existing_conversation_id}")
                self.conversation_id = existing_conversation_id
                return self.conversation_id
        
        # 创建新对话
        print("正在创建新对话...")
        try:
            conversation_res = self.aiagentplatform.conversations.create(
                inputs={"var": "variable"},
                user_id=self.user_id,
                app_key=self.api_key
            )
            self.conversation_id = conversation_res['Conversation']['AppConversationID']
            print(f"对话创建成功，对话ID: {self.conversation_id}")
            
            # 保存对话ID
            self.save_conversation_id(self.conversation_id)
            return self.conversation_id
            
        except Exception as e:
            print(f"创建对话失败: {e}")
            raise
    
    def send_message(self, message: str) -> Dict[str, Any]:
        """
        发送单条消息并获取回复
        
        Args:
            message: 要发送的消息
            
        Returns:
            response_data: 包含回复信息的字典
        """
        if not self.conversation_id:
            raise ValueError("对话ID未初始化，请先调用create_or_load_conversation()")
        
        try:
            print(f"发送消息: {message}")
            chat_res = self.aiagentplatform.chat.create(
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                query=message
            )
            
            # 构建响应数据
            response_data = {
                "message": message,
                "answer": chat_res.answer,
                "conversation_id": self.conversation_id,
                "timestamp": "2025-08-03"  # 可以添加实际时间戳
            }
            
            # 保存到对话历史
            self.chat_history.append(response_data)
            
            print(f"智能体回复: {chat_res.answer}")
            return response_data
            
        except Exception as e:
            print(f"发送消息失败: {e}")
            raise
    
    def multi_round_chat(self, messages: List[str]) -> List[Dict[str, Any]]:
        """
        进行多轮对话
        
        Args:
            messages: 要发送的消息列表
            
        Returns:
            responses: 所有回复的列表
        """
        responses = []
        
        for i, message in enumerate(messages, 1):
            print(f"\n=== 第{i}轮对话 ===")
            try:
                response = self.send_message(message)
                responses.append(response)
            except Exception as e:
                print(f"第{i}轮对话失败: {e}")
                # 可以选择继续或中断
                continue
        
        return responses
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.chat_history
    
    def save_chat_history(self, filename: str = "chat_history.json"):
        """保存对话历史到文件"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.chat_history, f, indent=2, ensure_ascii=False)
            print(f"✅ 对话历史已保存到 {filename}")
        except Exception as e:
            print(f"保存对话历史失败: {e}")
    
    def process_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        处理多轮对话的回复数据
        
        Args:
            responses: 回复数据列表
            
        Returns:
            processed_data: 处理后的数据
        """
        processed_data = {
            "total_rounds": len(responses),
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "messages": [],
            "answers": [],
            "summary": {}
        }
        
        for i, response in enumerate(responses, 1):
            processed_data["messages"].append(response["message"])
            processed_data["answers"].append(response["answer"])
            
            # 可以在这里添加更多的数据处理逻辑
            # 例如：关键词提取、情感分析、内容总结等
        
        # 生成摘要信息
        processed_data["summary"] = {
            "first_message": responses[0]["message"] if responses else None,
            "last_message": responses[-1]["message"] if responses else None,
            "average_answer_length": sum(len(ans) for ans in processed_data["answers"]) / len(processed_data["answers"]) if processed_data["answers"] else 0
        }
        
        return processed_data


def main():
    """主函数 - 演示多轮对话API的使用"""
    
    # 配置参数
    api_key = 'd2a7gnen04uuiosfsnk0'
    base_url = 'https://aiagentplatform.cmft.com'
    user_id = 'Siga'
    
    # 创建多轮对话API实例
    chat_api = MultiRoundChatAPI(api_key, base_url, user_id)
    
    try:
        # 创建或加载对话
        conversation_id = chat_api.create_or_load_conversation(use_existing=True)
        print(f"使用对话ID: {conversation_id}")
        
        # 定义要发送的消息列表
        messages = [
            "中国科学院大学-动力工程及工程热物理-杨斌的简历情况",
            "你能帮我做什么？",
            "我上一个问题是什么？",
            "你的知识库里有什么？",
            "请总结一下我们刚才的对话内容"
        ]
        
        # 进行多轮对话
        print("\n开始多轮对话...")
        responses = chat_api.multi_round_chat(messages)
        
        # 处理回复数据
        print("\n处理回复数据...")
        processed_data = chat_api.process_responses(responses)
        
        # 输出处理结果
        print(f"\n=== 处理结果 ===")
        print(f"总对话轮数: {processed_data['total_rounds']}")
        print(f"对话ID: {processed_data['conversation_id']}")
        print(f"用户ID: {processed_data['user_id']}")
        print(f"平均回复长度: {processed_data['summary']['average_answer_length']:.2f} 字符")
        
        # 保存对话历史
        chat_api.save_chat_history()
        
        # 返回处理后的数据供后续使用
        return processed_data, responses
        
    except Exception as e:
        print(f"程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    # 运行主函数
    processed_data, responses = main()
    
    # 这里可以添加后续的数据处理逻辑
    if processed_data and responses:
        print("\n=== 后续处理示例 ===")
        print("所有回复已保存到变量中，可以进行进一步处理：")
        print(f"- responses: 包含{len(responses)}轮对话的原始回复")
        print(f"- processed_data: 包含处理后的结构化数据")
        
        # 示例：访问特定轮次的回复
        if responses:
            print(f"\n第一轮回复: {responses[0]['answer'][:100]}...")
            print(f"最后一轮回复: {responses[-1]['answer'][:100]}...") 
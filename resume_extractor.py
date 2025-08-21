import json
import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from multi_round_chat import MultiRoundChatAPI
from query_loader import QueryLoader


class ResumeExtractor:
    """简历信息提取器"""
    
    def __init__(self, api_key: str, base_url: str, user_id: str):
        """
        初始化简历提取器
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            user_id: 用户ID
        """
        self.chat_api = MultiRoundChatAPI(api_key, base_url, user_id)
        self.extracted_data = []  # 存储所有提取的简历数据
        
    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        从智能体回复中提取JSON数据
        
        Args:
            response_text: 智能体的回复文本
            
        Returns:
            parsed_data: 解析后的JSON数据，如果解析失败返回None
        """
        try:
            # 查找JSON开始和结束的位置
            start_marker = "```json"
            end_marker = "```"
            
            start_pos = response_text.find(start_marker)
            if start_pos == -1:
                # 如果没有找到```json标记，尝试直接解析整个文本
                return json.loads(response_text.strip())
            
            # 找到JSON开始位置
            json_start = start_pos + len(start_marker)
            
            # 找到JSON结束位置
            end_pos = response_text.find(end_marker, json_start)
            if end_pos == -1:
                # 如果没有找到结束标记，尝试解析到文本末尾
                json_text = response_text[json_start:].strip()
            else:
                json_text = response_text[json_start:end_pos].strip()
            
            # 解析JSON
            parsed_data = json.loads(json_text)
            return parsed_data
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始文本: {response_text[:200]}...")
            return None
        except Exception as e:
            print(f"提取JSON时发生错误: {e}")
            return None
    
    def process_resume_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        处理简历查询并提取信息
        
        Args:
            query: 简历查询问题
            
        Returns:
            extracted_info: 提取的简历信息字典
        """
        try:
            # 发送查询
            response = self.chat_api.send_message(query)
            
            # 提取JSON数据
            extracted_info = self.extract_json_from_response(response['answer'])
            
            if extracted_info:
                # 检查是否所有字段都为空
                if self._is_all_fields_empty(extracted_info):
                    print(f"提取的JSON数据所有字段都为空: {query}")
                    return None
                
                # 添加查询信息
                extracted_info['查询问题'] = query
                extracted_info['对话ID'] = response['conversation_id']
                extracted_info['时间戳'] = response['timestamp']
                
                # 处理列表字段，将其转换为字符串以便Excel显示
                for key, value in extracted_info.items():
                    if isinstance(value, list):
                        extracted_info[key] = '; '.join(value) if value else ''
                
                return extracted_info
            else:
                print(f"无法从回复中提取JSON数据: {query}")
                return None
                
        except Exception as e:
            print(f"处理简历查询失败: {e}")
            return None
    
    def _is_all_fields_empty(self, data: Dict[str, Any]) -> bool:
        """
        检查数据中所有字段是否都为空
        
        Args:
            data: 要检查的数据字典
            
        Returns:
            is_empty: 是否所有字段都为空
        """
        # 需要检查的关键字段（排除系统添加的字段）
        key_fields = [
            '姓名', '性别', '最高学历', '硕士专业', '硕士院校', '硕士院校类别',
            '本科院校', '本科院校类别', '本科专业', '成绩排名', '项目经历',
            '项目经历关键词tag', '实习经历', '实习经历关键词tag', '硕士课题内容',
            '课题内容关键词', '奖学金情况', '英语能力大学英语等级',
            '英语能力托福和雅思及其分数', '编程语言', '加分项'
        ]
        
        for field in key_fields:
            if field in data:
                value = data[field]
                # 检查字段值是否为空
                if isinstance(value, str) and value.strip():
                    return False  # 有非空字符串值
                elif isinstance(value, list) and value:
                    return False  # 有非空列表值
                elif value and str(value).strip():
                    return False  # 有其他非空值
        
        # 所有关键字段都为空
        return True
    
    def batch_extract_resumes(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        批量提取简历信息
        
        Args:
            queries: 简历查询问题列表
            
        Returns:
            extracted_data: 提取的简历数据列表
        """
        # 创建或加载对话
        conversation_id = self.chat_api.create_or_load_conversation(use_existing=True)
        print(f"使用对话ID: {conversation_id}")
        
        extracted_data = []
        failed_queries = []  # 记录失败的查询
        
        for i, query in enumerate(queries, 1):
            print(f"\n=== 处理第{i}个简历查询 ===")
            print(f"查询: {query}")
            
            extracted_info = self.process_resume_query(query)
            
            if extracted_info:
                extracted_data.append(extracted_info)
                print(f"✅ 成功提取简历信息")
            else:
                print(f"❌ 提取简历信息失败")
                # 记录失败的查询
                failed_queries.append({
                    '序号': i,
                    '查询内容': query,
                    '失败时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '失败原因': '提取失败或无返回数据或所有字段为空'
                })
        
        self.extracted_data = extracted_data
        self.failed_queries = failed_queries  # 保存失败的查询列表
        
        # 如果有失败的查询，保存到文件
        if failed_queries:
            self.save_failed_queries()
        
        return extracted_data
    
    def export_to_excel(self, filename: str = "resume_data.xlsx") -> bool:
        """
        将提取的简历数据导出到Excel
        
        Args:
            filename: 输出文件名
            
        Returns:
            success: 是否成功导出
        """
        if not self.extracted_data:
            print("没有数据可以导出")
            return False
        
        try:
            # 创建DataFrame
            df = pd.DataFrame(self.extracted_data)
            
            # 重新排列列的顺序，将重要字段放在前面
            important_columns = [
                '姓名', '性别', '最高学历', '硕士专业', '硕士院校', '硕士院校类别',
                '本科院校', '本科院校类别', '本科专业', '成绩排名', '英语能力大学英语等级',
                '编程语言', '奖学金情况', '加分项'
            ]
            
            # 获取所有列
            all_columns = list(df.columns)
            
            # 重新排列列顺序
            ordered_columns = []
            for col in important_columns:
                if col in all_columns:
                    ordered_columns.append(col)
            
            # 添加其他列
            for col in all_columns:
                if col not in ordered_columns:
                    ordered_columns.append(col)
            
            # 重新排列DataFrame
            df = df[ordered_columns]
            
            # 导出到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='简历信息', index=False)
                
                # 获取工作表
                worksheet = writer.sheets['简历信息']
                
                # 调整列宽
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)  # 最大宽度50
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"✅ 简历数据已导出到 {filename}")
            print(f"共导出 {len(self.extracted_data)} 条简历信息")
            return True
            
        except Exception as e:
            print(f"导出Excel失败: {e}")
            return False
    
    def export_to_json(self, filename: str = "resume_data.json") -> bool:
        """
        将提取的简历数据导出到JSON文件
        
        Args:
            filename: 输出文件名
            
        Returns:
            success: 是否成功导出
        """
        if not self.extracted_data:
            print("没有数据可以导出")
            return False
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.extracted_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 简历数据已导出到 {filename}")
            return True
            
        except Exception as e:
            print(f"导出JSON失败: {e}")
            return False
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """
        获取提取摘要信息
        
        Returns:
            summary: 摘要信息字典
        """
        if not self.extracted_data:
            return {"total_count": 0}
        
        summary = {
            "total_count": len(self.extracted_data),
            "successful_extractions": len([d for d in self.extracted_data if d.get('姓名')]),
            "unique_names": list(set([d.get('姓名', '') for d in self.extracted_data if d.get('姓名')])),
            "education_levels": list(set([d.get('最高学历', '') for d in self.extracted_data if d.get('最高学历')])),
            "universities": list(set([d.get('硕士院校', '') for d in self.extracted_data if d.get('硕士院校')]))
        }
        
        return summary
    
    def save_failed_queries(self, filename: str = None) -> bool:
        """
        保存失败的查询到文件
        
        Args:
            filename: 输出文件名，如果为None则自动生成
            
        Returns:
            success: 是否成功保存
        """
        if not hasattr(self, 'failed_queries') or not self.failed_queries:
            print("没有失败的查询需要保存")
            return True
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'failed_queries_{timestamp}.xlsx'
        
        try:
            # 创建DataFrame
            df = pd.DataFrame(self.failed_queries)
            
            # 导出到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='失败查询', index=False)
                
                # 获取工作表
                worksheet = writer.sheets['失败查询']
                
                # 调整列宽
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)  # 最大宽度50
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"✅ 失败查询已保存到 {filename}")
            print(f"共保存 {len(self.failed_queries)} 条失败查询")
            return True
            
        except Exception as e:
            print(f"保存失败查询失败: {e}")
            return False
    
    def get_failed_queries_summary(self) -> Dict[str, Any]:
        """
        获取失败查询摘要信息
        
        Returns:
            summary: 失败查询摘要信息字典
        """
        if not hasattr(self, 'failed_queries') or not self.failed_queries:
            return {"failed_count": 0}
        
        summary = {
            "failed_count": len(self.failed_queries),
            "failed_queries": self.failed_queries
        }
        
        return summary


def main():
    """主函数 - 演示简历信息提取"""
    
    # 配置参数
    api_key = 'd2a7gnen04uuiosfsnk0'
    base_url = 'https://aiagentplatform.cmft.com'
    user_id = 'Siga'
    
    # 创建简历提取器
    extractor = ResumeExtractor(api_key, base_url, user_id)
    
    # 使用查询加载器
    query_loader = QueryLoader()
    
    # 从文件读取查询列表（支持Excel、CSV、TXT格式）
    resume_queries = query_loader.load_queries("resume_queries.xlsx")
    
    # 如果文件不存在或读取失败，结束程序并提示错误
    if not resume_queries:
        print("❌ 错误：无法读取查询列表文件")
        print("请确保以下文件之一存在：")
        print("- resume_queries.xlsx")
        print("- resume_queries.csv") 
        print("- resume_queries.txt")
        print("\n你可以运行以下命令创建示例文件：")
        print("python create_sample_queries.py")
        print("\n程序已退出。")
        return
    
    # 显示读取的查询列表
    print("\n=== 读取的查询列表 ===")
    for i, query in enumerate(resume_queries, 1):
        print(f"{i}. {query}")
    
    try:
        # 批量提取简历信息
        print("\n开始批量提取简历信息...")
        extracted_data = extractor.batch_extract_resumes(resume_queries)
        
        if extracted_data:
            # 显示提取摘要
            summary = extractor.get_extraction_summary()
            print(f"\n=== 提取摘要 ===")
            print(f"总查询数: {summary['total_count']}")
            print(f"成功提取数: {summary['successful_extractions']}")
            print(f"提取到的姓名: {summary['unique_names']}")
            
            # 导出到Excel
            extractor.export_to_excel("resume_data.xlsx")
            
            # 导出到JSON
            extractor.export_to_json("resume_data.json")
            
            # 显示第一条数据示例
            if extracted_data:
                print(f"\n=== 第一条数据示例 ===")
                first_data = extracted_data[0]
                for key, value in first_data.items():
                    if isinstance(value, str) and len(value) > 100:
                        print(f"{key}: {value[:100]}...")
                    else:
                        print(f"{key}: {value}")
        
        else:
            print("没有成功提取到任何简历数据")
        
        # 保存对话历史
        extractor.chat_api.save_chat_history("resume_chat_history.json")
        
    except Exception as e:
        print(f"程序执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 
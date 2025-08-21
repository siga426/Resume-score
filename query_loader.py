import pandas as pd
import os
from typing import List, Optional


class QueryLoader:
    """查询列表加载器"""
    
    def __init__(self):
        """初始化查询加载器"""
        pass
    
    def load_from_excel(self, filename: str, sheet_name: str = "Sheet1", column_index: int = 0) -> List[str]:
        """
        从Excel文件读取查询列表
        
        Args:
            filename: Excel文件名
            sheet_name: 工作表名称
            column_index: 列索引（0表示第一列）
            
        Returns:
            queries: 查询列表
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(filename, sheet_name=sheet_name)
            
            # 获取指定列数据
            column_data = df.iloc[:, column_index]
            
            # 过滤空值和NaN，并自动补齐"的简历情况"
            queries = []
            for query in column_data:
                if pd.notna(query) and str(query).strip():
                    query_text = str(query).strip()
                    # 如果查询不包含"的简历情况"，则自动添加
                    if not query_text.endswith("的简历信息"):
                        # query_text += "？"
                        query_text += "的简历信息"
                    queries.append(query_text)
            
            print(f"✅ 从Excel文件 {filename} 成功读取 {len(queries)} 个查询")
            return queries
            
        except FileNotFoundError:
            print(f"❌ Excel文件 {filename} 不存在")
            return []
        except Exception as e:
            print(f"❌ 读取Excel文件失败: {e}")
            return []
    
    def load_from_csv(self, filename: str, column_index: int = 0, encoding: str = 'utf-8') -> List[str]:
        """
        从CSV文件读取查询列表
        
        Args:
            filename: CSV文件名
            column_index: 列索引（0表示第一列）
            encoding: 文件编码
            
        Returns:
            queries: 查询列表
        """
        try:
            # 读取CSV文件
            df = pd.read_csv(filename, encoding=encoding)
            
            # 获取指定列数据
            column_data = df.iloc[:, column_index]
            
            # 过滤空值和NaN，并自动补齐"的简历情况"
            queries = []
            for query in column_data:
                if pd.notna(query) and str(query).strip():
                    query_text = str(query).strip()
                    # 如果查询不包含"的简历情况"，则自动添加
                    if not query_text.endswith("的简历情况"):
                        query_text += "的简历情况"
                    queries.append(query_text)
            
            print(f"✅ 从CSV文件 {filename} 成功读取 {len(queries)} 个查询")
            return queries
            
        except FileNotFoundError:
            print(f"❌ CSV文件 {filename} 不存在")
            return []
        except Exception as e:
            print(f"❌ 读取CSV文件失败: {e}")
            return []
    
    def load_from_txt(self, filename: str, encoding: str = 'utf-8') -> List[str]:
        """
        从文本文件读取查询列表（每行一个查询）
        
        Args:
            filename: 文本文件名
            encoding: 文件编码
            
        Returns:
            queries: 查询列表
        """
        try:
            with open(filename, 'r', encoding=encoding) as f:
                lines = f.readlines()
            
            # 过滤空行和空白字符，并自动补齐"的简历情况"
            queries = []
            for line in lines:
                if line.strip():
                    query_text = line.strip()
                    # 如果查询不包含"的简历情况"，则自动添加
                    if not query_text.endswith("的简历情况"):
                        query_text += "的简历情况"
                    queries.append(query_text)
            
            print(f"✅ 从文本文件 {filename} 成功读取 {len(queries)} 个查询")
            return queries
            
        except FileNotFoundError:
            print(f"❌ 文本文件 {filename} 不存在")
            return []
        except Exception as e:
            print(f"❌ 读取文本文件失败: {e}")
            return []
    
    def load_queries(self, filename: str, file_type: Optional[str] = None) -> List[str]:
        """
        智能加载查询列表（自动检测文件类型）
        
        Args:
            filename: 文件名
            file_type: 文件类型（可选，自动检测）
            
        Returns:
            queries: 查询列表
        """
        if not os.path.exists(filename):
            print(f"❌ 错误：文件 {filename} 不存在")
            print(f"当前工作目录：{os.getcwd()}")
            print(f"请检查文件路径是否正确")
            return []
        
        # 自动检测文件类型
        if file_type is None:
            file_type = self._detect_file_type(filename)
        
        # 根据文件类型加载
        if file_type == 'excel':
            return self.load_from_excel(filename)
        elif file_type == 'csv':
            return self.load_from_csv(filename)
        elif file_type == 'txt':
            return self.load_from_txt(filename)
        else:
            print(f"❌ 不支持的文件类型: {file_type}")
            return []
    
    def _detect_file_type(self, filename: str) -> str:
        """
        检测文件类型
        
        Args:
            filename: 文件名
            
        Returns:
            file_type: 文件类型
        """
        extension = filename.lower().split('.')[-1]
        
        if extension in ['xlsx', 'xls']:
            return 'excel'
        elif extension == 'csv':
            return 'csv'
        elif extension == 'txt':
            return 'txt'
        else:
            # 默认尝试Excel
            return 'excel'
    
    def create_sample_files(self):
        """创建示例文件"""
        
        # 示例查询列表
        sample_queries = [
            "大连理工大学-船舶与海洋工程-张贤宇的简历情况",
            "上海交通大学-轮机工程-陈浩的简历情况",
            "哈尔滨工程大学-船舶与海洋工程-李明的简历情况",
            "武汉理工大学-轮机工程-王强的简历情况",
            "华中科技大学-机械工程-刘伟的简历情况"
        ]
        
        # 创建Excel文件
        df_excel = pd.DataFrame({'简历查询': sample_queries})
        df_excel.to_excel("resume_queries.xlsx", index=False, sheet_name='Sheet1')
        print("✅ 创建示例Excel文件: resume_queries.xlsx")
        
        # 创建CSV文件
        df_csv = pd.DataFrame({'简历查询': sample_queries})
        df_csv.to_csv("resume_queries.csv", index=False, encoding='utf-8')
        print("✅ 创建示例CSV文件: resume_queries.csv")
        
        # 创建TXT文件
        with open("resume_queries.txt", 'w', encoding='utf-8') as f:
            for query in sample_queries:
                f.write(query + '\n')
        print("✅ 创建示例TXT文件: resume_queries.txt")
        
        print(f"\n示例文件已创建，包含 {len(sample_queries)} 个查询")


def main():
    """主函数 - 演示查询加载器"""
    
    loader = QueryLoader()
    
    # 创建示例文件
    print("=== 创建示例文件 ===")
    loader.create_sample_files()
    
    # 测试加载功能
    print("\n=== 测试加载功能 ===")
    
    # 从Excel加载
    excel_queries = loader.load_from_excel("resume_queries.xlsx")
    print(f"Excel查询数量: {len(excel_queries)}")
    
    # 从CSV加载
    csv_queries = loader.load_from_csv("resume_queries.csv")
    print(f"CSV查询数量: {len(csv_queries)}")
    
    # 从TXT加载
    txt_queries = loader.load_from_txt("resume_queries.txt")
    print(f"TXT查询数量: {len(txt_queries)}")
    
    # 智能加载
    smart_queries = loader.load_queries("resume_queries.xlsx")
    print(f"智能加载查询数量: {len(smart_queries)}")


if __name__ == "__main__":
    main() 
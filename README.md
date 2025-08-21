# 多轮对话API调用脚本 & 简历信息提取器

基于原有的 `test_rounds.py` 程序，创建了一个功能完整的多轮对话API调用脚本，支持在同一个conversationID下进行多轮对话，并将每轮对话的返回值保存到变量中用于后续处理。

特别针对简历信息提取场景，提供了专门的JSON解析和Excel导出功能。

## 文件说明

- `multi_round_chat.py` - 主要的多轮对话API类
- `simple_chat_example.py` - 简化的使用示例
- `resume_extractor.py` - 简历信息提取器（核心功能）
- `resume_extraction_example.py` - 简历提取使用示例
- `test_rounds.py` - 原始程序（参考）
- `requirements.txt` - 依赖包列表

## 主要功能

### 1. MultiRoundChatAPI 类

核心功能类，提供以下方法：

- `create_or_load_conversation()` - 创建新对话或加载已有对话
- `send_message()` - 发送单条消息并获取回复
- `multi_round_chat()` - 进行多轮对话
- `process_responses()` - 处理多轮对话的回复数据
- `save_chat_history()` - 保存对话历史到文件
- `get_chat_history()` - 获取对话历史

### 2. 数据存储

每轮对话的返回值包含以下信息：
```python
{
    "message": "用户发送的消息",
    "answer": "AI智能体的回复",
    "conversation_id": "对话ID",
    "timestamp": "时间戳"
}
```

### 3. ResumeExtractor 类（简历信息提取）

专门用于处理简历信息提取的类，提供以下功能：

- `extract_json_from_response()` - 从智能体回复中提取JSON数据
- `process_resume_query()` - 处理简历查询并提取信息
- `batch_extract_resumes()` - 批量提取简历信息
- `export_to_excel()` - 导出简历数据到Excel表格
- `export_to_json()` - 导出简历数据到JSON文件
- `get_extraction_summary()` - 获取提取摘要信息

## 使用方法

### 基本使用

```python
from multi_round_chat import MultiRoundChatAPI

# 创建API实例
chat_api = MultiRoundChatAPI(api_key, base_url, user_id)

# 创建或加载对话
conversation_id = chat_api.create_or_load_conversation(use_existing=True)

# 定义消息列表
messages = [
    "你好，请介绍一下你自己",
    "你能帮我做什么事情？",
    "请给我一个简单的Python代码示例"
]

# 进行多轮对话
responses = chat_api.multi_round_chat(messages)

# 处理回复数据
processed_data = chat_api.process_responses(responses)

# 保存对话历史
chat_api.save_chat_history()
```

### 访问回复数据

```python
# 访问特定轮次的回复
first_response = responses[0]
print(f"第一轮问题: {first_response['message']}")
print(f"第一轮回答: {first_response['answer']}")

# 访问所有回答
all_answers = [response['answer'] for response in responses]

# 访问处理后的数据
print(f"总对话轮数: {processed_data['total_rounds']}")
print(f"对话ID: {processed_data['conversation_id']}")
print(f"平均回复长度: {processed_data['summary']['average_answer_length']}")
```

### 运行示例

```bash
# 运行完整示例
python multi_round_chat.py

# 运行简化示例
python simple_chat_example.py

# 运行简历提取示例
python resume_extractor.py

# 运行简历提取简化示例
python resume_extraction_example.py
```

## 配置参数

在脚本中修改以下配置参数：

```python
api_key = 'd2a7gnen04uuiosfsnk0'  # 你的API密钥
base_url = 'https://aiagentplatform.cmft.com'  # API基础URL
user_id = 'Siga'  # 用户ID
```

## 输出文件

脚本会生成以下文件：

- `conversation_id.json` - 保存的对话ID
- `chat_history.json` - 对话历史记录
- `all_chat_data.json` - 所有对话数据（包含统计信息）
- `resume_data.xlsx` - 简历数据Excel表格
- `resume_data.json` - 简历数据JSON文件
- `phd_candidates.xlsx` - 博士候选人筛选结果
- `top_university_graduates.xlsx` - 985高校毕业生筛选结果

## 后续处理示例

### 通用对话处理

```python
# 1. 提取所有回答
all_answers = [response['answer'] for response in responses]

# 2. 计算平均回答长度
avg_length = sum(len(answer) for answer in all_answers) / len(all_answers)

# 3. 查找包含特定关键词的回答
keyword = "Python"
python_answers = [answer for answer in all_answers if keyword in answer]

# 4. 进行文本分析
# 可以添加关键词提取、情感分析、内容总结等功能
```

### 简历数据处理

```python
from resume_extractor import ResumeExtractor

# 创建简历提取器
extractor = ResumeExtractor(api_key, base_url, user_id)

# 批量提取简历
queries = [
    "中国科学院大学-动力工程及工程热物理-杨斌的简历情况",
    "清华大学-计算机科学与技术-张三的简历情况"
]

extracted_data = extractor.batch_extract_resumes(queries)

# 数据筛选和处理
# 1. 按学历筛选
phd_candidates = [d for d in extracted_data if '博士' in str(d.get('最高学历', ''))]

# 2. 按学校类别筛选
top_universities = [d for d in extracted_data if '985' in str(d.get('本科院校类别', ''))]

# 3. 按编程技能筛选
python_developers = [d for d in extracted_data if 'Python' in str(d.get('编程语言', ''))]

# 4. 导出到Excel
extractor.extracted_data = phd_candidates
extractor.export_to_excel("phd_candidates.xlsx")
```

## 错误处理

脚本包含完整的错误处理机制：

- 网络连接检查
- API地址验证
- 认证信息验证
- 智能体可用性检查
- 对话ID有效性验证

## 注意事项

1. 确保网络连接正常
2. 验证API密钥和地址的正确性
3. 检查智能体在平台上的可用性
4. 对话ID会自动保存，可以继续之前的对话
5. 所有回复数据都会保存到变量中，方便后续处理
6. 简历提取功能需要智能体返回JSON格式数据
7. 安装依赖包：`pip install -r requirements.txt`

## 扩展功能

可以在 `process_responses()` 方法中添加更多数据处理逻辑：

- 关键词提取
- 情感分析
- 内容总结
- 文本分类
- 实体识别等

## 🚀 Web界面功能

### 现代化Web界面
- **文件上传**: 支持拖拽上传Excel、CSV、TXT文件
- **实时进度**: 显示提取进度条
- **自动打开**: 提取完成后自动打开Excel文件
- **结果下载**: 支持Excel和JSON格式下载
- **用户友好**: 直观的操作界面

### 启动Web界面
```bash
python start_web.py
```

### 访问地址
http://localhost:5000

### 文件说明
- `web_app.py` - Flask Web应用
- `templates/index.html` - 前端界面
- `start_web.py` - 启动脚本
- `Web界面使用说明.md` - 详细使用说明 
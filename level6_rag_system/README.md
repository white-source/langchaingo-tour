# Level 6: RAG 系统

> **学习时间**: 150 分钟  
> **难度**: ⭐⭐⭐⭐⭐ 高级  
> **前置要求**: 完成 Level 1-5  

---

## 🎯 学习目标

1. **文档加载和分割** - 处理外部文本数据
2. **向量化和嵌入** - 转换为向量表示
3. **向量数据库** - 存储和检索相似文档
4. **完整 RAG 管道** - 组合所有部分

---

## 📚 核心概念

### RAG（检索增强生成）流程

```
问题 → 向量化 → 检索相似文档 → 组合到 Prompt → LLM → 回答
```

### 关键步骤

1. **文档加载**：从文件/网页加载文本
2. **分割**：将长文本分成小块
3. **嵌入**：转换为向量（使用嵌入模型）
4. **存储**：保存到向量数据库
5. **检索**：根据相似度找相关文档
6. **生成**：用检索的文档增强 LLM 提示

---

## 💻 核心 API

```python
# 加载文档
from langchain_community.document_loaders import TextLoader
loader = TextLoader("file.txt")
docs = loader.load()

# 分割文本
from langchain_text_splitters import CharacterTextSplitter
splitter = CharacterTextSplitter(chunk_size=1000)
chunks = splitter.split_documents(docs)

# 创建嵌入
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings()

# 创建向量数据库
from langchain_community.vectorstores import FAISS
vectorstore = FAISS.from_documents(chunks, embeddings)

# 检索器
retriever = vectorstore.as_retriever()

# 在链中使用
retrieved_docs = retriever.invoke("query")
```

---

本级详细内容见 [main.py](./main.py)


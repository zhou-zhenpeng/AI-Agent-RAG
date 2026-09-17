\# 📚 AI-Agent-RAG



基于 RAG（Retrieval-Augmented Generation）的科研文献智能问答系统。



用户可以上传 PDF 科研论文，系统自动完成文本解析、清洗、分块、向量化和语义检索，并调用 DeepSeek 大语言模型基于检索到的论文证据回答问题，同时提供论文页码引用，提高回答的可追溯性。



\## ✨ 功能特点



\- 📄 支持科研论文 PDF 上传与解析

\- ✂️ 自动进行文本清洗和重叠分块

\- 🧠 使用 `multilingual-e5-small` 生成文本向量

\- 🔍 基于向量相似度进行 Top-K 语义检索

\- 🤖 使用 DeepSeek 大语言模型生成回答

\- 📚 强制模型基于检索到的论文证据回答

\- 🔗 回答中提供论文文件名和 PDF 页码引用

\- 🔎 展示检索片段及相似度

\- 🖥️ 基于 Streamlit 构建 Web 交互界面

\- 🔐 API Key 通过环境变量管理，避免硬编码泄露



\## 🏗️ 系统流程



```text

PDF 论文上传

&#x20;     ↓

PDF 文本解析

&#x20;     ↓

文本清洗

&#x20;     ↓

Chunk 分块

&#x20;     ↓

Sentence Transformer

&#x20;     ↓

Embedding 向量

&#x20;     ↓

语义相似度检索

&#x20;     ↓

Top-K 论文证据

&#x20;     ↓

DeepSeek LLM

&#x20;     ↓

回答 + 论文页码引用

```



\## 🧠 RAG 实现



\### 文档处理



系统使用 `pypdf` 解析 PDF，并按照页面保留来源信息。



当前分块参数：



```text

Chunk Size: 800

Overlap: 150

Minimum Chunk Size: 250

```



同时对部分论文页眉、下载信息以及 References 等内容进行过滤。



\### Embedding



使用：



```text

intfloat/multilingual-e5-small

```



文档使用：



```text

passage: document text

```



问题使用：



```text

query: user question

```



并对 Embedding 进行归一化。



\### Retrieval



计算问题向量与论文文本块向量之间的相似度，并选择相似度最高的 Top-4 文本块：



```text

Question

&#x20;  ↓

Query Embedding

&#x20;  ↓

Similarity Search

&#x20;  ↓

Top-4 Chunks

```



\### Evidence-grounded Generation



检索结果被作为上下文发送给 DeepSeek。



Prompt 要求模型：



\- 只能依据提供的论文证据回答

\- 关键结论必须引用证据

\- 证据不足时明确说明无法确认

\- 不允许自行生成不存在的论文页码或来源



最终将证据编号映射为实际论文文件名和 PDF 页码。



\## 🛠️ 技术栈



| 技术 | 用途 |

|---|---|

| Python | 核心开发语言 |

| Streamlit | Web UI |

| PyPDF | PDF 文本解析 |

| Sentence Transformers | Embedding |

| multilingual-e5-small | 多语言文本向量模型 |

| NumPy | 向量相似度计算 |

| DeepSeek API | 大语言模型 |

| OpenAI Python SDK | API 调用 |



\## 📁 项目结构



```text

AI-Agent-RAG/

│

├── app.py

├── requirements.txt

├── README.md

└── .gitignore

```



\## 🚀 快速开始



\### 1. Clone 项目



```bash

git clone https://github.com/zhou-zhenpeng/AI-Agent-RAG.git

cd AI-Agent-RAG

```



\### 2. 安装依赖



```bash

pip install -r requirements.txt

```



\### 3. 配置 DeepSeek API Key



Windows PowerShell：



```powershell

$env:DEEPSEEK\_API\_KEY="your\_api\_key"

```



请勿将真实 API Key 写入代码或上传到 GitHub。



\### 4. 启动项目



```bash

streamlit run app.py

```



打开 Streamlit 页面后：



1\. 上传 PDF 科研论文

2\. 点击处理论文并建立索引

3\. 输入关于论文的问题

4\. 系统检索相关论文内容

5\. DeepSeek 根据检索证据生成回答

6\. 查看回答对应的论文页码和检索证据



\## 🎯 项目目标



本项目旨在探索 RAG 在科研论文阅读场景中的应用，通过结合语义检索和大语言模型，降低直接使用 LLM 时产生幻觉的风险，并提高科研问答结果的可解释性和可追溯性。



\## 🔮 后续计划



\- \[ ] 支持多篇 PDF 构建统一知识库

\- \[ ] 使用 FAISS / Chroma 构建向量数据库

\- \[ ] 增加 BM25 + Vector Search 混合检索

\- \[ ] 增加 Reranker 提升检索准确率

\- \[ ] 支持多轮对话与 Conversation Memory

\- \[ ] 支持流式回答

\- \[ ] 增加 RAG 自动评估

\- \[ ] Docker 容器化

\- \[ ] 云端部署



\## 🔐 Security



本项目不会在代码中存储 DeepSeek API Key。



请通过环境变量配置：



```text

DEEPSEEK\_API\_KEY

```



`.env` 等敏感文件已通过 `.gitignore` 排除。



\## 📄 License



This project is currently intended for learning and research purposes.


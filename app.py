from pathlib import Path
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from openai import OpenAI
import streamlit as st
import numpy as np
import json
import os
import re

st.set_page_config(
    page_title="科研文献 RAG 助手",
    page_icon="📚",
    layout="wide",
)


@st.cache_resource
def load_embedding_model():
    return SentenceTransformer(
        "intfloat/multilingual-e5-small"
    )


def clean_page_text(text):
    kept_lines = []

    for line in text.splitlines():
        line_lower = line.lower().strip()

        noise_phrases = [
            "downloaded from http",
            "www.pnas.org/cgi/doi",
        ]

        if any(phrase in line_lower for phrase in noise_phrases):
            continue

        if (
            "pnas" in line_lower
            and "vol." in line_lower
            and "no." in line_lower
        ):
            continue

        kept_lines.append(line)

    cleaned_text = " ".join(kept_lines)
    cleaned_text = re.sub(r"\s+", " ", cleaned_text)

    return cleaned_text.strip()


def extract_and_chunk_pdf(pdf_file, source_name):
    reader = PdfReader(pdf_file)

    chunks = []
    chunk_size = 800
    overlap = 150
    min_chunk_size = 250

    for page_number, page in enumerate(reader.pages, start=1):
        original_text = page.extract_text() or ""

        end_match = re.search(
            r"(?:^|\n)\s*"
            r"(ACKNOWLEDGMENTS?|REFERENCES|BIBLIOGRAPHY)"
            r"\s*(?:\n|$)",
            original_text,
            flags=re.IGNORECASE,
        )

        reached_end = end_match is not None

        if reached_end:
            original_text = original_text[:end_match.start()]

        text = clean_page_text(original_text)

        page_chunks = []
        start = 0
        chunk_number = 1

        while start < len(text):
            end = start + chunk_size
            piece = text[start:end].strip()

            if len(piece) < min_chunk_size and page_chunks:
                page_chunks[-1]["text"] += " " + piece
            elif piece:
                page_chunks.append({
                    "source": source_name,
                    "page": page_number,
                    "chunk_id": chunk_number,
                    "text": piece,
                })
                chunk_number += 1

            start += chunk_size - overlap

        chunks.extend(page_chunks)

        if reached_end:
            break

    return chunks, len(reader.pages)


def build_embeddings(chunks, model):
    texts = [
        "passage: " + chunk["text"]
        for chunk in chunks
    ]

    return model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


st.title("📚 科研文献 RAG 问答助手")
st.caption("上传论文，自动建立向量知识库并生成带页码引用的回答")

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    st.error("没有检测到 DEEPSEEK_API_KEY")
    st.code(
        '$env:DEEPSEEK_API_KEY="你的DeepSeek API Key"',
        language="powershell",
    )
    st.stop()

embedding_model = load_embedding_model()

with st.sidebar:
    st.header("建立知识库")

    uploaded_file = st.file_uploader(
        "上传一篇 PDF 论文",
        type=["pdf"],
    )

    build_button = st.button(
        "处理论文并建立索引",
        type="primary",
    )

    if build_button:
        if uploaded_file is None:
            st.warning("请先上传 PDF")
        else:
            try:
                with st.spinner("正在读取并切分论文……"):
                    chunks, total_pages = extract_and_chunk_pdf(
                        uploaded_file,
                        uploaded_file.name,
                    )

                if not chunks:
                    st.error("没有提取到文字，PDF 可能是扫描图片")
                else:
                    with st.spinner("正在创建向量索引……"):
                        embeddings = build_embeddings(
                            chunks,
                            embedding_model,
                        )

                    st.session_state["chunks"] = chunks
                    st.session_state["embeddings"] = embeddings
                    st.session_state["source_name"] = uploaded_file.name
                    st.session_state["total_pages"] = total_pages

                    st.success("知识库建立成功")

            except Exception as error:
                st.error("处理 PDF 失败")
                st.exception(error)

    if "chunks" in st.session_state:
        st.divider()
        st.write("当前论文：", st.session_state["source_name"])
        st.write("PDF 总页数：", st.session_state["total_pages"])
        st.write("文本块数量：", len(st.session_state["chunks"]))


if "chunks" not in st.session_state:
    st.info("请在左侧上传 PDF，然后点击“处理论文并建立索引”")
    st.stop()

chunks = st.session_state["chunks"]
embeddings = st.session_state["embeddings"]

question = st.text_input(
    "请输入关于论文的问题",
    placeholder="例如：这篇论文的主要研究结论是什么？",
)

ask_button = st.button(
    "开始检索并回答",
    type="primary",
)

if ask_button:
    if not question.strip():
        st.warning("请先输入问题")
        st.stop()

    with st.spinner("正在检索论文证据……"):
        question_embedding = embedding_model.encode(
            "query: " + question,
            normalize_embeddings=True,
        )

        scores = embeddings @ question_embedding
        top_indices = np.argsort(scores)[::-1][:4]

        context_parts = []
        source_mapping = {}
        retrieved_results = []

        for result_number, chunk_index in enumerate(
            top_indices,
            start=1,
        ):
            chunk = chunks[chunk_index]
            score = float(scores[chunk_index])
            source_id = f"S{result_number}"

            source_mapping[source_id] = (
                f"[{chunk['source']}，第{chunk['page']}页]"
            )

            context_parts.append(
                f"[{source_id}]\n"
                f"来源文件：{chunk['source']}\n"
                f"PDF页码：{chunk['page']}\n"
                f"原文：{chunk['text']}"
            )

            retrieved_results.append({
                "source_id": source_id,
                "source": chunk["source"],
                "page": chunk["page"],
                "chunk_id": chunk["chunk_id"],
                "score": score,
                "text": chunk["text"],
            })

        context = "\n\n".join(context_parts)

    system_prompt = """
你是一名严谨的科研文献问答助手。

规则：
1. 只能依据提供的论文证据回答。
2. 使用中文回答，专业术语可以保留英文。
3. 每个关键结论必须引用证据编号，例如：[S1]。
4. 只能使用已经提供的证据编号。
5. 不要自行书写文件名或页码。
6. 证据不足时，明确说明无法确认。
7. 区分论文结论、模型设置和背景信息。
"""

    user_prompt = f"""
用户问题：
{question}

论文证据：
{context}

请严格依据以上证据回答。
"""

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    with st.spinner("正在生成回答……"):
        try:
            response = client.chat.completions.create(
                model="deepseek-flash",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.1,
                stream=False,
            )

            answer = response.choices[0].message.content

            for source_id, source_text in source_mapping.items():
                answer = answer.replace(
                    f"[{source_id}]",
                    source_text,
                )

            for source_text in set(source_mapping.values()):
                duplicated = source_text + source_text

                while duplicated in answer:
                    answer = answer.replace(
                        duplicated,
                        source_text,
                    )

            st.subheader("回答")
            st.markdown(answer)

            st.subheader("检索证据")

            for result in retrieved_results:
                title = (
                    f"{result['source_id']}｜"
                    f"第 {result['page']} 页｜"
                    f"相似度 {result['score']:.4f}"
                )

                with st.expander(title):
                    st.write("文件：", result["source"])
                    st.write("文本块：", result["chunk_id"])
                    st.write(result["text"])

        except Exception as error:
            st.error("DeepSeek 调用失败")
            st.exception(error)
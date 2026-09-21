"""
Loads hotel_data.csv, converts each row into a text document,
embeds with sentence-transformers, and persists to ChromaDB.

Run once (or re-run to refresh):  python ingest.py
"""

import os
import pandas as pd
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

CSV_PATH = "data/hotel_data.csv"
CHROMA_DIR = "chroma_db"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_documents(csv_path: str) -> list[Document]:
    df = pd.read_csv(csv_path)
    docs = []
    for _, row in df.iterrows():
        text = str(row.get("content", "")).strip()
        if not text:
            continue
        metadata = {
            "category": str(row.get("category", "")) if pd.notna(row.get("category")) else "",
            "name": str(row.get("name", "")) if pd.notna(row.get("name")) else "",
        }
        docs.append(Document(page_content=text, metadata=metadata))
    return docs


def build_vectorstore(docs: list[Document], persist_dir: str) -> Chroma:
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=persist_dir,
    )
    return vectorstore


if __name__ == "__main__":
    print(f"Loading documents from {CSV_PATH} ...")
    docs = load_documents(CSV_PATH)
    print(f"  {len(docs)} documents loaded.")

    print(f"Building ChromaDB at ./{CHROMA_DIR} ...")
    vs = build_vectorstore(docs, CHROMA_DIR)
    print(f"  Done. {vs._collection.count()} vectors stored.")

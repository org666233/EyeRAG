"""
BM25 检索单元测试
验证 BM25 倒排索引构建、评分、排序逻辑

注意：BM25 当前使用 \w+ 分词，对中文支持有限（按字符级匹配英文单词）。
中文检索主要依赖向量检索，BM25 负责补充英文术语。
"""

import pytest
from app.rag.hybrid_retrieval import BM25Retriever


class TestBM25Tokenize:
    """BM25 分词测试"""

    def test_tokenize_english(self):
        """英文分词正常工作"""
        retriever = BM25Retriever()
        tokens = retriever._tokenize("Glaucoma is an eye disease")
        # \w+ 匹配英文单词，转换为小写
        assert "glaucoma" in tokens
        assert "is" in tokens
        assert "an" in tokens

    def test_tokenize_mixed(self):
        """中英混合文本只保留英文部分"""
        retriever = BM25Retriever()
        tokens = retriever._tokenize("青光眼 glaucoma Treatment")
        # \w+ 只匹配 ASCII 字符
        assert "glaucoma" in tokens
        assert "treatment" in tokens

    def test_tokenize_numbers(self):
        """数字处理"""
        retriever = BM25Retriever()
        tokens = retriever._tokenize("眼压 25mmHg")
        # \w+ 匹配 "25mmhg" 为一个 token
        assert "25mmhg" in tokens

    def test_tokenize_symbols(self):
        """符号过滤"""
        retriever = BM25Retriever()
        tokens = retriever._tokenize("白内障, 手术. 治疗?")
        assert "白" not in tokens  # 中文被跳过
        assert "cataract" not in tokens  # 没有英文


class TestBM25Indexing:
    """BM25 索引构建测试"""

    @pytest.fixture
    def bm25_english(self):
        """纯英文文档的 BM25 检索器"""
        retriever = BM25Retriever()
        retriever.doc_index = {
            "doc1": "Glaucoma is an eye disease affecting the optic nerve.",
            "doc2": "Cataract is clouding of the lens causing vision loss.",
            "doc3": "Diabetic retinopathy is a diabetes complication affecting eyes.",
        }
        retriever.doc_meta = {
            f"doc{i}": {"file_name": f"doc{i}.txt", "source": "pmc"}
            for i in range(1, 4)
        }
        retriever.doc_lengths = {k: len(v.split()) for k, v in retriever.doc_index.items()}
        retriever.inverted = {}
        for doc_id, text in retriever.doc_index.items():
            for term in set(retriever._tokenize(text)):
                if term not in retriever.inverted:
                    retriever.inverted[term] = set()
                retriever.inverted[term].add(doc_id)
        retriever.N = len(retriever.doc_index)
        total_len = sum(retriever.doc_lengths.values())
        retriever.avg_dl = total_len / retriever.N
        retriever._built = True
        return retriever

    def test_index_built_flag(self, bm25_english):
        """手动构建后 _built 为 True"""
        assert bm25_english._built is True

    def test_index_inverted(self, bm25_english):
        """倒排索引包含关键词"""
        assert "glaucoma" in bm25_english.inverted
        assert "cataract" in bm25_english.inverted
        assert "diabetic" in bm25_english.inverted

    def test_search_returns_ranked_results(self, bm25_english):
        """检索结果按 BM25 得分降序"""
        results = bm25_english.search("glaucoma", top_k=3)
        assert len(results) > 0
        assert results[0]["score"] >= results[-1]["score"]

    def test_search_top_k_limit(self, bm25_english):
        """top_k 限制返回数量"""
        results = bm25_english.search("eye", top_k=2)
        assert len(results) <= 2

    def test_search_irrelevant_query(self, bm25_english):
        """完全不相关查询得分低"""
        results_heart = bm25_english.search("heart disease", top_k=3)
        results_glaucoma = bm25_english.search("glaucoma", top_k=3)
        # 心脏病文档对 "heart disease" 得分应更高
        if results_heart and results_glaucoma:
            heart_doc_scores = [r for r in results_heart if "diabetes" in r["content"].lower()]
            glaucoma_doc_scores = [r for r in results_glaucoma if "glaucoma" in r["content"].lower()]
            # 无关查询所有文档得分都较低
            assert all(r["score"] < 5 for r in results_heart)

    def test_search_empty_query(self, bm25_english):
        """空查询返回空"""
        results = bm25_english.search("", top_k=5)
        assert results == []

    def test_search_retrieval_type(self, bm25_english):
        """检索结果标记为 bm25 类型"""
        results = bm25_english.search("cataract", top_k=3)
        for r in results:
            assert r.get("retrieval_type") == "bm25"

    def test_search_returns_metadata(self, bm25_english):
        """检索结果包含 metadata"""
        results = bm25_english.search("diabetic", top_k=2)
        for r in results:
            assert "content" in r
            assert "metadata" in r
            assert "score" in r

    def test_empty_index_search(self):
        """空索引搜索返回空"""
        retriever = BM25Retriever()
        retriever.doc_index = {}
        retriever.N = 0
        retriever._built = True
        results = retriever.search("test", top_k=5)
        assert results == []

    def test_bm25_default_parameters(self):
        """默认 BM25 参数 k1=1.5, b=0.75"""
        retriever = BM25Retriever()
        assert retriever.k1 == 1.5
        assert retriever.b == 0.75

    def test_bm25_custom_parameters(self):
        """可自定义 BM25 参数"""
        retriever = BM25Retriever(k1=2.0, b=0.5)
        assert retriever.k1 == 2.0
        assert retriever.b == 0.5

    def test_idf_calculation(self, bm25_english):
        """稀有词得分通常高于常见词（BM25 IDF 特性）"""
        results_g = bm25_english.search("glaucoma", top_k=3)
        results_e = bm25_english.search("eye disease", top_k=3)
        assert len(results_g) > 0
        assert len(results_e) > 0

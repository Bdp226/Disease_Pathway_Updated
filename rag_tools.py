import os
import re
import time
from typing import List, Dict, Any
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi


EVAL_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or",
    "that", "the", "this", "to", "with", "patient", "patients", "disease", "diseases", "stage", "stages",
    "pain", "point", "points", "care", "clinical", "treatment", "management"
}

class AdvancedRAG:
    def __init__(self, embeddings_model):
        self.embeddings = embeddings_model
        
    def perform_hybrid_search(self, query: str, faiss_store: FAISS, k: int = 10, alpha: float = 0.5) -> List[Dict[str, Any]]:
        """
        Combines Semantic Search (FAISS) and Keyword Search (BM25) using Reciprocal Rank Fusion (RRF).
        This approach runs 100% locally without requiring external cross-encoder models to be downloaded.
        """
        # We retrieve candidates from FAISS
        fetch_k = max(k * 2, 20)
        docs = faiss_store.similarity_search(query, k=fetch_k)
        
        if not docs:
            return []

        # For a true RRF, we'd also run BM25 on the full corpus, but since we don't have the corpus list 
        # easily accessible, we'll apply BM25 re-ranking on the retrieved FAISS chunks.
        tokenized_corpus = [doc.page_content.lower().split() for doc in docs]
        bm25 = BM25Okapi(tokenized_corpus)
        
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # Combine using a simple normalized scoring (approximating RRF)
        # FAISS docs are ordered by semantic relevance (index 0 is best)
        results = []
        for i, doc in enumerate(docs):
            # Semantic rank score (higher is better, max is fetch_k)
            semantic_score = fetch_k - i
            # Keyword score
            keyword_score = bm25_scores[i]
            
            # Combined score
            combined_score = (alpha * semantic_score) + ((1 - alpha) * keyword_score)
            results.append({
                "doc": doc,
                "score": combined_score
            })
            
        # Sort by combined score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        top_k = results[:k]
        
        final_results = []
        for item in top_k:
            final_results.append({
                "text": item["doc"].page_content,
                "metadata": item["doc"].metadata,
                "relevance_score": float(item["score"])
            })
            
        return final_results


def _tokenize_eval(text: str) -> List[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    tokens = [t for t in cleaned.split() if len(t) > 2 and t not in EVAL_STOPWORDS]
    return tokens


def build_synthetic_benchmark_cases(pathway_data: Dict[str, Any], max_cases_per_disease: int = 12) -> List[Dict[str, Any]]:
    """Build deterministic benchmark cases from staged pain-point data.

    Each case contains:
    - query
    - disease_name
    - expected_stage
    - expected_keywords
    """
    if not pathway_data:
        return []

    disease_name = (pathway_data.get("disease_name") or "").lower().strip()
    stages = pathway_data.get("stages", {}) or {}
    cases: List[Dict[str, Any]] = []

    for stage_name, stage_data in stages.items():
        for pp in stage_data.get("pain_points", []) or []:
            description = (pp.get("description") or "").strip()
            if not description:
                continue

            keywords = []
            for tok in _tokenize_eval(description):
                if tok not in keywords:
                    keywords.append(tok)
                if len(keywords) >= 6:
                    break

            if not keywords:
                continue

            query = f"What are key pain points in {stage_name} for {disease_name}?"
            cases.append(
                {
                    "query": query,
                    "disease_name": disease_name,
                    "expected_stage": stage_name,
                    "expected_keywords": keywords,
                }
            )

            if len(cases) >= max_cases_per_disease:
                return cases

    return cases


class RAGEvaluator:
    """Quantitative retrieval evaluator for local RAG performance tracking."""

    def _is_relevant(self, result: Dict[str, Any], expected_keywords: List[str], expected_stage: str = "") -> bool:
        text = (result.get("text") or "").lower()
        stage = (result.get("stage") or "").lower()
        expected_stage_l = (expected_stage or "").lower()

        # Allow stage-aware relevance: if stage matches, require lighter keyword overlap.
        keyword_hits = sum(1 for k in expected_keywords if k and k.lower() in text)
        stage_match = expected_stage_l and expected_stage_l in stage

        if stage_match and keyword_hits >= 1:
            return True
        return keyword_hits >= 2

    def evaluate(self, cases: List[Dict[str, Any]], retrieve_fn, k: int = 5) -> Dict[str, Any]:
        """Evaluate retrieval with Hit@k, Precision@k, MRR, Recall@k, and latency stats.

        retrieve_fn signature: retrieve_fn(query: str, disease_name: str, k: int) -> List[Dict[str, Any]]
        """
        if not cases:
            return {
                "summary": {
                    "total_queries": 0,
                    "hit_rate_at_k": 0.0,
                    "precision_at_k": 0.0,
                    "recall_at_k": 0.0,
                    "mrr": 0.0,
                    "avg_latency_ms": 0.0,
                    "p95_latency_ms": 0.0,
                    "k": k,
                },
                "per_query": [],
            }

        hit_count = 0
        precision_sum = 0.0
        recall_sum = 0.0
        reciprocal_rank_sum = 0.0
        latencies_ms: List[float] = []
        per_query = []

        for case in cases:
            query = case.get("query", "")
            disease_name = case.get("disease_name", "")
            expected_keywords = case.get("expected_keywords", []) or []
            expected_stage = case.get("expected_stage", "")

            start = time.perf_counter()
            results = retrieve_fn(query, disease_name, k)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)

            if not isinstance(results, list):
                results = []

            relevances = [self._is_relevant(r, expected_keywords, expected_stage) for r in results]
            relevant_count = sum(1 for x in relevances if x)
            hit = relevant_count > 0
            hit_count += 1 if hit else 0

            precision = relevant_count / max(k, 1)
            precision_sum += precision

            # For this benchmark set, each case expects at least one matching pain point context.
            recall = 1.0 if hit else 0.0
            recall_sum += recall

            rr = 0.0
            for idx, rel in enumerate(relevances, start=1):
                if rel:
                    rr = 1.0 / idx
                    break
            reciprocal_rank_sum += rr

            per_query.append(
                {
                    "query": query,
                    "disease_name": disease_name,
                    "expected_stage": expected_stage,
                    "hit": hit,
                    "precision_at_k": round(precision, 4),
                    "reciprocal_rank": round(rr, 4),
                    "latency_ms": round(elapsed_ms, 2),
                    "top_stage_predictions": [r.get("stage", "") for r in results[:3]],
                }
            )

        total = len(cases)
        lat_sorted = sorted(latencies_ms)
        p95_idx = max(0, min(len(lat_sorted) - 1, int(0.95 * len(lat_sorted)) - 1))

        return {
            "summary": {
                "total_queries": total,
                "hit_rate_at_k": round(hit_count / total, 4),
                "precision_at_k": round(precision_sum / total, 4),
                "recall_at_k": round(recall_sum / total, 4),
                "mrr": round(reciprocal_rank_sum / total, 4),
                "avg_latency_ms": round(sum(latencies_ms) / total, 2),
                "p95_latency_ms": round(lat_sorted[p95_idx], 2),
                "k": k,
            },
            "per_query": per_query,
        }


from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_ollama import ChatOllama
class GraphRAG:
    def __init__(self, uri="bolt://neo4j:7687", user="neo4j", password="password", model="llama3"):
        neo4j_uri = os.environ.get("NEO4J_URI", uri)
        neo4j_user = os.environ.get("NEO4J_USER", user)
        neo4j_password = os.environ.get("NEO4J_PASSWORD", password)
        
        try:
            self.graph = Neo4jGraph(
                url=neo4j_uri, username=neo4j_user, password=neo4j_password
            )
            # Use Llama3 to generate Cypher and answer
            self.llm = ChatOllama(model=model, temperature=0)
            self.chain = GraphCypherQAChain.from_llm(
                cypher_llm=self.llm,
                qa_llm=self.llm,
                graph=self.graph,
                verbose=True,
                allow_dangerous_requests=True # Required by newer langchain for db access
            )
        except Exception as e:
            print(f"Failed to initialize GraphRAG: {e}")
            self.graph = None
            self.chain = None

    def query(self, question: str) -> str:
        """Query the Knowledge Graph using natural language."""
        if not self.chain:
            return "Graph database connection is not available."
        
        try:
            # Refresh schema before querying
            self.graph.refresh_schema()
            response = self.chain.invoke({"query": question})
            return response.get("result", "I could not find an answer in the graph.")
        except Exception as e:
            print(f"GraphRAG error: {e}")
            return f"Error querying the graph: {str(e)}"

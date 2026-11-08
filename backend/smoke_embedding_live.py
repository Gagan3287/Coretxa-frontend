"""
Live smoke test for Google embedding models:
  - gemini-embedding-001
  - gemini-embedding-2-preview
Validates vector length == 768, computes L2 norm, and checks cosine similarities.
Never prints API keys or raw vector values.
"""
import asyncio
import math
from app.services.embedding import embed_texts

SENTENCES = {
    "a": "How many casual leaves do staff get?",
    "b": "Employees are entitled to twelve casual leaves per year.",
    "c": "The cafeteria serves lunch from noon.",
}

MODELS = [
    "gemini-embedding-001",
    "gemini-embedding-2-preview",
]


def l2_norm(vec: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def cosine_similarity(u: list[float], v: list[float]) -> float:
    dot = sum(a * b for a, b in zip(u, v))
    nu = l2_norm(u)
    nv = l2_norm(v)
    if nu == 0.0 or nv == 0.0:
        return 0.0
    return dot / (nu * nv)


async def test_model(model_name: str) -> bool:
    print(f"\nModel: {model_name}")
    print("-" * 50)
    texts = [SENTENCES["a"], SENTENCES["b"], SENTENCES["c"]]
    vectors = await embed_texts(texts, model=model_name)

    vec_a, vec_b, vec_c = vectors[0], vectors[1], vectors[2]

    norm_a = l2_norm(vec_a)
    norm_b = l2_norm(vec_b)
    norm_c = l2_norm(vec_c)

    print(f"Sentence (a) -> length: {len(vec_a)}, L2 norm: {norm_a:.6f}")
    print(f"Sentence (b) -> length: {len(vec_b)}, L2 norm: {norm_b:.6f}")
    print(f"Sentence (c) -> length: {len(vec_c)}, L2 norm: {norm_c:.6f}")

    sim_ab = cosine_similarity(vec_a, vec_b)
    sim_ac = cosine_similarity(vec_a, vec_c)

    print(f"Cosine similarity (a, b): {sim_ab:.6f}")
    print(f"Cosine similarity (a, c): {sim_ac:.6f}")

    passed = (
        len(vec_a) == 768
        and len(vec_b) == 768
        and len(vec_c) == 768
        and sim_ab > sim_ac
    )
    print(f"Status: {'PASS' if passed else 'FAIL'} (sim(a,b) > sim(a,c): {sim_ab > sim_ac})")
    return passed


async def main():
    print("=== Live Google Embedding Smoke Test ===")
    results = {}
    for m in MODELS:
        results[m] = await test_model(m)

    print("\n" + "=" * 50)
    print("Summary of models passing:")
    for m, ok in results.items():
        print(f"  {m}: {'PASS' if ok else 'FAIL'}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

import sys
import time
from pipeline.rag import ask

question = "Comment divorcer ?"

print("Running 5 tests with cache DISABLED (log_to_db=False) to observe model variance...\n")

results = []
for i in range(5):
    print(f"--- Test {i+1} ---")
    t0 = time.time()
    res = ask(question, log_to_db=False)
    t1 = time.time()
    
    print(f"Time taken: {t1-t0:.2f}s")
    print(f"Retrieved chunks: {res.retrieved_count}")
    print(f"Answer snippet: {res.answer[:150]}...\n")
    results.append(res.answer)

print("\n--- Comparison ---")
for i, ans in enumerate(results):
    print(f"\nResult {i+1} length: {len(ans)} chars")


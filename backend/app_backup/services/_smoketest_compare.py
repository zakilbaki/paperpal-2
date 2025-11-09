from compare import similarity

if __name__ == "__main__":
    a = "Graph neural networks model relational data with message passing."
    b = "GNNs propagate information along edges to learn on graphs."
    s = similarity(a, b)
    print(f"[OK] Similarity: {s:.3f}")
    # simple guard rails
    if not (0.5 <= s <= 1.0):
        raise SystemExit("[FAIL] similarity out of expected range")

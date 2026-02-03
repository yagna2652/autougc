"""
AutoUGC - Simple UGC Video Generation.

A minimal pipeline that analyzes TikTok videos and generates
similar style videos for your products.

Usage:
    from src.pipeline import create_initial_state, run_pipeline

    state = create_initial_state(
        video_url="https://tiktok.com/...",
        product_description="My product",
    )

    result = run_pipeline(state)
    print(result["generated_video_url"])
"""

__version__ = "0.2.0"

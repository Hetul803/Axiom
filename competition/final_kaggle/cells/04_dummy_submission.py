import os
if not bool(os.getenv("KAGGLE_IS_COMPETITION_RERUN")):
    import pandas as pd
    submission = pd.DataFrame(
        data=[["1_0", "1", True, 1]],
        columns=["row_id", "game_id", "end_of_game", "score"],
    )
    submission.to_parquet(
        "/kaggle/working/submission.parquet",
        index=False,
    )

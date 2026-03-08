from app.engine.run import run_from_files


def run(payload: dict) -> dict:
    return run_from_files(payload)

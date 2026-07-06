"""Pipeline entrypoints."""


def run_twitter_etl():
    from twitter_etl import run_twitter_etl as run

    return run()

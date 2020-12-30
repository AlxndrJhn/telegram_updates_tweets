from pathlib import Path

import telegram_updates_tweets
from poetry_publish.publish import poetry_publish


def publish():
    poetry_publish(
        package_root=Path(telegram_updates_tweets.__file__).parent.parent,
        version=telegram_updates_tweets.__version__,
    )

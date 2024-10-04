import logging
import os

import connexion  # type: ignore
import nltk
from dotenv import load_dotenv

load_dotenv()

# download nltk data
nltk.download("stopwords")
nltk.download("punkt")

API_VERSION = "api.yaml"
EXTENDED_STOPWORDS = set()


class UpstreamProviderError(Exception):
    def __init__(self, message) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message


def create_app() -> connexion.FlaskApp:
    app = connexion.FlaskApp(__name__, specification_dir="../../.openapi")
    app.add_api(
        API_VERSION, resolver=connexion.resolver.RelativeResolver("provider.app")
    )
    logging.basicConfig(level=logging.INFO)
    flask_app = app.app
    config_prefix = os.path.split(os.getcwd())[1].upper()
    flask_app.config.from_prefixed_env(config_prefix)
    flask_app.config["APP_ID"] = config_prefix

    if extended_stopwords := flask_app.config.get("EXTENDED_STOPWORDS", ""):
        EXTENDED_STOPWORDS.update(set(extended_stopwords.split()))

    return flask_app

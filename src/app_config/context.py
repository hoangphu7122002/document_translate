import logging
import pymongo
from pymongo.server_api import ServerApi
import certifi

logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.ERROR)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class MongoContext:
    """
    Mongodb application context
    """

    def __init__(self, config):
        log.info("Initialize context of application using mongodb...")
        self.mongo_host = config.get("mongodb", "mongodb.host")
        self.mongo_user = config.get("mongodb", "mongodb.username")
        self.mongo_pass = config.get("mongodb", "mongodb.password")
        self.mongo_db = config.get("mongodb", "mongodb.database")
        self.mongo_uri = "mongodb+srv://%s:%s@%s/?authSource=admin" % (
            self.mongo_user,
            self.mongo_pass,
            self.mongo_host,
        )
        self.mongo_client = pymongo.MongoClient(self.mongo_uri, server_api=ServerApi('1'), tlsCAFile=certifi.where())[self.mongo_db]
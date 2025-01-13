from src.utils.config import Config
# from src.app_config.context import MongoContext
from src.processors.translate_pipeline import TranslatePipeline
# from src.api.services.service import SummaryService

"""
Use lazy loading to initiate all instances need for backend application and store in 'globals'
"""


def use_config(config_file):
    config = Config(config_file)
    register("config", config)

def register(instance_name, instance):
    globals()[instance_name] = instance

def get(instance_name):
    instance = globals().get(instance_name)
    if instance is None:
        # if instance_name == "mongo_context":
        #     config = get("config")
        #     instance = MongoContext(config)
        # elif instance_name == 'mongo_client':
        #     mongo_context = get("mongo_context")
        #     instance = mongo_context.mongo_client
        if instance_name == 'translate_pipeline':
            instance = TranslatePipeline()
        # elif instance_name == 'summary_service':
            # instance = SummaryService()
        elif instance_name == 'model_infer':
            from src.processors.translate_infer import InferEngine
            instance = InferEngine()
        register(instance_name, instance)
    return instance
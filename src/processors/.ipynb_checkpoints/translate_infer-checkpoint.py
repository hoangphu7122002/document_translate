from huggingface_hub.hf_api import HfFolder
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from src.processors.base_processor import BaseProcessor
from src.app_config import app_context

class SingletonMeta(type):
    """
    The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class MyInstanceModel(metaclass=SingletonMeta):
    def __init__(self,config):
        HfFolder.save_token(config.get('huggingface', 'token.key'))
        self.model_name = config.get('huggingface', 'model.name')
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name,skip_special_tokens=False)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to('cuda')
        
    def get_model(self):
        return self.model

    def get_tokenizer(self):
        return self.tokenizer
    
class InferEngine(BaseProcessor):
    
    def __init__(self):
        super().__init__()
        self.config = app_context.get('config')
        self.model, self.tokenizer = self.load_model()
        
    def load_model(self):
        ins = MyInstanceModel(self.config)
        return ins.get_model(), ins.get_tokenizer()
    
    def inference(self, inp, en_vi=False):
        if type(inp) == str:
            inp = [inp]
        if en_vi == False: inp = ['vi: ' + ele for ele in inp]
        else: inp = ['en: ' + ele for ele in inp]

        batch_token = self.tokenizer(inp, return_tensors="pt", padding=True, max_length = 1024).input_ids.to('cuda')
        outputs = self.model.generate(batch_token,max_length=1024)
        list_output = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
        
        return list_output
            
            





        
from huggingface_hub.hf_api import HfFolder
from vllm.lora.request import LoRARequest
from vllm import LLM, SamplingParams
from huggingface_hub import snapshot_download
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

    def __init__(self, config):
        HfFolder.save_token(config.get('huggingface', 'token.key'))
        self.model = LLM(model=config.get('huggingface', 'model.name'),
                         enable_lora=True, max_lora_rank=64, gpu_memory_utilization=0.8)

        section = snapshot_download(repo_id=config.get('huggingface', 'model.section'))
        table = snapshot_download(repo_id=config.get('huggingface', 'model.table'))
        multitask = snapshot_download(repo_id=config.get('huggingface', 'model.multitask'))
        docs_sum = snapshot_download(repo_id=config.get('huggingface', 'model.docs_sum'))

        self.lora_mode = {
            "section": section,
            "table": table,
            "multitask": multitask,
            "docs_sum": docs_sum
        }

    def get_model(self):
        return self.model

    def get_snapshot(self):
        return self.lora_mode


class InferEngine(BaseProcessor):

    def __init__(self):

        super().__init__()

        self.config = app_context.get('config')

        self.model, self.lora_mode = self.load_model()
        self.sampling_params = self.set_sampling_param()
        self.multitask = bool(self.config.get('model', 'multitask'))

        self.dict_ref_lora = {
            "section": (1, "section_adapter"),
            "table": (2, "table_adapter"),
            "multitask": (3, "multitask_adapter"),
            "docs_sum": (4, "docs_sum_adapter")
        }

    def set_sampling_param(self, sampling=None):
        if sampling == None:
            return SamplingParams(
                temperature=0,
                top_k=1,
                max_tokens=2000,
                stop=["</s>"]
            )
        return sampling

    def load_model(self):
        ins = MyInstanceModel(self.config)
        return ins.get_model(), ins.get_snapshot()

    def get_prompt_batch(self, input, mode):
        return [self.get_prompt(ele, mode) for ele in input]

    def get_prompt(self, input, mode):
        if mode == 'section':
            len_word = len(input.split(' '))
            prompt1 = f''' Tóm tắt văn bản sau với số từ lớn hơn 100 từ và bé hơn 150 từ, không sinh ra các nội dung không có trong văn bản'''
            prompt2 = f'''Tóm tắt văn bản sau với số từ lớn hơn 200 từ và bé hơn 250 từ, không sinh ra các nội dung không có trong văn bản'''
            prompt3 = f'''Tóm tắt văn bản sau với số từ lớn hơn 300 từ, không sinh ra các nội dung không có trong văn bản'''
            prompt4 = f'''Tóm tắt văn bản sau với số từ lớn hơn 400 từ, không sinh ra các nội dung không có trong văn bản'''
            if len_word <= 250:
                prompt_choose = prompt1
            elif len_word <= 650:
                prompt_choose = prompt2
            elif len_word <= 900:
                prompt_choose = prompt3
            else:
                prompt_choose = prompt4
            prompt_choose += ', trình bày theo dạng gạch đầu dòng' + f''', văn bản cần tóm tắt {input}. ## Nội dung tóm tắt:'''
            return prompt_choose

        elif mode == 'table':
            return f"""Tóm tắt thông tin dạng bảng dưới dạng văn xuôi, với bảng biểu diễn dưới dạng các trường dữ liệu sẽ nằm trong cặp tag <field><field> và các hàng sẽ cách nhau bằng dấu '\n', ###thông tin bảng: {input} ## Nội dung tóm tắt:"""

        elif mode == 'docs_sum':
            len_word = len(input.split(' '))
            if len_word <= 1000:
                ratio = 0.4
            elif len_word <= 2000:
                ratio = 0.3
            elif len_word <= 3000:
                ratio = 0.2
            else:
                ratio = 0.1
            prompt = f'''Tóm tắt văn bản dài sau bằng cách đưa ra các ý chính nhất và diễn đạt lại thành văn bản, lưu ý số từ phải lớn hơn bằng >= {ratio} số từ ban đầu, văn bản cần tóm tắt là: {input}. ## Nội dung tóm tắt: '''
            return prompt

    def inference(self, input, mode, multitask=None):
        if type(input) == str:
            input = [input]

        prompt = self.get_prompt_batch(input, mode)
        filtered_prompt = [p for p in prompt if len(p) > 0]

        if (multitask is None and self.multitask is True) or (multitask is True):
            mode = 'multitask'

        name_ref_lora = self.dict_ref_lora[mode]
        lora_path = self.lora_mode[mode]

        result = self.model.generate(
            filtered_prompt,
            self.sampling_params,
            lora_request=LoRARequest(name_ref_lora[1], name_ref_lora[0], lora_path)
        )

        list_output = [r.outputs[0].text for r in result]

        return list_output

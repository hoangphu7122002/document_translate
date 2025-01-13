from src.processors.pdf_processor import PDFProcessor
from src.processors.section_parser import SectionHierarchicalParser
from src.processors.section_merger import SectionMerger
from src.processors.base_processor import BaseProcessor
from src.app_config import app_context
from tqdm import tqdm
import logging
import re

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s %(message)s', level=logging.INFO)

def num_cut(s,target):
    j = 0
    count = 0

    s = s.split(' ')
    target = target.split(' ')

    for i in range(len(s)):
        if s[i] == target[j]:
            j += 1
            if j == len(target):
                j = 0
                count += 1
        else:
            j = 0
            if (s[i] == target[j]):
                j += 1

    return count

def LMAS(s):
    words = s.split()
    dict_count = {}
    for dist in range(1, len(words) - 1):
        for i in range(0,len(words) - dist + 1):
            j = i + dist
            if dist == 1:
                dict_count[words[i]] = dict_count.get(words[i],0) + 1
            else:
                substr = " ".join(words[i:j])
                dict_count[substr] = dict_count.get(substr,0) + 1

    count = -1
    save_str = ""
    
    for k,v in dict_count.items():
        str_temp = k
        if len(str_temp) >= len(s) * 0.5:
            continue
        count_temp = num_cut(s, str_temp)
        if count_temp == 1: continue

        if count_temp * (len(str_temp) + 1) > count * (len(save_str) + 1):
            count = count_temp
            save_str = str_temp
            # print(save_str," ",count," ",v)
            
    return save_str,count

def replace_LMAS(s):
    s = s.strip()
    s = re.sub(r"\s+"," ",s)
    
    pattern,count = LMAS(s)
    len_word = len(pattern.split(' '))
    if count == -1: return s
    
    words = s.split(' ')
    word = pattern
    if len_word == 1:
        if count <= 5: return s
        if count <= 0.05 * len(s):
            return s
        if word == words[-1]:
            save = -1
            for j in range(len(words)):
                if word == words[j]:
                    continue
                else:
                    save = j
                    break

            s = s[:j]
            return s
            
    if len_word <= 3 and count <= 5:
        return s
    
    idx = s.find(pattern)
    s = s[:idx + len(pattern)]

    return s

def add_newline_before_headings(text):
    # Biểu thức regex nhận diện các tiêu đề dạng số hoặc chữ cái, ví dụ: "1.", "2.", "III.", "Part I"
    pattern = r'(\b\d+\.\s|\b[A-Z]+\.\s|Part\s+[A-Z]+|\b[a-z]\)\s|\b[a-z]\/\s)'
    
    # Thêm newline trước các đề mục tìm thấy
    new_text = re.sub(pattern, r'\n\1', text)
    
    return new_text.strip()  # Xóa khoảng trắng không cần thiết ở đầu và cuối

def get_depth(item):
    if isinstance(item, str) or (isinstance(item, dict) and len(item['child']) == 0):
        return 1
    return 1 + max(get_depth(child) for child in item['child'])

class TranslatePipeline(BaseProcessor):
    RETRY = False
    
    def __init__(self):
        super().__init__()

        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)

        self.config = app_context.get('config')
        
        self.pdf = PDFProcessor()
        self.model_infer = app_context.get('model_infer')
        self.section_parser = SectionHierarchicalParser()
        self.section_merger = SectionMerger()
        
        # self.batch_size = 4
        # self.min_length = 300
        # self.max_length = 300

        self.batch_size = int(self.config.get('pipeline', 'batch_size'))
        self.min_length = int(self.config.get('pipeline', 'min_length'))
        self.max_length = int(self.config.get('pipeline', 'max_length'))
        
    
    def raw_process(self, docs, en_vi = False):
        docs = [ele.replace('\n','<n>') for ele in docs]
        result = self.model_infer.inference(docs, en_vi)
        res = "\n".join(result).replace('<n>','\n').replace('en:','').replace('vi:','')

        return res
        
    def raw_process_file(self,save_path,en_vi = False):
        text = self.pdf_proc.process_raw_file(save_path)
        text = text.split('.')
        docs = []

        str_temp = ""
        for txt in text:
            str_temp += text + '. ' 
            if len(str_temp.split(' ')) > self.max_length:
                str_temp = str_temp.replace('\n','<n>')
                docs.append(str_temp)
                str_temp = ""
                
        res = ""
        for i in range(0, len(docs), self.batch_size):
            batch = docs[i:i + self.batch_size]
            res += self.model_infer.inference(batch, en_vi).replace('<n>','\n') + '\n'
        res = res.replace('en:','').replace('vi:','')
        return res
    
    def process(self, path=None, doc=None, en_vi = False):
        if path is not None:
            item = path
            item = self.pdf.process(item)
            self.log.info(f'Finish reading file')
            #not support table
            
            item = item['sections']
        elif doc is not None:
            item = doc.split('\n')
        else:
            raise Exception('path or doc must not be None')

        item = self.section_parser.section_parsing(item, max_level=self.max_length)
        item = {'value': '', 'child': item}
        self.log.info('Finish parsing item')
        
        current_target_level = min(get_depth(item) - 1, self.max_length)
        while current_target_level >= 0:
            item = self.section_merger.merge(item, current_target_level, max_length=self.max_length)
            self.log.info(f'Finish merging item at level {current_target_level}')
            current_target_level -= 1            
        
        text_value = [doc['value'] for doc in item['child']]
        batchs = []
        outputs = []
        
        batch = []
        for txt in text_value:
            txt = txt.replace('\n','<n>')
            batch.append(txt)
            if len(batch) == self.batch_size:
                batchs.append(batch)
                batch = []

        for batch in tqdm(batchs):
            result = self.model_infer.inference(batch, en_vi)
            for res in result:
                # res = res.replace(' - ',' \n- ')
                # res = add_newline_before_headings(res).replace('en:','').replace('vi:','')
                res = res.replace('en:','').replace('vi:','')
                res = replace_LMAS(res)
                res = res.replace('<n>','\n')
                outputs.append(res)

        self.log.info(f'Finish translate!!')
        
        docs = '\n'.join(outputs)
        docs.replace('<n>','\n')
        
        return docs

        # return batchs
import pprint
import regex
import pymupdf4llm
import string
from io import StringIO
import pandas as pd
import pymupdf


class PDFProcessor():
    def __init__(self):
        self.stopword = ['danh mục', 'phụ lục']

    def table_markdown_to_dict(self, table):
        table_str = '\n'.join(table)
        table = pd.read_csv(StringIO(table_str), sep='|')
        table = table.fillna('')
        non_null_cols = [col for col in table.columns if table[col].apply(lambda x: len(str(x).strip()) > 0).any()]
        table = table[non_null_cols].to_dict(orient="records")
        return table

    def process_table(self, md_text):

        md_text_lst = md_text.split('\n')
        parsed_text_lst = []

        tables = {}
        table_flag = 0
        sep_count = 0
        table_count = 0
        for line in md_text_lst:

            # Skip if encounter page break '-----' or empty table rows |----|----|'
            if len(line) > 0 and len(line.replace('|', '').replace('-', '')) == 0:
                continue

            if line.count('|') >= 3:  # If encounter table rows
                if table_flag == 0: # If no table are being tracked
                    tables[f'table_{table_count}'] = [line] # Initiate new table
                    table_flag = 1 # Trigger table flag
                    sep_count = line.count('|') # Track columns count to ensure the next rows belong to the same table
                    parsed_text_lst.append(f'<table_{table_count}>') # Add <table_num> tag to text
                else: # If currently tracking table
                    if line.count('|') == sep_count: # Check if this row has the same number of columns as the table being tracked
                        # Check if the row contains value like "|Col 1|"
                        # -> The original row are splitted into 2 rows due to page break, this row and the previous row are essentially the one single row
                        check_col = bool(regex.search(r'\|Col\d+\|', line))
                        if check_col:
                            # If true, join this row and the previous row and append to the table list
                            line_lst = regex.sub(r'(?<=\|)Col\d+(?=\|)', '', line).split('|')
                            last_line_lst = tables[f'table_{table_count}'].pop().split('|')
                            join_line = [' '.join([col1, col2]) for col1, col2 in zip(last_line_lst, line_lst)]
                            line = '|'.join(join_line)
                        tables[f'table_{table_count}'].append(line)
                    else: # If this row has the different number of columns, append row to a new table
                        table_count += 1
                        tables[f'table_{table_count}'] = [line]
                        sep_count = line.count('|')
                        parsed_text_lst.append(f'<table_{table_count}>')
            else: # If encounter text
                if len(line) > 0 and table_flag == 1: # Reset table variable
                    table_flag = 0
                    sep_count = 0
                    table_count += 1
                parsed_text_lst.append(line) # Add text to text list

        parsed_text = '\n'.join(parsed_text_lst)

        for key in tables.keys():
            tables[key] = self.table_markdown_to_dict(tables[key])
        return tables, parsed_text

    def read_and_remove_addons(self, path):
        doc = pymupdf.open(path)
        md_texts = []
        for ind in range(doc.page_count):
            md_text = pymupdf4llm.to_markdown(path, pages=[ind])
            lines = md_text.split('\n')
            for line in lines:
                # Stop reading if encounter 'Phụ lục' or 'Danh mục' section
                clean_line = None
                for stopword in self.stopword:
                    if stopword in line.lower():
                        if clean_line is None:
                            clean_line = line.strip().replace('\n', ' ').translate(
                                str.maketrans('', '', string.punctuation))
                        clean_line_lst = clean_line.split(' ')
                        if ' '.join(clean_line_lst[:2]).lower() in ['phụ lục', 'danh mục'] and len(clean_line_lst) <= 5:
                            return '\n'.join(md_texts)
                md_texts.append(line)
        return '\n'.join(md_texts)

    def process(self, path):
        md_text = self.read_and_remove_addons(path)

        tables, text = self.process_table(md_text)

        text = regex.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        noi_nhan_flag = 0
        parsed_text_lst = []
        text_lst = ['<SECTION>'] + text.split('\n\n')
        for line in text_lst:
            if len(line) > 0:
                line = line.replace('\n', ' ').strip()
                clean_line = line.translate(str.maketrans('', '', string.punctuation))
                if clean_line.strip().lower() == 'nơi nhận':
                    noi_nhan_flag = 1
                if noi_nhan_flag == 1 and clean_line.isupper():
                    noi_nhan_flag = 0
                    parsed_text_lst.append('<SECTION>')
                parsed_text_lst.append(line)
        return {'tables': tables, 'sections': parsed_text_lst}

    def process_raw_file(self,path):
        md_text = self.read_and_remove_addons(path)
        tables, text = self.process_table(md_text)

        text = regex.sub(r'(?<!\n)\n(?!\n)', ' ', text)

        return text
if __name__ == '__main__':
    pdf = PDFProcessor()
    file_path = 'data/136_KH-UBND_608984.pdf'

    a = pdf.process(file_path)
    pp = pprint.PrettyPrinter(indent=4, depth=None, compact=False)

    pp.pprint(a)


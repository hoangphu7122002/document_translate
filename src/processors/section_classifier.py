import re

import pandas


class SectionClassifier:
    def __init__(self):
        pass

    @staticmethod
    def is_roman(input_str):
        roman = r'^M{0,3}(CM|CD|D?C{0,3})?(XC|XL|L?X{0,3})?(IX|IV|V?I{0,3})?([.)])'
        return bool(re.match(roman, input_str))

    @staticmethod
    def is_number(input_str):
        number = r'^([\s\d]+)([.):])'
        return bool(re.match(number, input_str))

    @staticmethod
    def get_number(input_str):
        try:
            next_word = input_str.split(' ')[1]
            # next_word = re.sub(r'[.,()]+', '', next_word)
            return next_word
        except:
            return None

    @staticmethod
    def starts_with_number_alphabet(input_str, replace=False):
        pattern = r'^([0-9]+|^M{0,3}(CM|CD|D?C{0,3})?(XC|XL|L?X{0,3})?(IX|IV|V?I{0,3})?+|[a-zA-ZàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôốồổỗộơớờởỡợùúũụủưứừửữựỳỵỷỹýÀÁÃẠẢĂẮẰẲẴẶÂẤẦẨẪẬÈÉẸẺẼÊỀẾỂỄỆĐÌÍĨỈỊÒÓÕỌỎÔỐỒỔỖỘƠỚỜỞỠỢÙÚŨỤỦƯỨỪỬỮỰỲỴỶỸÝ])([.)])'
        check = bool(re.match(pattern, input_str))
        if replace:
            if check:
                return ' '.join(input_str.split()[1:])
            else:
                return input_str
        else:
            return check

    @staticmethod
    def is_upper(input_str):
        pattern = r'([A-ZÀÁÃẠẢĂẮẰẲẴẶÂẤẦẨẪẬÈÉẸẺẼÊỀẾỂỄỆĐÌÍĨỈỊÒÓÕỌỎÔỐỒỔỖỘƠỚỜỞỠỢÙÚŨỤỦƯỨỪỬỮỰỲỴỶỸÝ])([.)])'
        return bool(re.match(pattern, input_str))

    @staticmethod
    def is_lower(input_str):
        pattern = r'([a-zàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôốồổỗộơớờởỡợùúũụủưứừửữựỳỵỷỹý])([.)])'
        return bool(re.match(pattern, input_str))

    @staticmethod
    def is_all_uppercase(input_str: str):
        """
        Check if all characters in the input string are uppercase.

        Parameters:
        input_string (str): The input string to be checked.

        Returns:
        bool: True if all characters in the input string are uppercase, False otherwise.
        """
        return input_str.isupper()

    def classify(self, input_str):
        input_str = str(input_str)
        keywords = ["<i>", "<section>"]
        for keyword in keywords:
            if input_str.startswith(keyword):
                return '-1'
        if input_str.startswith("<SECTION>"):
            return '0'

        pattern_1 = r"^(Điều)\s+(.*)$"
        pattern_2 = r"^(Chương)\s+(.*)$"
        pattern_3 = r"^(Phần)\s+(.*)$"
        pattern_4 = r"^(Mục)\s+(.*)$"

        # Điều
        if re.match(pattern_1, input_str):
            if self.is_number(self.get_number(input_str)):
                return '1'
            if self.is_roman(self.get_number(input_str)):
                return '2'
        # Chương
        if re.match(pattern_2, input_str):
            input_str = input_str + '.'
            if self.is_number(self.get_number(input_str)):
                return '3'
            if self.is_roman(self.get_number(input_str)):
                return '4'
        # Phần
        if re.match(pattern_3, input_str):
            input_str = input_str + '.'
            if self.is_number(self.get_number(input_str)):
                return '5'
            if self.is_roman(self.get_number(input_str)):
                return '6'
        # Mục
        if re.match(pattern_4, input_str):
            input_str = input_str + '.'
            if self.is_number(self.get_number(input_str)):
                return '7'
            if self.is_roman(self.get_number(input_str)):
                return '8'

        if self.is_number(input_str):
            return '9'

        if self.is_roman(input_str):
            return '10'

        if self.is_lower(input_str):
            return '11'

        if self.is_upper(input_str):
            return '12'

        if input_str == 'nan' or input_str == '':
            return '-1'
        return '-1'

    @staticmethod
    def calculate_len(row):
        if row['is_section']:
            return len((str(row['section']) + str(row['section_content'])).split(' '))
        else:
            return len(str(row['content']).split(' '))

    def section_classifier(self, df: pandas.DataFrame, infer=False):
        df['section'] = df['section'].apply(lambda x: str(x).strip())
        df['class'] = df['section'].apply(lambda x: self.classify(x))
        if not infer:
            rm_list = list(df[df['class'].isna()].groupby(['_id'])['_id'].value_counts().index)
            df = df[~df['_id'].isin(rm_list)]
        df['len'] = df.apply(lambda x: self.calculate_len(x), axis=1)
        return df

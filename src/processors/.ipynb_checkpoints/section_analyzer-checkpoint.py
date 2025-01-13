import json

import pandas
import regex
from bs4 import BeautifulSoup

# from bs4 import BeautifulSoup

pandas.options.mode.chained_assignment = None


class SectionAnalyzer:
    def __init__(self):
        pass

    def starts_with_keyword(self, input_str: str, replace: bool = False):
        """
        Check if the input string starts with specific keywords or patterns.

        Parameters:
        input_str (str): The input string to be checked.
        replace (bool, optional): If True, replace the keyword with an empty string or return the remaining string after the keyword. Defaults to False.

        Returns:
        bool or str: If `replace` is False, returns True if the input string starts with a keyword or pattern, False otherwise.
                    If `replace` is True, returns the modified string after replacing the keyword with an empty string, or returns the remaining string after the keyword.
        """

        # Keywords to check for at the beginning of the input string
        keywords = ["<i>", "<section>", "<SECTION>"]

        for keyword in keywords:
            if input_str.startswith(keyword):
                if replace:
                    return input_str.replace(keyword, '')
                return True

        pattern = r"^(Điều|Chương|Phần|Mục)\s+(.*)$"
        match = regex.match(pattern, input_str)
        if match:
            try:
                # Extract the next word after the keyword
                next_word = input_str.split(' ')[1]
                # Remove punctuation marks from the next word
                next_word = regex.sub(r'[.,()]+', '', next_word)
                if self.is_number(next_word) and replace:
                    # If replace is True, return the string after removing the keyword and the number
                    return ' '.join(input_str.split()[2:])
                return self.is_number(next_word)  # Return True if the next word is a number or a Roman numeral
            except:
                print("Có ký tự không mong muốn")

        else:
            if replace:
                return input_str
            return False

    @staticmethod
    def starts_with_number_alphabet(input_str: str, replace: bool = False):
        """
        Check if the input string starts with a number, a Roman numeral, or an alphabet character.

        Parameters:
        input_str (str): The input string to be checked.
        replace (bool, optional): If True, returns the remaining string after the initial number, Roman numeral,
                                  or alphabet character. Defaults to False.

        Returns:
        bool or str: If `replace` is False, returns True if the input string starts with a number, a Roman numeral,
                     or an alphabet character, False otherwise.
                     If `replace` is True, returns the modified string after removing the initial number, Roman numeral,
                     or alphabet character.
        """

        # Regular expression pattern to match numbers, Roman numerals, or alphabet characters at the beginning of the
        # input string
        pattern = r'^([0-9]+|^M{0,3}(CM|CD|D?C{0,3})?(XC|XL|L?X{0,3})?(IX|IV|V?I{0,3})?+|[a-zA-ZàáãạảăắằẳẵặâấầẩẫậèéẹẻẽêềếểễệđìíĩỉịòóõọỏôốồổỗộơớờởỡợùúũụủưứừửữựỳỵỷỹýÀÁÃẠẢĂẮẰẲẴẶÂẤẦẨẪẬÈÉẸẺẼÊỀẾỂỄỆĐÌÍĨỈỊÒÓÕỌỎÔỐỒỔỖỘƠỚỜỞỠỢÙÚŨỤỦƯỨỪỬỮỰỲỴỶỸÝ])([.)])'

        # Check if the input string matches the pattern
        check = bool(regex.match(pattern, input_str))

        if replace:
            if check:
                # If the input string matches the pattern and replace is True, return the string after the initial
                # character
                return ' '.join(input_str.split()[1:])
            else:
                return input_str  # Return the input string unchanged if it does not match the pattern
        else:
            return check  # Return True if the input string matches the pattern, False otherwise

    @staticmethod
    def is_number(num: str):
        """
        Determine whether the input is a valid number or a Roman numeral.

        Parameters:
        num (str): The input string to be checked.

        Returns:
        bool: True if the input is a valid number or a Roman numeral, False otherwise.
        """

        # Regular expression pattern for Roman numerals
        roman = regex.compile(r"""^M{0,3}(CM|CD|D?C{0,3})?(XC|XL|L?X{0,3})?(IX|IV|V?I{0,3})?$""", regex.VERBOSE)

        # Regular expression pattern for numbers
        number = regex.compile(r'^([\s\d]+)$')

        # Check if the input matches either the Roman numeral pattern or the number pattern
        if regex.match(roman, num) or regex.match(number, num):
            return True
        return False

    def check_replace_section(self, input_str: str, replace: bool = False):
        """
        Check if the input string starts with a specific keyword, a number, a Roman numeral, or is all uppercase.
        Optionally, replace the starting keyword or characters with an empty string.

        Parameters: input_str (str): The input string to be checked. replace (bool, optional): If True, replaces the
        starting keyword or characters with an empty string. Defaults to False.

        Returns: bool or str:
        If `replace` is False, returns True if the input string starts with a keyword, a number, a Roman numeral,
        or is all uppercase. False otherwise.
        If `replace` is True, returns the modified string after removing the starting keyword or characters.
        """
        if replace:
            if self.starts_with_keyword(input_str):
                return self.starts_with_keyword(input_str, replace)
            if self.starts_with_number_alphabet(input_str):
                return self.starts_with_number_alphabet(input_str, replace)
            return input_str
        else:
            return self.starts_with_keyword(input_str) or self.starts_with_number_alphabet(
                input_str)

    def section_processing(self, df: pandas.DataFrame):
        """
        Process DataFrame containing HTML content and table data to extract sections and content.

        Parameters:
        df (pandas.DataFrame): DataFrame containing columns '_id', 'category', 'link', 'loai_van_ban', 'noi_dung_html', and 'danh_sach_bang'.

        Returns:
        pandas.DataFrame: Processed DataFrame with additional columns 'section', 'is_section', 'section_content', and 'content'.
        """

        # Remove unwanted characters and extra spaces from sections
        df['section'] = df['section'].apply(lambda x: x.replace('\xa0', ' '))
        df['section'] = df['section'].apply(lambda x: x.replace('**', ''))
        df['section'] = df['section'].apply(lambda x: x.replace('\r\n', ' '))
        df['section'] = df['section'].apply(lambda x: x.replace('\n', ' '))
        df['section'] = df['section'].apply(lambda x: x.strip())
        df['section'] = df['section'].apply(lambda x: regex.sub(r'-{3,}', '', x))
        df['section'] = df['section'].apply(lambda x: regex.sub(r'\s+', ' ', x))

        # Drop rows with null values in 'section' column
        df.dropna(subset=['section'], inplace=True)
        df = df[df['section'].str.strip().str.len() > 0]

        # Check if each section is a section or content
        df['is_section'] = df['section'].apply(lambda x: self.check_replace_section(x))

        # Extract section content and remove it from section column
        df['section_content'] = df['section'].apply(lambda x: self.check_replace_section(x, True))
        df['section_content'] = df.apply(lambda row: row['section_content'] if row['is_section'] else '', axis=1)

        # Create 'content' column containing non-section text
        df['content'] = df.apply(lambda row: row['section'] if not row['is_section'] else '', axis=1)

        # Remove section content from section column
        df['section'] = df.apply(lambda row: row['section'].replace(row['section_content'], ''), axis=1)

        # Remove content from section column
        df['section'] = df.apply(lambda row: row['section'] if row['is_section'] else '', axis=1)

        # Reset index of DataFrame
        df = df.reset_index(drop=True)

        return df

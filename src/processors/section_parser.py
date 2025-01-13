import json
import pandas as pd

from src.processors.pdf_processor import PDFProcessor
from src.processors.section_analyzer import SectionAnalyzer
from src.processors.section_classifier import SectionClassifier


class SectionHierarchicalParser():
    def __init__(self):
        pass

    @staticmethod
    def _get_section_class(unique_list, rm_list=None, max_level=3):

        """
        Extracts a list of unique section classes from `unique_list` excluding any classes in `rm_list`,
        up to a maximum of `max_level` classes.
        :param unique_list: A list of unique section classes to be processed.
        :param rm_list: A list of section classes to be removed from `unique_list`. Defaults to ['-1'].
        :param max_level: The maximum number of section classes to be returned. Defaults to 3.
        :return: A list containing up to `max_level` section classes from `unique_list` that are not in `rm_list`.
        """
        if rm_list is None:
            rm_list = ['-1']
        result = []
        index = 0

        while len(result) < max_level and index < len(unique_list):
            if unique_list[index] not in rm_list:
                result.append(unique_list[index])
            index += 1

        return result

    @staticmethod
    def _find_positions_diff_sections(section_class: list, all_class: list):
        """
        Finds the positions of elements from `section_class` in `all_class`, pairs them into adjacent sections
        as they appear in `section_class`, and returns the positions of elements that lie between these pairs.
        :parameter section_class: A list of section classes to find in `all_class`.
        :parameter all_class: The list containing all classes from which positions are to be found.
        :returns:
            A list of positions in `all_class` that lie between the pairs of adjacent elements from `section_class`.
        """
        # Tìm vị trí của các phần tử trong section_class trong all_class
        positions = []
        for section in section_class:
            positions.append([i for i, x in enumerate(all_class) if x == section])

        # Gộp các vị trí lại thành từng cặp liền kề trong section_class
        results = []
        for i in range(len(section_class) - 1):
            start_positions = positions[i]
            end_positions = positions[i + 1]
            for start in start_positions:
                p_end = -1
                for end in end_positions:
                    if start < end:
                        results.append((start, end))
                        if p_end != -1 and start - p_end < 3:
                            results.append((p_end, start))
                        break
                    p_end = end
        results = sorted(results, key=lambda x: (x[1], -x[0]))
        # Kết quả cuối cùng
        result = []
        last_seen = None

        for t in results:
            if t[1] != last_seen:
                result.append(t)
                last_seen = t[1]
        # Tìm vị trí các phần tử nằm giữa các cặp vị trí trong all_class
        between_positions = []
        for start, end in result:
            between_positions.extend(range(start + 1, end))

        return between_positions

    @staticmethod
    def _find_positions_same_sections(section_class, all_class):
        positions = []
        for section in section_class:
            positions.append([i for i, x in enumerate(all_class) if x == section])
        section = []
        for k in range(len(positions) - 1):
            p = positions[k]
            for i in range(len(p) - 1):
                tmp = {}
                for j in range(p[i] + 1, p[i + 1]):
                    if all_class[j] not in section_class:
                        tmp[j] = positions[k + 1][0]
                    else:
                        tmp = {}
                        break
                if tmp:
                    section.append(tmp)

        return section

    @staticmethod
    def _split_by_class(df, section_class):
        split_class = []
        try:
            # Get content first
            df_class = df[~df['class'].isin(section_class)]
            df_class['text'] = df_class.apply(
                lambda row: row['section'] + ' ' + row['section_content'] + ' ' + row['content'], axis=1)
            dict_class = df_class['text'].to_dict()
            split_class.append(dict_class)
        except:
            pass
        section_class.reverse()
        for i in range(len(section_class)):
            df_class = df[df['class'] == section_class[i]]
            df_class['text'] = df_class.apply(
                lambda row: row['section'] + ' ' + row['section_content'] + ' ' + row['content'], axis=1)
            dict_class = df_class['text'].to_dict()
            split_class.append(dict_class)

        return split_class

    @staticmethod
    def _create_child_list(high_lv: dict, low_lv: dict):
        high_key = list(high_lv.keys())
        low_key = list(low_lv.keys())
        child_list = {}

        for i in range(len(high_key)):
            tmp = []
            for j in range(len(low_key)):
                if i < len(high_key) - 1:
                    if high_key[i] < low_key[j] < high_key[i + 1]:
                        tmp.append(low_lv[low_key[j]])
                else:
                    if low_key[j] > high_key[i]:
                        tmp.append(low_lv[low_key[j]])
            child_list[high_key[i]] = {'value': high_lv[high_key[i]], 'child': tmp}
        return child_list

    def _gen_tree_structure(self, split_class: list):
        tmp = self._create_child_list(split_class[1], split_class[0])
        for i in range(2, len(split_class)):
            # print(i)
            tmp = self._create_child_list(split_class[i], tmp)
        return list(tmp.values())

    @staticmethod
    def find_class_end_row(all_class, section_class):
        for i in range(len(all_class) - 1, -1, -1):
            if all_class[i] in section_class:
                return all_class[i]
        return None

    def section_parsing(self, list_text, max_level=3):
        df = pd.DataFrame({'section': list_text})
        analyzer = SectionAnalyzer()
        df = analyzer.section_processing(df)

        classifier = SectionClassifier()
        df = classifier.section_classifier(df, infer=True)

        # Add end section
        section_class = self._get_section_class(df['class'].unique(), max_level=max_level)
        all_class = df['class'].tolist()
        end_row = {col: '' for col in df.columns}
        end_row['class'] = self.find_class_end_row(all_class, section_class)
        new_row = pd.Series(end_row)
        df = pd.concat([df, pd.DataFrame([new_row])])

        # Searching for content between two adjacent sections at different level
        all_class = df['class'].tolist()
        p1 = self._find_positions_diff_sections(section_class, all_class)
        for idx in p1:
            if idx > 0:
                df.at[idx - 1, 'content'] += df.at[idx, 'content']
                df.at[idx - 1, 'section'] += df.at[idx, 'section']
                df.at[idx - 1, 'section_content'] += '\n' + df.at[idx, 'section_content']
        df.drop(p1, inplace=True)
        df.reset_index(drop=True, inplace=True)
        all_class = df['class'].tolist()

        # Searching for content between two adjacent sections at the same level
        p2 = self._find_positions_same_sections(section_class, all_class)
        for mapping in p2:
            for key, value in mapping.items():
                df.at[key, 'class'] = df.at[value, 'class']

        if len(section_class) > 1:
            df['class'] = df['class'].replace('0', section_class[1])
            section_class = section_class[1:]

        for col in df.columns:
            if col != 'class':
                df.at[df.index[-1], col] = ''

        split_class = self._split_by_class(df, section_class)

        tree = self._gen_tree_structure(split_class)
        return tree  # , df_bug


if __name__ == '__main__':
    pdf = PDFProcessor()
    path = '../data/pdf/23_2024_QD-UBND_608997.pdf'

    lines = pdf.extract_text_from_file(path)
    list_text = lines[1]

    tree = SectionHierarchicalParser().section_parsing(list_text)
    with open(path.replace('pdf', 'json'), 'w', encoding='utf-8') as json_file:
        json.dump(tree, json_file, indent=4, ensure_ascii=False)

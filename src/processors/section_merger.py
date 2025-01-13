import json

class SectionMerger:
    """
    Merge sections into chunks with a specified maximum length
    Use function merge() or get()
    """


    def __init__(self):
        pass

    def get_section(self, item, max_length, title=''):
        add_text = ''
        if isinstance(item, dict):
            add_text += item['value'] + '\n'
        elif isinstance(item, str):
            add_text += item + '\n'
        else:
            raise TypeError('Only dictionary-typed or string-typed children allowed')

        if len(self.text.split(' ')) + len(add_text.split(' ')) > max_length and len(self.text.strip()) > 0:
            if self.text.replace('\n', '') != title:
                self.text_list.append({'text': self.text, 'len': len(self.text.split(' '))})
            self.text = title

        self.text += add_text + '\n'
        if isinstance(item, dict) and item.get('child'):
            for child in item['child']:
                self.get_section(child, max_length, title+item['value'])

        return self.text_list

    def get(self, item, merge_level, current_level=0, max_length=200):
        output = {'value': item['value'], 'child': []}
        if current_level + 1 == merge_level:
            self.text_list = []
            for child in item['child']:
                self.text = ''
                self.get_section(child, max_length=max_length)
                if self.text:
                    self.text_list.append({'text': self.text, 'len': len(self.text.split(' '))})
                output['child'] = self.text_list
            return output
        elif item['child'] is not None:
            for child in item['child']:
                if isinstance(child, dict):
                    child_output = self.get(child, merge_level, current_level + 1, max_length)
                    if isinstance(child_output, dict):
                        output['child'].append(child_output)
                    else:
                        output['child'] += child_output
                else:
                    output['child'].append(child)
        return output

    def merge_section(self, item, max_length):
        '''Take all children of item and merge into chunks, return list of merged chunks'''

        text = '' # Initiate chunk string
        output = [] # List of chunk
        cnt = 0 # Count the number of text added to chunk
        summary_len = -1 # Keep track summary length of the previous child, -1 if text is original and not a summary

        for child in item['child']:
            # add_text is text to be added to text
            if isinstance(child, str):
                add_text = child
            elif isinstance(child, dict):
                add_text = child['value']
            else:
                raise TypeError('Only dictionary or string children allowed')

            # If length of text + add_text + text title > max_length
            if len(item['value'].split(' ')) + len(text.split(' ')) + len(add_text.split(' ')) > max_length and len(text) > 0:
                # Cut off text as a new chunk
                o = {'value': '\n '.join([f"{item['value']}", text]),
                   'child': []}
                o['len'] = len(o['value'].split(' '))
                # If the chunk only has 1 text and that text is a summary,
                # keep summary_len to notify and not summarize it in the next stage
                if cnt == 1 and summary_len > 0:
                    o['summary_len'] = summary_len
                output.append(o)

                # Reset variable
                text = ''
                cnt = 0

            # add_text will be the first string of the next chunk
            text = '\n '.join([text, add_text])
            cnt += 1
            if isinstance(child, dict):
                summary_len = child.get('summary_len', -1)

        # Add remaining text to ouput
        o = {'value': text, #'\n '.join([f"{item['value']}", text]),
             'child': []}
        o['len'] = len(o['value'].split(' '))
        output.append(o)

        return output

    def merge(self, item, merge_level, current_level=0, max_length=200):
        # Pre-order traverse the tree
        # From the deepest node upward, at each level, append all the node child to a list
        # Use merge_section to merge all children of the node from the list above into chunks with max_length
        child_output = [] # List of children of the current items
        for child in item['child']:
            if isinstance(child, dict) and child.get('child'): # If child has deeper level, pre-order traverse with it
                child_output += self.merge(child, merge_level, current_level + 1, max_length=max_length)
            else:  # Else add child to children list
                if isinstance(child, dict):
                    child = child['value']
                child = {'value': child, 'child': [], 'len': len(child.split(' '))}
                child_output.append(child)
        item['child'] = child_output

        # Merge if current level is deeper than merge level:
        if merge_level <= current_level:
            # If merge level == 0, return in special format
            if merge_level == 0:
                return {'value': '', 'child': self.merge_section(item, max_length=max_length)}
            # Else start merging child_output into chunks, return list to be added to child_output of outer recursion
            return self.merge_section(item, max_length=max_length)

        # If current_level == 0, return item, end recursion
        if current_level == 0:
            return item
        else: # Return list of item to be added to child_output to be added to child_output of outer recursion
            return [item]

if __name__ == '__main__':
    merger = SectionMerger()
    name = '23_2024_QD-UBND_608997'
    with open(f'data/{name}.json', encoding='utf-8') as f:
        item = json.load(f)

    level = 3
    item = merger.merge(item, level)
    # item = merger.get(item, level)

    with open(f'data/{name}_{level}_v2.json', 'w', encoding='utf-8') as f:
        json.dump(item, f, indent=3, ensure_ascii=False)
    # with open(f'data/{name}_{level}.json', 'w', encoding='utf-8') as f:
    #     json.dump(item, f, indent=3, ensure_ascii=False)





from src.processors.pdf_processor import PDFProcessor
from src.processors.section_parser import SectionHierarchicalParser
from src.processors.section_merger import SectionMerger
from src.processors.base_processor import BaseProcessor
from src.app_config import app_context
from collections import deque
import logging
import numpy as np
import json

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s %(message)s', level=logging.INFO)


def batched(iterable, n):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


class SummaryPipeline(BaseProcessor):
    RETRY = False

    def __init__(self):

        super().__init__()

        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)

        self.config = app_context.get('config')

        self.pdf_proc = PDFProcessor()
        self.section_parser = SectionHierarchicalParser()
        self.model_infer = app_context.get('model_infer')
        self.section_merger = SectionMerger()

        self.batch_size = int(self.config.get('pipeline', 'batch_size'))
        self.max_depth = int(self.config.get('pipeline', 'max_depth'))
        self.min_length = int(self.config.get('pipeline', 'min_length'))
        self.max_length = int(self.config.get('pipeline', 'max_length'))

        self.sections = deque([])
        self.outputs = deque([])

        self.level_0_child = -1

        self.summary_limit = [{'summary_len': 400, 'section_len': 2000},
                              {'summary_len': 600, 'section_len': 4000},
                              {'summary_len': 1500, 'section_len': np.inf},
                              ]

    def parse_level(self, item, target_level, current_level=0, mode='queue'):
        if current_level == target_level:
            # Only summary if item is not yet summarized
            if mode == 'queue' and item.get('summary_len') is None:
                self.sections.append(item['value'])
            if mode == 'dequeue' and item.get('summary_len') is None:
                summary = self.outputs.popleft()
                summary_len = len(summary.split(' '))
                if summary_len < item['len']:
                    item['summary_len'] = summary_len
                    item['old_text'] = item['value']
                    item['value'] = summary
        else:
            for ind, child in enumerate(item['child']):
                if isinstance(child, dict):
                    item['child'][ind] = self.parse_level(child, target_level, current_level + 1, mode)
        return item

    def get_depth(self, item):
        if isinstance(item, str) or (isinstance(item, dict) and len(item['child']) == 0):
            return 1
        return 1 + max(self.get_depth(child) for child in item['child'])

    def get_text(self, item, result=None):
        if result is None:
            result = []
        if isinstance(item, dict):
            result.append(item['value'])
            for child in item['child']:
                result = self.get_text(child, result)
        elif isinstance(item, str):
            result.append(item)
        return result

    def raw_process(self, docs, type, multitask=None):
        res = []
        for i in range(0, len(docs), self.batch_size):
            batch = docs[i:i + self.batch_size]
            res += self.model_infer.inference(batch, type, multitask)
        return res

    def process(self, path=None, doc=None, debug=False, final=False, multitask=None):

        #Reset variables
        self.sections = deque([])
        self.outputs = deque([])

        self.level_0_child = -1

        # If input is a path, read pdf file and process table
        if path is not None:

            item = path

            # Read from pdf file and convert to markdown text
            item = self.pdf_proc.process(item)

            self.log.info(f'Finish reading file')

            # Use model to summarize table
            for tables in batched(list(item['tables'].keys()), self.batch_size):
                table_batch = [item['tables'][key] for key in tables]
                table_output = self.model_infer.inference(table_batch, 'table')

                # Replace summarized tables to table placeholder (<table 0>, <table 1>,...) in text
                for key, output in zip(tables, table_output):
                    for ind, section in enumerate(item['sections']):
                        item['sections'][ind] = section.replace(f'<{key}>', output)

                self.log.info(f'Finish process tables: {len(item["tables"].keys())}')

            item = item['sections']

        # If input is text
        elif doc is not None:
            item = doc.split('\n')

        # If both is None, raise errors
        else:
            raise Exception('path or doc must not be None')

        # Track original text length
        self.item_length = len(' '.join(item).split(' '))
        self.log.info(f'Section length: {self.item_length}')

        # Split text into sections with tree structure, set max depth of tree using max_level
        item = self.section_parser.section_parsing(item, max_level=self.max_length)
        item = {'value': '', 'child': item}
        self.log.info('Finish parsing item')

        # Summarize starting from the deepest level of the tree to the root
        # Track the level of the tree that are being used for summary
        current_target_level = min(self.get_depth(item) - 1, self.max_depth)

        while current_target_level >= 0:

            self.log.info(f'Starting summary at level {current_target_level}')

            # Merge splitted text to the current_target_level
            # -> After merging, max_depth of the tree is current_target_level
            item = self.section_merger.merge(item, current_target_level, max_length=self.max_length)
            self.log.info(f'Finish merging item at level {current_target_level}')

            # Tree always has the form {'value': '', 'child': [<children>]} a.k.a root is always null
            # -> Always summary from level 1 onwards
            # -> If level = 0, set it back to 1
            # Parse tree to enqueue all nodes at the current_target_level,
            # a.k.a at the deepest level of the tree, for summary
            if current_target_level == 0:
                self.parse_level(item, 1, mode='queue')
            else:
                self.parse_level(item, current_target_level, mode='queue')
            self.log.info(f'Finish parsing item (1) at level {current_target_level}, queue: {len(self.sections)}')

            # If current_target_level == 0, retry = False, and the number of level 0 children is the same as previous loop
            # -> Increase section merger max length and restart
            # if current_target_level == 0:
            #     child_cnt = len(item['child'])
            #     if self.RETRY is False and child_cnt == self.level_0_child:
            #         self.max_length = int(self.config.get('pipeline', 'max_length2'))
            #         self.log.info(f'No change in merging at level 0, change max_len to {self.max_length}')
            #         self.RETRY = True
            #         continue
            #     else:
            #         self.level_0_child = len(item['child'])

            # Process all nodes for summarization at the queue by batch, skip if node has text length < min_length
            # Add summarized nodes to an output queue if node has text length > 250, else add original node
            batch = []
            batch_track = []
            outputs = []
            while len(self.sections) > 0:
                text = self.sections.popleft()
                if len(text.split(' ')) < self.min_length and current_target_level > 0:
                    batch_track.append(text)
                else:
                    batch_track.append(None)
                    batch.append(text)

                if (len(batch) == self.batch_size or len(self.sections) == 0) and len(batch) > 0:
                    outputs += self.model_infer.inference(batch, 'section', multitask=multitask)
                    batch = []

            outputs = outputs[::-1]
            for track in batch_track:
                if track is None:
                    self.outputs.append(outputs.pop())
                else:
                    self.outputs.append(track)
            if len(outputs) > 0:
                raise ValueError(
                    f'All outputs must be added to queue, outputs added: {len(self.outputs)}, outputs remained: {len(outputs)}')

            self.log.info(f'Finish summarize item at level {current_target_level}, dequeue: {len(self.outputs)}')

            # Parse tree to dequeue all summarized nodes to replace original nodes
            # at the current_target_level, a.k.a at the deepest level of the tree
            if current_target_level == 0:
                item = self.parse_level(item, 1, mode='dequeue')
            else:
                item = self.parse_level(item, current_target_level, mode='dequeue')

            self.log.info(f'Finish summary at level {current_target_level}')

            # Check if summary reached target level
            # if yes, stop summarizing, if no, continue
            summary = '\n'.join(self.get_text(item))
            summary_len = len(summary.split(' '))
            self.log.info(f'Summary length: {summary_len}')
            # for summary_limit in self.summary_limit:
            #     if self.item_length <= summary_limit['section_len']:
            #         if summary_len <= summary_limit['summary_len']:
            #             print(summary)
            #             summary = self.model_infer.inference([summary], 'docs_sum')
            #             return summary[0]
            #         break

            # For debug
            if debug:
                print('=============================')
                print(current_target_level)
                print(json.dumps(item, ensure_ascii=False, indent=3))
                print('=============================')

            current_target_level = current_target_level - 1


        # Summary one last time for too long summary
        if final:
            summary_final = self.model_infer.inference([summary], 'docs_sum')
            return summary_final[0]
        return summary


if __name__ == '__main__':
    app_context.use_config('src/config/config-phuong.ini')
    pipeline = SummaryPipeline()
    name = '06_2024_TT-BKHDT_608043'
    print(pipeline.process(f'data/{name}.pdf'))

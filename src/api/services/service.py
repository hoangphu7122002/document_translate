import logging
from pymongo import ReplaceOne, InsertOne
from src.app_config import app_context

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s %(message)s', level=logging.ERROR)

class BasedataService:
    # index name will be set by subclasses
    INDEX_NAME_PROPERTY = 'UNKNOWN'

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.INFO)
        self.index_name = self.INDEX_NAME_PROPERTY

        self.client = app_context.get('mongo_client')
        self.db = self.client[self.index_name]

        self.cnt_stored_items = 0
        self.cnt_failed_items = 0
        self.cnt_invalid_items = 0

    def get_item(self, item_id):
        try:
            return self.db.find_one({'doc_id': item_id})
        except Exception:
            return None

    def get_items(self, query=None, limit=10):
        if query is None:
            query = {}
        try:
            return self.db.find(query, limit=limit)
        except Exception:
            return None

    def count(self, query=None):
        if query is None:
            query = {}
        count = self.db.count_documents(query)
        return count

    def insert_items(self, items):
        if type(items) != list:
            return False, 'Accept only list of entries.'

        success_items = []
        failed_items = []
        # validation
        for item in items:
            # is_valid, msg = self.validate_item(item)
            # if not is_valid:
            #     self.cnt_invalid_items += 1
            #     failed_items.append({
            #         'item': item,
            #         'message': msg
            #     })
            #     continue
            success_items.append(item)

        if not success_items:
            return False, {'failed_items': failed_items}

        try:
            bulk_insert = []
            for item in success_items:
                if item.get('_id'):
                    bulk_insert.append(ReplaceOne({'_id': item['_id']}, item, upsert=True))
                else:
                    item['_id'] = item['doc_id']
                    bulk_insert.append(InsertOne(item))
            results = self.db.bulk_write(bulk_insert)
            success_count = results.upserted_count + results.inserted_count
            self.log.info('Saved %s items', success_count)
            self.cnt_stored_items += success_count
            msg = {
                'success_items': success_count,
                'failed_items': results.bulk_api_result['writeErrors']
            }
            return True, msg

        except Exception as ex:
            self.log.exception(ex)
            return False, {'msg': ex}

    def delete_item(self, item_id):
        self.db.delete_one({'_id': item_id})
        return True

    def insert_item(self, item):
        # is_valid, msg = self.validate_item(item)
        #
        # if not is_valid:
        #     return False, msg

        if item.get('_id'):
            self.db.replace_one({'_id': item['_id']}, item, upsert=True)
        else:
            item['_id'] = item['doc_id']
            self.db.insert_one(item)

        msg = {
                'success_items': 1,
                'failed_items': []
            }

        return True, msg

    def update_item(self, item_id, update_item):
        result = self.db.update_one({"_id": item_id}, update_item)
        return True, result

    def validate_item(self, entry):
        raise NotImplementedError

class SummaryService(BasedataService):
    INDEX_NAME_PROPERTY = 'vo_summary'

    def __init__(self):
        super().__init__()


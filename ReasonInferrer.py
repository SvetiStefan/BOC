import os
import operator
import math
import jieba
import similarity
from csv_parser import read_csv_with_headers
from misc import check_keys
from collections import defaultdict

class ReasonInferrer(object):
    """
        This class infers call reasons for call transactions
    """
    def __init__(self, call_reason, trans_file):
        check_keys(["file_name"], call_reason, "call_reason", basestring)
        check_keys(["call_reason_id_index", "call_reason_index"], call_reason, "call_reason", int)
        if not os.path.isfile(trans_file):
            raise Exception("{0} does not exist.".format(trans_file))
        self._call_reason_setting = call_reason
        self._trans_file = trans_file
        self._call_reasons = {}
        self._call_reasons_segmented = {}
        self._trans = []

    def find_reasons(self, limit=0):
        self.load_call_reason()
        self.load_trans_and_find_reasons(limit)

    def load_call_reason(self):
        attribute_map, lines = read_csv_with_headers(self._call_reason_setting['file_name'])
        id_index = self._call_reason_setting['call_reason_id_index']
        reason_index = self._call_reason_setting['call_reason_index']
        for line in lines:
            self._call_reasons[line[id_index]] = line[reason_index]
            segmented = list(jieba.cut(line[reason_index]))
            self._call_reasons_segmented[line[id_index]] = segmented

    def load_trans_and_find_reasons(self, limit):
        trans_count = 0
        with open(self._trans_file, 'r') as f:
            for line in f:
                items = line.split('\t')
                chinese_parts = []
                for item in items[:-1]:
                    try:
                        chinese_part = item[item.index('(')+1 : -1]
                        if chinese_part != '':
                            chinese_parts.append(list(jieba.cut(chinese_part)))
                    except:
                        print "Invalid transaction :" + one_trans
                reason_id, reason_str, vote_score = self.find_reason(chinese_parts)
                print line.strip(), reason_id, reason_str, vote_score
                trans_count += 1
                if limit > 0 and trans_count >= limit:
                    return
                if trans_count % 10 == 0:
                    raw_input('Press any key to get another 10 results...')

    def get_best_similarity(self, one_trans):
        highest_similarity = 0.0
        best_reason_index = 0
        for key, vec in self._call_reasons_segmented.iteritems():
            sim = similarity.simple_similarity(vec, one_trans)
            if sim > highest_similarity:
                highest_similarity = sim
                best_reason_index = key
        return highest_similarity, best_reason_index

    def find_reason(self, chinese_parts):
        reason_id = 0
        reason_str = 'Not found'
        vote_score = 0.0
        if len(chinese_parts) == 0:
            return reason_id, reason_str, vote_score
        votes = defaultdict(float)
        for i in reversed(range(len(chinese_parts))):
            highest_similarity, best_reason_index = self.get_best_similarity(chinese_parts[i])
            adjusted_similarity = highest_similarity * math.pow(0.5, (len(chinese_parts) - i - 1))
            votes[best_reason_index] += adjusted_similarity
        votes_sorted = sorted(votes.items(), key=operator.itemgetter(1), reverse=True)
        if votes_sorted[0][0] in self._call_reasons:
            reason_str = self._call_reasons[votes_sorted[0][0]]
        return votes_sorted[0][0], reason_str, votes_sorted[0][1]

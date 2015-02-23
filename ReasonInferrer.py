# -*- coding: utf-8 -*-
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
    def __init__(self, trcode, call_reason, trans_file):
        check_keys(["file_name"], call_reason, "call_reason", basestring)
        check_keys(["call_reason_id_index", "call_reason_index"], call_reason, "call_reason", int)
        check_keys(["file_name"], trcode, "trcode", basestring)
        check_keys(["code_id_index", "code_type_index", "code_name_index", "code_reason_index"], trcode, "trcode", int)
        if not os.path.isfile(trans_file):
            raise Exception("{0} does not exist.".format(trans_file))
        self._call_reason_setting = call_reason
        self._trans_file = trans_file
        self._call_reasons = {}
        self._call_reasons_segmented = {}
        self._trans = []
        self._trcode = trcode
        self._code_mapping = {}
        self._load_code_mapping()
        self._load_call_reason()

    def _load_code_mapping(self):
        _, lines = read_csv_with_headers(self._trcode['file_name'])
        for line in lines:
            code_id = line[self._trcode["code_id_index"]]
            code_type = line[self._trcode["code_type_index"]].strip()
            code_name = line[self._trcode["code_name_index"]].strip()
            code_reason = line[self._trcode["code_reason_index"]].strip()
            self._code_mapping[code_id] = [code_type, code_name, code_reason]

    def _load_call_reason(self):
        _, lines = read_csv_with_headers(self._call_reason_setting['file_name'])
        id_index = self._call_reason_setting['call_reason_id_index']
        reason_index = self._call_reason_setting['call_reason_index']
        for line in lines:
            self._call_reasons[line[id_index]] = line[reason_index].strip()
            segmented = list(jieba.cut(line[reason_index].strip()))
            self._call_reasons_segmented[line[id_index]] = segmented

    def find_reasons(self, start=0, end=0, min_len=0):
        trans_count = 0
        valid_trans_count = 0
        with open('res.csv', 'w') as fout:
            with open(self._trans_file, 'r') as f:
                for line in f:
                    trans_count += 1
                    if trans_count < start+1:
                        continue
                    if end != 0 and trans_count > end:
                        return
                    items = line.split('\t')
                    chinese_parts = []
                    full_trans = []
                    for item in items[:-1]:
                        if item in self._code_mapping:
                            code_type, chinese_part, code_reason = self._code_mapping[item]
                            if chinese_part.decode('utf-8') not in ['', u'综合查询']:
                                chinese_parts.append([list(jieba.cut(chinese_part)), code_reason, code_type])
                            full_trans.append("{0}({1})".format(item, chinese_part))
                        else:
                            full_trans.append("{0}".format(item))
                        # try:
                        #     chinese_part = item[item.index('(')+1 : -1]
                        #     if chinese_part.decode('utf-8') not in ['', u'综合查询']:
                        #         chinese_parts.append(list(jieba.cut(chinese_part)))
                        # except:
                        #     print "Invalid transaction :" + line
                    if len(chinese_parts) < min_len:
                        continue
                    reason_str = self._arrange_trans_and_find_reason(chinese_parts)

                    print '->'.join(full_trans), items[-1].strip(), '\t', reason_str
                    fout.write('{0}\t{1}\t{2}\n'.format('->'.join(full_trans), items[-1].strip(), reason_str))
                    valid_trans_count += 1
                    if valid_trans_count % 10 == 0:
                        raw_input('Press any key to get another 10 results...')

    def _get_best_similarity(self, one_trans):
        highest_similarity = 0.0
        best_reason_index = 0
        for key, vec in self._call_reasons_segmented.iteritems():
            sim = 0.0
            # print one_trans[-1], type(one_trans[-1])
            # print vec[-1], type(vec[-1])
            # print one_trans[-1] == u'查询', vec[-1] == u'查询'
            # if one_trans[-1] == u'查询' and vec[-1] == u'查询':
            #     raw_input('press any key to continue')
            if one_trans[-1] != u'查询' and vec[-1] != u'查询':
                sim = similarity.simple_similarity(vec, one_trans)
            elif one_trans[-1] == u'查询' and vec[-1] == u'查询':
                #raw_input('press any key to continue')
                sim = similarity.simple_similarity(vec[:-1], one_trans[:-1])
            if sim > highest_similarity:
                highest_similarity = sim
                best_reason_index = key
        return highest_similarity, best_reason_index

    def _arrange_trans_and_find_reason(self, chinese_parts):
        reason_str = "0-综合查询/未知(0.0)"
        if len(chinese_parts) == 0:
            return reason_id+'-'+reason_str, vote_score
        reasons = defaultdict(float)
        one_seg = []
        found_action = False
        for chinese_part in chinese_parts:
            one_seg.append(chinese_part[:-1])
            if chinese_part[-1] == '2':
                found_action = True
                reason_str, sim = self._find_reason(one_seg, has_action=True)
                reasons[reason_str] += sim
                one_seg = []
        # Action type of trans not found, consider query type of trans
        if len(one_seg) > 0 and not found_action: 
            reason_str, sim = self._find_reason(one_seg, has_action=False)
            reasons[reason_str] += sim
        if len(reasons) > 1:
            raw_input('found transaction with 2 reasons')
        reason_sorted = sorted(reasons.items(), key=operator.itemgetter(1), reverse=True)
        reason_str = ', '.join(['{0}({1})'.format(key, value) for [key, value] in reason_sorted])
        return reason_str


    def _find_reason(self, chinese_parts, has_action, use_mapping=True):
        reason_id = 0
        reason_str = "综合查询/未知"
        vote_score = 0.0
        votes = defaultdict(float)
        for i in reversed(range(len(chinese_parts))):
            highest_similarity, best_reason_index = self._get_best_similarity(chinese_parts[i][0])
            if use_mapping and chinese_parts[i][1] != '':
                best_reason_index = chinese_parts[i][1]
                highest_similarity = 1.0
            adjusted_similarity = highest_similarity * math.pow(0.5, (len(chinese_parts) - i - 1))
            votes[best_reason_index] += adjusted_similarity
            if has_action and i == (len(chinese_parts) - 1) and highest_similarity > 0:
                break
        votes_sorted = sorted(votes.items(), key=operator.itemgetter(1), reverse=True)
        if votes_sorted[0][0] in self._call_reasons:
            reason_str = self._call_reasons[votes_sorted[0][0]]
        return votes_sorted[0][0]+'-'+reason_str, votes_sorted[0][1]

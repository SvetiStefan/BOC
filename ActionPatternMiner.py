# -*- coding: utf-8 -*-
import os
import argparse
import operator
import math
import json
import jieba
import similarity
from csv_parser import read_csv_with_headers
from misc import check_keys
from collections import defaultdict

class ActionPatternMiner(object):
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
        self._call_reasons = {}
        self._trans_file = trans_file
        self._trans = []
        self._trcode = trcode
        self._code_mapping = {}
        self._action_pattern = {}
        self._action_stats = {}
        self._load_code_mapping()
        self._load_call_reasons()

    def _load_code_mapping(self):
        _, lines = read_csv_with_headers(self._trcode['file_name'])
        for line in lines:
            code_id = line[self._trcode["code_id_index"]]
            code_type = line[self._trcode["code_type_index"]].strip()
            code_name = line[self._trcode["code_name_index"]].strip()
            code_reason = line[self._trcode["code_reason_index"]].strip()
            self._code_mapping[code_id] = [code_type, code_name, code_reason]

    def _load_call_reasons(self):
        _, lines = read_csv_with_headers(self._call_reason_setting['file_name'])
        id_index = self._call_reason_setting['call_reason_id_index']
        reason_index = self._call_reason_setting['call_reason_index']
        for line in lines:
            self._call_reasons[line[id_index]] = line[reason_index].strip()

    def mine_patterns(self):
        with open(self._trans_file, 'r') as f:
            for line in f:
                items = line.split('\t')
                one_seg = []
                freq = int(items[-1])
                for item in items[:-1]:
                    if item == 'C108021':
                        continue
                    if item in self._code_mapping:
                        code_type, chinese_part, code_reason = self._code_mapping[item]
                        one_seg.append('{0}({1})'.format(item, chinese_part))
                        if code_type == '2':
                            self._handle_one_pattern(one_seg, code_reason, freq)
                            self._stat_one_pattern(one_seg, freq)
                            one_seg = []
                    else:
                        one_seg.append(item+'()')
        self._output_patterns()

    def _gen_pattern(self, raw_pattern):
        pre_item = 'Nil'
        clean_pattern = []
        for item in raw_pattern:
            if item != pre_item:
                clean_pattern.append(item)
                pre_item = item
        return clean_pattern

    def _stat_one_pattern(self, one_pattern, freq):
        if one_pattern[-1] not in self._action_stats:
            self._action_stats[one_pattern[-1]] = {}
        if 'total' not in self._action_stats[one_pattern[-1]]:
            self._action_stats[one_pattern[-1]]['total'] = 0
        self._action_stats[one_pattern[-1]]['total'] += freq
        if len(one_pattern) > 1:
            clean_pattern = self._gen_pattern(one_pattern[:-1])
            for item in clean_pattern:
                if item not in self._action_stats[one_pattern[-1]]:
                    self._action_stats[one_pattern[-1]][item] = 0
                self._action_stats[one_pattern[-1]][item] += freq

    def _handle_one_pattern(self, one_pattern, reason, freq):
        if reason == '':
            reason = 'Unknow'
        else:
            reason = self._call_reasons[reason]
        if reason not in self._action_pattern:
            self._action_pattern[reason] = {}
        if one_pattern[-1] not in self._action_pattern[reason]:
            self._action_pattern[reason][one_pattern[-1]] = {}
        pattern = ''
        if len(one_pattern) == 1:
            pattern = 'Nil'
        else:
            pattern = ','.join(self._gen_pattern(one_pattern[:-1]))
        if pattern not in self._action_pattern[reason][one_pattern[-1]]:
            self._action_pattern[reason][one_pattern[-1]][pattern] = 0
        self._action_pattern[reason][one_pattern[-1]][pattern] += freq

    def _output_patterns(self):
        with open('action_pattern.txt', 'w') as f:
            for reason in self._action_pattern:
                for action in self._action_pattern[reason]:
                    f.write('{0}\t{1}:\n'.format(reason, action))
                    pattern_sorted = sorted(self._action_pattern[reason][action].items(), key=operator.itemgetter(1), reverse=True)
                    for pattern, freq in pattern_sorted:
                        f.write('{0}:{1},{2}\t{3}\n'.format(reason, pattern, action, freq))
        with open('pattern_stat.txt', 'w') as f:
            for action in self._action_stats:
                total = self._action_stats[action]['total']
                items_sorted = sorted(self._action_stats[action].items(), key=operator.itemgetter(1), reverse=True)
                item_with_freq = []
                for item, freq in items_sorted:
                    if item == 'total':
                        continue
                    prob = freq*1.0/total
                    if prob < 0.1:
                        continue
                    item_with_freq.append('{0}({1:.2f})'.format(item, prob))
                f.write('{0} : {1}...\n'.format(action, ','.join(item_with_freq)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--setting', default='settings.json', help='setting of ReasonInferrer, default settings.json')
    args = parser.parse_args()
    with open(args.setting, 'r') as f:
        setting = json.load(f)
        pattern_miner = ActionPatternMiner(setting['trcode'], setting['call_reason'], setting['trans_stat_output'])
        pattern_miner.mine_patterns()


if __name__ == '__main__':
    main()
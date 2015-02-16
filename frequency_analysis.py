import os
import sys
import math
import operator
import jieba
import json
import csv_parser
import similarity
from LogParser import LogParser
from datetime import datetime


call_reasons = {}
call_reasons_segmented ={}
trans_sorted = None

setting_file = 'settings.json'


def load_trans_and_find_reason(file_name):
    trans_sorted = []
    with open(file_name, 'r') as f:
        for line in f:
            items = line.split('\t')
            trans = '\t'.join(items[:-1])
            freq = int(items[-1])
            trans_sorted.append([trans, freq])
    find_reason_with_similarity(trans_sorted[:10])

def load_call_reason(file_name):
    attribute_map, lines = csv_parser.read_csv_with_headers(file_name)
    for line in lines:
        call_reasons[line[0]] = line[1]
        segmented = list(jieba.cut(line[1]))
        call_reasons_segmented[line[0]] = segmented

def get_best_similarity(one_trans):
    highest_similarity = 0.0
    best_reason_index = 0
    for key, vec in call_reasons_segmented.iteritems():
        sim = similarity.simple_similarity(vec, one_trans)
        if sim > highest_similarity:
            highest_similarity = sim
            best_reason_index = key
    return highest_similarity, best_reason_index

def find_reason_with_similarity(trans_collection):
    reason_id = 0
    reason_str = 'Not found'
    vote_score = 0.0
    for one_trans in trans_collection:
        items = one_trans[0].split('\t')
        chinese_parts = []
        for item in items:
            try:
                chinese_part = item[item.find('(')+1 : -1]
                if chinese_part != '':
                    chinese_parts.append(list(jieba.cut(chinese_part)))
            except:
                print "Invalid transaction :" + one_trans
        if len(chinese_parts) == 0:
            print one_trans[0], reason_id, reason_str, vote_score
            continue
        votes = {}
        for i in reversed(range(len(chinese_parts))):
            highest_similarity, best_reason_index = get_best_similarity(chinese_parts[i])
            adjusted_similarity = highest_similarity*math.pow(0.5, (len(chinese_parts) - i - 1))
            if best_reason_index not in votes:
                votes[best_reason_index] = adjusted_similarity
            else:
                votes[best_reason_index] += adjusted_similarity
        votes_sorted = sorted(votes.items(), key=operator.itemgetter(1), reverse=True)
        reason_str = 'Not found' if votes_sorted[0][0] not in call_reasons else call_reasons[votes_sorted[0][0]]
        print one_trans[0], one_trans[1], votes_sorted[0][0], reason_str, votes_sorted[0][1]




def main():
    with open(setting_file, 'r') as f:
        setting = json.load(f)
        if not os.path.isfile(setting['trans_stat_output']):
            log_parser = LogParser(setting['service_log'], setting['trcode'], setting["filter_str"])
            log_parser.process_and_store(setting['trans_stat_output'])
        load_call_reason(setting['call_reason']['file_name'])
        load_trans_and_find_reason(setting['trans_stat_output'])



if __name__ == '__main__':
    main()
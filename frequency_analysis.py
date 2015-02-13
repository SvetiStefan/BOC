import sys
import math
import operator
import jieba
import csv_parser
import similarity

from datetime import datetime

log_file_name = 'data/servicelog'
trcode_file_name = 'data/TRCODE.csv'
call_reason_file_name = 'data/call_reason.csv'
date_index = 3
trans_id_index = 1
trans_code_index = 4
trans = {}
code_2_meaning = {}
call_reasons = {}
call_reasons_segmented ={}
trans_sorted = None



def make_code_mapping(file_name):
    attribute_map, lines = csv_parser.read_csv_with_headers(file_name)
    for line in lines:
        code_2_meaning[line[0]] = line[2]

def make_trans_and_sort(trcode_file_name):
    make_code_mapping(trcode_file_name)
    trans_stat = {}
    for trans_items in trans.itervalues():
        itemset = []
        for one_item in trans_items:
            if one_item in code_2_meaning:
                itemset.append('{0}({1})'.format(one_item, code_2_meaning[one_item]))
            else:
                itemset.append(one_item+'()')
        trans_key = '\t'.join(itemset)
        if trans_key not in trans_stat:
            trans_stat[trans_key] = 1
        else:
            trans_stat[trans_key] += 1
    print "transaction types: ", len(trans_stat)
    trans_sorted = sorted(trans_stat.items(), key=operator.itemgetter(1), reverse=True)
    # for one_trans in trans_sorted[:100]:
    #     print one_trans[0], one_trans[1]
    find_reason_with_similarity(trans_sorted[:100])

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
        print one_trans[0], votes_sorted[0][0], reason_str, votes_sorted[0][1]

def read_trans(file_name):
    current_date = datetime.strptime('2014-06-01', '%Y-%m-%d')
    prefix = ''
    with open(file_name, 'r') as f:
        start_date = datetime.strptime('2014-06-01', '%Y-%m-%d')
        end_date = datetime.strptime('2014-08-31', '%Y-%m-%d')
        total_days = (end_date - start_date).days
        for line in f:
            items = line.split('\t')
            trans_id = items[trans_id_index]
            # filter, only consider CSR trans
            if trans_id[:3] != 'CSR':
                continue
            trans_code = items[trans_code_index]
            date = None
            try:
                date = datetime.strptime(items[date_index], '%Y-%m-%d')
            except:
                print 'Invalid date {0}'.format(items[date_index])
                exit(0)
            #new day
            if current_date != date:
                current_date = date
                elapsed_days = (current_date - start_date).days
                percentage = str(100*elapsed_days/total_days)+'%'
                sys.stdout.write('{0}... {1} accomplished\r'.format(current_date.strftime('Processing data on %Y-%m-%d'), percentage)) 

            if trans_id not in trans:
                trans[trans_id] = [trans_code]
            else:
                trans[trans_id].append(trans_code)
    sys.stdout.write('\n')
    print "transaction number: ", len(trans)


def main():
    
    read_trans(log_file_name)
    load_call_reason(call_reason_file_name)
    make_trans_and_sort(trcode_file_name)


if __name__ == '__main__':
    main()
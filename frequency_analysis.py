import os
import operator
from datetime import datetime

file_name = 'data/servicelog'
date_index = 3
trans_id_index = 1
trans_code_index = 4
trans = {}


def sort_trans():
	trans_stat = {}
	for trans_items in trans.itervalues():
		trans_key = '\t'.join(trans_items)
		if trans_key not in trans_stat:
			trans_stat[trans_key] = 1
		else:
			trans_stat[trans_key] += 1
	print "transaction types: ", len(trans_stat)
	trans_sorted = sorted(trans_stat.items(), key=operator.itemgetter(1), reverse=True)
	print trans_sorted[:10]


def read_trans(file_name):
    current_date = None
    with open(file_name, 'r') as f:
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
                print current_date

            if trans_id not in trans:
                trans[trans_id] = [trans_code]
            else:
                trans[trans_id].append(trans_code)
    print "transaction number: ", len(trans)


def main():
    read_trans(file_name)
    sort_trans()


if __name__ == '__main__':
    main()
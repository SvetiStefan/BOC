import os
file_name = 'servicelog'

def main():
    stat = {}
    counter = 0
    CSR_raw_count = 0
    with open(file_name, 'r') as f:
        for line in f:
            counter += 1
            if counter < 10:
            	print line
            fields = line.split('\t')
            key = fields[1]
            if fields[1][:3] == 'CSR':
            	CSR_raw_count += 1
            if key not in stat:
                stat[key] = []
            stat[key].append(fields[4])
    CSR_count = 0
    for key in stat:
        if key[:3] == 'CSR':
            CSR_count += 1
            #print key
        # if stat[key] > 1:
        #     print key
    print counter
    print CSR_raw_count
    print len(stat)
    print CSR_count

if __name__ == '__main__':
    main()
import csv

def remove_quote(item):
    if len(item) > 1 and item[0] == '"' and item[-1] =='"':
        return item[1:-1]
    else:
        return item

def read_csv_with_headers(filename):
    attribute_map = {}
    lines = []
    with open(filename, 'rU') as f:
        reader = csv.reader(f)
        headers = reader.next()
        attribute_index = 0
        for item in headers:
            attribute_map[remove_quote(item)] = attribute_index
            attribute_index += 1
        for line in reader:
            clean_line = [remove_quote(item) for item in line]
            lines.append(clean_line)
    return attribute_map, lines
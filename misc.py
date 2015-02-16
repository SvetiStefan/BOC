
def check_keys(keys, d, d_name, tp):
    for key in keys:
        if key not in d or not isinstance(d[key],tp):
            raise Exception('Key {0} not found in {1} or its value is not {2}.'.format(key, d_name, tp))

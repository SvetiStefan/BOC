import os
import json
from LogParser import LogParser
from ReasonInferrer import ReasonInferrer

setting_file = 'settings.json'

def main():
    with open(setting_file, 'r') as f:
        setting = json.load(f)
        if not os.path.isfile(setting['trans_stat_output']):
            log_parser = LogParser(setting['service_log'], setting["filter_str"])
            log_parser.process_and_store(setting['trans_stat_output'])
        reason_inferrer = ReasonInferrer(setting['trcode'], setting['call_reason'], setting['trans_stat_output'])
        reason_inferrer.find_reasons(start=0, end=0, min_len=10)

if __name__ == '__main__':
    main()
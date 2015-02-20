# -*- coding: utf-8 -*-
import math

def remove_stop_words(words):
    stop_words = set([" ", "-", u"―"])
    return [word for word in words if word not in stop_words ]

def simple_similarity(words1, words2):
    '''index words'''
    clean_words1 = remove_stop_words(words1)
    clean_words2 = remove_stop_words(words2)
    word_to_index = {}
    index = 0
    for word in clean_words1 + clean_words2:
        if word not in word_to_index:
            word_to_index[word] = index
            index += 1
    # keys = sorted(word_to_index.iterkeys(), key=lambda k: word_to_index[k])
    # print keys
    # for key in keys:
    #     print key
    def normalised_bag_of_words(words):
        #print words
        words_vec = [0]*len(word_to_index)
        for word in words:
            words_vec[word_to_index[word]] += 1
        norm = math.sqrt(sum(x*x for x in words_vec))
        #print [1.0*x/norm for x in words_vec]
        return [1.0*x/norm for x in words_vec]
    words1_vec = normalised_bag_of_words(clean_words1)
    words2_vec = normalised_bag_of_words(clean_words2)
    # print words1_vec
    # print words2_vec
    #raw_input("press any key to continue")
    return sum(words1_vec[i]*words2_vec[i] for i in range(0, len(word_to_index)))

def main():
    """
        use main for simple testing
    """
    words1 = [u"个人", u"卡", u"账单", u"调阅"]
    words2 = [u"虚拟", u"卡", u"查询", u"实体", u"卡"]
    print simple_similarity(words1, words2)

if __name__ == '__main__':
    main()
import math

def simple_similarity(words1, words2):
    '''index words'''
    word_to_index = {}
    index = 0
    for word in words1+words2:
        if word not in word_to_index:
            word_to_index[word] = index
            index += 1
    def normalised_bag_of_words(words):
        #print words
        words_vec = [0]*len(word_to_index)
        for word in words:
            words_vec[word_to_index[word]] += 1
        norm = math.sqrt(sum(x*x for x in words_vec))
        #print [1.0*x/norm for x in words_vec]
        return [1.0*x/norm for x in words_vec]
    words1_vec = normalised_bag_of_words(words1)
    words2_vec = normalised_bag_of_words(words2)
    #raw_input("press any key to continue")
    return sum(words1_vec[i]*words2_vec[i] for i in range(0, len(word_to_index)))

# 训练doc2vec模型代码：

import codecs, nltk
from os import sendfile
from gensim.models import doc2vec
from gensim.models.doc2vec import Doc2Vec
import multiprocessing

from nltk.util import pr

def cut_passage(passage_dict):
    passage_word_dict = []
    for text in passage_dict:
        word_list = nltk.word_tokenize(text)   # text.split(" ") 
        l = len(word_list)
        if len(word_list)!= 0 : word_list[l-1] = word_list[l-1].strip()
        passage_word_dict.append(word_list)
    return passage_word_dict

def train(cut_sentence, model_save_name):
    print("开始训练模型...")
    x_train = []
    for i, text in enumerate(cut_sentence):
        document = doc2vec.TaggedDocument(text, [i])
        x_train.append(document)
    model = Doc2Vec(x_train, min_count=1,vector_size=300, window=3,workers=4)
    model.train(x_train, total_examples=model.corpus_count,epochs=10)
    model.save(model_save_name)
    print("模型保存完毕...")

def look_up(model_name, title_dict, passage_dict, passage_word_dict, test_num):
    test_passage_word_list = passage_word_dict[test_num]
    model = Doc2Vec.load(model_name)
    vector = model.infer_vector(doc_words=test_passage_word_list)
    sims = model.docvecs.most_similar([vector], topn = 10) 
    # print(vector)  # 打印文本的对应向量

    print("\n\n测试第", test_num, "个，名为：", title_dict[test_num])
    # print("具体文本为：", passage_dict[test_num])
    # sim2 = model.docvecs.similarity(test_num,test_num)

    for count, sim in sims:
        title = title_dict[count]
        sentence = passage_dict[count]
        print("\n\n第", count, "个，名为：", title, "\n长度为：", len(sentence), "相似度为：", sim)
        # print("具体文本为：", sentence)

def save_node(model_name, data_filename, passage_dict):
    print("正在将模型保存为节点数据...")
    target = codecs.open(data_filename, 'w',encoding="utf8")
    model = Doc2Vec.load(model_name)
    length = len(passage_dict)
    for i in range(length):
        for j in range(length):
            if i == j: continue
            sim = model.docvecs.similarity(i,j)
            target.writelines(str(i) +  " " + str(j) + " " + str(sim) + "\n")
    target.close()
    print("保存完毕...")

def main():
    pass

if __name__ == "__main__":
    main()
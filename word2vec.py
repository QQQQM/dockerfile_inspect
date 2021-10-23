
import jieba
import codecs
from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence
import logging

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


def jieba_cut_passage():
    f=codecs.open('./SGYY.txt','r',encoding="utf8")
    target = codecs.open("./gushi.txt", 'w',encoding="utf8")

    print('open files')
    line_num=1
    line = f.readline()

    #循环遍历每一行，并对这一行进行分词操作
    #如果下一行没有内容的话，就会readline会返回-1，则while -1就会跳出循环
    while line:
        print('---- processing ', line_num, ' article----------------')
        line_seg = " ".join(jieba.cut(line))
        target.writelines(line_seg)
        line_num = line_num + 1
        line = f.readline()

    #关闭两个文件流，并退出程序
    f.close()
    target.close()
    exit()

def train():
    #首先打开需要训练的文本
    shuju = open('gushi.txt', 'rb')
    #通过Word2vec进行训练
    model = Word2Vec(LineSentence(shuju), sg=1,vector_size=100, window=10, min_count=5, workers=15,sample=1e-3)
    #保存训练好的模型
    model.save('SanGuoYanYiTest.word2vec')
    print('训练完成')

def lookup():
    # 加载已训练好的模型
    model_1 = Word2Vec.load('SanGuoYanYiTest.word2vec')
    # # 计算两个词的相似度/相关程度
    # y1 = model_1.similarity("新闻", "热度")
    # print(u"新闻和热度的相似度为：", y1)
    # print("-------------------------------\n")
    
    # 计算某个词的相关词列表
    y2 = model_1.wv.most_similar("赤兔马", topn=10)  # 10个最相关的

    print(u"和赤兔马最相关的词有：\n")
    for item in y2:
        print(item[0], item[1])
    print("-------------------------------\n")

def main():
    print("hello")
    # jieba_cut_passage()
    # train()
    lookup()

if __name__ == "__main__":
    main()
import os, doc2vec

from nltk.util import pr
import get_dockerfile_from_database



def get_dict(passage_dict, title_dict):
    # dockerfile_filename = codecs.open("./file_txt/gushi2.txt", 'w',encoding="utf8")
    dockerfile_maneger = get_dockerfile_from_database.Dockerfile_Maneger("localhost", "test", 500, 0, passwd = "123456") # ("211.69.198.51", "dockerfile", 1, 0) 
    dockerfile_list = dockerfile_maneger.lookup()
    for i in range(len(dockerfile_list)):
        image_id = dockerfile_list[i][0].replace("+","/")
        content = dockerfile_list[i][1]
        print("\n", i, "---", image_id)
        passage = get_dockerfile_from_database.deal_dockerfile(content)

        if len(passage) != 0: 
            title_dict.append(image_id)
            passage_dict.append(get_dockerfile_from_database.deal_dockerfile(content)) 
    

def main():
    os.system("clear")
    passage_dict = []
    title_dict = []
    model_save_name = "./file_txt/model-500"
    model_read_name = model_save_name
    # 获取文章和标题的列表
    get_dict(passage_dict, title_dict)
    passage_word_dict = doc2vec.cut_passage(passage_dict)
    test_num = 150
    # 将文档打上tag并进行训练
    # doc2vec.train(passage_word_dict, model_save_name)
    # doc2vec.train(passage_dict, model_save_name)
    doc2vec.look_up(model_read_name, title_dict, passage_dict, passage_word_dict, test_num)

if __name__ == "__main__":
    main()
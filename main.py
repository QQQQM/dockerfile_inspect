import os, codecs, doc2vec

from nltk.util import pr
import get_dockerfile_from_database
import label_propagation



def get_dict(passage_dict, title_dict, num):
    # dockerfile_filename = codecs.open("./file_txt/gushi2.txt", 'w',encoding="utf8")
    dockerfile_maneger = get_dockerfile_from_database.Dockerfile_Maneger("localhost", "test", num, 0, passwd = "123456") # ("211.69.198.51", "dockerfile", 1, 0) 
    dockerfile_list = dockerfile_maneger.lookup()
    for i in range(len(dockerfile_list)):
        image_id = dockerfile_list[i][0].replace("+","/")
        content = dockerfile_list[i][1]
        print("\n", i, "---", image_id)
        passage = get_dockerfile_from_database.deal_dockerfile(content)

        if len(passage) != 0: 
            title_dict.append(image_id)
            passage_dict.append(get_dockerfile_from_database.deal_dockerfile(content)) 

def save_classify(data_save_path, cluster_group, label_dict, title_dict, passage_dict):
    print(cluster_group)
    print(label_dict)
    for i in label_dict:
        group_name = data_save_path + str(i) + ".txt"
        f = codecs.open(group_name, 'w',encoding="utf8")
        for passage_index in cluster_group[i]:
            f.writelines(title_dict[int(passage_index)] + "\n")
            f.writelines(passage_dict[int(passage_index)] + "\n\n")
        f.close()


def main():
    os.system("clear")    
    num = 100000
    title_dict = []
    passage_dict = []
    
    data_save_path = "./data-" + str(num) + "/"
    if not os.path.exists(data_save_path):  os.makedirs(data_save_path)
    data_save_name = data_save_path + "label_data.txt"
    model_save_name = "./model/model-" + str(num)
    model_read_name = model_save_name
    
    # 获取文章和标题的列表
    get_dict(passage_dict, title_dict, num)
    passage_word_dict = doc2vec.cut_passage(passage_dict)
    test_num = 1
    
    # # 将文档打上tag并进行训练
    doc2vec.train(passage_word_dict, model_save_name)
    
    # # 测试用，在训练好的模型中匹配文档
    # # doc2vec.look_up(model_read_name, title_dict, passage_dict, passage_word_dict, test_num)

    # # 将模型保存为节点数据
    doc2vec.save_node(model_read_name, data_save_name, passage_dict)
    # 通过label propagation算法获得节点分类
    cluster_group, label_dict = label_propagation.classify(data_save_name)
    # 保存分类数据，方便比较
    save_classify(data_save_path, cluster_group, label_dict, title_dict, passage_dict)

if __name__ == "__main__":
    main()
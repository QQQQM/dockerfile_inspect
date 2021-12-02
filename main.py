import re, os, json, codecs, doc2vec
from nltk.util import pr
from form_ast import deal_shell
import get_dockerfile_from_database
import label_propagation



def get_dict(passage_dict, title_dict, table_name, num, flag = 0):
    # dockerfile_filename = codecs.open("./file_txt/gushi2.txt", 'w',encoding="utf8")
    dockerfile_maneger = get_dockerfile_from_database.Dockerfile_Maneger("localhost", "test", num, 0, passwd = "123456", table_name = table_name) # ("211.69.198.51", "dockerfile", 1, 0) 
    dockerfile_list = dockerfile_maneger.lookup()
    for i in range(len(dockerfile_list)):
        image_id = dockerfile_list[i][0].replace("+","/")
        content = dockerfile_list[i][1]
        print("\n", i, "---", image_id)
        passage = get_dockerfile_from_database.deal_dockerfile(content)        
        title_dict.append("baaaaaaad--" + image_id) if flag == 1 else title_dict.append(image_id)
        passage_dict.append(passage)

def get_dict_layer(passage_dict, title_dict, table_name, num, flag = 0):
    dockerfile_maneger = get_dockerfile_from_database.Dockerfile_Maneger("localhost", "test", num, 0, passwd = "123456", table_name = table_name ) # ("211.69.198.51", "dockerfile", 1, 0) 
    dockerfile_list = dockerfile_maneger.lookup()
    for i in range(len(dockerfile_list)):
        image_id = dockerfile_list[i][0].replace("+","/")
        content = dockerfile_list[i][1]
        print("\n", i, "---", image_id)        
        passage = get_dockerfile_from_database.deal_dockerfile_layer(content)
        for cnt, each_passage in enumerate(passage):
            title_dict.append("baaaaaaad--" + image_id + "--" + str(cnt)) if flag == 1 else title_dict.append(image_id + "--" + str(cnt))
        passage_dict += passage
        
def get_dict_ast(passage_dict, title_dict, table_name, num, flag = 0):
    ast_dict = []
    dockerfile_maneger = get_dockerfile_from_database.Dockerfile_Maneger("localhost", "test", num, 0, passwd = "123456", table_name = table_name ) # ("211.69.198.51", "dockerfile", 1, 0) 
    dockerfile_list = dockerfile_maneger.lookup()
    for i in range(len(dockerfile_list)):
        image_id = dockerfile_list[i][0].replace("+","/")
        content = dockerfile_list[i][1]
        print("\n", i, "---", image_id)        
        passage, ast_dict_tem = get_dockerfile_from_database.deal_dockerfile_ast(content)
        for cnt, each_passage in enumerate(passage):
            title_dict.append("baaaaaaad--" + image_id + "--" + str(cnt)) if flag == 1 else title_dict.append(image_id + "--" + str(cnt))
        passage_dict += passage
        ast_dict += ast_dict_tem
    return ast_dict

def save_classify(data_save_path, cluster_group, label_dict, title_dict, passage_dict):
    print(cluster_group)
    print(label_dict)
    f_json = open(data_save_path + "/result.json","w")
    # json_str = json.dumps(cluster_group, sort_keys=True, indent=4)
    json.dump(cluster_group, f_json, sort_keys=True, indent=4)

    for i in label_dict:
        group_name = data_save_path + str(i) + ".txt"
        f = codecs.open(group_name, 'w',encoding="utf8")
        for passage_index in cluster_group[i]:
            f.writelines(title_dict[int(passage_index)] + "\n")
            f.writelines(passage_dict[int(passage_index)] + "\n\n")
        f.close()

# 先获取dockerfile文件信息，然后根据doc2vec训练模型，将相似度的数据表带入label propagation之后进行分类
def train_model_and_label_propagation():
    os.system("clear")
    layer = True
    Bad_image = True
    

    num = 5000
    bad_num = 600
    bad_dict_num = 0
    title_dict = []
    passage_dict = []

    if layer == False:
        # 使用方式一获取文章和标题的列表
        if Bad_image == True:
            get_dict(passage_dict, title_dict, "bad_dockerfile", bad_num, flag = 1)     # 方式一：以 dockerfile 为节点获取恶意节点
            bad_dict_num = len(title_dict)
        get_dict(passage_dict, title_dict, "dockerfile", num)                           # 方式一：以 dockerfile 为节点
    else:
        # 使用方式二获取文章和标题的列表
        if Bad_image == True:
            get_dict_layer(passage_dict, title_dict, "bad_dockerfile", bad_num, flag = 1)   # 方式二：以 dockerfile 的 layer 为节点获取恶意节点
            bad_dict_num = len(title_dict)  
        get_dict_layer(passage_dict, title_dict, "dockerfile", num)                         # 方式二：以 dockerfile 的 layer 为节点
    print(len(title_dict))
    print(len(passage_dict))
    
    layer_add = "layer-" if layer == True else ""
    data_save_path = "./" + layer_add + "data-" + str(num) + "(" + str(bad_dict_num) + ")/"
    if not os.path.exists(data_save_path):  os.makedirs(data_save_path)
    model_save_name = data_save_path + "model-" + str(num)
    data_save_name = data_save_path + "label_data.txt"
    model_read_name = model_save_name
    
    # 将文档打上tag并进行训练
    passage_word_dict = doc2vec.cut_passage(passage_dict)
    doc2vec.train(passage_word_dict, model_save_name)
    
    # # # 测试用，在训练好的模型中匹配文档
    # # # test_num = 1
    # # # doc2vec.look_up(model_read_name, title_dict, passage_dict, passage_word_dict, test_num)

    # 将模型保存为节点数据
    doc2vec.save_node(model_read_name, data_save_name, passage_dict)
    # 通过label propagation算法获得节点分类
    cluster_group, label_dict = label_propagation.classify(data_save_name)
    # 保存分类数据，方便比较
    save_classify(data_save_path, cluster_group, label_dict, title_dict, passage_dict)
    
def form_ast():
    os.system("clear")
    print("hello")
    num = 3
    title_dict = []
    json_dict = []
    passage_dict = []
    ast_dict = get_dict_ast(passage_dict, title_dict, "dockerfile", num)                       # 方式二：以 dockerfile 的 layer 为节点
    # print(passage_dict)
    # for cnt, content in enumerate(passage_dict):
    #     json_dict.append(title_dict[cnt])
    #     json_dict.append(content)
    #     json_dict += deal_shell.outer_test(content, title_dict[cnt])
    f_json = open("./dockerfile.json","w")
    json.dump(ast_dict, f_json, sort_keys=True, indent=4)
    f_json.close()

def main():
    # train_model_and_label_propagation()
    form_ast()
    # deal_shell.main()
    

if __name__ == "__main__":
    main()
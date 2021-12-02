# from nltk.util import pr


def label_propagation(vector_dict, edge_dict):
    '''标签传播
    input:  vector_dict(dict)节点：社区
            edge_dict(dict)存储节点之间的边和权重
    output: vector_dict(dict)节点：社区
    '''
    # 初始化，设置每个节点属于不同的社区
    t = 0
    # 以随机的次序处理每个节点
    repeate_stack = {}
    while True:
        if (check(vector_dict, edge_dict, repeate_stack) == 0):
            t = t + 1
            print("iteration: ", t)
            print(repeate_stack)
            # 对每一个node进行更新
            for node in vector_dict.keys():
                adjacency_node_list = edge_dict[node]  # 获取节点node的邻接节点
                vector_dict[node] = get_max_community_label(vector_dict, adjacency_node_list)
            # print(vector_dict)
        else:
            break
    return vector_dict
    
def get_max_community_label(vector_dict, adjacency_node_list):
    '''得到相邻接的节点中标签数最多的标签
    input:  vector_dict(dict)节点：社区
            adjacency_node_list(list)节点的邻接节点
    output: 节点所属的社区
    '''
    label_dict = {}
    for node in adjacency_node_list:
        node_id_weight = node.strip().split(":")
        node_id = node_id_weight[0]  # 邻接节点
        node_weight = node_id_weight[1]  # 与邻接节点之间的权重
        # node_weight = int(node_id_weight[1])  # 与邻接节点之间的权重
        if vector_dict[node_id] not in label_dict:
            label_dict[vector_dict[node_id]] = node_weight
        else:
            label_dict[vector_dict[node_id]] += node_weight
    # 找到最大的标签
    sort_list = sorted(label_dict.items(), key=lambda d: d[1], reverse=True)
    return sort_list[0][0]

def check(vector_dict, edge_dict, repeate_stack):
    '''检查是否满足终止条件
    input:  vector_dict(dict)节点：社区
            edge_dict(dict)存储节点之间的边和权重
    output: 是否需要更新
    '''
    for node in vector_dict.keys():
        adjacency_node_list = edge_dict[node]  # 与节点node相连接的节点
        node_label = vector_dict[node]  # 节点node所属社区
        label = get_max_community_label(vector_dict, adjacency_node_list)
        if node_label == label:  # 对每个节点，其所属的社区标签是最大的
            continue
        else:

            # print("出问题的节点是：", node)
            # print("出问题的节点label是：", node_label)
            # print("权值最大的的节点label是：", label)
            key = str(node) + "+" + str(node_label) + "+" +  str(label)
            if key in repeate_stack and repeate_stack[key]>=3 : continue
            
            if key not in repeate_stack:
                repeate_stack[key] = 1 
            else:
                repeate_stack[key] += 1
            # for i in repeate_stack:
                # if repeate_stack[i]>=3: return 1
            return 0
    return 1

def loadData(filePath):
    f = open(filePath)
    vector_dict = {}
    edge_dict = {}
    for line in f.readlines():
        lines = line.strip().split(" ")
        for i in range(2):
            if lines[i] not in vector_dict:
                # vector_dict[lines[i]] = lines[i]
                vector_dict[lines[i]] = int(lines[i])
                edge_list = []
                if len(lines) == 3:
                    edge_list.append(lines[1 - i] + ":" + lines[2])
                else:
                    edge_list.append(lines[1 - i] + ":" + "1")
                edge_dict[lines[i]] = edge_list
            else:
                edge_list = edge_dict[lines[i]]
                if len(lines) == 3:
                    edge_list.append(lines[1 - i] + ":" + lines[2])
                else:
                    edge_list.append(lines[1 - i] + ":" + "1")
                edge_dict[lines[i]] = edge_list
    return vector_dict, edge_dict

def classify(data_save_name):
    print("正在对节点分类...")
    label_dict = set([])
    vector, edge = loadData(data_save_name)
    print("数据加载完成...")
    vector_dict = label_propagation(vector, edge)
    # print(vector_dict)
    cluster_group = dict()
    for node in vector_dict.keys():
        cluster_id = vector_dict[node]
        print("cluster_id, node", cluster_id, node)
        if cluster_id not in cluster_group.keys():
            cluster_group[cluster_id] = [node]
        else:
            label_dict.add(cluster_id)
            cluster_group[cluster_id].append(node)
    print("分类完成...")
    return cluster_group, label_dict


def main():
    label_dict = set([])
    filePath = './data/label_data.txt'
    vector, edge = loadData(filePath)
    print(vector)
    print(edge)
    vector_dict = label_propagation(vector, edge)
    print(vector_dict)
    cluster_group = dict()
    for node in vector_dict.keys():
        cluster_id = vector_dict[node]
        print("cluster_id, node", cluster_id, node)
        if cluster_id not in cluster_group.keys():
            cluster_group[cluster_id] = [node]
        else:
            label_dict.add(cluster_id)
            cluster_group[cluster_id].append(node)
    print(cluster_group)
    print(label_dict)

if __name__ == '__main__':
    main()

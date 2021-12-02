import enum
import os, sys, re, json
from typing import Pattern
import deal_shell
sys.path.append(os.path.dirname(__file__) + os.sep + ".." )
import get_dockerfile_from_database as get_data

def print_line():
    print("=======================================================================================================================================")

def print_dict(dict):       # 按照普通空行格式打印dict
    for i in dict: print(i + "\n")

def print_json(json_dict):  # 按照json格式打印dict
    print(json.dumps(json_dict, sort_keys=True, indent=4))

def save_json(json_dict):  # 按照json格式存储dict
    f = open("./form_ast/result.json", "w")
    json.dump(json_dict, f, sort_keys=True, indent=4)
    f.close()

def get_raw_data_local(table_name, num, start): # 获取最原始的数据文件
    title_dict = []
    content_dict = []
    dockerfile_maneger = get_data.Dockerfile_Maneger("localhost", "test", num, start = start, passwd = "123456", table_name = table_name )
    dockerfile_list = dockerfile_maneger.lookup()
    for i in range(len(dockerfile_list)):
        image_id = dockerfile_list[i][0].replace("+","/")
        content = dockerfile_list[i][1]
        content_dict.append(content)
        title_dict.append(image_id)
    return title_dict, content_dict

def save_raw_data_local(filename, table_name, num, start):  # 将dockerfile数据存入文本文件
    f = open(filename, "w")
    title_dict, content_dict = get_raw_data_local(table_name, num, start)
    for i in range(len(title_dict)):
        f.writelines("\n" + str(i) + "---" + title_dict[i] + "\n")
        f.writelines(content_dict[i])
        f.writelines("=======================================================================================================================================")
    f.close()

def save_command_data_local(filename , table_name, num, start):  # 将dockerfile  command数据存入文本文件
    f = open(filename, "w")
    passage_cnt = -1
    title_dict, content_dict, type_dict = get_command_dict(table_name, num, start)
    for cnt, layer in enumerate(content_dict):
        if title_dict[cnt][-1] == "0": passage_cnt += 1
        f.writelines("\np: " + str(passage_cnt) + ",l:" + str(cnt) + "---" + title_dict[cnt] + "\n")
        for cnt2, command_dict in enumerate(layer):
            f.writelines("\n\n第" +  str(cnt2) + "个dockerfile command类型为" + type_dict[cnt][cnt2])
            for command in command_dict:
                f.writelines("\n" + command + "\n")
        f.writelines("\n=======================================================================================================================================")
    f.close()

def get_expecial_command(command):
    # print("处理前的command为：", command)
    # 匹配for循环进行替换
    for_re_str = r'for\s(.*?)in(.*?)do(.*?)done'
    for_re_str_all = r'for\s.*?in.*?do.*?done'
    find_list = re.findall(for_re_str, command)
    find_list_all = re.findall(for_re_str_all, command)
    for cnt, item in enumerate(find_list):
        command_sub = ""
        item1 = item[0].lstrip().rstrip()
        item2 = item[1].lstrip().rstrip().rstrip(";").rstrip()
        item3 = item[2].lstrip().rstrip()
        for item_var in item1.split():
            for item_list in item2.split():
                command_sub += re.sub("\$"+ item_var, item_list, item3)
        # print("======", command_sub)
        # print("======", find_list_all[cnt])
        command = command.replace(find_list_all[cnt], command_sub).replace(";;",";")
    # 匹配if循环进行替换
    if_re_str = r'if\s(.*?)then(.*?)(elif\s(.*?)then(.*?))*(else(.*?))*fi'
    if_re_str_all = r'(if\s.*?then.*?(elif\s.*?then.*?)*(else.*?)*fi)'
    find_list = re.findall(if_re_str, command)
    find_list_all = re.findall(if_re_str_all, command)
    # print(find_list, len(find_list))
    # print(find_list_all, len(find_list_all))
    for cnt, item in enumerate(find_list):
        command_sub = ""
        item = [i.lstrip().rstrip() for i in item if "elif" not in i and "else" not in i and i.lstrip().rstrip() != ""]
        # print_dict(item)
        for cnt2, item_var in enumerate(item):
            if cnt2 != len(item)-1 and cnt2 % 2 == 0: continue
            command_sub += item_var
        command = command.replace(find_list_all[cnt][0], command_sub).replace(";;",";") 
        command = re.sub(r";\s*\)", ")", command)  
    # print("\n处理后的command为：", command)
    return command
    
def get_layer_data_local(table_name, num, start):  # 获取layer粒度的数据文件
    layer_title_dict = []         
    layer_content_dict = []
    dockerfile_maneger = get_data.Dockerfile_Maneger("localhost", "test", num, start = start, passwd = "123456", table_name = table_name )
    dockerfile_list = dockerfile_maneger.lookup()
    for i in range(num):
        image_id = dockerfile_list[i][0].replace("+","/")   # 处理镜像名
        content = dockerfile_list[i][1]                     # 获取镜像dockerfile
        content = get_expecial_command(content)
        layer_dict = get_data.get_layer_dict(content)       # 将dockerfile 按照CMD以及ENTRYPOINT进行分层（CMD与ENTRYPOINT命令也会加入该层数组中）
        layer_content_dict += layer_dict                    
        for cnt, each_dict in enumerate(layer_dict):
            layer_title_dict.append(image_id + "--" + str(cnt))   # 镜像名按照分层加上数字标号
    return layer_title_dict, layer_content_dict

def get_command_dict(table_name, num, start): # 获取command粒度的数据文件
    type_dict = []
    command_dict = []
    layer_title_dict, layer_content_dict = get_layer_data_local(table_name, num, start)
    for cnt, layer in enumerate(layer_content_dict):
        layer_command = []
        layer_type = []
        for cnt2, command in enumerate(layer):
            # command = get_expecial_command(command)
            command_list = command.split("&&")
            command_list = [i.lstrip().rstrip() for i in command_list]
            layer_type.append(command_list[0].split(" ")[0])
            command_list[0] = " ".join(command_list[0].split()[1:])
            layer_command.append(command_list)
        command_dict.append(layer_command)
        type_dict.append(layer_type)
    return layer_title_dict, command_dict, type_dict

def get_not_RUN(typename, command):
    # print(command, "\n")
    json_dockerfile_command = []
    if typename == "ADD":
        dockerfile_command = {"type":"ADD", "file": "", "position": ""}
        dockerfile_command["file"] = command.split()[0].split(":")[-1]
        dockerfile_command["position"] = command.split()[-1]
    elif typename == "COPY":
        dockerfile_command = {"type":"COPY", "file": "", "position": ""}
        dockerfile_command["file"] = command.split()[0].split(":")[-1]
        dockerfile_command["position"] = command.split()[-1]
    elif typename == "CMD":
        dockerfile_command = {"type":"CMD", "command": ""}
        dockerfile_command["command"] = command.lstrip("[").rstrip("]").lstrip("\"").rstrip("\"")
    elif typename == "ONBUILD":
        dockerfile_command = {"type":"ONBUILD", "command": ""}
        dockerfile_command["command"] = command
    elif typename == "WORKDIR":
        dockerfile_command = {"type":"WORKDIR", "position": ""}
        dockerfile_command["position"] = command.split()[-1]
    elif typename == "MAINTAINER":
        dockerfile_command = {"type":"MAINTAINER", "name": ""}
        dockerfile_command["name"] = command   
    elif typename == "STOPSIGNAL":
        dockerfile_command = {"type":"STOPSIGNAL", "name": ""}
        dockerfile_command["name"] = command   
    elif typename == "EXPOSE":
        dockerfile_command = {"type":"EXPOSE", "port": []}
        dockerfile_command["port"] = command.split()
    elif typename == "ENTRYPOINT":
        dockerfile_command = {"type":"ENTRYPOINT", "command": ""}
        dockerfile_command["command"] = command
    elif typename == "VOLUME":
        dockerfile_command = {"type":"VOLUME", "command": ""}
        dockerfile_command["command"] = command.lstrip("[").rstrip("]")
    elif typename == "USER":
        dockerfile_command = {"type":"USER", "command": ""}
        dockerfile_command["command"] = command.lstrip("[").rstrip("]")
    elif typename == "ENV":
        dockerfile_command = {"type":"ENV", "dict": {}}
        if "BEGIN RSA PRIVATE KEY" in command:
            dockerfile_command["dict"][command.split("=")[0]] = "RSA PRIVATE KEY NOT LOAD"
        else:
            env = command.split("=")
            env = [item.lstrip().rstrip() for item in env if item.lstrip().rstrip() != ""]
            for i in range(len(env)-1):
                key = env[i] if i == 0 else env[i].split()[-1]
                value = env[i+1] if i == len(env)-2 else " ".join(env[i+1].split()[:-1])
                dockerfile_command["dict"][key] =  value
            if len(env) == 1:
                dockerfile_command["dict"][env[0].split()[0]] =  " ".join(env[0].split()[1:]).lstrip()
    elif typename == "LABEL":
        dockerfile_command = {"type":"LABEL", "dict": {}}
        label = re.split("=|==", command)
        label = [item.lstrip().rstrip() for item in label if item.lstrip().rstrip() != ""]
        for i in range(len(label)-1):
            key = label[i] if i == 0 else label[i].split()[-1]
            value = label[i+1] if i == len(label)-2 else " ".join(label[i+1].split()[:-1])
            dockerfile_command["dict"][key] =  value
    elif typename == "ARG":
        dockerfile_command = {"type":"ARG", "dict": {}}
        label = re.split("=|==", command)
        label = [item.lstrip().rstrip() for item in label if item.lstrip().rstrip() != ""]
        for i in range(len(label)-1):
            key = label[i] if i == 0 else label[i].split()[-1]
            value = label[i+1] if i == len(label)-2 else " ".join(label[i+1].split()[:-1])
            dockerfile_command["dict"][key] =  value
        if len(label) == 1:
            dockerfile_command["dict"][label[0].split()[0]] =  " ".join(label[0].split()[1:]).lstrip()
    else:
        dockerfile_command = {"type":"Default" + typename, "command": ""}
        dockerfile_command["command"] = typename if command == "" else command
    # print(dockerfile_command)
    json_dockerfile_command.append(dockerfile_command)
    return json_dockerfile_command

def get_base_info(layer_dict):  # 根据获取的命令的json_dict格式文件中的第一层进行ast的提取
    base_dict  = {"type":"BASE", "content": ""}
    print_line()
    return base_dict

def get_ast_not_run(command):  # 根据获取的命令的json_dict格式文件中的非RUN类型进行ast的提取
    if command["type"] == "WORKDIR" :
        ast_command = {"type":"CHANGE_POSITION", "name":command["type"], "content": command["position"]}
    elif command["type"] == "ONBUILD" :
        command_type = command["command"].split()[0]
        command_content = command["command"].split(" ",1)[1]
        if command_type != "RUN":
            ast_command = get_ast_not_run(get_not_RUN(command_type, command_content)[0])
        else:
            ast_command = get_ast_run(deal_shell.bashlex_match(command_content.lstrip("[").rstrip("]").strip())[0])
        ast_command["type"] = "ONBUILD_" + ast_command["type"]
    elif command["type"] in ["ENTRYPOINT", "CMD"] :
        ast_command = {"type":"CMD", "name":command["type"], "content": command["command"]}
    else:  
        ast_command = {"type":"NOT_INCLUDE_" + command["type"], "name":command["name"] if 'name' in command else "NO_NAME", "content": ""}
    return ast_command

def get_ast_run(command):  # 根据获取的命令的json_dict格式文件中的RUN类型进行ast的提取
    if "pipe" in command:
        command["second"]["para"] = command["first"]["name"]
        ast_command = get_ast_run(command["second"])
    elif "redirection-to" in command:
        ast_command = {"type":"CHANGE_FILE", "name":command["name"], "content": command["redirection-to"]}
    elif command["name"] in ["apt-get install", "apk install","pip install"]:
        ast_command = {"type":"INSTALL", "name":command["name"], "content": command["para"]}
    elif command["name"] in ["apt-get", "apk","pip","/usr/bin/yum", "yum"] and "install" in command["para"]:
        ast_command = {"type":"INSTALL", "name":command["name"] + " install", "content": [ i for i in command["para"] if i != "install"]}
    elif command["name"] in ["apk"] and "add" in command["para"]:
        ast_command = {"type":"INSTALL", "name":command["name"] + " add", "content": [ i for i in command["para"] if i != "add"]}
    elif command["name"] in ["git clone"]:
        ast_command = {"type":"INSTALL", "name":command["name"], "content": [i.lstrip("https://github.com").rstrip(".git") for i in command["para"] if "https://github.com" in i]}
    elif command["name"] in ["wget"]:
        ast_command = {"type":"INSTALL", "name":command["name"], "content": [i.split("/")[-1] for i in command["para"] if "https://" in i]}
    
    elif command["name"] in ["apt-get clean", "apt-get purge","pip uninstall", "apk del"]:
        ast_command = {"type":
            "UNINSTALL", "name":command["name"] , "content": command["para"]}
    elif command["name"] in ["make","cmake"]:
        ast_command = {"type":"MAKE", "name":command["name"], "content": command["para"]}
    elif command["name"] in ["cd"]:
        ast_command = {"type":"CHANGE_POSITION", "name":command["name"], "content": command["para"]}
    elif command["name"] in ["cp", "mv"]:
        ast_command = {"type":"CHANGE_NAME", "name":command["name"], "content": command["para"]}
    else:
        ast_command = {"type":"NOT_INCLUDE_" + command["type"], "name":command["name"] if 'name' in command else "NO_NAME", "content": command["para"]}
    return ast_command

def show_save_data(table_name, num, start):   # 将dockerfile数据存入文本文件，并进行展示操作
    filename = "./form_ast/dockerfile_content/bad_dockerfile_command_"
    num = 600
    for start in range(0,1000,1000):
        filename_tem = filename + str(start) + "_" + str(start + num) + ".txt"
        save_command_data_local(filename_tem, table_name, num, start)  
   
def show_ast_command(table_name, num, start):  # 通过command粒度的数据文件获取json_dict格式的解析结果,并进行展示操作
    title_dict, content_dict, type_dict = get_command_dict(table_name, num, start)
    f_error = open("./form_ast/AST过程中出现的错误.txt","w+")
    json_dict = []
    passage_cnt = 0
    for cnt, layer in enumerate(content_dict):
        print_line()
        json_layer = []
        if title_dict[cnt][-1] == "0": passage_cnt += 1
        print("\np: " , passage_cnt , ",l:", cnt, "---该层名为：", title_dict[cnt], "，---dockerfile command数量为：", len(layer))
        for cnt2, command_dict in enumerate(layer):
            print("\n第", cnt2 , "个dockerfile command类型为", type_dict[cnt][cnt2])
            if type_dict[cnt][cnt2] != "RUN":   # 先手动处理不是RUN的情况
                json_dockerfile_command = []
                # if len(command_dict)!=1: 
                #     print("非RUN的命令有&&连接")
                #     f_error.writelines(title_dict[cnt] + "  " + command_dict[0] + "---- error is: 非RUN的命令有&&连接\n")
                for command in command_dict:
                    if command == "": continue
                    json_dockerfile_command += get_not_RUN(type_dict[cnt][cnt2], command)
            else:
                json_dockerfile_command = []
                for command in command_dict:
                    command = command.lstrip("[").rstrip("]").lstrip().rstrip()
                    # print("\n命令是：", command)
                    try:
                        dockerfile_command = deal_shell.bashlex_match(command)
                        # print_json(dockerfile_command)
                        json_dockerfile_command += (dockerfile_command)
                    except Exception as e:
                        print("command error!", e)
                        f_error.writelines(title_dict[cnt] + "  " + command + "---- error is: " + str(e) + "\n")
            json_layer.append(json_dockerfile_command)
        json_dict.append(json_layer)
    save_json(json_dict)
    return title_dict, json_dict

def show_ast(title_dict, json_dict):   # 通过json格式的解析结果,获取按照ast格式排列的树
    print_line()
    print_line()
    ast_dict = []
    print("len(title_dict) = ", len(title_dict), "len(json_dict) = ", len(json_dict))
    for cnt, layer in enumerate(json_dict):
        ast_layer = []
        print("len(layer) = ", len(layer))
        print("\n----镜像名为：", title_dict[cnt])
        if title_dict[cnt][-1] == "0":   # 如果是第0层单独处理为BASE层
            ast_layer.append(get_base_info(layer))
        else:
            for dockerfile_command in layer:
                print("len(dockerfile_command) = ", len(dockerfile_command))
                for command in dockerfile_command:
                    print("-----", command, type(command))
                    ast_command = get_ast_not_run(command) if command["type"] != "RUN" else get_ast_run(command)
                    if "NOT_INCLUDE" not in ast_command["type"]: ast_layer.append(ast_command) 
                    # ast_layer.append(ast_command) 
        ast_dict.append(ast_layer)
    print_json(ast_dict)
    save_json(ast_dict)

def main():
    num = 600
    start = 0
    table_name = "bad_dockerfile"  # for 228,416   if 138
    # table_name = "dockerfile"   # for 2,   if 1245
    title_dict, json_dict = show_ast_command(table_name, num, start)
    show_ast(title_dict, json_dict)
    
if __name__ == "__main__":
    os.system("clear")
    main()
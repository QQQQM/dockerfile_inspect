import matcher
import markupsafe, urllib
import re, os, json, bashlex, pymysql
from dockerfile_parse import DockerfileParser

# f = open("./deal_shell/command.txt", "w")

# 预处理脚本内容，去除语法解析器无法解析的内容
def handle_script(content):
    # 去开头的bash -c 
    content = re.sub(r'^/bin/(ba)*?sh(\s)*(-+\S+\s+)*', '', content)
    content = re.sub(r'#\(nop\)', '', content)
    content = re.sub(r';\s*&&', '&&', content)
    # 解决多个{echo xxx； echo xxx；……| tee xxx}的情况
    pattern = re.compile(r'(?<=echo)\s*.*?;')
    content_temp = content
    content_temp_list = re.split(r"([|])",content_temp)  # 按照pip分组，防止一句话有多个这种特征出现
    content = ""
    for i in content_temp_list: 
        content_new = "echo"
        for j in re.findall(pattern,i):
            j = j.lstrip().rstrip().rstrip(";").rstrip()
            content_new += " " + j
        i = re.sub(r'\{(\s*echo.*?;)*\s*\}', content_new, i)
        content += i

    content = re.sub(r'\[', '', content)
    content = re.sub(r'\]', '', content)
    # 去除掉注释
    # content = re.sub(r'^[\s]*?#[\s\S]*?\r\n', '', content)
    # content = re.sub(r'#+[\s|\S]*?\n', '\r\n', content)
    # content = re.sub(r'\r\n\r\n', '\r\n', content)
    # 处理<<EOF EOF的问题
    content = re.sub(r'[\s]*?<<[\s]*?EOF[\s|\S]*?EOF', '', content)
    # 去除case语句
    content = re.sub(r'case[\s|\S]*?esac', 'echo "aaa"', content)
    # 提取while语句中的内容,去除while[]do done外壳，将内容放到内容中进行检测
    while_re_str = r'while[\s|\S|\r\n|\r]*?do([\s|\S|\r\n|\r]*?)done'
    find_list = re.findall(while_re_str, content)
    for item in find_list:
        content = re.sub(while_re_str, item, content, 1)

    # 去除[ $之间的空格
    content = re.sub('\[\s+\$', '[$', content)
    # 去除[ "$之间的空格
    content = re.sub('\[\s+"\$', '["$', content)
    # 去除[ `之间的空格
    content = re.sub('\[\s+`', '[`', content)
    content = re.sub('{', '', content)
    content = re.sub('}', '', content)

    # 带括号不支持
    # 处理do\r的问题
    content = re.sub(r'do\r', 'do \r\n', content)


    # \r\n变成\n
    content = re.sub(r'\r\n', '\n', content)
    # 处理每行末尾空格的情况
    content = re.sub(r'[\s]*?\n', '\n', content)

    # 去除空行
    content = re.sub(r'[\n]{2,}', '\n', content)

    content = content.strip()
    # print(repr(content))
    #print(content)
    return content

# 接受字符串dockerfile文本，返回分行的list
def extract_dockerfile(dockerfile):
    sentence = [i for i in dockerfile.split("\n\n") if i != ""]
    return sentence  

# 接受字符串类型输入，可以是一整个dockerfile也可以是一行命令
def extract_sentence(dockerfile):
    dockerfile = dockerfile.replace("\n"," ")
    dfp = DockerfileParser(path="./data")  
    dfp.content = dockerfile

    dataset = []
    json_dict = []     # 用于返回的json列表
    for command in dfp.structure:  
        # 对分析后的dockerfile逐条处理
        if (command["instruction"] == "/BIN/SH" or command["instruction"] == "/BIN/BASH") and "/bin/bash -c set" not in command["content"] and  "/bin/sh -c set" not in command["content"]:
            # f.writelines(dockerfile + "\n")
            data = command["value"].lstrip("-c").replace("&&", ";").replace("|", ";").replace("{", ";").replace("}", ";").replace("[", ";").replace("]", ";").split(";")
            dataset += data
    
    for item in dataset:
        d = {"name": "", "flag": "", "para": []}
        item_dict = item.split(" ")
        item_dict = [i.lstrip().rstrip() for i in item_dict if i != ""]
        item_dict = [i for i in item_dict if i != ""]
        
        # 去除/bin/bash带着的参数，并对首位的符号进行清除
        while(1):
            if item_dict == []: break
            if item_dict[0][0] == "-" or re.findall( r"=", item_dict[0]) or item_dict[0] == "for":
                item_dict.pop(0)
                continue
            if re.match(r"[^0-9a-zA-Z]", item_dict[0]):
                item_dict[0] = item_dict[0].lstrip(item_dict[0][0])
                if item_dict[0] == "": item_dict.pop(0)
                continue
            if re.findall( r"[^a-zA-Z0-9]$", item_dict[0]):
                item_dict[0] = item_dict[0].rstrip(item_dict[0][-1])
                continue
            break

        # 空集合则跳过
        if item_dict == []: continue

        # 如果是apt get则多获取一个命令
        paraflag = 0
        if item_dict[0] == "apt-get" and len(item_dict)>=2:
            while(1):
                if re.match(r"[^0-9a-zA-Z]", item_dict[1]):
                    item_dict[1] = item_dict[1].lstrip(item_dict[1][0])
                    continue
                if re.findall( r"[^a-zA-Z0-9]$", item_dict[1]):
                    item_dict[1] = item_dict[1].rstrip(item_dict[1][-1])
                    continue
                break
            # apt get的情况下添加一个命令并获取flag
            d["name"] = item_dict[0] + " " + item_dict[1]
            for morecommand in item_dict[2:]:
                if morecommand[0] == "-" and paraflag == 0:
                    d["flag"] = morecommand
                    continue
                else:
                    while(1):
                        if re.match(r"[^0-9a-zA-Z]", morecommand):
                            morecommand = morecommand.lstrip(morecommand[0])
                            continue
                        if re.findall( r"[^a-zA-Z0-9]$", morecommand):
                            morecommand = morecommand.rstrip(morecommand[-1])
                            continue
                        break
                    d["para"].append(morecommand)
                    paraflag = 1
            d["para"] = [i for i in d["para"] if i != ""]
            json_dict.append(d)
            continue

        # 非apt get的情况下添加一个命令并获取flag
        d["name"] = item_dict[0]
        for morecommand in item_dict[1:]:
            if morecommand[0] == "-" and paraflag == 0:
                d["flag"]  = morecommand
                continue
            else:
                while(1):
                    if re.match(r"[^0-9a-zA-Z]", morecommand):
                        morecommand = morecommand.lstrip(morecommand[0])
                        continue
                    if re.findall( r"[^a-zA-Z0-9]$", morecommand):
                        morecommand = morecommand.rstrip(morecommand[-1])
                        continue
                    break
                d["para"].append(morecommand) 
                paraflag = 1
        d["para"] = [i for i in d["para"] if i != ""]
        json_dict.append(d)
    return json_dict
   

def bashlex_match(cmd):
    command_list = []
    m = matcher.matcher(cmd)
    groups = m.match_json()
    commandgroups = groups[1:]
    # shellgroup = groups[0]
    # print(shellgroup)
    # for m in shellgroup.results:
    #     print("result --- ", m)
    flag_pipe = 0
    pipe_sign = ""
    # print("lenlenlen = ", len(commandgroups))
    for commandgroup in commandgroups:
        # print(commandgroup)
        # for m in commandgroup.results:            
        #     print("result --- ", m)
        d = {"type":"RUN", "name": "", "flag": [], "para": []}
        flag_apt = 0
        for cnt in range(len(commandgroup.results)):
            if flag_apt == 1:flag_apt = 0;continue
            if cnt == 0 and commandgroup.results[0].text[0] != "-":
                if commandgroup.results[0].text in ["apt-get", "apk", "git", "pip"] \
                    and len(commandgroup.results) >=2 \
                    and commandgroup.results[1].text[0] != "-":
                    d["name"] = commandgroup.results[0].text + " " + commandgroup.results[1].text
                    flag_apt = 1
                else:
                    d["name"] = commandgroup.results[0].text
                continue
            if commandgroup.results[cnt].match == "pipe":
                flag_pipe = 1
                pipe_sign = commandgroup.results[cnt].text
                continue
            if commandgroup.results[cnt].match == "redirect":
                d["redirection-to"] = commandgroup.results[cnt].text
                continue
            if len(commandgroup.results[cnt].text) >=1 and (commandgroup.results[cnt].text[0] == "-" or commandgroup.results[cnt].text[0] == "+"):
                d["flag"].append(commandgroup.results[cnt].text)
            else:
                d["para"].append(commandgroup.results[cnt].text)
        if flag_pipe == 1:
            d_pipe = {"type":"RUN", "first": {}, "pipe": "" , "second": {}}
            d_pipe["first"] = d
            d_pipe["pipe"] = pipe_sign
            flag_pipe += 1
            continue
        elif flag_pipe == 2:
            d_pipe["second"] = d
            flag_pipe = 0
            pipe_sign = ""
            command_list.append(d_pipe)
            continue
        command_list.append(d)
    return command_list

# 进行变量溯源
def source_var(content):
    # print("------------------------------------------------------")
    partten = re.compile(r'\sENV.*?\n')
    cmd_list = re.findall(partten,content)
    for i in cmd_list: 
        
        if "=" in i.split()[1]: i = i.replace("="," ")
        var_name = "$" + i.split()[1]
        var_content = " ".join(i.split()[2:])
        # print(var_name, var_content)
        content = content.replace(var_name, var_content)
    # print("------------------------------------------------------")
    
    return content

# 使用explainshell的方式对命令进行解析，接受原始命令
def explainshell_way(content, image_id, f_error):
    json_dict = []
    ast_dict = []
    image_dict = []
    content = source_var(content)
    sentence = extract_dockerfile(content)
    for cmd in sentence:
        print("\n\n正在处理的原命令为：", cmd)
        if "/usr/sbin/policy-rc.d  && echo 'exit 101'" in cmd:
            print("出现exit 101跳过------------------------------------------------------")
            
            continue
        else:
            if re.match(r"CMD", cmd.lstrip()) != None:
                print("出现CMD分layer------------------------------------------------------")
                if len(json_dict) != 0: ast_dict.append(json_dict) 
                json_dict = []
                continue
        
        
        cmd_after = cmd.replace("\n"," ")
        cmd_list = cmd.lstrip().split()
        # if (cmd_list[0] == "/bin/sh" or cmd_list[0] == "/bin/bash") and "/bin/bash -c set" not in cmd and  "/bin/sh -c set" not in cmd:
        cmd_after = handle_script(cmd_after)
        print("处理后为：", cmd_after)
        if cmd_after.lstrip() == "": continue
        
        try:
            json_dict += bashlex_match(cmd_after)
        except Exception as e:
            print("command error!", e)
            f_error.writelines(image_id + "  " + cmd + "---- error is: " + str(e) + "\n")
    if len(json_dict) != 0: ast_dict.append(json_dict)
    for cnt, _ in enumerate(ast_dict):
        image_dict.append(image_id + "--" + str(cnt))
    return ast_dict, image_dict

# 使用parse配合自行解析的方式对命令进行解析，接收原始命令
def parser_way(content, json_dict):
    sentence = extract_dockerfile(content)
    for sen in sentence:
        json_dict += extract_sentence(sen)
    return json_dict

    
def main():
    ast_dict = []
    image_dict = []
    f_json = open("./form_ast/result.json","w")
    f_error = open("./form_ast/command_error.txt","w+")
    
    start = 0
    num = 100
    conn = pymysql.connect(host = 'localhost', port = 3306, user = "root", passwd = "123456", db = "test")
    cur = conn.cursor()
    sql = "select * from dockerfile limit " + str(start) + "," + str(num) + ";"
    cnt = cur.execute(sql)
    print("共查询", cnt, "条记录")
    for i in range(cnt):
        result = cur.fetchone()
        image_id = result[0].replace("+","/")
        content = result[1]
        print("\n", i, "---", image_id)
        json_dict, image_dict_tem = explainshell_way(content, image_id, f_error)
        # parser_way(content, json_dict)
        image_dict += image_dict_tem
        ast_dict += json_dict
        
    json_str = json.dumps(ast_dict, sort_keys=True, indent=4)
    # print(json_str)
    json.dump(ast_dict, f_json, sort_keys=True, indent=4)
    draw_chain(ast_dict, image_dict)
    
    
def draw_chain(ast_dict, image_dict):
    print(len(ast_dict))
    print(len(image_dict))
    chain_json = open("./form_ast/chain.json","w")
    chain_dict = []
    for cnt, ast in enumerate(ast_dict):
        chain = {}
        chain["image_name"] = image_dict[cnt]
        for cmd in ast:
            if "name" in cmd and "para" in cmd : 
                if cmd['name'] == "ADD"  or "install" in cmd['name'] or 1:
                    # print(cmd['name'])
                    # print(cmd['para'])
                    for para in cmd['para']:
                        # print(para)
                        # print(cmd['name'])
                        # print(chain.keys())
                        # print()
                        if para in chain.keys():
                            chain[para].append(cmd['name'])
                        else:
                            chain[para] = []
                            chain[para].append(cmd['name'])
            else:  # 针对有pipline的情况
                print(cmd['first'])
                print(cmd['second'])
        
        chain_dict.append(chain)
    # json_str = json.dumps(chain_dict, sort_keys=True, indent=4)
    # print(json_str)
    json.dump(chain_dict, chain_json, sort_keys=True, indent=4)
    

def first_class():
    f = open("./form_ast/command.txt")
    f_error = open("./form_ast/command_error.txt","w+")
    command_list_all = []
    for index, cmd in enumerate(f.readlines()[180:181]):
        print("\n\n正在处理：", index, "原命令为：", cmd)
        # cmd = '/bin/sh -c find . -type f -exec chmod 644 {} ;&& find . -type d -exec chmod 755 {} ;'
        # cmd = 'ls -s|sort -nr'
        # cmd = "for user in $(cut -f1 -d: /etc/passwd); do crontab -u $user -l 2>/dev/null; done"
        cmd = handle_script(cmd)
        print("处理后为：", cmd)
        try:
            command_list_all += bashlex_match(cmd)
        except Exception as e:
            print("command error!", e)
            f_error.writelines(str(index) + "  " + cmd + "\n")
    f.close()
    f_error.close()
    json_str = json.dumps(command_list_all, sort_keys=True, indent=4)
    print(json_str)
    return command_list_all

if __name__ == "__main__":
    os.system("clear")
    main()
    # first_class()

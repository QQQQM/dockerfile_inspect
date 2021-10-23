import re, os, nltk, pymysql
from dockerfile_parse import DockerfileParser

class Dockerfile_Maneger(object):
    def __init__(self, host, name , num, start = 0, passwd=""):  # localhost, test, 1, 0    211.69.198.51,dockerfile,1,0,passwd = 123456
        self.database_name = name
        self.lookup_start = start
        self.lookup_num = num
        self.passwd = passwd
        self.result_list = []
        self.conn = pymysql.connect(host = host, port = 3306, user = "root", passwd = passwd, db = self.database_name)
        self.cur = self.conn.cursor()
    
    def lookup(self):
        sql = "select * from dockerfile limit " + str(self.lookup_start) + "," + str(self.lookup_num) + ";"
        cnt = self.cur.execute(sql)
        print("共查询", cnt, "条记录")
        for i in range(cnt):
            result = self.cur.fetchone()
            self.result_list.append(result)
            # image_id = result[0].replace("+","/")
            # print("\n", i, "---", image_id)
            # if self.passwd == "":
            #     manifest = result[1]
            #     history = result[2]
            #     print("manifest ------ ", manifest)               
            #     print("history ------ ", history)               
            # else:
            #     content = result[1]
            #     print("content ------ ", content)  
            # explainshell_way(content, json_dict, image_id, f_error)
            # parser_way(content, json_dict)
        return self.result_list
    
        # 接受字符串dockerfile文本，返回分行的list

# 预处理脚本内容，去除语法解析器无法解析的内容
def handle_script(content):
    # 去开头的bash -c 
    content = re.sub(r'^/bin/sh -c set', '', content)
    content = re.sub(r'^/bin/(ba)*?sh(\s)*(-+\S+\s+)*', '', content)
    content = re.sub(r'#\(nop\)', '', content)
    content = re.sub(r';\s*&&', '&&', content)
    content = re.sub(r'\s-+\S+', '', content)
    content = re.sub(r',-+\S+', '', content)
    content = re.sub(r';-+\S+', '', content)
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


def extract_dockerfile(dockerfile):
    dockerfile = dockerfile.replace("="," ")
    sentence = [i for i in dockerfile.split("\n\n") if i != ""]
    return sentence  

# 使用parse配合自行解析的方式对命令进行解析，接收原始命令
def deal_dockerfile(content):
    passage = ""
    sentence = extract_dockerfile(content)
    for sen in sentence:
        # print(sen)
        if "/usr/sbin/policy-rc.d  && echo 'exit 101'" in sen:
            continue
        else:
            sen = handle_script(sen)
            # print("处理后---", sen,"\n")
            passage += sen + " "
    # for sen in sentence:
    #     json_dict += extract_sentence(sen)
    # print("\n\n----", nltk.word_tokenize(passage))
    # print("\n\n----", nltk.pos_tag(nltk.word_tokenize(passage))) #对分完词的结果进行词性标注
    return passage

def main():
    os.system("clear")
    print("正在以main进程从数据库中获取dockerfile")
    flag = 0
    dockerfile_maneger = Dockerfile_Maneger("localhost", "test", 1, 0, passwd = "123456") if flag == 0 else  Dockerfile_Maneger("211.69.198.51", "dockerfile", 1, 0) 
    dockerfile_maneger.lookup()

if __name__ == "__main__":
    main()
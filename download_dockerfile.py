# need two paras: python3 download_dockerfile.py $imageList
# $targetPath is a dir
# $imageList is a file (store images list)

import os
import re
import sys
import time
import threading
import requests
import pymysql
# from github_analyzer import resolve_Dockerfile_from_github

# basePath = "./" + sys.argv[1] + "/"
conn = pymysql.connect(
            host = 'localhost',#mysql服务器地址
            port = 3306,#端口号
            user = "root",
            passwd = "123456",
            db = 'test',#数据库名称
        )
cur = conn.cursor()#创建并返回游标
cnt = 0

class download_thread(threading.Thread):
    def __init__(self, image, type):
        threading.Thread.__init__(self)
        # image read from file contains "\n"
        self.image = image.strip()
        # have tag
        #self.image = image.strip().split(":")[0]

        self.user = image.split('/')[0]
        self.imageName = image.split('/')[1].strip()
        # have tag
        #self.tag =  image.strip().split(":")[1]

        self.maliciousType = type
        

        self.github = ""            # git master url
        self.githubCommits = {}     # githubCommits["branch-number"] = date
        self.Dockerfile = []
        self.tags = {}              # tags["tag's name"] = [build history]

        self.githubExistFlag = 0    # 0 is github not exist; 1 is exist
        self.DockerfileFlag = 0     # 0 represent "Dockerfile" page don't exist; 1 is exist
        self.tagsFlag = 0           # 0 represent "tags" page don't exist; 1 is exist
        self.buildsFlag = 0         # 0 represent "builds" page don't exist; 1 is exist

    def run(self):
        print('[INFO] Start Crawl Thread: ',self.image)

        self.resolve_images_info()

        # Download image's Dockerfile
        """
        if self.DockerfileFlag == 1:
            path = basePath + self.maliciousType + ":" + self.user + "+" + self.imageName + ":latest"
            
            if os.path.isfile(path):
                return
            
            dockerfile = open(path, "a+")
            
            #for content in self.Dockerfile:
            #    dockerfile.write(content + "\n\n")
            
            dockerfile.write(self.Dockerfile)
            dockerfile.close()
            return
        """

        if self.tagsFlag == 1:
            for tag, history in self.tags.items():
                # path = basePath + self.maliciousType + ":" + self.user + "+" + self.imageName + ":" + tag
                # if os.path.isfile(path):
                #     continue
                data_str = ""
                # dockerfile = open(path, "a+")
                for content in history:
                    data_str += content
                    data_str += "\n\n"
                    # dockerfile.write(content + "\n\n")
                # dockerfile.close()
                data_str = re.sub("\\\\\"","\"",data_str)
                data_str = re.sub("\"","\\\"",data_str)                
                sql = "INSERT INTO `bad_dockerfile`(`name`, `content`) VALUES (\"" + self.user + "+" + self.imageName + ":" + tag + "\",\"" + data_str + "\");"
                cur.execute(sql)
                conn.commit()
                global cnt
                print("data-----------------------",cnt)
                cnt += 1
            return
        else:
            print ("don't have build history", self.image)
            return

    def resolve_images_info(self):
        # Get tags list and image history of each tag
        self.check_tags()
        # Get 1. github commit; 2. github url; 3. judging github address whether exist
        
        #self.check_builds()
        # Get Dockerfile in Docker hub
        #self.check_Dockerfile()
        # Get Dockerfile from Github if it doesn't exist in Dockerhub
        #if self.DockerfileFlag == 0 and self.githubExistFlag == 1:
        #    self.Dockerfile, self.DockerfileFlag = resolve_Dockerfile_from_github(self.github + "/Dockerfile")

    def check_tags(self):
        print("[INFO] Resolving Tags:", self.image)

        url = 'https://hub.docker.com/v2/repositories/{}/tags/'.format(str(self.image))
        headers = {
            'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
        }
        content = requests.get(url,headers=headers)

        if content.status_code != 200:
            return

        content = content.json()

        try:
            tags = content["results"]
            if len(tags) == 0:
                with open("no-Dockerfile-no-history.list", "a+") as log:
                    log.write(self.image + "\n")
                return

            # set tag: this image has building history
            self.tagsFlag = 1

            for tag in tags:
                # get image's tags
                tagName = tag["name"]
                # get build history of each tag, "history" is a list []
                history = resolve_tags_to_imageHistory(self.image, tag["name"])

                if history == None:
                    with open("no-Dockerfile-no-history.list", "a+") as log:
                        log.write(self.image + "\n")
                        continue

                self.tags[tagName] = history

        except Exception as e:
            self.tagsFlag = 0
            print ("\033[1;31m[WARN]\033[0m Can't resolve images' tag list...")

    def check_builds(self):
        print("[INFO] Resolving Builds:", self.image)

        url = 'https://hub.docker.com/api/audit/v1/build/?include_related=true&offset=0&limit=50&object=%2Fapi%2Frepo%2Fv1%2Frepository%2F{}%2F{}%2F'.format(str(self.user),str(self.imageName))
        headers = {
            'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
        }
        content = requests.get(url,headers=headers)

        if content.status_code != 200:
            return None

        content = content.json()

        try:
            if content["meta"]["total_count"] != 0:
                self.buildsFlag = 1
                for object in content["objects"]:
                    # save the github commit and start create date in dict self.githubCommit
                    if "commit" in object and "start_date" in object:
                        commit = object["commit"]
                        date = object["start_date"]
                        self.githubCommits[commit] = date

                    if "source_repo" in object and self.github == "":
                        self.github = "https://github.com/" + object["source_repo"]
                        self.githubExistFlag = Check_github_exist(self.github)
            else:
                self.buildsFlag = 0
        except Exception as e:
            self.buildsFlag = 0
            print ("\033[1;31m[WARN]\033[0m Can't resolve builds logs...")

    def check_Dockerfile(self):
        print("[INFO] Resolving Dockerfile:", self.image)

        url = 'https://hub.docker.com/v2/repositories/{}/dockerfile/'.format(str(self.image))
        headers = {
            'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
        }
        content = requests.get(url,headers=headers)

        if content.status_code != 200:
            print (content.status_code)
            return

        content = content.json()

        try:
            if content["contents"] != "":
                dockerfile = content
                self.DockerfileFlag = 1
                self.Dockerfile = dockerfile["contents"]
                """
                # remove annotate
                anno = re.compile(r'[#](.*?)[\n]', re.S)
                Dockerfile = anno.sub(' ', dockerfile["contents"])#.replace("\\\n", "").replace("\n\n", "\n").strip().split("\n")
                # remove the blank
                for index in range(len(Dockerfile)):
                    Dockerfile[index] = Dockerfile[index].strip()
                # Return a self.Dockerfile = ["FROM...", "RUN ..."]
                self.Dockerfile = Dockerfile
                """
            else:
                self.DockerfileFlag = 0
        except Exception as e:
            self.DockerfileFlag = 0
            print ("\033[1;31m[WARN]\033[0m Can't resolve Dockerfile...")

def Check_github_exist(github):
    headers = {
        'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
    }
    content = requests.get(github,headers=headers)
    if content.status_code == 200:
        return 1
    else:
        return 0

# Getting the Dockerfile from "tags" page.
def resolve_tags_to_imageHistory(image, tag):
    url = 'https://hub.docker.com/v2/repositories/{}/tags/{}/images'.format(str(image),str(tag))
    headers = {
        'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
    }
    content = requests.get(url,headers=headers)

    if content.status_code != 200:
        return None

    content = content.json()

    try:
        imageHistory = []
        # [0] is needed, also only one result
        for commands in content[0]["layers"]:
            imageHistory.append(commands["instruction"].replace("\t", " ")) #.replace("\u0026","&").replace("\\", ""))
        return imageHistory
    except Exception as e:
        return None

def main(path):
    cores = 10
    newPath = "./" + path
    images = open(newPath, "r").readlines()
    for image in images:
        if "/" not in image:
            continue
        analyze_thread = []
        thread = download_thread(image, path.split(".")[0])

        # keep the threads < cores numbers
        if len(threading.enumerate()) < cores:
            thread.start()
            analyze_thread.append(thread)
        else:
            for t in analyze_thread:
                t.join()

            thread.start()
            analyze_thread.append(thread)

        for t in analyze_thread:
            t.join()
    
    conn.commit()
    cur.close()   
    conn.close()#关闭对象

if __name__ == '__main__':
    
    main(sys.argv[1])
    

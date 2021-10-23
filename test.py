import logging

'''format=%(asctime)s具体时间 %(filename)s文件名 %(lenvelname)s日志等级 %(message)s具体信息
   datemt=%a星期 %d日期 %b月份 %Y年份 %H:%M:%S时间'''
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(filename)s %(levelname)s %(message)s',
                    datefmt='%a %d %b %Y %H:%M:%S', filename='my.log', filemode='w')
# logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

logging.warning('this is warning')
logging.info('this is info')
logging.debug('this is debug')
logging.error('this is error')
logging.critical('this is critical')

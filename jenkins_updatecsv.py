#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author   : johnnyliu
# @Time     : 2023/7/11
# @Project  : test_tools

import threading
import csv
import json
import time

import requests
import logging
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置日志记录
# create logger obj
logger = logging.getLogger()

# set log level
logger.setLevel(logging.INFO)

# file handler
handler = logging.FileHandler('jenkins_updatecsv.log', mode='w', encoding='utf-8')
handler.setFormatter(logging.Formatter("%(asctime)s-%(name)s-%(levelname)s: %(message)s"))

logger.addHandler(handler)

def get_cookies():
    '''
    登录jenkins，获取cookies
    :return:
    '''
    # 配置无头浏览器选项
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 启用无头模式
    chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速
    chrome_options.add_argument("--no-sandbox")  # 避免沙箱限制

    # 创建无头浏览器对象
    driver = webdriver.Chrome(options=chrome_options)

    # 打开登录页面
    driver.get("https://jenkins.wywk.cn")

    # 执行登录操作
    username_input = driver.find_element(By.ID, 'username')
    password_input = driver.find_element(By.ID, 'password')
    login_button = driver.find_element(By.ID, 'login-submit')

    # 登录jenkins
    username_input.send_keys("")
    password_input.send_keys("")
    login_button.click()

    # 获取登录后的 cookie 信息
    cookies = driver.get_cookies()
    jenkins_token = {}
    jenkins_token.update({cookies[1]['name']: cookies[1]['value']})
    logging.info('成功获取cookies' + str(jenkins_token))
    return jenkins_token

def get_lastbuildnum(job_name, cookies):
    '''
    调用jenkins API获取最新的构建number
    :param job_name:
    :return:
    '''
    # 避免Max retries exceeded with url，增加重试
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    url = 'https://jenkins.wywk.cn/job/' + job_name + '/api/json?pretty=true'

    # 发送 POST 请求，并在请求中包含 Cookie 和其他头信息
    # 还是会出现Max retries exceeded with url，暂时sleep 3s
    time.sleep(3)
    response = session.get(url, cookies=cookies)
    json_str = json.loads(response.text)
    lastbuildnum = json_str['builds'][0]['number']
    return lastbuildnum


if __name__ == '__main__':
    while True:
        logging.info('selenium登录，获取cookie')
        jenkins_cookies = get_cookies()
        with open('jenkins_jobconfig.csv', 'r') as file:
            reader = csv.reader(file)
            rows = list(reader)
            for i in range(len(rows)):
                job_name = rows[i][0]
                logging.info('处理第' + str(i) + '行数据。项目名称' + job_name)
                lastbuildnum = get_lastbuildnum(job_name, jenkins_cookies)
                logging.info('更新项目名称' + job_name + '最后一次构建编号' + str(lastbuildnum))
                rows[i][1] = lastbuildnum
                logging.info('输出更新后的项目名称和最后一次构建编号' + str(rows))

        # 更新后的job_name和lastbuildnum写入csv
        with open('jenkins_jobconfig.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)
            logging.info('完成更新并写入csv成功')

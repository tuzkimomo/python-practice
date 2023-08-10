#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author   : johnnyliu
# @Time     : 2023/7/11
# @Project  : test_tools

import threading
import time
import csv
import json
import requests
import logging
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置日志记录
# create logger obj
logger = logging.getLogger()

# set log level
logger.setLevel(logging.INFO)

# file handler
handler = logging.FileHandler('jenkins_automation.log', mode='w', encoding='utf-8')
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

    # jenkins用户名密码
    username_input.send_keys("")
    password_input.send_keys("")
    login_button.click()

    # 获取登录后的 cookie 信息
    cookies = driver.get_cookies()
    jenkins_token = {}
    jenkins_token.update(cookies[1])
    logging.info('成功获取cookies' + str(jenkins_token))
    return jenkins_token

def get_buildstates(cookies, job_name, last_buildnum):
    '''
    获取构建状态
    :param job_name:
    :param last_buildnum:
    :return:
    '''

    # 避免Max retries exceeded with url，增加重试
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    url = 'https://jenkins.wywk.cn/job/' + job_name + '/' + last_buildnum + '/wfapi/nextPendingInputAction'

    # 发送 POST 请求，并在请求中包含 Cookie 和其他头信息
    # 还是会出现Max retries exceeded with url，暂时sleep 3s
    time.sleep(3)
    response = session.get(url, cookies=cookies)
    logging.info('接口' + url + '返回内容' + response.text)
    json_str = json.loads(response.text)
    if response.text != 'null':
        if "请确认是否发布至test环境..." in json_str['message']:
            return 0
        elif "请确认是否发布至uat环境..." in json_str['message']:
            return 1
        else:
            pass
    elif response.text == 'null':
        pass
    else:
        pass

def jenkins_click(env):
    '''
    自动完成jenkins审批
    :param env:
    :return:
    '''
    if env == 0:
        # test环境
        box_xpath = '//*[@id="pipeline-box"]/div/div/table/tbody[2]/tr[1]/td[6]/div/div/div[1]/span'
    if env == 1:
        # uat环境
        box_xpath = '//*[@id="pipeline-box"]/div/div/table/tbody[2]/tr[1]/td[7]/div/div/div[1]/span'

    # 配置无头浏览器选项
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 启用无头模式
    chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速
    chrome_options.add_argument("--no-sandbox")  # 避免沙箱限制
    driver = webdriver.Chrome(options=chrome_options)

    # Todo 优化省掉登录过程

    # 打开登录页面
    driver.get("https://jenkins.wywk.cn")

    # 执行登录操作
    username_input = driver.find_element(By.ID, 'username')
    password_input = driver.find_element(By.ID, 'password')
    login_button = driver.find_element(By.ID, 'login-submit')

    # jenkins用户名密码
    username_input.send_keys("113075")
    password_input.send_keys("TLL2021c")
    login_button.click()
    logging.info('jenkins_click完成登录')
    url = 'https://jenkins.wywk.cn/job/' + job_name
    driver.get(url)
    logging.info('jenkins_click打开jenkins')
    time.sleep(2)
    element = driver.find_element(By.XPATH,box_xpath)
    # 鼠标悬停在元素上
    actions = ActionChains(driver)
    actions.move_to_element(element).perform()
    logging.info('jenkins_click鼠标悬停在元素上')
    time.sleep(2)
    deploy_button = driver.find_element(By.XPATH,
                                        '//button[@class="btn btn-primary btn-sm proceed-button" and text()="确认发布!"]')
    deploy_button.click()
    logging.info('jenkins_click点击确认发布成功')
    # 关闭浏览器
    driver.quit()


if __name__ == '__main__':
    while True:
        logging.info('selenium登录，获取cookie')
        jenkins_cookies = get_cookies()
        with open('jenkins_jobconfig.csv', 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                job_name = row[0]
                last_buildnum = row[1]
                logging.info ('读取csv中的项目：' + job_name + '最后一次构建：' + str(last_buildnum))
                # 调用nextPendingInputAction接口的cookie需要重新定义...
                api_cookies = {}
                api_cookies.update({jenkins_cookies['name']: jenkins_cookies['value']})
                print (api_cookies)
                # 判断是否需要审批
                needclick = get_buildstates(api_cookies, job_name, last_buildnum)
                logging.info('判断是否需要审批结果是：' + str(needclick) + '    p.s. 0:test环境审批；1:uat环境需要时审批。其他环境或没有审批直接pass')
                if needclick in (0,1):
                    jenkins_click(needclick)
                    logging.info('项目' + job_name + '已经自动完成审批')
                else:
                    logging.info('项目' + job_name + '没有需要审批的build，pass')
                    pass

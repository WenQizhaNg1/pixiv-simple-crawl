import datetime
import json
import os.path
import random
import time

import cloudscraper
from fake_useragent import UserAgent
import pymysql

headers = {
    'authority': 'www.pixiv.net',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
    'cache-control': 'max-age=0',
    'referer': 'https://www.pixiv.net/ranking.php?mode=daily_r18&content=illust',
    'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    # 使用随机UserAgent
    'user-agent': UserAgent(cache_path=r"output.json").random
}


# 连接到数据库
def link_to_mysql(hosts: str, user: str, password: str, db: str, port: int = 3306):
    conn = pymysql.connect(host=hosts, user=user, password=password, db=db, port=port,charset='utf8mb4')
    return conn

#  TODO 获取pixiv cookie
def get_pixiv_cookie(username:str,password:str,proxy: str = 'localhost',port: int = 10809) -> dict:
    
    proxies = {
        'http': proxy + ':' + str(port),
        'https': proxy + ':' + str(port) 
        }
    
    # 构建params
    params = {
        'content-type': 'application/x-www-form-urlencoded',
        'referer': 'https://accounts.pixiv.net/login?return_to=https://www.pixiv.net/&lang=zh&source=pc&view_type=page',
        'sec-ch-ua': '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'user-agent': UserAgent(cache_path=r"output.json").random,
        'lang': 'zh'
    }
    
    # 构建登录表单()
    data = {
        'login_id': username,
        'password': password,
        'source': 'pc',
        'app_ios': '0',
        'return_to': 'https://www.pixiv.net/',
        'recaptcha_enterprise_score_token':'',
        'tt': ''
    }
    
    # 获取pixiv cookie
    url = 'https://accounts.pixiv.net/login?lang=zh&source=pc&view_type=page&ref=wwwtop_accounts_index'
    scraper = cloudscraper.create_scraper()
    scraper.get(url,proxies=proxies)
    return scraper.cookies.get_dict()

# fetch_daily_ranking_list 获取每日排行榜
def fetch_daily_ranking_list(s:cloudscraper,cookie: str, proxy: str = 'http://localhost', port: int = 10809) -> object:
    proxies = {
        'http': proxy + ':' + str(port),
        'https': proxy + ':' + str(port) 
        }
    pic_dict = []
    url = 'https://www.pixiv.net/ranking.php'
    params = {
        'mode': 'daily_r18',
        'p': '1',
        'format': 'json'
    }
    
    res = s.get(url,headers=headers,proxies=proxies,cookies=cookie,params=params)
    # 如果返回的状态码不是200，就抛出异常
    if res.status_code != 200:
        raise Exception('请求失败')
    # 读取json数组
    pic_dict = res.json()['contents']
    
    # 读取下一页
    params = {
        'mode': 'daily_r18',
        'p': '2',
        'format': 'json'
    }
    res = s.get(url,headers=headers,proxies=proxies,cookies=cookie,params=params)
    # 如果返回的状态码不是200，就抛出异常
    if res.status_code != 200:
        raise Exception('请求失败')
    # 读取json数组
    pic_dict += res.json()['contents']
    return pic_dict

# 对比数据库中的数据，返回数据库不存在的图片
def compare_with_mysql(conn: pymysql, pic_dict: list) -> list:
    # 获取数据库中的图片id
    cursor = conn.cursor()
    cursor.execute('select pixiv_id from setu_pic')
    pic_id = cursor.fetchall()
    # 关闭游标
    cursor.close()
    # 将数据库中的图片id转换为list
    pic_id = [i[0] for i in pic_id]
    # 对比数据库中的图片id和爬取的图片id
    new_pic = []
    for pic in pic_dict:
        if pic['illust_id'] not in pic_id:
            new_pic.append(pic)
    return new_pic

# 下载图片
def download_img(s:cloudscraper,daily_list: list,cookies:dict, proxy: str = 'http://localhost', port: int = 10809) -> None:
    proxies = {
        'http': proxy + ':' + str(port),
        'https': proxy + ':' + str(port) 
        }
        # 提取图片id列表
    id_list = [i['illust_id'] for i in daily_list]
    
    if len(id_list) == 0:
        print('没有新图片')
        return
    else:
        for id in id_list:
            url = 'https://www.pixiv.net/ajax/illust/' + str(id) + '/pages'
            res = s.get(url,headers=headers,proxies=proxies,cookies=cookies)
            if res.status_code == 200:
                single_image_list = res.json()['body']
                index = 1
                for single_image in single_image_list:
                    img_url = single_image['urls']['original']
                    print(img_url)
                    img = s.get(img_url,headers=headers,proxies=proxies,cookies=cookies)
                    if img.status_code == 200:
                        with open('img/daily-common/' + str(id) + '_' + str(index) + '.jpg','wb') as f:
                            f.write(img.content)
                            index  = index + 1
                            # 打印图片下载信息
                            print('图片下载成功，图片id为：' + str(id) + '，图片序号为：' + str(index))
                            # 随机休眠1-3秒
                            time.sleep(random.randint(1,3))
                    else:
                        print('图片下载失败，图片序号为：' + str(index))
                        # 随机休眠1-3秒
                        time.sleep(random.randint(1,3))
            else:
                print('图片下载失败，图片id为：' + str(id))
    return
    
# 将图片信息写入数据库
def write_to_mysql(conn: pymysql, daily_list: list) -> None:
    if len(daily_list) == 0:
        print('没有新图片')
        return
    # 获取数据库中的图片id
    cursor = conn.cursor()
    for pic in daily_list:
        # 构建sql语句
        sql = 'insert into setu_pic(pixiv_id,author_id,pic_path,rating_count,view_count) values(%s,%s,%s,%s,%s)'
        # 构建参数
        params = (pic['illust_id'],pic['user_id'],'daily-common/',pic['rating_count'],pic['view_count'])
        # 执行sql语句
        cursor.execute(sql,params)
        conn.commit()
    cursor.close()
    # 关闭连接
    conn.close()
    return

if __name__ == '__main__':
    # 由键盘输入cookie
    cookie = "first_visit_datetime_pc=2023-01-29+19:02:51; p_ab_id=3; p_ab_id_2=8; p_ab_d_id=962067425; yuid_b=JZRTIXQ; privacy_policy_notification=0; a_type=0; b_type=1; login_ever=yes; pt_60er4xix=uid=ow5LrhgGyJxFQ7HOMH8sTg&nid=1&vid=AqF0YnbxxJb9HCM3e3kElQ&vn=1&pvn=1&sact=1675010151730&to_flag=0&pl=X5HI-3shhhNWgXmBfR1aMQ*pt*1675008864517; first_visit_datetime=2023-01-30+02:41:00; privacy_policy_agreement=5; device_token=0664d4fd900dd63baccb336478a6c33e; c_type=25; QSI_S_ZN_5hF4My7Ad6VNNAi=v:0:0; webp_available=1; PHPSESSID=34452338_jGgNQguo5Zi53Ohyd1CkO7BLFxy6UGHy; tag_view_ranking=0xsDLqCEW6~RTJMXD26Ak~KN7uxuR89w~PHsucBd84t~mZj99dTY1x~jH0uD88V6F~HbfqxxCMSP~7qtAnPrz1r~Gc2jc2ni0g~5oPIfUbtd6~4QveACRzn3~wlFTylDV0b~TcgCqYbydo~leIwAgTj8E~1SQy4SHbjC~k_6Tbz5i0P~faHcYIP1U0~3gc3uGrU1V~_EOd7bsGyl~Lt-oEicbBr~5U2rd7nRim~BSlt10mdnm~ZxAyxs0UWi~FO5UFnietZ~TjzQohypbT~nQRrj5c6w_~mFuvKdN_Mu~PvCsalAgmW~yCCrC4yzT3~6GYRfMzuPl~_vCZ2RLsY2~IpBVNx19zX~WjRN9ve4kb~_zgYWz7CbE~dbWQByG3DG~pinM0-ubtH~48UjH62K37~jpIZPQ502H~yREQ8PVGHN~AGF29gcJU3~bfM8xJ-4gy~_3oeEue7S7~lvb9wvOmP1~m2xpOASczc~gTlYXi_7gu~yPNaP3JSNF~y9_NhLUb-E~kGYw4gQ11Z~4ZEPYJhfGu~9V46Zz_N_N~rOnsP2Q5UN~jk9IzfjZ6n~FHZwS-O-_-~TbuodNZ_0Z~Ca0ugDlrQN~HY55MqmzzQ~wKl4cqK7Gl; __cf_bm=gI7ORvkDbR_lQTxKDSKKre2qf9CufKtIgKYSqN51ZZg-1681554953-0-AUs1G1U11n2vDUnQDYGa6pNMlikAq4VfvmzYtyDs7xOqjI88ZgOtxrqUXGXnf+b81ikaOeWsut7FNpyaGTuUW08UDNNvKPKyPrBDXpIXMKl7"
    cookies = {c.split('=')[0]: c.split('=')[1] for c in cookie.split('; ')}
    s = cloudscraper.create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    })
    # 获取每日排行榜
    daily_list = fetch_daily_ranking_list(s,cookies)
    # 对比数据库中的数据，返回数据库不存在的图片
    conn= link_to_mysql(hosts='localhost',user='root',password='qwer109109',db='pixivsetu')
    daily_list = compare_with_mysql(conn,daily_list)
    
    
    # # 开始下载图片
    download_img(s,daily_list,cookies)
    
    # 将图片信息写入数据库
    # TODO 对照下载失败照片
    write_to_mysql(conn,daily_list)
    
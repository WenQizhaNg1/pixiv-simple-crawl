import datetime
import os.path
import random
import time

import cloudscraper
from fake_useragent import UserAgent



headers = {
    'authority': 'www.pixiv.net',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
    'cache-control': 'max-age=0',
    # 从网页header中取cookie填入
    'cookie': '',
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

# 本地代理
proxies = {
    'http': 'socks5://127.0.0.1:10808',
    'https': 'socks5://127.0.0.1:10808',
}
# 进入日榜的query
params1 = {
    'mode': 'daily_r18',
    'p': '1',
    'format': 'json'
}

# 取图片的query
params2 = {
    'lang': 'zh',
    'version': ''
}

if __name__ == '__main__':
    # 反cf五秒盾初始化
    s = cloudscraper.create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    })

    # 时间格式初始化
    today = datetime.datetime.today()
    # 准备数据
    pid_dict = {}
    res = s.get('https://www.pixiv.net/ranking.php', headers=headers, params=params1, proxies=proxies)
    for content in res.json()['contents']:
        pid_dict[str(content['rank'])] = str(content['illust_id'])
    res2 = s.get('https://www.pixiv.net/ranking.php',proxies=proxies, headers=headers, params={
        'mode': 'daily_r18',
        'p': '2',
        'format': 'json'
    })
    for content in res2.json()['contents']:
        pid_dict[str(content['rank'])] = str(content['illust_id'])
    print(pid_dict['1'])


    if len(pid_dict) != 0:
        for rank, i in pid_dict.items():
            # 随机睡眠时间防止被封
            time.sleep(random.randint(2, 5))
            num = 1
            url = 'https://www.pixiv.net/ajax/illust/' + i + '/pages'
            r = s.get(url=url, headers=headers, params=params2, proxies=proxies)
            if r.status_code == 200:
                for urls in r.json()['body']:
                    imgurl = urls['urls']['original']
                    imgr = s.get(imgurl, headers=headers, proxies=proxies)
                    if imgr.status_code == 200:
                        path = 'img/daily-r18/' + str(today.date())
                        if os.path.exists(path) is False:
                            os.mkdir(path)
                        with open(path + '/' + rank + '_' + str(num) + '.jpg', 'wb') as f:
                            f.write(imgr.content)
                            print('PIXIV_ID:' + i + '号第' + str(num) + '张图片下载成功！' + '#rank' + rank)
                        num = num + 1
                    else:
                        print(i + '号第' + str(num) + '个图片下载失败！跳过。。。')
                        continue
            else:
                print(i + '号下载失败，跳过。。。')
                continue
        print("图片爬取结束。。。")
    else:
        print('图片不存在或者网络连接错误！')

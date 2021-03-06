#-*- coding: utf-8 -*-

import random
import time
import re
import config
import utils

from scrapy import Request
from validator import Validator


class JDSpider(Validator):
    name = 'jd'

    def __init__(self, name = None, **kwargs):
        super(JDSpider, self).__init__(name, **kwargs)

        self.urls = [
            'https://item.jd.com/11478178241.html',
            'https://item.jd.com/4142680.html',
            'https://item.jd.com/3133859.html',
            'https://item.jd.com/1594371260.html',
            'https://item.jd.com/1746190049.html',
            'https://item.jd.com/11349957411.html',
            'https://item.jd.com/1231104.html',
            'https://item.jd.com/11290644320.html',
            'http://item.jd.com/1786149566.html',
            'https://item.jd.com/10011422267.html',
        ]

        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Host': 'item.jd.com',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:52.0) Gecko/20100101 Firefox/52.0',
        }

        self.success_mark = 'comments'
        # self.is_record_web_page = True
        self.init()

    def start_requests(self):
        count = utils.get_table_length(self.sql, self.name)
        count_free = utils.get_table_length(self.sql, config.httpbin_table)

        ids = utils.get_table_ids(self.sql, self.name)
        ids_free = utils.get_table_ids(self.sql, config.httpbin_table)

        for i in range(0, count + count_free):
            table = self.name if (i < count) else config.httpbin_table
            id = ids[i] if i < count else ids_free[i - len(ids)]

            proxy = utils.get_proxy_info(self.sql, table, id)
            if proxy == None:
                continue

            url = random.choice(self.urls)
            pattern = re.compile('\d+', re.S)
            product_id = re.search(pattern, url).group()

            cur_time = time.time()
            yield Request(
                    url = url,
                    headers = self.headers,
                    meta = {
                        'cur_time': cur_time,
                        'download_timeout': self.timeout,
                        'proxy_info': proxy,
                        'table': table,
                        'id': proxy.get('id'),
                        'proxy': 'http://%s:%s' % (proxy.get('ip'), proxy.get('port')),
                        'vali_count': proxy.get('vali_count', 0),
                        'product_id': product_id,
                    },
                    dont_filter = True,
                    callback = self.get_comment_count,
                    errback = self.error_parse,
            )

    def get_comment_count(self, response):
        name = response.xpath('//img[@id="spec-img"]/@alt').extract_first()
        self.log('name:%s' % name)

        pattern = re.compile('commentVersion:\'(\d+)\'', re.S)
        comment_version = re.search(pattern, response.body).group(1)

        # sort type 5:推荐排序 6:时间排序
        url = 'https://club.jd.com/comment/productPageComments.action?callback=fetchJSON_comment98vv' \
              '{comment_version}&productId={product_id}&score=0&sortType={sort_type}&page=0&pageSize=10' \
              '&isShadowSku=0'. \
            format(product_id = response.meta.get('product_id'), comment_version = comment_version, sort_type = '6')

        cur_time = time.time()
        yield Request(
                url = url,
                headers = {
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Host': 'club.jd.com',
                    'Referer': 'https://item.jd.com/%s.html' % response.meta.get('product_id'),
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:52.0) Gecko/20100101 '
                                  'Firefox/52.0',
                },
                method = 'GET',
                meta = {
                    'proxy': response.meta.get('proxy'),
                    'cur_time': cur_time,
                    'download_timeout': self.timeout,
                    'proxy_info': response.meta.get('proxy_info'),
                    'table': response.meta.get('proxy_info'),
                    'id': response.meta.get('id'),
                    'vali_count': response.meta.get('vali_count', 0),
                },
                dont_filter = True,
                callback = self.success_parse,
                errback = self.error_parse
        )

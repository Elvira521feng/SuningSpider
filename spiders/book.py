# -*- coding: utf-8 -*-
import scrapy

"""
需求: 大分类:名称,URL; 小分类名称,URL; 图书的标题,图片,出版商,价格信息
步骤:
1. 创建爬虫项目
2. 创建爬虫
3. 完善爬虫
3.1 修改起始URL
3.2 提取大分类,小分类标题和URL, 根据小分类的URL构建列表页请求
3.3 解析列表页, 提取图书标题和封面图片的URL, 构建详情页的请求
3.4 解析详情页, 提取出版社, 价格(构建价格请求)
3.5 解析价格
3.6 实现列表页分页

"""

from copy import deepcopy
import re


class BookSpider(scrapy.Spider):
    name = 'book'
    allowed_domains = ['suning.com']

    # 3.1 修改起始URL
    start_urls = ['https://book.suning.com/']

    def parse(self, response):
        # 提取大分类和小分类信息
        # 获取包含大分类, 小分类的div列表
        divs = response.xpath('//div[@class="menu-item"]')
        # 获取子菜单div列表
        sub_divs = response.xpath('//div[contains(@class, "menu-sub")]')

        # 遍历divs, 获取大分类小分类信息
        for div in divs:
            item = {}
            item['b_category_name'] = div.xpath('./dl/dt/h3/a/text()').extract_first()
            item['b_category_url'] = div.xpath('./dl/dt/h3/a/@href').extract_first()

            # 获取包含小分类信息的a标签列表
            a_s = div.xpath('./dl/dd/a')
            # 如果a_s是一个空列表, 就要从子菜单中提取小分类信息
            if len(a_s) == 0:
                sub_div = sub_divs[divs.index(div)]
                a_s = sub_div.xpath('./div[1]/ul/li/a')
            # 遍历a_s, 提取小分类信息
            for a in a_s:
                item['s_category_name'] = a.xpath('./text()').extract_first()
                item['s_category_url'] = a.xpath('./@href').extract_first()
                # print(item)
                # 根据小分类的URL, 构建列表页请求
                # 当在循环外边创建的item对象(或字典),  传递给下一个解析函数时候, 需要进行一个深拷贝, 否则数据就会错乱
                yield scrapy.Request(item['s_category_url'], callback=self.parse_book_list, meta={'item': deepcopy(item)})

    def parse_book_list(self, response):
        # 3.3 解析列表页, 提取图书标题和封面图片的URL, 构建详情页的请求
        item = response.meta['item']

        # 获取包含图书信息的li标签列表
        lis = response.xpath('//*[@id="filter-results"]/ul/li')
        # 遍历lis, 获取图书名称和图片信息
        for li in lis:
            item['book_name'] = li.xpath('.//p[@class="sell-point"]/a/text()').extract_first()
            item['book_img'] =  'https:' + li.xpath('.//img/@src2').extract_first()
            # print(item)

            # 构建详情页的请求
            # 详情URL
            detail_url = 'https:' + li.xpath('.//p[@class="sell-point"]/a/@href').extract_first()
            # 构建详情页请求, 交给引擎
            yield scrapy.Request(detail_url, callback=self.parse_book_detail, meta={'item':  deepcopy(item)})

        # 实现翻页
        # 1. 获取下一页URL
        # 观察规律:
        #  第一页: https://list.suning.com/1-264003-0.html
        #  第2页: https://list.suning.com/1-264003-1.html
        #  第3页: https://list.suning.com/1-264003-2.html
        # print(response.url)
        # 把 https://list.suning.com/1-262518-0-0-0-0.html 改为 https://list.suning.com/1-262518-0.html
        current_url = re.sub('(-0)+', '-0', response.url)
        # print(current_url)
        # param.currentPage = "0";
        # param.pageNumbers = "61";
        current_page = int(re.findall('param.currentPage\s*=\s*"(\d+)"', response.text)[0])
        page_numbers = int(re.findall('param.pageNumbers\s*=\s*"(\d+)"', response.text)[0])
        # print(current_page)
        # print(page_numbers)
        # 计算下1页的页号
        next_page = current_page + 1
        # 如果有下一页, 就生成下一页的URL
        if next_page < page_numbers:
            # 构建下一页的URL
            # 生成替换的后缀
            subfix = '-{}.html'.format(next_page)
            # 举例: 1 -> -1.html
            next_url = re.sub('-\d+.html', subfix, current_url)
            print(next_url)
            # 构建下一页请求
            yield scrapy.Request(next_url, callback=self.parse_book_list, meta={'item': deepcopy(item)})

    def parse_book_detail(self, response):
        # 解析详情页
        # 3.4 解析详情页, 提取出版社, 价格(构建价格请求)
        item = response.meta['item']

        item['book_publisher'] = response.xpath('//*[@id="productName"]/a/text()').extract_first()

        # - 1. 准备价格URL模板
        price_url = 'https://pas.suning.com/nspcsale_0_000000000{}_000000000{}_{}_20_021_0210101.html'
        # - 2. 从详情页URL中提取数据
        datas =  re.findall('https://product.suning.com/(\d+)/(\d+).html', response.url)[0]
        # - 3. 生成完整价格URL
        price_url = price_url.format(datas[1], datas[1], datas[0])
        # print(item)
        # print(price_url)

        # 构建价格请求
        yield scrapy.Request(price_url, callback=self.parse_price, meta={'item': item})

    def parse_price(self, response):
        # 解析价格
        item = response.meta['item']
        # 思路: 如果有促销价格, 就使用促销价格, 如果没有就使用网络价格
        price = re.findall('"promotionPrice":\s*"(\d+.\d+)"', response.text)
        if len(price) == 0:
            price = re.findall('"netPrice":\s*"(\d+.\d+)"', response.text)

        # 获取价格信息
        item['price'] = price[0]
        # print(item)
        # 把数据交给引擎
        yield item

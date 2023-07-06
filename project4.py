from bs4 import BeautifulSoup
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import *

import pandas as pd
import numpy as np
from collections import defaultdict
import re
import os
import glob
import time
import pickle


class scraper(object):

    def __init__(self, homepage, login_page, filename):
        self.homepage = homepage
        self.login_page = login_page
        self.filename = filename
        self.driver = self.login()
        self.data_dir = os.getcwd() + '/data/'

    def load_file(self, filename):
        if os.path.isfile(filename):
            val = input('{0} exists. Run and overwrite the existed file(Y/N)? Your Answer: '.format(filename))
            if val.lower() == 'y':
                result = False
            else:
                print('Keep File')
                result = True
        else:
            result = False
        return result

    def login(self):
        Options().add_argument("--headless")
        driver = webdriver.Chrome('/usr/local/bin/chromedriver')
        driver.get(self.login_page)
        u = driver.find_element_by_name('email')
        u.send_keys('kim@fantasticimport.com')
        p = driver.find_element_by_name('pwd')
        p.send_keys('Aa875104')
        driver.find_element_by_name('btn_submit_login').click()
        return driver

    def gen_soup(self, url):
        page = requests.get(url, headers={"User-Agent": "XY"}).text
        soup = BeautifulSoup(page, 'html.parser')
        return soup

    def gen_urllist(self, return_ = True):
        soup = self.gen_soup(self.homepage)
        urls = [l for l in [s.a.get('href') for s in soup.find_all('li', class_ = 'dropdown-submenu')] if 'category' in l]
        url_list = [self.homepage + u for u in urls]
        with open('url_list.pkl', 'wb') as u_list:
            pickle.dump(url_list, u_list)
        if return_:
            return url_list

    def gen_categorylist(self, print_ = False, return_ = True):
        if self.load_file('url_list.pkl'):
            with open('url_list.pkl', 'rb') as file:
                url_list = pickle.load(file)
        else:
            url_list = self.gen_urllist()

        category_list = []
        for url in url_list:
            soup = self.gen_soup(url)
            for page in [l for l in [t.a.get('href') for t in soup.find_all('span', class_='panel-title')] if l]:
                pl = self.homepage + page
                soup = self.gen_soup(pl)

                sublist = soup.find_all('span', class_='panel-title')
                if not sublist:
                    if soup.find('p', text = "Sorry, we're all sold out!"):
                        pass
                    else:
                        category_list.append(pl)
                else:
                    for sub_p in [l for l in [t.a.get('href') for t in sublist] if l]:
                        sub_pl = self.homepage + sub_p
                        category_list.append(sub_pl)

        if print_:
            print('{0} categories found.'.format(len(category_list)))

        with open('category_list.pkl', 'wb') as cat_list:
            pickle.dump(category_list, cat_list)
        if return_:
            return category_list

    def gen_productlist(self, print_ = False, return_ = True):
        if self.load_file('category_list.pkl'):
            with open('category_list.pkl', 'rb') as file:
                category_list = pickle.load(file)
        else:
            category_list = self.gen_categorylist()

        product_list = []
        for cat in category_list:
            self.driver.get(cat)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            for prod in soup.find_all('div', class_='item-image'):
                link = self.homepage + prod.a.get('href')
                product_list.append(link)
            page_no = int(scraper.driver.find_element_by_class_name('total-page').text.split(' ')[-1])
            for i in range(page_no - 1):
                try:
                    scraper.driver.find_element_by_xpath("//img[@src='images/next-page.png']").click()
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    for prod in soup.find_all('div', class_='item-image'):
                        link = self.homepage + prod.a.get('href')
                        product_list.append(link)
                except NoSuchElementException:
                       break
        if print_:
            print('{0} products found.'.format(len(product_list)))
        with open('product_list.pkl', 'wb') as prod_list:
            pickle.dump(product_list, prod_list)
        if return_:
            return product_list

    def check_textExist(self, soup_output):
        if soup_output:
            return soup_output.text.strip()
        else:
            return np.nan

    def gen_productinfo(self):

        with open('product_list.pkl', 'rb') as file:
            product_list = pickle.load(file)

        product_info = defaultdict(list)

        for i, link in enumerate(product_list):
            print('Processing product {0}'.format(i))
            try:
                self.driver.get(link)
            except:
                self.driver.quit()
                self.login()
                continue

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            ## description
            product_info['Title'].append(self.check_textExist(soup.find('div', class_="product-name fontMontserrat")))
            ## product number
            product_info['Product Number'].append(self.check_textExist(soup.find('span', {'id':'pr_number'})))
            # inner price
            product_info['Inner Price'].append(self.check_textExist(soup.find('span', {'id':'pr_inner_price'})))
            ## case price
            product_info['Case Price'].append(self.check_textExist(soup.find('span', {'id':'pr_case_price'})))
            ## upc
            product_info['UPC'].append(self.check_textExist(soup.find('span', {'id':'pr_upc'})))
            ## availability
            product_info['Availability'].append(self.check_textExist(soup.find('span', {'id':'pr_availability'})))
            ## image link
            if soup.find('img', {'id':'product-image-file'}):
                product_info['Image Link'].append(soup.find('img', {'id':'product-image-file'}).get('src'))
            elif not soup.find('img', {'id':'product-image-file'}):
                product_info['Image Link'].append(np.nan)
            ## size
            if soup.find('span', text = 'SIZE:'):
                product_info['Size'].append(soup.find('span', text = 'SIZE:').next_sibling.strip())
            elif not soup.find('span', text = 'SIZE:'):
                product_info['Size'].append(np.nan)
            ## packaging
            if soup.find('span', text = 'PACKAGING:'):
                product_info['Packaging'].append(soup.find('span', text = 'PACKAGING:').next_sibling.strip())
            elif not soup.find('span', text = 'PACKAGING:'):
                product_info['Packaging'].append(np.nan)
            ## description
            if soup.find('div', class_ = 'description-text').find_all('p'):
                product_info['Description'].append(' '.join([p.text.strip() for p in soup.find('div', class_ = 'description-text').find_all('p')]).strip())
            elif not soup.find('div', class_ = 'description-text').find_all('p'):
                product_info['Description'].append(np.nan)
            ## features
            if soup.find('div', class_ = 'description-text').find('ol'):
                product_info['Features'].append(str([b.text for b in soup.find('div', class_ = 'description-text').find('ol').find_all('li')]))
            elif not soup.find('div', class_ = 'description-text').find('ol'):
                product_info['Features'].append(np.nan)

        return product_info

    def save_productInfo(self):
        product_info = self.gen_productinfo()
        with open('product_info.pkl', 'wb') as prod_info:
            pickle.dump(product_info, prod_info)

    def gen_df(self):
        file = self.data_dir + self.filename
        with open('product_info.pkl', 'rb') as prod_info:
            product_info = pickle.dump(prod_info)
        df = pd.DataFrame(product_info)
        return df

    def df2csv(self):
        file = self.data_dir + self.filename
        if os.path.isfile(file):
            val = input('File exists. Run and overwrite the existed file(Y/N)? Your Answer: ')
            if val.lower() == 'y':
                df = self.gen_df()
                df.to_csv(self.data_dir + self.filename, index=False)
            else:
                print('Keep File')
        else:
            df = self.gen_df()
            df.to_csv(self.data_dir + self.filename, index=False)

    def load_csv(self, file_name):
        file = self.data_dir + file_name
        if os.path.isfile(file):
            df = pd.read_csv(file)
            return df
        else:
            print('File Does Not Exist!')


if __name__ == '__main__':
    homepage = 'https://www.portofinointl.com/'
    login_link = 'https://www.portofinointl.com/signup.php'
    filename = 'portofinointl.csv'

    scraper = scraper(homepage, login_link, filename)
    scraper.save_productInfo()

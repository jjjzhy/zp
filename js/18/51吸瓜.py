# -*- coding: utf-8 -*-
# by @嗷呜
import json
import random
import re
import sys
import threading
import time
from base64 import b64decode, b64encode
from urllib.parse import urlparse

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend)
        except:
            self.proxies = {}  # Disable proxies for testing if needed
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua-platform': '"macOS"',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="134", "Google Chrome";v="134"',
            'DNT': '1',
            'sec-ch-ua-mobile': '?0',
            'Origin': '',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.host = self.host_late(self.gethosts())
        self.headers.update({'Origin': self.host, 'Referer': f"{self.host}/"})
        self.getcnh()

    def log(self, message):
        print(f"[Spider] {message}")

    def fetch_with_retry(self, url, retries=3, delay=1):
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=10)
                response.raise_for_status()
                return response
            except Exception as e:
                self.log(f"Request failed for {url}: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(delay)
        return None

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        response = self.fetch_with_retry(self.host)
        if not response:
            self.log("Failed to fetch home content")
            return {'class': [], 'list': []}
        data = self.getpq(response.text)
        result = {}
        classes = []
        for k in data('.category-list ul li').items():
            classes.append({
                'type_name': k('a').text(),
                'type_id': k('a').attr('href')
            })
        result['class'] = classes
        result['list'] = self.getlist(data('#index article a'))
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        if '@folder' in tid:
            id = tid.replace('@folder', '')
            videos = self.getfod(id)
        else:
            url = f"{self.host}{tid}{pg}"
            response = self.fetch_with_retry(url)
            if not response:
                self.log(f"Failed to fetch category content: {url}")
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 999999}
            data = self.getpq(response.text)
            videos = self.getlist(data('#archive article a'), tid)
        result = {
            'list': videos,
            'page': pg,
            'pagecount': 1 if '@folder' in tid else 99999,
            'limit': 90,
            'total': 999999
        }
        return result

    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}"
        response = self.fetch_with_retry(url)
        if not response:
            self.log(f"Failed to fetch detail content: {url}")
            return {'list': [{'vod_play_from': '51吸瓜', 'vod_play_url': f"Failed to load content${url}"}]}
        data = self.getpq(response.text)
        vod = {'vod_play_from': '51吸瓜'}

        # Extract content/tags
        try:
            clist = []
            if data('.tags .keywords a'):
                for k in data('.tags .keywords a').items():
                    title = k.text()
                    href = k.attr('href')
                    clist.append('[a=cr:' + json.dumps({'id': href, 'name': title}) + '/]' + title + '[/a]')
            vod['vod_content'] = ' '.join(clist) or data('.post-title').text() or "No content available"
        except Exception as e:
            self.log(f"Error extracting tags: {str(e)}")
            vod['vod_content'] = data('.post-title').text() or "No content available"

        # Extract video URLs
        try:
            plist = []
            if data('.dplayer'):
                for c, k in enumerate(data('.dplayer').items(), start=1):
                    config = json.loads(k.attr('data-config') or '{}')
                    video_url = config.get('video', {}).get('url', '')
                    if video_url:
                        plist.append(f"视频{c}${video_url}")
                    else:
                        self.log(f"No video URL in config for player {c}")
            # Fallback: Check for video elements
            if not plist and data('video source'):
                for c, k in enumerate(data('video source').items(), start=1):
                    video_url = k.attr('src')
                    if video_url:
                        plist.append(f"视频{c}${video_url}")
            vod['vod_play_url'] = '#'.join(plist) if plist else f"No video available${url}"
        except Exception as e:
            self.log(f"Error extracting video URLs: {str(e)}")
            vod['vod_play_url'] = f"Error retrieving video${url}"

        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/search/{key}/{pg}"
        response = self.fetch_with_retry(url)
        if not response:
            self.log(f"Failed to fetch search content: {url}")
            return {'list': [], 'page': pg}
        data = self.getpq(response.text)
        return {'list': self.getlist(data('#archive article a')), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        parse = 1
        try:
            if '.m3u8' in id:
                parse = 0
                id = self.proxy(id, type='m3u8')
            elif '.ts' in id:
                id = self.proxy(id, type='ts')
            else:
                self.log(f"Unknown video format for URL: {id}")
        except Exception as e:
            self.log(f"playerContent error: {str(e)}")
        return {'parse': parse, 'url': id, 'header': self.headers}

    def localProxy(self, param):
        try:
            if param.get('type') == 'img':
                res = requests.get(param['url'], headers=self.headers, proxies=self.proxies, timeout=10)
                res.raise_for_status()
                return [200, res.headers.get('Content-Type'), self.aesimg(res.content)]
            elif param.get('type') == 'm3u8':
                return self.m3Proxy(param['url'])
            else:
                return self.tsProxy(param['url'])
        except Exception as e:
            self.log(f"localProxy error: {str(e)}")
            return [500, "text/plain", f"Proxy error: {str(e)}"]

    def proxy(self, data, type='m3u8'):
        if data and self.proxies:
            return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        return data

    def decrypt_key(self, encrypted_data):
        try:
            key = b'f5d965df75336270'
            iv = b'97b60394abc2fbe1'
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(encrypted_data), AES.block_size)
            return decrypted
        except Exception as e:
            self.log(f"Key decryption error: {str(e)}")
            return None

    def m3Proxy(self, url):
        try:
            url = self.d64(url)
            headers = self.headers.copy()
            ydata = requests.get(url, headers=headers, proxies=self.proxies, allow_redirects=True, timeout=10)
            ydata.raise_for_status()
            data = ydata.text

            if ydata.url != url:
                url = ydata.url
            lines = data.strip().split('\n')
            last_r = url[:url.rfind('/')]
            parsed_url = urlparse(url)
            durl = parsed_url.scheme + "://" + parsed_url.netloc
            iskey = True

            for index, string in enumerate(lines):
                if iskey and 'URI' in string:
                    pattern = r'URI="([^"]*)"'
                    match = re.search(pattern, string)
                    if match:
                        key_url = match.group(1)
                        if not key_url.startswith('http'):
                            key_url = (last_r if key_url.count('/') < 2 else durl) + ('' if key_url.startswith('/') else '/') + key_url
                        key_response = requests.get(key_url, headers=headers, proxies=self.proxies, timeout=10)
                        key_data = self.decrypt_key(key_response.content)
                        if key_data:
                            key_b64 = b64encode(key_data).decode('utf-8')
                            lines[index] = re.sub(pattern, f'URI="data:application/octet-stream;base64,{key_b64}"', string)
                        else:
                            lines[index] = re.sub(pattern, f'URI="{self.proxy(key_url, "mkey")}"', string)
                        iskey = False
                        continue
                if '#EXT' not in string and string.strip():
                    if not string.startswith('http'):
                        domain = last_r if string.count('/') < 2 else durl
                        string = domain + ('' if string.startswith('/') else '/') + string
                    lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
            data = '\n'.join(lines)
            return [200, "application/vnd.apple.mpegurl", data]
        except Exception as e:
            self.log(f"m3Proxy error: {str(e)}")
            return [500, "text/plain", f"Error processing m3u8: {str(e)}"]

    def tsProxy(self, url):
        try:
            url = self.d64(url)
            data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True, timeout=10)
            data.raise_for_status()
            return [200, data.headers['Content-Type'], data.content]
        except Exception as e:
            self.log(f"tsProxy error: {str(e)}")
            return [500, "text/plain", f"Error processing ts: {str(e)}"]

    def e64(self, text):
        try:
            if isinstance(text, str):
                text_bytes = text.encode('utf-8')
            else:
                text_bytes = text
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            self.log(f"Base64 encoding error: {str(e)}")
            return ""

    def d64(self, encoded_text):
        try:
            if isinstance(encoded_text, str):
                encoded_bytes = encoded_text.encode('utf-8')
            else:
                encoded_bytes = encoded_text
            decoded_bytes = b64decode(encoded_bytes, validate=True)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            self.log(f"Base64 decoding error: {str(e)}")
            return ""

    def gethosts(self):
        url = 'https://51cg.fun'
        curl = self.getCache('host_51cn')
        if curl:
            try:
                response = self.fetch_with_retry(curl)
                if response:
                    data = self.getpq(response.text)('a').attr('href')
                    if data:
                        parsed_url = urlparse(data)
                        url = parsed_url.scheme + "://" + parsed_url.netloc
            except Exception as e:
                self.log(f"Error checking cached host: {str(e)}")
        try:
            response = self.fetch_with_retry(url)
            if not response:
                raise Exception("Failed to fetch hosts")
            html = self.getpq(response.text)
            html_pattern = r"Base64\.decode\('([^']+)'\)"
            html_match = re.search(html_pattern, html('script').eq(-1).text(), re.DOTALL)
            if not html_match:
                raise Exception("未找到html")
            html_content = b64decode(html_match.group(1)).decode()
            html = self.getpq(html_content)('script').eq(-4).text()
            return self.hstr(html)
        except Exception as e:
            self.log(f"获取: {str(e)}")
            return []

    def getcnh(self):
        response = self.fetch_with_retry(f"{self.host}/ybml.html")
        if not response:
            self.log("Failed to fetch ybml.html")
            return
        data = self.getpq(response.text)
        url = data('.post-content[itemprop="articleBody"] blockquote p').eq(0)('a').attr('href')
        if url:
            parsed_url = urlparse(url)
            host = parsed_url.scheme + "://" + parsed_url.netloc
            self.setCache('host_51cn', host)

    def hstr(self, html):
        pattern = r"(backupLine\s*=\s*\[\])\s+(words\s*=)"
        replacement = r"\1, \2"
        html = re.sub(pattern, replacement, html)
        data = f"""
        var Vx = {{
            range: function(start, end) {{
                const result = [];
                for (let i = start; i < end; i++) {{
                    result.push(i);
                }}
                return result;
            }},

            map: function(array, callback) {{
                const result = [];
                for (let i = 0; i < array.length; i++) {{
                    result.push(callback(array[i], i, array));
                }}
                return result;
            }}
        }};

        Array.prototype.random = function() {{
            return this[Math.floor(Math.random() * this.length)];
        }};

        var location = {{
            protocol: "https:"
        }};

        function executeAndGetResults() {{
            var allLines = lineAry.concat(backupLine);
            var resultStr = JSON.stringify(allLines);
            return resultStr;
        }};
        {html}
        executeAndGetResults();
        """
        return self.p_qjs(data)

    def p_qjs(self, js_code):
        try:
            from com.whl.quickjs.wrapper import QuickJSContext
            ctx = QuickJSContext.create()
            result_json = ctx.evaluate(js_code)
            ctx.destroy()
            return json.loads(result_json)
        except Exception as e:
            self.log(f"执行失败: {e}")
            return []

    def host_late(self, url_list):
        if isinstance(url_list, str):
            urls = [u.strip() for u in url_list.split(',')]
        else:
            urls = url_list

        if len(urls) <= 1:
            return urls[0] if urls else ''

        results = {}
        threads = []

        def test_host(url):
            try:
                start_time = time.time()
                response = requests.head(url, headers=self.headers, proxies=self.proxies, timeout=1.0, allow_redirects=False)
                delay = (time.time() - start_time) * 1000
                results[url] = delay
            except Exception:
                results[url] = float('inf')

        for url in urls:
            t = threading.Thread(target=test_host, args=(url,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return min(results.items(), key=lambda x: x[1])[0]

    def getlist(self, data, tid=''):
        videos = []
        l = '/mrdg' in tid
        for k in data.items():
            a = k.attr('href')
            b = k('h2').text()
            c = k('span[itemprop="datePublished"]').text()
            if a and b and c:
                videos.append({
                    'vod_id': f"{a}{'@folder' if l else ''}",
                    'vod_name': b.replace('\n', ' '),
                    'vod_pic': self.getimg(k('script').text()),
                    'vod_remarks': c,
                    'vod_tag': 'folder' if l else '',
                    'style': {"type": "rect", "ratio": 1.33}
                })
        return videos

    def getfod(self, id):
        url = f"{self.host}{id}"
        response = self.fetch_with_retry(url)
        if not response:
            self.log(f"Failed to fetch folder content: {url}")
            return []
        data = self.getpq(response.text)
        vdata = data('.post-content[itemprop="articleBody"]')
        r = ['.txt-apps', '.line', 'blockquote', '.tags', '.content-tabs']
        for i in r:
            vdata.remove(i)
        p = vdata('p')
        videos = []
        for i, x in enumerate(vdata('h2').items()):
            c = i * 2
            videos.append({
                'vod_id': p.eq(c)('a').attr('href'),
                'vod_name': p.eq(c).text(),
                'vod_pic': f"{self.getProxyUrl()}&url={p.eq(c+1)('img').attr('data-xkrkllgl')}&type=img",
                'vod_remarks': x.text()
            })
        return videos

    def getimg(self, text):
        match = re.search(r"loadBannerDirect\('([^']+)'\)", text)
        if match:
            url = match.group(1)
            return f"{self.getProxyUrl()}&url={url}&type=img"
        return ''

    def aesimg(self, word):
        try:
            key = b'f5d965df75336270'
            iv = b'97b60394abc2fbe1'
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(word), AES.block_size)
            return decrypted
        except Exception as e:
            self.log(f"AES decryption error for image: {str(e)}")
            return word
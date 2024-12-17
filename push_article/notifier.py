import hashlib
import json
import time
import jinja2
import requests
from push_article.httpclient import HTTPClient


class Notification(object):
    def __init__(self, company_id, app_id, app_secret):
        
        self.openapi_host = "https://openapi.wps.cn"
        self.notification_url = '/kopen/woa/v2/dev/app/messages'
        self.company_id = company_id
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = HTTPClient(timeout=5, retries=3, http_log_debug=True)

    def _sig(self, content_md5, url, date):
        sha1 = hashlib.sha1(self.app_secret.lower().encode('utf-8'))
        sha1.update(content_md5.encode('utf-8'))
        sha1.update(url.encode('utf-8'))
        sha1.update("application/json".encode('utf-8'))
        sha1.update(date.encode('utf-8'))
        return "WPS-3:%s:%s" % (self.app_id, sha1.hexdigest())

    def request(self, method, uri, body=None, headers=None):
        if method == "PUT" or method == "POST" or method == "DELETE":
            body = json.dumps(body)

        if method == "PUT" or method == "POST" or method == "DELETE":
            content_md5 = hashlib.md5(body.encode('utf-8')).hexdigest()
        else:
            content_md5 = hashlib.md5("".encode('utf-8')).hexdigest()

        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        # print date
        header = {"Content-type": "application/json",
                  'X-Auth': self._sig(content_md5, uri, date), 'Date': date,
                  'Content-Md5': content_md5}

        if headers is not None:
            header = {}
            for key, value in headers.items():
                header[key] = value

        url = "%s%s" % (self.openapi_host, uri)
        return self.client.request(url, method, data=body, headers=header, verify=False)

    def _token(self):
        url = "/oauthapi/v3/inner/company/token?app_id=%s" % self.app_id
        # print("[request] url:", url, "\n")

        _, rsp = self.request("GET", url)
        if rsp.__contains__('company_token'):
            return rsp["company_token"]
        else:
            print("no company-token found in response, authorized failed")
            exit(-1)

    def _upload_sign(self, image_size):
        url = '/kopen/woa/api/v2/developer/mime/upload' + '?company_token=%s' % self._token() + '&service_key=%s' % self.app_id + '&type=image' + '&size=212992'
        _, rsp = self.request("GET", url)
        # print(rsp)
        return rsp

    def upload_image(self, image_path='/root/banner.png', image_size=212045):
        with open(image_path, 'rb') as f:
            rsp = self._upload_sign(image_size)
            url = rsp['url']
            headers = rsp['headers']
            store_key = rsp['store_key']
            store_key_sha1 = rsp['store_key_sha1']
            payload = f.read()
            response = requests.request("PUT", url, headers=headers, data=payload)
            print(response.text)
            return store_key, store_key_sha1

    def send(self, company_uid, content=None, msg_type=1):
        data = {
            "to_users": {
                "company_id": self.company_id,
                "company_uids": [company_uid]
            },
            "msg_type": msg_type,
            "app_key": self.app_id,
            "content": content
        }
        url = self.notification_url + '?company_token=%s' % self._token()
        resp, body = self.request('POST', url, body=data)
        # print(body)

    def send_text(self, company_uid, text=None):
        msg = {
            "type": 1,
            "body": text,
        }
        self.send(company_uid, msg)

    def send_markdown(self, company_uid, docs):
        msg = {
            "type": 1,
            "style": "markdown",
            "body": gen_markdown(docs),
        }
        self.send(company_uid, msg)

    #
    def send_card(self, company_uid, docs, template='msg_card.json'):
        msg = gen_card(docs, template)
        self.send(company_uid, msg, 23)
        print("协作消息已成功推送！")


def gen_markdown(docs):
    title = "推荐文章"
    # 生成Markdown文本
    return (
            "# {}\n\n".format(title, ) +
            "\n### 点赞用户与文档\n\n" +
            "\n".join([
                " **{}**\n     - 作者：{}\n     - 热度：{}\n     - 链接：{}\n".format(
                    doc.doc_name, doc.doc_author, doc.hots, doc.doc_url
                )
                for doc in docs
            ])
    )


def gen_card(docs, template='msg_card.json'):
    kwargs = {}
    for index, doc in enumerate(docs):
        # kwargs['doc_name_%s' % (index + 1)] = doc.doc_name
        # kwargs['doc_url_%s' % (index + 1)] = doc.doc_url
        # kwargs['doc_author_%s' % (index + 1)] = doc.doc_author
        # kwargs['doc_hots_%s' % (index + 1)] = doc.hots
        # kwargs['doc_likes_%s' % (index + 1)] = doc.likes
        # kwargs['doc_views_%s' % (index + 1)] = doc.doc_views
        # kwargs['doc_view_person_count_%s' % (index + 1)] = doc.doc_view_person_count
        # kwargs['created_at_%s' % (index + 1)] = doc.created_at.date()
        # 使用 get 方法访问字典的值
        kwargs['doc_name_%s' % (index + 1)] = doc.get('title', 'Unknown Title')
        kwargs['doc_url_%s' % (index + 1)] = doc.get('link', 'Unknown URL')
        kwargs['doc_priority_%s' % (index + 1)] = doc.get('priority', 0)  # 默认优先级设为 0
        kwargs['doc_source_%s' % (index + 1)] = doc.get('source', 'Unknown Source')
        kwargs['doc_description_ai_summary_%s' % (index + 1)] = doc.get('description_ai_summary', 'No Summary')

    env = jinja2.Environment(loader=jinja2.FileSystemLoader('./'))
    temp = env.get_template(template)
    content = temp.render(**kwargs)
    return content

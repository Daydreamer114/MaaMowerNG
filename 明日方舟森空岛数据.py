import hashlib
import hmac
import json
import time
from urllib import parse

import requests

app_code = "4ca99fa6b56cc2ba"

# 签到url
sign_url = "https://zonai.skland.com/api/v1/game/attendance"
# 绑定的角色url
binding_url = "https://zonai.skland.com/api/v1/game/player/binding"
# 验证码url
login_code_url = "https://as.hypergryph.com/general/v1/send_phone_code"
# 验证码登录
token_phone_code_url = "https://as.hypergryph.com/user/auth/v2/token_by_phone_code"
# 密码登录
token_password_url = "https://as.hypergryph.com/user/auth/v1/token_by_phone_password"
# 使用token获得认证代码
grant_code_url = "https://as.hypergryph.com/user/oauth2/v2/grant"
# 使用认证代码获得cred
cred_code_url = "https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code"


class SKLand:
    def __init__(
        self,
    ):
        self.record_path = "./skland.csv"
        self.account_list = []

        self.account_list.append(
            {
                "account": "account",
                "isCheck": True,
                "password": "password",
            }
        )
        self.header = {
            "cred": "",
            "User-Agent": "Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0",
            "Accept-Encoding": "gzip",
            "Connection": "close",
        }
        self.header_login = {
            "User-Agent": "Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0",
            "Accept-Encoding": "gzip",
            "Connection": "close",
        }

        self.reward = []
        # 签名请求头一定要这个顺序，否则失败
        # timestamp是必填的,其它三个随便填,不要为none即可
        self.header_for_sign = {"platform": "", "timestamp": "", "dId": "", "vName": ""}
        self.sign_token = ""
        self.all_recorded = True

    def start(self):
        for item in self.account_list:
            self.all_recorded = False
            self.save_param(self.get_cred_by_token(self.log(item)))
            for i in self.get_binding_list():
                body = {"gameId": 1, "uid": i.get("uid")}
                ingame = f"https://zonai.skland.com/api/v1/game/player/info?uid={i.get('uid')}"
                resp = requests.get(
                    ingame,
                    headers=self.get_sign_header(ingame, "get", body, self.header),
                ).json()
                with open("森空岛数据.json", "w", encoding="utf-8") as 保存:
                    json.dump(resp, 保存, ensure_ascii=False, indent=4)
                print(resp["data"]["chars"])

    def save_param(self, cred_resp):
        self.header["cred"] = cred_resp["cred"]
        self.sign_token = cred_resp["token"]

    def log(self, account):
        r = requests.post(
            token_password_url,
            json={"phone": account["account"], "password": account["password"]},
            headers=self.header_login,
        ).json()
        if r.get("status") != 0:
            raise Exception(f'获得token失败：{r["msg"]}')
        return r["data"]["token"]

    def get_cred_by_token(self, token):
        return self.get_cred(self.get_grant_code(token))

    def get_grant_code(self, token):
        response = requests.post(
            grant_code_url,
            json={"appCode": app_code, "token": token, "type": 0},
            headers=self.header_login,
        )
        resp = response.json()
        if response.status_code != 200:
            raise Exception(f"获得认证代码失败：{resp}")
        if resp.get("status") != 0:
            raise Exception(f'获得认证代码失败：{resp["msg"]}')
        return resp["data"]["code"]

    def get_cred(self, grant):
        resp = requests.post(
            cred_code_url, json={"code": grant, "kind": 1}, headers=self.header_login
        ).json()
        if resp["code"] != 0:
            raise Exception(f'获得cred失败：{resp["message"]}')
        return resp["data"]

    def get_binding_list(self):
        v = []
        resp = requests.get(
            binding_url,
            headers=self.get_sign_header(binding_url, "get", None, self.header),
        ).json()

        if resp["code"] != 0:
            print(f"请求角色列表出现问题：{resp['message']}")
            if resp.get("message") == "用户未登录":
                print("用户登录可能失效了，请重新运行此程序！")
                return []
        for i in resp["data"]["list"]:
            if i.get("appCode") != "arknights":
                continue
            v.extend(i.get("bindingList"))
        return v

    def get_sign_header(self, url: str, method, body, old_header):
        h = json.loads(json.dumps(old_header))
        p = parse.urlparse(url)
        if method.lower() == "get":
            h["sign"], header_ca = self.generate_signature(
                self.sign_token, p.path, p.query
            )
        else:
            h["sign"], header_ca = self.generate_signature(
                self.sign_token, p.path, json.dumps(body)
            )
        for i in header_ca:
            h[i] = header_ca[i]
        return h

    def generate_signature(self, token: str, path, body_or_query):
        """
        获得签名头
        接口地址+方法为Get请求？用query否则用body+时间戳+ 请求头的四个重要参数（dId，platform，timestamp，vName）.toJSON()
        将此字符串做HMAC加密，算法为SHA-256，密钥token为请求cred接口会返回的一个token值
        再将加密后的字符串做MD5即得到sign
        :param token: 拿cred时候的token
        :param path: 请求路径（不包括网址）
        :param body_or_query: 如果是GET，则是它的query。POST则为它的body
        :return: 计算完毕的sign
        """
        # 总是说请勿修改设备时间，怕不是yj你的服务器有问题吧，所以这里特地-2

        t = str(int(time.time()) - 2)
        token = token.encode("utf-8")
        header_ca = json.loads(json.dumps(self.header_for_sign))
        header_ca["timestamp"] = t
        header_ca_str = json.dumps(header_ca, separators=(",", ":"))
        s = path + body_or_query + t + header_ca_str
        hex_s = hmac.new(token, s.encode("utf-8"), hashlib.sha256).hexdigest()
        md5 = (
            hashlib.md5(hex_s.encode("utf-8"))
            .hexdigest()
            .encode("utf-8")
            .decode("utf-8")
        )
        return md5, header_ca


a = SKLand()
a.start()

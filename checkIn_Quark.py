import os 
import re 
import sys 
import requests 

# 替代 notify 功能
def send(title, message):
    print(f"{title}: {message}")

# 提前定义全局变量，符合编码规范
cookie_quark = []

# 获取环境变量 
def get_env(): 
    """读取并解析COOKIE_QUARK环境变量，返回多账号Cookie列表"""
    cookie_list = []
    # 判断 COOKIE_QUARK是否存在于环境变量 
    if "COOKIE_QUARK" in os.environ: 
        # 读取系统变量，使用正则分割（支持\n 或 && 分隔多账号）
        cookie_raw = os.environ.get('COOKIE_QUARK').strip()
        cookie_list = [cookie.strip() for cookie in re.split(r'\n|&&', cookie_raw) if cookie.strip()]
    else: 
        # 标准日志输出 
        print('❌未添加COOKIE_QUARK变量') 
        send('夸克自动签到', '❌未添加COOKIE_QUARK变量') 
        # 脚本退出 
        sys.exit(0) 

    return cookie_list 

class Quark:
    '''
    Quark类封装了签到、领取签到奖励的方法
    '''
    def __init__(self, user_data):
        '''
        初始化方法
        :param user_data: 用户信息，用于后续的请求
        '''
        self.param = user_data
        # 配置请求头，模拟移动端请求，提高API兼容性
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/115.0 Firefox/115.0",
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive"
        }

    def convert_bytes(self, b):
        '''
        将字节转换为 MB GB TB
        :param b: 字节数
        :return: 返回 MB GB TB 格式化字符串
        '''
        if not isinstance(b, (int, float)) or b < 0:
            return "0.00 B"
        units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = 0
        while b >= 1024 and i < len(units) - 1:
            b /= 1024
            i += 1
        return f"{b:.2f} {units[i]}"

    def get_growth_info(self):
        '''
        获取用户当前的签到信息
        :return: 成功返回签到信息字典，失败返回False
        '''
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }
        try:
            # 添加超时设置（10秒），捕获网络请求异常
            response = requests.get(
                url=url,
                params=querystring,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()  # 捕获HTTP状态码错误（如403、500）
            return response.json().get("data", False)
        except Exception as e:
            print(f"❌ 获取成长信息失败：{str(e)}")
            return False

    def get_growth_sign(self):
        '''
        执行每日签到
        :return: 成功返回(True, 签到奖励字节数)，失败返回(False, 错误信息)
        '''
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }
        data = {"sign_cyclic": True}
        try:
            response = requests.post(
                url=url,
                json=data,
                params=querystring,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            resp_json = response.json()
            if resp_json.get("data"):
                return True, resp_json["data"]["sign_daily_reward"]
            else:
                return False, resp_json.get("message", "未知错误")
        except Exception as e:
            return False, f"网络请求异常：{str(e)}"

    def queryBalance(self):
        '''
        查询抽奖余额
        :return: 成功返回余额，失败返回错误信息
        '''
        url = "https://coral2.quark.cn/currency/v1/queryBalance"
        querystring = {
            "moduleCode": "1f3563d38896438db994f118d4ff53cb",
            "kps": self.param.get('kps'),
        }
        try:
            response = requests.get(
                url=url,
                params=querystring,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            resp_json = response.json()
            if resp_json.get("data"):
                return resp_json["data"]["balance"]
            else:
                return resp_json.get("msg", "未知错误")
        except Exception as e:
            return f"网络请求异常：{str(e)}"

    def do_sign(self):
        '''
        执行签到任务
        :return: 返回签到结果日志字符串
        '''
        log = ""
        # 每日领空间
        growth_info = self.get_growth_info()
        if growth_info:
            log += (
                f" {'88VIP' if growth_info.get('88VIP', False) else '普通用户'} {self.param.get('user', '未知用户')}\n"
                f"💾 网盘总容量：{self.convert_bytes(growth_info.get('total_capacity', 0))}，"
                f"签到累计容量：")
            cap_composition = growth_info.get('cap_composition', {})
            log += f"{self.convert_bytes(cap_composition.get('sign_reward', 0))}\n"
            
            cap_sign = growth_info.get("cap_sign", {})
            if cap_sign.get("sign_daily", False):
                log += (
                    f"✅ 签到日志: 今日已签到+{self.convert_bytes(cap_sign.get('sign_daily_reward', 0))}，"
                    f"连签进度({cap_sign.get('sign_progress', 0)}/{cap_sign.get('sign_target', 0)})\n"
                )
            else:
                sign, sign_return = self.get_growth_sign()
                if sign:
                    log += (
                        f"✅ 执行签到: 今日签到+{self.convert_bytes(sign_return)}，"
                        f"连签进度({cap_sign.get('sign_progress', 0) + 1}/{cap_sign.get('sign_target', 0)})\n"
                    )
                else:
                    log += f"❌ 签到异常: {sign_return}\n"
        else:
            log += f"❌ 签到异常: 获取成长信息失败\n"

        return log


def main():
    '''
    主函数：批量执行多账号签到
    :return: 返回汇总签到结果字符串
    '''
    msg = ""
    global cookie_quark
    cookie_quark = get_env()

    print(f"✅ 检测到共 {len(cookie_quark)} 个夸克账号\n")

    for i, cookie in enumerate(cookie_quark):
        # 解析Cookie为键值对字典，增加健壮性判断
        user_data = {}
        try:
            for a in cookie.replace(" ", "").split(';'):
                if not a.strip():
                    continue
                # 判断片段中是否包含=，避免索引错误
                if '=' not in a:
                    continue
                key = a[:a.index('=')]
                value = a[a.index('=') + 1:]
                user_data[key] = value
        except Exception as e:
            log = f"🙍🏻‍♂️ 第{i + 1}个账号 ❌ Cookie解析失败：{str(e)}\n"
            msg += log
            print(log)
            continue

        # 开始执行单个账号签到
        log_header = f"🙍🏻‍♂️ 第{i + 1}个账号\n"
        msg += log_header
        try:
            sign_log = Quark(user_data).do_sign()
            msg += sign_log + "\n"
        except Exception as e:
            error_log = f"❌ 账号签到执行失败：{str(e)}\n"
            msg += error_log + "\n"

    # 发送汇总结果
    try:
        send('夸克自动签到', msg)
    except Exception as err:
        print(f'%s\n❌ 结果输出失败，请查看运行日志！' % err)

    return msg[:-1] if msg else msg


if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    main()
    print("----------夸克网盘签到完毕----------")

# -*- coding:utf-8 -*-
__author__ = 'Qiushi Huang'

import optparse  # sys.argv的功能类似
# python ftp_client.py -h 192.168.22.33 -p 8091
# user:
# password
import socket
import json


class FTPClient(object):
    """ftp客户端"""
    MSG_SIZE = 1024   # 客户端收取消息最长1024

    def __init__(self):
        self.username = None   # 先占位，后期赋值
        parser = optparse.OptionParser()
        parser.add_option("-s", "--server", dest="server", help="ftp server ip_addr")
        parser.add_option("-P", "--port", type="int", dest="port", help="ftp server port")
        parser.add_option("-u", "--username", dest="username", help="username info")
        parser.add_option("-p", "--password", dest= "password", help= "password info")
        self.options, self.args = parser.parse_args()

        # print(self.options, self.args)
        # print(type(self.options), type(self.args))  # <class 'optparse.Values'> <class 'list'>
        """
        执行程序，提示信息
        # python3 ftp_client.py 1  324
        {'server': None, 'port': None, 'username': None, 'password': None} ['1', '324']
        # python3 -s 127.0.0.1 -P 3308 -u admin -p admin
        {'server': '127.0.0.1', 'port': 3308, 'username': 'admin', 'password': 'admin'} []
        """
        self.argv_verification()  # 调用参数检查
        self.make_connection()  # 创建链接

    def argv_verification(self):
        """检查参数合法性，必须有-s -p"""
        # dict.get(key, default=None)  # 返回字典中key对应的值，若key不存在字典中，则返回default的值（default默认为None）
        # self.option虽然打印出来的形式是字典，但实际是类
        # if not self.options.get('server') or not self.options.get('port'):
        if not self.options.server or not self.options.port:
            exit("Error: must supply server and port parameters")

    def make_connection(self):
        """创建socket链接"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.options.server, self.options.port))

    def get_response(self):
        """
        收到的每个消息都需要序列化
        获取服务器端返回
        :return:
        """
        data = self.sock.recv(self.MSG_SIZE)
        return json.loads(data.decode('utf-8'))

    def auth(self):
        """用户认证"""
        count = 0
        while count < 3:
            username = input("username: ").strip()
            if not username:continue
            password = input("passwrod: ").strip()
            cmd = {
                "action_type": "auth",
                "username": username,
                "password": password
            }
            self.sock.send(json.dumps(cmd).encode('utf-8'))
            # self.sock.recv(1024)
            response = self.get_response()  # 拿到返回数据
            print('response: ', response)
            """  后面的0是zfill的效果
            response:  "{"filesize": 1024, "status_code": 200, "status_msg": 
            "Passed authentication!", "fill": "000000...000"}"
            """
            if response.get('status_code') == 200:  # path auth
                self.username = username   # 给username赋值，方便后期使用
                return True
            else:
                print(response.get("status_msg"))
            count += 1

    def interactive(self):
        """处理与FTPserver的所有交互"""
        if self.auth():  # 代表验证成功
            """验证通过过，进行下一步交互"""
            while True:
                user_input = input("[%s]:>>" % self.username).strip()
                if not user_input:continue

                cmd_list = user_input.split()   # ['get', 'a.txt']
                if hasattr(self, "_%s" % cmd_list[0]):
                    func = getattr(self, "_%s" % cmd_list[0])
                    func(cmd_list[1:])  # 对列表切片，处理更多参数
                    # get fill --md5

    def parameter_check(self, args, min_args=None, max_args=None, exact_args=None):   # 不为None时则设置了值
        """解决命令参数合法性检查"""
        if min_args:   # 如果设置了最小参数数量
            if len(args) < min_args:
                print("must provide at least %s parameters but %s received" % (min_args, len(args)))
                return False
        if max_args:   # 如果设置了最大参数数量
            if len(args) > max_args:
                print("need at most %s parameters but %s received." % (max_args, len(args)))
                return False
        if exact_args:  # 如果设置了参数数量
            if len(args) != exact_args:
                print("need exactly %s parameters but %s received." % (exact_args, len(args)))
                return False
        return True  # 上述情况都没发生return True

    def send_msg(self, action_type, **kwargs):
        """打包消息发送到远程"""
        msg_data = {
            'action_type': action_type,
            'fill': ''
        }
        msg_data.update(kwargs)   # 字典update方法把两个字典合在一起

        bytes_msg = json.dumps(msg_data).encode()
        if self.MSG_SIZE > len(bytes_msg):  # 少于定长时，需要补位
            msg_data['fill'] = msg_data['fill'].zfill(self.MSG_SIZE - len(bytes_msg))
            bytes_msg = json.dumps(msg_data).encode()

        self.sock.send(bytes_msg)

    def _get(self, cmd_args):
        """
        从FTP服务端下载文件
        1.拿到文件名
        2.发送到远程
        3.等待服务器相应返回消息
            3.1 如果文件存在，同时发回文件大小
                3.1.1 循环接收
            3.2 文件如果不存在
                print status_msg
        :param cmd_args:
        :return:
        """
        if self.parameter_check(cmd_args, min_args=1):  # 参数检查,返回True则继续操作
            """
            [alex]>>:get
            must provide at least 1 parameters but 0 received
            [alex]:>>get 123 213
            [alex]:>>
            """
            filename = cmd_args[0]  # 文件名
            self.send_msg(action_type='get', filename=filename)   # 发送消息，操作命令和文件名
            response = self.get_response()   # 等待服务端返回消息
            if response.get('status_code') == 301:   # file exist, ready to receive
                file_size = response.get('file_size')
                # 打开文件，循环收
                received_size = 0
                f = open(filename, 'wb')
                while received_size < file_size:
                    if file_size - received_size < 8192:   # 最后一次可收取完文件内容
                        data = self.sock.recv(file_size - received_size)
                    else:  # 其他情况正常收
                        data = self.sock.recv(8192)
                    received_size += len(data)
                    f.write(data)
                    print(received_size, file_size)
                else:
                    print("----file [%s] recv done, received size [%s]----" % (filename, file_size))
                    f.close()
            else:
                print(response.get('status_msg'))
                """
                [alex]:>>get test.mp4
                File does not exist!
                """

    def _put(self):
        pass


if __name__ == '__main__':
    client = FTPClient()   # 实例化
    client.interactive()  # 用户交互

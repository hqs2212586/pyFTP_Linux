# -*- coding:utf-8 -*-
__author__ = 'Qiushi Huang'

import os
import socket
from conf import settings
import json
import hashlib
import configparser


class FTPServer(object):
    """处理与客户端所有的交互socket server"""
    STATUS_CODE= {   # 状态码，前后端对应
        200: "Passed authentication!",
        201: "Wrong username or password!",
        300: "File does not exist!",
        301: "File exist, and this msg include the file size!"
    }

    MSG_SIZE = 1024   # 消息最长1024，包头定长

    def __init__(self, management_instance):
        """构造函数初始化"""
        self.management_instance = management_instance
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((settings.HOST, settings.PORT))  # ('127.0.0.1', 9001)
        # socket设置为监听模式，监听backlog外来的连接请求
        self.sock.listen(settings.MAX_SOCKET_LISTEN)
        self.accounts = self.load_accounts()
        self.user_obj = None

    def run_forever(self):
        """启动socket server"""
        print('starting FTP server on %s:%s'.center(50, '-') % (settings.HOST, settings.PORT))
        while True:
            # accept返回一个客户机socket(带有客户端的地址信息)
            # conn, addr = self.sock.accept()
            self.request, self.addr = self.sock.accept()   # 赋值conn,addr为全局变量
            """
            conn: <socket.socket fd=4, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 8080), raddr=('127.0.0.1', 55925)>
            addr: ('127.0.0.1', 65197)
            """
            print('got a new connection from %s' % (self.addr,))  # 占位符和元组的应用
            # got a new connection from ('127.0.0.1', 65197)
            self.handle()

    def handle(self):
        """
        处理与用户的所有指令交互
        handle执行完一个链接结束，需要在run_forever开始下一个链接
        :return:
        """
        while True:
            raw_data = self.request.recv(self.MSG_SIZE)   # 接收数据
            print('----->', raw_data)

            if not raw_data:
                print('connection %s is lost....' % (self.addr, ))
                # 断开一个客户端链接时，清掉request, addr
                del self.request, self.addr
                break

            data = json.loads(raw_data.decode('utf-8'))   # data赋值非常频繁，因此不赋为全值
            action_type = data.get("action_type")
            if action_type:
                """如果有收到消息"""
                if hasattr(self, "_%s" % action_type):   # 利用反射
                    func = getattr(self, "_%s" % action_type)
                    func(data)
            else:
                """如果收到的是None或者是不合法的消息"""
                print("invalid command,")

    def load_accounts(self):
        """加载所有账户的信息"""
        config_obj = configparser.ConfigParser()
        config_obj.read(settings.ACCOUNT_FILE)

        print(config_obj.sections())   # ['alex', 'egon']
        return config_obj

    def authenticate(self, username, password):
        """用户认证方法"""
        # 登录计数由客户端完成，服务器只管处理认证
        if username in self.accounts:
            _password = self.accounts[username]['password']
            md5_obj = hashlib.md5()
            md5_obj.update(password.encode('utf-8'))  # 在hash之前必须encode
            md5_password = md5_obj.hexdigest()
            print('password:', _password, md5_password)
            if md5_password == _password:
                print("passed authentication")
                # 认证成功之后，把用户信息存在当前类里（创建user_obj）
                self.user_obj = self.accounts[username]   # 拿到所有信息
                # 保存用户家目录，将家目录属性保存在对象user_obj中
                self.user_obj['home'] = os.path.join(settings.USER_HOME_DIR, username)

                return True
            else:
                print("wrong username or password")
                return False
        else:
            print("wrong username pr password11223")
            return False

    def send_response(self, status_code, *args, **kwargs):
        """
        打包发送消息给客户端
        :param status_code:
        :param args:
        :param kwargs:{filename:ddd, filesize:222}
        :return:
        """
        data = kwargs
        data['status_code'] = status_code   # 消息码
        data['status_msg'] = self.STATUS_CODE[status_code]  # 消息内容
        data['fill'] = ''
        bytes_data = json.dumps(data).encode('utf-8')
        # 判断变成byte的数据长度
        if len(bytes_data) < self.MSG_SIZE:
            # zfill() 方法返回指定长度的字符串，原字符串右对齐，前面填充0。
            data['fill'] = data['fill'].zfill(self.MSG_SIZE - len(bytes_data))
            bytes_data = json.dumps(data).encode('utf-8')

        self.request.send(bytes_data)   # request = conn

    def _auth(self, data):   # 用下划线区分与客户端交互的指令
        """处理用户认证请求"""
        print("auth", data)
        # 调用用户认证
        if self.authenticate(data.get('username'), data.get('password')):
            # 认证成功，
            # 1、标准化返回信息内容，运用状态码
            # 2、json.dumps
            # 3、 encode
            self.send_response(status_code=200, filesize=1024)

        else:
            # 认证失败
            self.send_response(status_code=201)

    def _get(self, data):
        """
        客户端从服务器下载文件
        1、拿到文件名
        2、判断文件是否存在
            2.1、如果存在返回状态码和文件大小
                2.1.1 打开文件，发送数据
            2.2、如果不存在，返回状态码

        :param data:
        :return:
        """
        filename = data.get('filename')  # 拿到文件名，data在handle方法中
        full_path = os.path.join(self.user_obj['home'], filename)  # 家目录和文件名拼起来
        if os.path.isfile(full_path):  # 判断文件是否存在
            filesize = os.stat(full_path).st_size    # os.stat获取文件属性，st_size为文件大小
            self.send_response(301, file_size=filesize)   # 发送文件状态和文件大小
            print("ready to send file")

            # 发送文件
            f = open(full_path, 'rb')
            for line in f:
                self.request.send(line)
            else:
                print('file send done..', full_path)
            f.close()
        else:
            self.send_response(300)



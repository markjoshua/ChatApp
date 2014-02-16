# coding: utf-8
from asyncore import dispatcher
from asynchat import async_chat
import socket, asyncore

PORT = 5267
NAME = 'FISH'
USAGE = '''
	login name --登陆服务器
	logout     --登出
	say words  --发言
	look       --查看房间内的用户
	who        --查看登陆服务器的人
	========================================
	'''
# 结束会话
class EndSession(Exception):
	pass

class CommandHandler:
	'''
		类似cmd中命令处理简单程序
	'''
	def unknown(self,session, cmd):
		# 响应未知命令
		session.push('Unknown command %s \r\n' % cmd)
		session.push('Check the usage : \r\n %s' %USAGE)
	def handle(self, session, line):
		# 处理会话中接收到的行
		if not line.strip():
			return
		# 分离出命令和说的话
		parts = line.split(' ' ,1)
		cmd = parts[0]
		try:
			line = parts[1].strip()
		except IndexError:
			line = ''
		# 查找处理程序
		meth = getattr(self, 'do_' + cmd , None)
		try:
			# 命令可以调用
			meth(session, line)
		except TypeError:
			self.unknown(session, cmd)

class Room(CommandHandler):
	'''
		创建一个用户或者多用户的环境，负责命令处理，和广播
	'''
	def __init__(self, server):
		self.server = server
		self.sessions = []
	def add(self, session):
		# 一个用户进入
		self.sessions.append(session)
	def remove(self, session):
		# 一个会话离开房间
		self.sessions.remove(session)
	def broadcast(self, line):
		# 向房间的人广播
		for session in self.sessions:
			session.push(line)
	def do_logout(self, session, line):
		# 响应logout命令
		raise EndSession
class LoginRoom(Room):
	'''
		为连接到的用户做准备工作
	'''
	def add(self, session):
		Room.add(self, session)
		# 向客户端问候一下
		self.broadcast('Welcome to %s\r\n' %self.server.name)
		self.broadcast('Chcek the usage : \r\n %s' %USAGE)
	def unknown(self, session, cmd):
		# 未知命令的处理, 弹出一个警告
		session.push('Please log in\n use "login <nick> " \r\n')
	def do_login(self, session, line):
		name = line.strip()
		# 确定输入了nickname
		if not name:
			session.push('Please enter a name \r\n')
		elif name in self.server.users:
			session.push('Sorry, the name %s in in use' %name)
			session.push('\n Please input another one:\r\n')
		else:
			# 名字okay, 就保存到users中
			session.name = name
			session.enter(self.server.main_room)
class ChatRoom(Room):
	'''
		为多用户相互聊天准备房间
	'''
	def add(self, session):
		# 告诉所有人，有人进来了
		self.broadcast(session.name + 'has entered the room!\r\n')
		self.server.users[session.name] = session
		Room.add(self, session)
	def remove(self, session):
		# 告诉所有人，有人离开
		Room.remove(self, session)
		self.broadcast(session.name + 'has left the room!\r\n')
	def do_say(self, session, line):
		self.broadcast(session.name + ': ' + line + '\r\n')

	def do_look(self, session, line):
		# 查询谁在房间
		session.push('The followings are in the room : \r\n')
		for user in self.sessions:
			session.push(user.name + '\r\n')
		session.push('=' * 20 + '\r\n')
	def do_who(self, session, line):
		session.push('The followings are logged in:\r\n')
		for name in self.server.users:
			session.push(name + '\r\n')
		session.push('=' * 20 + '\r\n')

class LogoutRoom(Room):
	# 为单用户准备的简单房间，只用于将用户名重服务器移除
	def add(self, session):
		#　当会话进入要删除的lougoutroom
		try:
			del self.server.users[session.name]
		except KeyError:
			pass
class ChatSession(async_chat):
	'''
		会话，负责和用户通信
	'''
	def __init__(self, server, sock):
		async_chat.__init__(self, sock)
		self.server = server
		self.set_terminator('\r\n')
		self.data = []
		self.name = None
		# 所有的会话开始于单独的LoginRoom中
		self.enter(LoginRoom(server))
	def enter(self, room):
		# 重当前房间移除自身，并将自己添加到下一个房间
		try:
			cur = self.room
		except AttributeError:
			pass
		else:
			cur.remove(self)
		self.room = room
		room.add(self)
		
	def collect_incoming_data(self, data):
		self.data.append(data)
	def found_terminator(self):
		line = ''.join(self.data)
		self.data = []
		try:
			self.room.handle(self, line)
		except EndSession:
			self.handle_close()
	def handle_close(self):
		async_chat.handle_close(self)
		self.enter(LogoutRoom(self.server))
class ChatServer(dispatcher):
	'''
		只有一个房间的聊天服务器
	'''
	def __init__(self, port, name):
		dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind(('', port))
		self.listen(5)
		self.name = name
		self.users = {}
		self.main_room = ChatRoom(self)
	def handle_accept(self):
		conn, addr = self.accept()
		ChatSession(self, conn)
if __name__ == '__main__':
	s = ChatServer(PORT, NAME)
	try:
		asyncore.loop()
	except KeyboardInterrupt:
		print	

from asyncore import dispatcher
from asynchat import async_chat
import socket, asyncore

PORT = 5267
NAME = 'TestChat'

class ChatSession(async_chat):
	def __init__(self, server, sock):
		async_chat.__init__(self, sock)
		self.server = server
		self.set_termiator('\r\n')
		self.data = []
		self.push('Welcome to %s\r\n' %self.sever.name)
	def collect_incoming_data(self, data):
		self.data.append(data)
	def found_terminator(self):
		line = ''.join(self.data)
		self.data = []
		self.server.broadcast(line)
	def handle_close(self):
		async_chat.handle_close(self)
		self.server.disconnect(self)
class ChatServer(dispatcher):
	def __init__(self, port, name):
		dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind(('', port))
		self.listen(5)
		self.name = name
		self.sessions = []
	def disconnect(self, session):
		self.sessions.remove(session)
	def broadcast(self, line):
		for session in self.sessions:
			session.push(line + '\r\n')
	def handle_accept(self):
		conn, addr = self.accept()
		self.sessions.append(ChatSession(self, conn))
class CommandHandler:
	def unknown(self, session, cmd):
		session.push('Unknown command %s \r\n' %cmd)
	def handle(self, cmd):
		if not line.strip():
			return
		parts = line.split(' ', 1)
		cmd = parts[0]
		try:
			line = parts[1].strip()
		except IndexError:
			line = ''
		meth = getattr(self, 'do_' + cmd, None)
		try:
			meth(session, line)
		except TypeError:
			self.unknown(session, cmd)
class EndSession(Exception):
	pass
class Room(CommandHandler):
	def __init__(self, server):
		self.server = server
		self.sessions = []
	def add(self, session):
		self.sessions.append(session)
	def remove(self, session):
		self.sessions.remove(session)
	def broadcast(self, line):
		for session in self.sessions:
			session.push(line)

	def do_logout(self, session, line):
		raise EndSession
if __name__ == '__main__':
	s = ChatServer(PORT, NAME)
	asyncore.loop()

#!/usr/bin/env python3

import os,sys,mpv,locale

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

def sgn(n): return -1 if n<0 else 1 if n>0 else 0

class Tray(QSystemTrayIcon):
	scrolled = pyqtSignal(int)
	def event(self, e): # scrolling
		def sgn(n): return -1 if n<0 else 1 if n>0 else 0
		if type(e) == QWheelEvent:
			self.scrolled.emit(sgn(e.angleDelta().y()))
		return QSystemTrayIcon.event(self,e)
	
	clicked = pyqtSignal(object)
	def onActivated(self, reason):
		global window
		if reason == QSystemTrayIcon.Trigger:
			self.clicked.emit(self.geometry())
		elif reason == QSystemTrayIcon.Context:
			if hasattr(self,'tuner') and self.tuner.isVisible():
				self.tuner.hide()
			self.contextMenu().popup(self.geometry().topLeft())
		else:
			print('TrayIcon.onActivated(reason:{})'.format(type(reason)))
	
	def __init__(self):
		QSystemTrayIcon.__init__(self)
		
		self.activated.connect(self.onActivated)
		
		contextMenu=QMenu()
		a = QAction(QIcon.fromTheme('application-exit'),'Exit',self)
		a.triggered.connect(quit) ; contextMenu.addAction(a)
		self.setContextMenu(contextMenu)
		
		self.setIcon(QIcon.fromTheme('process-stop'))
		self.show()
		self.basePixmap = self.icon().pixmap(self.geometry().size())
	
	def setPixmap(self, pixmap):
		self.setIcon(QIcon(pixmap))

class Player(mpv.MPV,QObject):
	titleChanged = pyqtSignal(object)
	timeChanged = pyqtSignal(float)
	started = pyqtSignal()
	stopped = pyqtSignal()
	def __init__(self, uri):
		QObject.__init__(self)
		mpv.MPV.__init__(self) # <- maybe here too
		self.volume,self.playing = 0,True
		self.play(uri)
		self.observe_property('media-title', self.media_title)
		self.observe_property('time-pos', self.time_observer)
	def setVolume(self, volume):
		self.volume = volume
	def media_title(self, n,v):
		if type(v) is bytes: c = v.decode('UTF-8')
		if v: self.titleChanged.emit(v)
	def time_observer(self, _name, value):
		playing = value != None
		if self.playing != playing:
			if playing:
				self.started.emit()
			else:
				self.stopped.emit()
		else:
			self.timeChanged.emit(value)
		self.playing = playing

class Dial(QDial):
	adjustStep = 5
	changed = pyqtSignal()
	changed_getPixmap = pyqtSignal(object)
	def __init__(self, tray):
		self.tray = tray
		QDial.__init__(self)
		self.setRange(0,100)
		self.seekStepper = QTimer()
		self.seekStepper.setSingleShot(False)
		self.seekStepper.timeout.connect(self.seekVolStep)
	def setVolume(self, volume):
		self.setValue(volume)
		self.changed_getPixmap.emit(self.grab())
		self.changed.emit()
		return self.value()
	def adjust(self, direction):
		return self.setVolume(self.value()+self.adjustStep*direction)
	def sizeHint(self):
		return self.tray.geometry().size()
	def seekVol(self, seekVolGoal, interval=50,stepSize=1):
		self.stepSize = stepSize
		self.seekVolGoal = seekVolGoal
		self.seekStepper.start(interval)
	def fadeIn(self):
		self.seekVol(75)
	def seekVolStep(self):
		d = self.seekVolGoal-self.value()
		if abs(d)>self.stepSize:
			self.adjust(sgn(d))
		else:
			self.setVolume(self.seekVolGoal)
			self.seekStepper.stop()

def run(uri):
	app = QApplication(sys.argv)
	locale.setlocale(locale.LC_NUMERIC, 'C') # mpv needs this
	
	tray = Tray()
	
	dial = Dial(tray)
	dial.changed_getPixmap.connect(tray.setPixmap)
	tray.scrolled.connect(dial.adjust)
	
	player = Player(uri)
	dial.valueChanged.connect(player.setVolume)
	player.started.connect(dial.fadeIn)
	
	sys.exit(app.exec())
args = sys.argv[1:]
uri = args[0] if len(args)==1 else ' '.join(args) if len(args)>1 else None
if uri:
	run(uri)
else:
	print('specify filepath/url to play')

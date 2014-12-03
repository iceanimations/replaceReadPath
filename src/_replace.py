import os
import os.path as osp
from PyQt4.QtGui import QApplication, QMessageBox, QFileDialog
from PyQt4 import uic
import msgBox
import util
reload(util)
import nuke

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

Form, Base = uic.loadUiType(osp.join(uiPath, 'main.ui'))
class Window(Form, Base):
    def __init__(self, parent=QApplication.activeWindow()):
        super(Window, self).__init__(parent)
        self.setupUi(self)
        
        self.currentDirectory = ''
        
        self.replaceButton.clicked.connect(self.replacePath)
        self.browseButton.clicked.connect(self.setPath)
        self.selectAllButton.clicked.connect(self.selectAllRead)
        self.pathBox.returnPressed.connect(self.replacePath)
        
    def getSelectedNodes(self):
        nodes = []
        selected = nuke.selectedNodes()
        if selected:
            for node in selected:
                if node.Class() == 'Read':
                    nodes.append(node)
        return nodes
    
    def setPath(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Directory',
                                                self.currentDirectory)
        if path:
            self.pathBox.setText(path)
            self.currentDirectory = path
    
    def getPath(self):
        path = self.pathBox.text()
        if not path:
            msgBox.showMessage(self, title='RRP',
                               msg='Sequence path not specified',
                               icon=QMessageBox.Information)
            return
        if not osp.exists(path):
            msgBox.showMessage(self, title='RRP',
                               msg='Specified path does not exist',
                               icon=QMessageBox.Information)
            return
        return path
    
    def selectAllRead(self):
        for node in nuke.allNodes():
            if node.Class() == 'Read':
                node.setSelected(True)
        
    def replacePath(self):
        nodes = self.getSelectedNodes()
        if not nodes:
            msgBox.showMessage(self, title='RRP',
                               msg='No Read node is currently selected',
                               icon=QMessageBox.Information)
            return
        path = self.getPath()
        if path:
            badNodesMapping = {}
            passes_dirs = os.listdir(path)
            if not passes_dirs:
                msgBox.showMessage(self, title='RRP',
                                   msg='No directory found in the specified path',
                                   icon=QMessageBox.Information)
                return
            for node in nodes:
                nodePath = node.knob('file').value()
                if nodePath:
                    basename3 = util.basename3(nodePath)
                    flag = False
                    for d in passes_dirs:
                        if basename3[:3].lower() == d[:3].lower():
                            tempPath = osp.join(path, d)
                            flag=True
                            break
                    if not flag:
                        badNodesMapping[node.name()] = 'No directory matches the name '+ util.splitPath(basename3)[0]
                        continue
                    passes = os.listdir(tempPath)
                    basenameMid = util.splitPath(basename3)[1]
                    basenameMidParts = basenameMid.split('_')
                    basenameMidLen = len(basenameMidParts)
                    flag = False
                    for pas in passes:
                        passParts = pas.split('_')
                        passLen = len(passParts)
                        if basenameMidLen == passLen:
                            if set(basenameMidParts[1:]) == set(passParts[1:]):
                                tempPath = osp.join(tempPath, pas)
                                flag = True
                    if not flag:
                        badNodesMapping[node.name()] = 'No directory matches the name '+ basenameMid
                        continue
                    fileNames = os.listdir(tempPath)
                    if not fileNames:
                        badNodesMapping[node.name()] = 'No file matches name '+ util.splitPath(basename3)[-1]
                        continue
                    newPath = osp.join(tempPath, fileNames[0])
                    if osp.exists(newPath):
                        node.knob('file').setValue(newPath.replace('\\', '/'))
                    else:
                        badNodesMapping[node.name()] = newPath
            if badNodesMapping:
                detail = 'Could not replace the following nodes\' paths'
                for node in badNodesMapping.keys():
                    detail += '\n\n'+node +'\n'+badNodesMapping[node]
                msgBox.showMessage(self, title='RRP',
                                   msg='System could not find some paths',
                                   icon=QMessageBox.Information,
                                   details=detail)
import re
import os
import os.path as osp
from PyQt4.QtGui import QApplication, QMessageBox, QFileDialog, qApp
from PyQt4 import uic
import msgBox
reload(msgBox)
import qutil
reload(qutil)
import nuke
import appUsageApp
import json

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

conf = {}
conf['lastDirectory'] = osp.expanduser('~')
confPath = osp.join(osp.expanduser('~'), '.nuke', 'rrp.json')

def readConf():
    global conf
    try:
        with open(confPath) as fp:
            conf = json.load(fp)
    except:
        pass

def writeConf():
    try:
        with open(confPath, 'w') as fp:
            json.dump(conf, fp)
    except:
        pass

readConf()


Form, Base = uic.loadUiType(osp.join(uiPath, 'main.ui'))
class Window(Form, Base):
    def __init__(self, parent=QApplication.activeWindow()):
        super(Window, self).__init__(parent)
        self.setupUi(self)

        self.currentDirectory = conf.get('lastDirectory', '')
        self.pathBox.setText(self.currentDirectory)

        self.progressBar.hide()

        self.replaceButton.clicked.connect(self.replacePath)
        self.browseButton.clicked.connect(self.setPath)
        self.selectAllButton.clicked.connect(self.selectAllRead)
        self.pathBox.returnPressed.connect(self.replacePath)
        self.rtdButton.mousePressEvent = lambda event: self.rtdButton.setStyleSheet('background-color: #5E2612')
        self.rtdButton.mouseReleaseEvent = lambda event: self.rtd()
        self.selectAllButton.hide()
        
        appUsageApp.updateDatabase('replaceReadPath')

    def rtd(self):
        self.rtdButton.setStyleSheet('background-color: darkRed')
        import redToDefault
        reload(redToDefault)
        redToDefault.change()
        self.statusBar().showMessage('Converted to default successfully', 2000)

    def closeEvent(self, event):
        self.deleteLater()
        del self

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
            conf['lastDirectory'] = path
            writeConf()

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

    def showProgressBar(self, maxVal=0):
        self.progressBar.show()
        self.progressBar.setMaximum(maxVal)
        qApp.processEvents()

    def hideProgressBar(self):
        self.progressBar.hide()
        self.progressBar.setValue(0)
        qApp.processEvents()

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
            self.showProgressBar(len(nodes))
            count = 1
            for node in nodes:
                nodePath = node.knob('file').value()
                if nodePath:
                    nodeName = node.name()
                    basename3 = qutil.basename3(nodePath)
                    basename3Parts = qutil.splitPath(basename3)
                    flag = False
                    for d in passes_dirs:
                        if basename3[:3].lower() == d[:3].lower():
                            tempPath = osp.join(path, d)
                            flag=True
                            break
                    if not flag:
                        badNodesMapping[nodeName] = 'No directory matches the name '+ osp.join(path, basename3Parts[0])
                        continue
                    passes = os.listdir(tempPath)
                    basenameMid = basename3Parts[1]
                    basenameMidParts = basenameMid.split('_')

                    # check if the basename3Parts[0] is in basename3Parts[1]
                    parentDirInBasename3 = False
                    if basename3Parts[0][:3].lower() == basenameMidParts[0][:3].lower():
                        parentDirInBasename3 =True
                    flag = False
                    for pas in passes:
                        passParts = pas.split('_')

                        # check if the parent directory name of pass directory is in pass name
                        parentDirInPass = False
                        if osp.basename(tempPath)[:3].lower() == passParts[0][:3].lower():
                            parentDirInPass = True

                        # handle the case when there is no parent directory name in pass directory name
                        start1 = 1 if parentDirInBasename3 else 0
                        start2 = 1 if parentDirInPass else 0

                        # handle the case when the parent directory is combination of two words joined with a underscore
                        if parentDirInBasename3 and len(basename3Parts[0].split('_')) > 1:
                            start1 += 1
                        if parentDirInPass:
                            if '_'.join(passParts[:2]).lower() == osp.basename(tempPath).lower():
                                start2 += 1
                        if set([tname.lower() for tname in basenameMidParts[start1:]]) == set([tname2.lower() for tname2 in passParts[start2:]]):
                            tempPath = osp.join(tempPath, pas)
                            flag = True
                    if not flag:
                        badNodesMapping[nodeName] = 'No directory matches the name '+ osp.join(tempPath, basenameMid)
                        continue
                    fileNames = os.listdir(tempPath)
                    if not fileNames:
                        badNodesMapping[nodeName] = 'No file matches name '+ osp.join(tempPath, basename3Parts[-1])
                        continue
                    filename = fileNames[0]
                    if len(fileNames) > 1:
                        frames = []
                        for phile in fileNames:
                            try:
                                frames.append(re.search('\d+\.', phile).group().strip('.'))
                            except:
                                pass
                        if frames:
                            frameNumber = frames[0]
                        else:
                            badNodesMapping[nodeName] = 'Frame number not found in the file name '+ osp.join(tempPath, filename)
                            continue
                        hashes = '#'*len(frameNumber)
                        newPath = osp.join(tempPath, filename.replace(frameNumber, hashes))
                        frames[:] = [int(frame) for frame in frames]
                        maxValue = max(frames); minValue = min(frames)
                        node.knob('first').setValue(minValue)
                        node.knob('last').setValue(maxValue)
                        node.knob('origlast').setValue(maxValue)
                        node.knob('origfirst').setValue(minValue)
                    else:
                        newPath = osp.join(tempPath, filename)
                    node.knob('file').setValue(newPath.replace('\\', '/'))
                    self.progressBar.setValue(count)
                    qApp.processEvents()
                    count += 1
            self.hideProgressBar()
            if badNodesMapping:
                numNodes = len(badNodesMapping)
                s = 's' if numNodes > 1 else ''
                detail = ''
                for node in badNodesMapping.keys():
                    detail += node +'\n'+badNodesMapping[node] + '\n\n'
                    nuke.toNode(node).knob('tile_color').setValue(0xff000000)
                msgBox.showMessage(self, title='RRP',
                                   msg='Could not replace the path for '+ str(numNodes) +' node'+s,
                                   icon=QMessageBox.Information,
                                   details=detail)

'''
Created on Jan 28, 2015

@author: qurban.ali
'''

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
import nukescripts
import appUsageApp
import json
import time

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

def getAnyReadPath():
    '''selects a random read node from the comp and returns it's path'''
    for node in nuke.allNodes('Read'):
        path = node.knob('file').value()
        if path and osp.exists(osp.dirname(path)):
            return qutil.dirname(path)
    return "\\\\renders\\Storage\\Projects\\external\\Al_Mansour_Season_02\\02_production"

conf = {}
conf['lastDirectory'] = getAnyReadPath()
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

__title__ = 'Read Node Tool'


Form, Base = uic.loadUiType(osp.join(uiPath, 'main.ui'))
class Window(Form, Base):
    def __init__(self, parent=QApplication.activeWindow()):
        super(Window, self).__init__(parent)
        self.setupUi(self)

        self.currentDirectory = conf.get('lastDirectory', '')
        self.pathBox.setText(self.currentDirectory)
        self.redNodes = []

        self.progressBar.hide()
        self.mainProgressBar.hide()

        self.replaceButton.clicked.connect(self.handleReplaceButton)
        self.browseButton.clicked.connect(self.setPath)
        self.pathBox.returnPressed.connect(self.handleReplaceButton)
        self.rtdButton.mousePressEvent = lambda event: self.rtdButton.setStyleSheet('background-color: #5E2612')
        self.rtdButton.mouseReleaseEvent = lambda event: self.rtd()
        self.reloadButton.clicked.connect(self.reloadSelected)
        self.createButton.toggled.connect(self.handleSeqButton)
        
        appUsageApp.updateDatabase('replaceReadPath')
        
    def handleSeqButton(self, val):
        self.replaceButton.setText('Create') if val else self.replaceButton.setText('Replace')

    def rtd(self):
        self.rtdButton.setStyleSheet('background-color: darkRed')
        import redToDefault
        reload(redToDefault)
        if redToDefault.change():
            self.statusBar().showMessage('Converted to default successfully', 2000)
            
    def reloadSelected(self):
        for node in self.getSelectedNodes():
            node.knob('reload').execute()

    def closeEvent(self, event):
        self.deleteLater()
        del self
    
    def createSeq(self):
        return self.createButton.isChecked()

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
            msgBox.showMessage(self, title=__title__,
                               msg='Sequence path not specified',
                               icon=QMessageBox.Information)
            return
        if not osp.exists(path):
            msgBox.showMessage(self, title=__title__,
                               msg='Specified path does not exist',
                               icon=QMessageBox.Information)
            return
        return path

    def showProgressBar(self, maxVal=0):
        self.progressBar.show()
        self.progressBar.setMaximum(maxVal)
        qApp.processEvents()

    def hideProgressBar(self):
        if not self.createSeq():
            self.progressBar.hide()
        self.progressBar.setValue(0)
        qApp.processEvents()
        
    def handleReplaceButton(self):
        if self.createSeq():
            self.createSequence()
        else: self.replacePath()
        
    def getSelectedNodes(self, typ='Read'):
        nodes = nuke.selectedNodes(typ)
        if not nodes:
            msg.showMessage(self, title=__title__,
                            msg='No "%s" found in the selection'%typ,
                            icon=QMessageBox.Information)
        return nodes
    
    def getShotPath(self):
        nodes = self.getSelectedNodes()
        if nodes:
            node = nodes[0]
            path = node.knob('file').value()
            if path:
                return qutil.dirname(path)

    def createSequence(self):
        del self.redNodes[:]
        bd_orig = self.getSelectedNodes(typ='BackdropNode')
        if bd_orig:
            if len(bd_orig) > 1:
                msgBox.showMessage(self, title=__title__,
                                   msg='More than one backdrops found in the selection',
                                   icon=QMessageBox.Information)
                return
            bd_orig = bd_orig[0]
            seqPath = self.getPath()
            currentShotPath = self.getShotPath() # shot path for selected backdrop
            if seqPath:
                shotNames = os.listdir(seqPath)
                shotNames.remove(osp.basename(osp.dirname(currentShotPath)))
                seqName = osp.dirname(seqPath)
                self.mainProgressBar.show()
                self.mainProgressBar.setMaximum(len(shotNames))
                for i, shotName in enumerate(shotNames):
                    seq_sh = '_'.join([seqName, shotName])
                    shotPath = osp.join(seqPath, shotName)
                    dirs = os.listdir(shotPath)
                    if dirs:
                        dirName = None
                        if len(dirs) > 1:
                            for directory in dirs:
                                if seq_sh in directory:
                                    dirName = directory
                                    break
                        else:
                            dirName = dirs[0]
                        if dirName:
                            shotFullPath = osp.join(shotPath, dirName)
                            nukescripts.node_copypaste()
                            bd = self.getSelectedNodes(typ='BackdropNode')[0]
                            bd_nodes = nuke.selectedNodes()
                            bd_nodes.remove(bd)
                            y = bd.ypos()
                            x = bd.xpos()
                            bd.setYpos(bd_orig.ypos())
                            bd.setXpos(bd_orig.xpos() + bd.screenWidth() + 50)
                            yDiff = bd.ypos() - y
                            xDiff = bd.xpos() - x
                            for node in bd_nodes:
                                node.setXYpos(node.xpos() + xDiff, node.ypos() + yDiff)
                            self.replacePath(shotFullPath)
                            bd_orig = bd
                    self.mainProgressBar.setValue(i+1)
                self.mainProgressBar.setValue(0)
                self.mainProgressBar.setMaximum(0)
                self.progressBar.hide()
                self.mainProgressBar.hide()
        if self.redNodes:
            msgBox.showMessage(self, title=__title__,
                               msg='Could not replace paths for some Read nodes. They are marked as Red',
                               icon=QMessageBox.Information,
                               btns=QMessageBox.Ok)
            del self.redNodes[:]

    def replacePath(self, path=None):
        nodes = self.getSelectedNodes()
        if not nodes:
            return
        if not path:
            path = self.getPath()
        if path:
            badNodesMapping = {}
            passes_dirs = os.listdir(path)
            if not passes_dirs and not self.createSeq():
                msgBox.showMessage(self, title=__title__,
                                   msg='No directory found in the specified path',
                                   icon=QMessageBox.Information)
                return
            self.showProgressBar(len(nodes))
            count = 1
            for node in nodes:
                nodePath = node.knob('file').value()
                if nodePath:
                    nodeName = node.name()
                    basename3 = qutil.basename(nodePath)
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

                    # check if the basename3Parts[0] is in basename3Parts[1] eg. Env is in Env_beauty
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
                if not self.createSeq():
                    msgBox.showMessage(self, title=__title__,
                                       msg='Could not replace the path for '+ str(numNodes) +' node'+s,
                                       icon=QMessageBox.Information,
                                       details=detail)
                else:
                    self.redNodes.extend([node for node in badNodesMapping.keys()])

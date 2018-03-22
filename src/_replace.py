'''
Created on Jan 28, 2015

@author: qurban.ali
'''

import re
import os
import os.path as osp
from PyQt4 import QtGui as gui
from PyQt4 import uic
import msgBox
import iutil
import nuke
import nukescripts
import appUsageApp
import json
import redToDefault
import cui
import createNukeMenu
import replaceCamera


reload(cui)
reload(redToDefault)
reload(iutil)
reload(msgBox)
reload(createNukeMenu)
reload(replaceCamera)


rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')


def getAnyReadPath():
    '''selects a random read node from the comp and returns it's path'''
    for node in nuke.allNodes('Read'):
        path = node.knob('file').value()
        if path and osp.exists(osp.dirname(path)):
            return iutil.dirname(path)
    return ("\\\\renders\\Storage\\Projects\\external\\"
            "Al_Mansour_Season_03\\02_production")


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

__title__ = 'Backdrop Tool'

Form, Base = uic.loadUiType(osp.join(uiPath, 'main.ui'))


class Window(Form, Base):
    def __init__(self, parent=gui.QApplication.activeWindow()):
        super(Window, self).__init__(parent)
        self.setupUi(self)

        self.currentDirectory = conf.get('lastDirectory', '')
        self.pathBox.setText(self.currentDirectory)
        self.redNodes = []
        self.shotsMenu = cui.MultiSelectComboBox(self, msg='--Select Shots--')
        self.buttonsLayout.insertWidget(2, self.shotsMenu)
        self.shotsMenu.hide()

        self.progressBar.hide()
        self.mainProgressBar.hide()

        self.replaceButton.clicked.connect(self.handleReplaceButton)
        self.browseButton.clicked.connect(self.setPath)
        self.pathBox.returnPressed.connect(self.handleReplaceButton)
        self.rtdButton.mousePressEvent = \
            lambda event: self.rtdButton.setStyleSheet(
                    'background-color: #5E2612')
        self.rtdButton.mouseReleaseEvent = lambda event: self.rtd()
        self.reloadButton.clicked.connect(self.reloadSelected)
        self.createButton.toggled.connect(self.handleSeqButton)
        self.pathBox.textChanged.connect(self.populateShots)
        self.populateShots()
        self.populateOtherBox()

        appUsageApp.updateDatabase('replaceReadPath')

    def populateOtherBox(self):
        layout = cui.FlowLayout(self.otherToolsBox)
        self.otherToolsBox.setLayout(layout)
        for key, val in createNukeMenu.nukeMenu.items():
            if key != __title__:
                btn = gui.QPushButton(key, self)
                layout.addWidget(btn)
                btn.clicked.connect(val[0])

    def populateShots(self):
        path = self.getPath(showMsg=False)
        if path and osp.exists(path):
            self.shotsMenu.addItems(sorted(os.listdir(path)))
        else:
            self.shotsMenu.clearItems()

    def getSelectedShots(self):
        return self.shotsMenu.getSelectedItems()

    def handleSeqButton(self, val):
        if val:
            self.replaceButton.setText('Create')
            self.shotsMenu.show()
        else:
            self.replaceButton.setText('Replace')
            self.shotsMenu.hide()

    def rtd(self):
        self.rtdButton.setStyleSheet('background-color: darkRed')
        if redToDefault.change():
            self.statusBar().showMessage('Converted to default successfully',
                                         2000)

    def reloadSelected(self):
        for node in self.getSelectedNodes():
            node.knob('reload').execute()

    def closeEvent(self, event):
        self.deleteLater()
        del self

    def createSeq(self):
        return self.createButton.isChecked()

    def replaceCameras(self):
        return self.cameraBox.isChecked()

    def setPath(self):
        path = gui.QFileDialog.getExistingDirectory(self, 'Select Directory',
                                                    self.currentDirectory)
        if path:
            self.pathBox.setText(path)
            self.currentDirectory = path
            conf['lastDirectory'] = path
            writeConf()

    def getPath(self, showMsg=True):
        path = self.pathBox.text()
        if showMsg:
            if not path:
                msgBox.showMessage(
                    self,
                    title=__title__,
                    msg='Sequence path not specified',
                    icon=gui.QMessageBox.Information)
                return
            if not osp.exists(path):
                msgBox.showMessage(
                    self,
                    title=__title__,
                    msg='Specified path does not exist',
                    icon=gui.QMessageBox.Information)
                return
        return path

    def showProgressBar(self, maxVal=0):
        self.progressBar.show()
        self.progressBar.setMaximum(maxVal)
        gui.qApp.processEvents()

    def hideProgressBar(self):
        if not self.createSeq():
            self.progressBar.hide()
        self.progressBar.setValue(0)
        gui.qApp.processEvents()

    def handleReplaceButton(self):
        if self.createSeq():
            self.createSequence()
        else:
            self.replacePath()

    def getSelectedNodes(self, typ='Read', msg=True):
        nodes = nuke.selectedNodes(typ)
        if not nodes:
            if msg:
                msgBox.showMessage(
                    self,
                    title=__title__,
                    msg='No "%s" found in the selection' % typ,
                    icon=gui.QMessageBox.Information)
        return nodes

    def getShotPath(self):
        nodes = self.getSelectedNodes()
        if nodes:
            node = nodes[0]
            path = node.knob('file').value()
            if path:
                return iutil.dirname(path)

    def createSequence(self):
        del self.redNodes[:]
        bd_orig = self.getSelectedNodes(typ='BackdropNode')
        if not bd_orig:
            return
        writeNode = self.getSelectedNodes('Write', msg=False)
        msg = ''
        if not writeNode:
            msg = 'Selected BackdropNode does not contain a Write node'
        if len(writeNode) > 1:
            msg = 'More than one write nodes found in the selection'
        if msg:
            btn = msgBox.showMessage(
                self,
                title=__title__,
                msg=msg,
                ques='Do you want to proceed?',
                icon=gui.QMessageBox.Information,
                btns=gui.QMessageBox.Yes | gui.QMessageBox.No)
            if btn == gui.QMessageBox.No:
                return
        if writeNode:
            writeNode = writeNode[0]
        if len(bd_orig) > 1:
            msgBox.showMessage(
                self,
                title=__title__,
                msg='More than one backdrops found in the selection',
                icon=gui.QMessageBox.Information)
            return
        bd_orig = bd_orig[0]
        seqPath = self.getPath()
        currentShotPath = self.getShotPath()  # shot path for selected backdrop
        errors = []
        if seqPath:
            shotNames = self.getSelectedShots()
            if not shotNames:
                shotNames = os.listdir(seqPath)

            try:
                shotNames.remove(osp.basename(osp.dirname(currentShotPath)))
            except ValueError:
                pass
            shotLen = len(shotNames)
            shotNames = sorted(shotNames)
            seqName = osp.basename(seqPath)
            self.mainProgressBar.show()
            self.mainProgressBar.setMaximum(shotLen)
            for i, shotName in enumerate(shotNames):
                seq_sh = '_'.join([seqName, shotName])
                shotPath = osp.join(seqPath, shotName)
                dirs = os.listdir(shotPath)
                if dirs:
                    dirName = None
                    if len(dirs) > 1:
                        for d in dirs:
                            if seq_sh in d or d == 'renders':
                                if d == 'renders':
                                    seq_sh = shotName
                                dirName = d
                                break
                    else:
                        dirName = dirs[0]
                    if dirName:
                        shotFullPath = osp.join(shotPath, dirName)
                        nukescripts.node_copypaste()
                        bd = self.getSelectedNodes(typ='BackdropNode')[0]
                        bd.knob('label').setValue(seq_sh)
                        bd_nodes = nuke.selectedNodes()
                        bd_nodes.remove(bd)
                        y = bd.ypos()
                        x = bd.xpos()
                        bd.setYpos(bd_orig.ypos())
                        bd.setXpos(bd_orig.xpos() + bd.screenWidth() + 50)
                        yDiff = bd.ypos() - y
                        xDiff = bd.xpos() - x
                        for node in bd_nodes:
                            node.setXYpos(node.xpos() + xDiff,
                                          node.ypos() + yDiff)
                        if writeNode:
                            outputPath = writeNode.knob('file').getValue()
                            if outputPath:
                                outputPath = iutil.dirname(outputPath, depth=2)
                                seqName = osp.basename(outputPath)
                                outputPath = osp.join(
                                        outputPath, seq_sh,
                                        seq_sh + '.%04d.jpg').replace(
                                                '\\', '/')
                                writeNode = self.getSelectedNodes('Write')[0]
                                writeNode.knob('file').setValue(outputPath)
                                try:
                                    iutil.mkdirr(osp.dirname(outputPath))
                                except:
                                    pass
                        redToDefault.change(msg=False)
                        self.replacePath(shotFullPath)
                        bd_orig = bd
                        shotLen -= 1
                    else:
                        errors.append(
                            'Could not find shot directory in %s' % shotPath)
                else:
                    errors.append('No directory found in %s' % shotPath)
                self.mainProgressBar.setValue(i + 1)
            self.mainProgressBar.setValue(0)
            self.mainProgressBar.setMaximum(0)
            self.progressBar.hide()
            self.mainProgressBar.hide()
        else:
            msgBox.showMessage(
                self,
                title=__title__,
                msg='No BackdropNode found in the selection',
                icon=gui.QMessageBox.Information)
            return
        if errors:
            details = '\n\n'.join(errors)
            msgBox.showMessage(
                self,
                title=__title__,
                msg='Could not create comps for %s shots' % shotLen,
                details=details,
                icon=gui.QMessageBox.Information)
        if self.redNodes:
            msgBox.showMessage(
                self,
                title=__title__,
                msg=('Could not replace paths for some Read nodes. They are '
                     'marked as Red'),
                icon=gui.QMessageBox.Information)
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
                msgBox.showMessage(
                    self,
                    title=__title__,
                    msg='No directory found in the specified path',
                    icon=gui.QMessageBox.Information)
                return
            self.showProgressBar(len(nodes))
            count = 1

            for node in nodes:
                nodePath = node.knob('file').value()

                if nodePath:
                    nodeName = node.name()
                    basename3 = iutil.basename(nodePath)
                    basename3Parts = iutil.splitPath(basename3)

                    if self.exactMatchButton.isChecked():
                        tempPath = osp.dirname(osp.join(path, basename3))
                        if not osp.exists(tempPath):
                            badNodesMapping[nodeName] = (
                                    'No directory matches name %s' % tempPath)
                            continue
                        fileNames = os.listdir(tempPath)
                    else:
                        flag = False
                        for d in passes_dirs:
                            if basename3[:3].lower() == d[:3].lower():
                                tempPath = osp.join(path, d)
                                flag = True
                                break
                        if not flag:
                            badNodesMapping[nodeName] = (
                                    'No directory matches the name ' +
                                    osp.join(path, basename3Parts[0]))
                            continue
                        passes = os.listdir(tempPath)
                        basenameMid = basename3Parts[1]
                        basenameMidParts = basenameMid.split('_')

                        # check if the basename3Parts[0] is in
                        # basename3Parts[1] eg. Env is in Env_beauty
                        parentDirInBasename3 = False
                        if basename3Parts[0][:3].lower() == basenameMidParts[
                                0][:3].lower():
                            parentDirInBasename3 = True
                        flag = False

                        for pas in passes:
                            passParts = pas.split('_')

                            # check if the parent directory name of pass
                            # directory is in pass name
                            parentDirInPass = False
                            if osp.basename(tempPath)[:3].lower() == passParts[
                                    0][:3].lower():
                                parentDirInPass = True

                            # handle the case when there is no parent directory
                            # name in pass directory name
                            start1 = 1 if parentDirInBasename3 else 0
                            start2 = 1 if parentDirInPass else 0

                            # handle the case when the parent directory is
                            # combination of two words joined with a underscore
                            if parentDirInBasename3 and len(
                                    basename3Parts[0].split('_')) > 1:
                                start1 += 1
                            if parentDirInPass:
                                if '_'.join(passParts[:2]).lower(
                                ) == osp.basename(tempPath).lower():
                                    start2 += 1

                            if set([
                                    tname.lower()
                                    for tname in basenameMidParts[start1:]
                            ]) == set([
                                    tname2.lower()
                                    for tname2 in passParts[start2:]
                            ]):
                                tempPath = osp.join(tempPath, pas)
                                flag = True

                        if not flag:
                            badNodesMapping[nodeName] = (
                                    'No directory matches the name ' +
                                    osp.join(tempPath, basenameMid))
                            continue
                        fileNames = os.listdir(tempPath)

                    if not fileNames:
                        badNodesMapping[nodeName] = 'No file matches name ' + \
                            osp.join(tempPath, basename3Parts[-1])
                        continue

                    filename = fileNames[0]
                    if len(fileNames) > 1:
                        frames = []
                        for phile in fileNames:
                            try:
                                frames.append(
                                    re.search('\d+\.', phile).group().strip(
                                        '.'))
                            except:
                                pass
                        if frames:
                            frameNumber = frames[0]
                        else:
                            badNodesMapping[nodeName] = (
                                'Frame number not found in the file name ' +
                                osp.join(tempPath, filename))
                            continue

                        hashes = '#' * len(frameNumber)
                        newPath = osp.join(tempPath,
                                           filename.replace(
                                               frameNumber, hashes))
                        frames[:] = [int(frame) for frame in frames]
                        maxValue = max(frames)
                        minValue = min(frames)
                        node.knob('first').setValue(minValue)
                        node.knob('last').setValue(maxValue)
                        node.knob('origlast').setValue(maxValue)
                        node.knob('origfirst').setValue(minValue)
                    else:
                        newPath = osp.join(tempPath, filename)
                    node.knob('file').setValue(newPath.replace('\\', '/'))
                    self.progressBar.setValue(count)
                    gui.qApp.processEvents()
                    count += 1
            self.hideProgressBar()

            if badNodesMapping:
                numNodes = len(badNodesMapping)
                s = 's' if numNodes > 1 else ''
                detail = ''
                for node in badNodesMapping.keys():
                    detail += node + '\n' + badNodesMapping[node] + '\n\n'
                    nuke.toNode(node).knob('tile_color').setValue(0xff000000)
                if not self.createSeq():
                    msgBox.showMessage(
                        self,
                        title=__title__,
                        msg='Could not replace the path for ' + str(numNodes) +
                        ' node' + s,
                        icon=gui.QMessageBox.Information,
                        details=detail)
                else:
                    self.redNodes.extend(
                        [node for node in badNodesMapping.keys()])

            if self.replaceCameras():
                replaceCamera.replaceBackdropCameras(nodes,
                                                     not self.createSeq())

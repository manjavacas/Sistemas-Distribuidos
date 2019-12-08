#!/usr/bin/python3
# -*- coding: utf-8 -*-

'''
Orchestrator for the management of download requests
'''

# Libs
import sys
import Ice
import IceStorm
import json

Ice.loadSlice('trawlnet.ice')
import TrawlNet

__author__ = 'Antonio Manjavacas'
__license__ = 'GPL'


class Orchestrator(Ice.Application):
    '''
    Download request receiver
    '''

    def __init__(self):
        '''
        Class constructor
        '''
        self.files = {}
        self.orchestrators = []

    def get_topic_manager(self):
        '''
        Obtains topic manager
        '''
        key = 'IceStorm.TopicManager.Proxy'
        proxy = self.communicator().propertyToProxy(key)

        if proxy is None:
            print('[ORCHESTRATOR] Error: topic key not set')
            return None

        print('[ORCHESTRATOR] Using IceStorm in: {0}'.format(key))
        return IceStorm.TopicManagerPrx.checkedCast(proxy)
    
    def subscribe_to(self, topic, subscriber):
        '''
        Implements topic subscription
        '''
        topic_mgr = self.get_topic_manager()
        if not topic_mgr:
            raise RuntimeError('[ORCHESTRATOR] Error getting topic manager')

        topic_name = 'UpdateEvents'
        qos = {}

        try:
            topic = topic_mgr.retrieve(topic_name)
        except IceStorm.NoSuchTopic:
            topic = topic_mgr.create(topic_name)

        topic.subscribeAndGetPublisher(qos, subscriber)

    def run(self, argv):
        '''
        Run method
        '''
        broker = self.communicator()

        ######################## TASKER ########################
        servant_orchestrator = OrchestratorI()
        adapter = broker.createObjectAdapter("OrchestratorAdapter")
        orchestrator_proxy = adapter.addWithUUID(servant_orchestrator)

        # Show proxy
        print(orchestrator_proxy, flush=True)

        # Set class attributes
        downloader_proxy = broker.stringToProxy(argv[1])
        downloader = TrawlNet.DownloaderPrx.checkedCast(downloader_proxy)

        if not downloader:
            raise RuntimeError(
                '[ORCHESTRATOR] Error: invalid downloader proxy')

        servant_orchestrator.downloader = downloader
        servant_orchestrator.orchestrator = self

        ######################## UPDATER ########################
        servant_updater = UpdateEventI()
        servant_updater.orchestrator = self
        broker.createObjectAdapter('UpdaterAdapter')
        updater_subscriber = adapter.addWithUUID(servant_updater)

        self.subscribe_to('UpdateEvents', updater_subscriber)

        ######################## GREETER ########################
        # servant_greeter = OrchestratorEventI()
        # broker.createObjectAdapter('GreeterAdapter')   
        
        
        adapter.activate()
        self.shutdownOnInterrupt()
        broker.waitForShutdown()

        return 0


class OrchestratorEventI(TrawlNet.OrchestratorEvent):
    
    def __init__(self):
        raise NotImplementedError
    
    def hello(self):
        raise NotImplementedError


class OrchestratorI(TrawlNet.Orchestrator):
    '''
    Orchestrator servant
    '''

    def __init__(self):
        '''
        Class constructor
        '''
        self.downloader = None
        self.orchestrator = None
        self.announcer = None
        
    def announce(self, other):
        '''
        Announces to other orchestrator
        '''
        if other not in self.orchestrator.orchestrators:
            self.orchestrator.orchestrators.append(other)
            
        print('[ORCHESTRATOR] Hi rookie!')
        for file_hash in self.orchestrator.files:
            if file_hash not in other.files:
                other.files[file_hash] = self.orchestrator.files[file_hash]

    def downloadTask(self, url, current=None):
        '''
        Sends a download task to a downloader
        '''
        print(
            '[ORCHESTRATOR] Receives task {0}. Sending to downloader...'.format(url))

        file_data = self.downloader.addDownloadTask(url)

        return file_data

    def getFileList(self, current=None):
        '''
        Returns the list of available files
        '''
        file_list = []

        for file_hash in self.orchestrator.files:
            file_info = TrawlNet.FileInfo()
            file_info.hash = file_hash
            file_info.name = self.orchestrator.files[file_hash]
            file_list.append(file_info)

        return file_list


class UpdateEventI(TrawlNet.UpdateEvent):
    '''
    Class for publishing in UpdateEvents topic
    '''
    
    def __init__(self):
        '''
        Class constructor
        '''
        self.orchestrator = None

    def newFile(self, file_info, current=None):
        '''
        Updates list with new files
        '''
        if not self.orchestrator:
            raise RuntimeError('[UPDATER] Error getting orchestrator')

        if file_info.hash not in self.orchestrator.files:
            print('[UPDATER] New file named {0}, with hash = {1}'.format(
                file_info.name, file_info.hash))
            self.orchestrator.files[file_info.hash] = file_info.name

if __name__ == '__main__':

    orchestrator = Orchestrator()
    sys.exit(orchestrator.main(sys.argv))

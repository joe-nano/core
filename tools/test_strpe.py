#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, getopt
import time
import random
import shlex, subprocess
import re

processes = []
DEVNULL = open(os.devnull, 'wb')

SEED = 12345678

nPeers = nTrusted = nMalicious = 0

port = 60000
playerPort = 61000

LAST_ROUND_NUMBER = 0
Q = 100

def checkdir():
    if not os.path.exists("./strpe-testing"):
        os.mkdir("./strpe-testing")

def usage():
    print "args error"

def run(runStr, out = DEVNULL):
    proc = subprocess.Popen(shlex.split(runStr), stdout=out, stderr=out)
    processes.append(proc)

def killall():
    for proc in processes:
        proc.kill()

def runStream():
    run("/Applications/VLC.app/Contents/MacOS/VLC ../src/Big_Buck_Bunny_small.ogv --sout \"#duplicate{dst=standard{mux=ogg,dst=,access=http}}\"")
    time.sleep(1)

def runSplitter(trustedPeers, ds = False):
    if len(trustedPeers) == 0:
        trustedPeers.append("127.0.0.1:1234")
    tps = ""
    for p in trustedPeers:
        tps += "\"{0}\" ".format(p)
    prefix = ""
    if ds: prefix = "ds"
    run("../src/splitter.py --buffer_size 1024 --source_port 8080 --strpe{0} {1} --strpe_log strpe-testing/splitter.log".format(prefix, tps))
    time.sleep(1)

def runPeer(trusted = False, malicious = False, ds = False):
    global port
    global playerPort
    #run peer
    strpeds = ""
    if ds: strpeds = "--strpeds"
    runStr = "../src/peer.py --use_localhost --port {0} --player_port {1} {2}".format(port, playerPort, strpeds)
    if trusted and not ds:
        runStr += " --trusted --checkall"
    if malicious:
        runStr += " --malicious --on_off_ratio 25"
    if not malicious:
         runStr += " --strpe_log ./strpe-testing/peer{0}.log".format(port)
    run(runStr, open("strpe-testing/peer{0}.out".format(port), "w"))
    time.sleep(2)
    #run netcat
    run("nc 127.0.0.1 {0}".format(playerPort))
    port, playerPort = port + 1, playerPort + 1

def check(x):
    with open("./strpe-testing/splitter.log") as fh:
        for line in fh:
            pass
        result = re.match("(\d*.\d*)\t(\d*)\s(\d*).*", line)
        if result != None and int(result.group(3)) <= x:
            return True
    return False

def initializeTeam(nPeers, nTrusted):
    print "running stream"
    runStream()

    print "running splitter"
    runSplitter([], True)

    print "running peers"

    for _ in range(nTrusted):
        print "trusted peer 127.0.0.1:{0}".format(port)
        runPeer(True, False, True)

    for _ in range(nPeers):
        print "well-intended peer 127.0.0.1:{0}".format(port)
        runPeer(False, False, True)

def churn():
    while checkForRounds():
        r = random.randint(1,100)
        if r <= 50:
            if r <= 25:
                print "malicious peer 127.0.0.1:{0}".format(port)
                runPeer(False, True, True)
            else:
                print "well-intended peer 127.0.0.1:{0}".format(port)
                runPeer(False, False, True)
        time.sleep(2)

def saveLastRound():
    global LAST_ROUND_NUMBER
    LAST_ROUND_NUMBER = findLastRound()

def findLastRound():
    with open("./strpe-testing/splitter.log") as fh:
        for line in fh:
            pass
        result = re.match("(\d*.\d*)\t(\d*)\s(\d*).*", line)
        if result != None:
             return int(result.group(2))

    return -1

def checkForRounds():
    currentRound = findLastRound()
    return currentRound - LAST_ROUND_NUMBER < Q

def main(args):
    random.seed(SEED)

    try:
        opts, args = getopt.getopt(args, "n:t:m:sq:")
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    ds = False
    nPeers = 10
    nTrusted = 1
    nMalicious = 0
    for opt, arg in opts:
        if opt == "-n":
            nPeers = int(arg)
        elif opt == "-t":
            nTrusted = int(arg)
        elif opt == "-m":
            nMalicious = int(arg)
        elif opt == "-s":
            ds = True

    print 'running with {0} peers ({1} trusted and {2} mal)'.format(nPeers, nTrusted, nMalicious)
    print 'strpeds=', ds
    nPeers = nPeers - nTrusted - nMalicious # for more friendly user input

    checkdir()

    initializeTeam(nPeers, nTrusted)

    time.sleep(10) # time for all peers buffering
    saveLastRound()

    print "simulating churn"
    churn()

    print "finish!"

    killall()
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        killall()
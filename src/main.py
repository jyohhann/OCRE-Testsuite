#!/usr/bin/env python3

from checker import *
from terraform import *
from kubern8s import *

import sys
try:
    import yaml
    import json
    from multiprocessing import Process, Queue
    import getopt
    import jsonschema
    import os
    import datetime
    import time
    import subprocess
    import string
    import re
    import shutil

except ModuleNotFoundError as ex:
    print(ex)
    sys.exit(1)

logger(
    "OCRE Cloud Benchmarking Validation Test Suite (CERN)",
    "#",
    "logging/header")

onlyTest = False
killResources = False
configs = ""
testsCatalog = ""
instanceDefinition = ""
extraInstanceConfig = ""
dependencies = ""
credentials = ""
totalCost = 0
procs = []
testsRoot = "tests/"
viaBackend = False
testsSharingCluster = ["s3Test", "dataRepatriationTest",
                       "perfsonarTest", "cpuBenchmarking", "dodasTest"]
customClustersTests = ["dlTest", "hpcTest"]
baseCWD = os.getcwd()
resultsExist = False
provDict = {
    'openstack': 'openstack_compute_instance_v2.kubenode[count.index].network[0].fixed_ip_v4',
    'exoscale': 'element(exoscale_compute.kubenode.*.ip_address, count.index)',
    'aws': 'element(aws_instance.kubenode.*.private_ip, count.index)',
    'azurerm': 'element(azurerm_network_interface.terraformnic.*.private_ip_address, count.index)',
    'google': 'element(google_compute_instance.kubenode.*.network_interface.0.network_ip, count.index)',
    'opentelekomcloud': '',
    'cloudstack': '',
    'cloudscale': '',
    'ibm': ''}
obtainCost = True
retry = None
publicRepo = "https://github.com/cern-it-efp/OCRE-Testsuite"


def initAndChecks():
    """Initial checks and initialization of variables.

    Returns:
        Array(str): Array containing the selected tests (strings)
    """

    global configs
    global testsCatalog
    global instanceDefinition
    global extraInstanceConfig
    global dependencies
    global credentials
    global obtainCost

    # --------File check
    if runCMD("terraform version", hideLogs=True) != 0:
        print("Terraform is not installed")
        stop(1)
    if runCMD("kubectl", hideLogs=True) != 0:
        print("kubectl is not installed")
        stop(1)

    configs = loadFile("../configurations/configs.yaml", required=True)
    testsCatalog = loadFile(
        "../configurations/testsCatalog.yaml", required=True)

    # SSH key checks: exists and permissions set to 600
    if os.path.isfile(configs["pathToKey"]) is False:
        print("Key file not found at '%s'" % configs["pathToKey"])
        stop(1)
    if "600" not in oct(os.stat(configs["pathToKey"]).st_mode & 0o777):
        print("Key permissions must be set to 600")
        stop(1)

    # disable schema validation for testing
    # try:
    #    jsonschema.validate(configs, loadFile("schemas/configs_sch.yaml"))
    # except jsonschema.exceptions.ValidationError as ex:
    #    print("Error validating configs.yaml: \n %s" % ex)
    #    stop(1)

    # try:
    #    jsonschema.validate(testsCatalog, loadFile("schemas/testsCatalog_sch.yaml"))
    # except jsonschema.exceptions.ValidationError as ex:
    #    print("Error validating testsCatalog.yaml: \n %s" % ex)
    #    stop(1)

    # this is now only required when not running on main clouds
    instanceDefinition = loadFile("../configurations/instanceDefinition")
    extraInstanceConfig = loadFile("../configurations/extraInstanceConfig")
    dependencies = loadFile("../configurations/dependencies")
    credentials = loadFile("../configurations/credentials")

    # --------General config checks
    # if "\"#NAME" not in instanceDefinition: # this has to be checked now only when not running on main clouds
    #    writeToFile("logging/header", "The placeholder comment for name at configs.yaml was not found!", True)
    #    stop(1)
    # if configs['providerName'] not in provDict:
    #    writeToFile("logging/header", "Provider '%s' not supported" % configs['providerName'], True)
    #    stop(1)

    # --------Tests config checks
    selected = []
    if testsCatalog["s3Test"]["run"] is True:
        selected.append("s3Test")
        obtainCost = checkCost(obtainCost,
                               configs["costCalculation"]["generalInstancePrice"])
        obtainCost = checkCost(
            obtainCost, configs["costCalculation"]["s3bucketPrice"])

    if testsCatalog["perfsonarTest"]["run"] is True:
        selected.append("perfsonarTest")
        obtainCost = checkCost(obtainCost,
                               configs["costCalculation"]["generalInstancePrice"])

    if testsCatalog["dataRepatriationTest"]["run"] is True:
        selected.append("dataRepatriationTest")
        obtainCost = checkCost(obtainCost,
                               configs["costCalculation"]["generalInstancePrice"])

    if testsCatalog["cpuBenchmarking"]["run"] is True:
        selected.append("cpuBenchmarking")
        obtainCost = checkCost(obtainCost,
                               configs["costCalculation"]["generalInstancePrice"])

    if testsCatalog["dlTest"]["run"] is True:
        selected.append("dlTest")
        obtainCost = checkCost(
            obtainCost, configs["costCalculation"]["GPUInstancePrice"])

    if testsCatalog["hpcTest"]["run"] is True:
        selected.append("hpcTest")
        obtainCost = checkCost(
            obtainCost, configs["costCalculation"]["GPUInstancePrice"])

    if testsCatalog["dodasTest"]["run"] is True:
        selected.append("dodasTest")
        obtainCost = checkCost(obtainCost,
                               configs["costCalculation"]["generalInstancePrice"])

    return selected


def s3Test():
    """Run S3 endpoints test."""

    res = False
    testCost = 0
    with open(testsRoot + "s3/raw/s3pod_raw.yaml", 'r') as infile:
        with open(testsRoot + "s3/s3pod.yaml", 'w') as outfile:
            outfile.write(
                infile.read().replace(
                    "ENDPOINT_PH",
                    testsCatalog["s3Test"]["endpoint"]) .replace(
                    "ACCESS_PH",
                    testsCatalog["s3Test"]["accessKey"]) .replace(
                    "SECRET_PH",
                    testsCatalog["s3Test"]["secretKey"]))

    start = time.time()  # create bucket
    if kubectl(
        Action.create,
        file=testsRoot +
        "s3/s3pod.yaml",
            toLog="logging/shared") != 0:
        writeFail(resDir, "s3Test.json",
                  "Error deploying s3pod.", "logging/shared")
    else:
        fetchResults(resDir, "s3pod:/home/s3_test.json",
                     "s3_test.json", "logging/shared")
        end = time.time()  # bucket deletion
        # cleanup
        writeToFile("logging/shared", "Cluster cleanup...", True)
        kubectl(Action.delete, type=Type.pod, name="s3pod")
        res = True
        if obtainCost is True:
            testCost = float(configs["costCalculation"]
                             ["s3bucketPrice"]) * (end - start) / 3600

    queue.put(({"test": "s3Test", "deployed": res}, testCost))


def dataRepatriationTest():
    """Run Data Repatriation Test -Exporting from cloud to Zenodo-."""

    res = False
    testCost = 0
    with open(testsRoot + "data_repatriation/raw/repatriation_pod_raw.yaml", 'r') as infile:
        with open(testsRoot + "data_repatriation/repatriation_pod.yaml", 'w') as outfile:
            outfile.write(infile.read().replace(
                "PROVIDER_PH", configs["providerName"]))

    if kubectl(
            Action.create,
            file="%sdata_repatriation/repatriation_pod.yaml" %
            testsRoot,
            toLog="logging/shared") != 0:
        writeFail(resDir, "data_repatriation_test.json",
                  "Error deploying data_repatriation pod.", "logging/shared")

    else:
        fetchResults(resDir, "repatriation-pod:/home/data_repatriation_test.json",
                     "data_repatriation_test.json", "logging/shared")
        # cleanup
        writeToFile("logging/shared", "Cluster cleanup...", True)
        kubectl(Action.delete, type=Type.pod, name="repatriation-pod")
        res = True

    queue.put(({"test": "dataRepatriationTest", "deployed": res}, testCost))


def cpuBenchmarking():
    """Run containerised CPU Benchmarking test."""

    res = False
    testCost = 0
    with open(testsRoot + "cpu_benchmarking/raw/cpu_benchmarking_pod_raw.yaml", 'r') as infile:
        with open(testsRoot + "cpu_benchmarking/cpu_benchmarking_pod.yaml", 'w') as outfile:
            outfile.write(infile.read().replace(
                "PROVIDER_PH", configs["providerName"]))

    if kubectl(
            Action.create,
            file="%scpu_benchmarking/cpu_benchmarking_pod.yaml" %
            testsRoot,
            toLog="logging/shared") != 0:
        writeFail(resDir, "cpu_benchmarking.json",
                  "Error deploying cpu_benchmarking_pod.", "logging/shared")
    else:
        fetchResults(
            resDir, "cpu-benchmarking-pod:/tmp/cern-benchmark_root/bmk_tmp/result_profile.json",
            "cpu_benchmarking.json",
            "logging/shared")
        # cleanup
        writeToFile("logging/shared", "Cluster cleanup...", True)
        kubectl(Action.delete, type=Type.pod, name="cpu-benchmarking-pod")
        res = True

    queue.put(({"test": "cpuBenchmarking", "deployed": res}, testCost))


def perfsonarTest():
    """Run Networking Performance test -perfSONAR toolkit-."""

    res = False
    testCost = 0
    endpoint = testsCatalog["perfsonarTest"]["endpoint"]
    if kubectl(
        Action.create,
        file=testsRoot +
        "perfsonar/ps_pod.yaml",
            toLog="logging/shared") != 0:
        writeFail(resDir, "perfsonar_results.json",
                  "Error deploying perfsonar pod.", "logging/shared")
    else:
        while kubectl(
            Action.cp,
            podPath="ps-pod:/tmp",
            localPath=testsRoot +
            "perfsonar/ps_test.py",
                fetch=False) != 0:
            pass  # Copy script to pod
        # Run copied script
        dependenciesCMD = "yum -y install python-dateutil python-requests"
        runScriptCMD = "python /tmp/ps_test.py --ep %s" % endpoint
        runOnPodCMD = "%s && %s" % (dependenciesCMD, runScriptCMD)
        if kubectl(Action.exec, name="ps-pod", cmd="%s" % runOnPodCMD) != 0:
            writeFail(resDir, "perfsonar_results.json",
                      "Error running script test on pod.", "logging/shared")
        else:
            fetchResults(resDir, "ps-pod:/tmp/perfsonar_results.json",
                         "perfsonar_results.json", "logging/shared")
            res = True
            # cleanup
            writeToFile("logging/shared", "Cluster cleanup...", True)
            kubectl(Action.delete, type=Type.pod, name="ps-pod")

    queue.put(({"test": "perfsonarTest", "deployed": res}, testCost))


def dodasTest():
    """Run DODAS test."""

    res = False
    testCost = 0
    if kubectl(
        Action.create,
        file=testsRoot +
        "dodas/dodas_pod.yaml",
            toLog="logging/shared") != 0:
        writeFail(resDir, "dodas_test.json",
                  "Error deploying DODAS pod.", "logging/shared")
    else:
        while kubectl(
                Action.cp,
                localPath="%sdodas/custom_entrypoint.sh" %
                testsRoot,
                podPath="dodas-pod:/CMSSW/CMSSW_9_4_0/src",
                fetch=False) != 0:
            pass  # Copy script to pod
        # Run copied script
        if kubectl(
                Action.exec,
                name="dodas-pod",
                cmd="sh /CMSSW/CMSSW_9_4_0/src/custom_entrypoint.sh") != 0:
            writeFail(resDir, "dodas_results.json",
                      "Error running script test on pod.", "logging/shared")
        else:
            fetchResults(resDir, "dodas-pod:/tmp/dodas_test.json",
                         "dodas_results.json", "logging/shared")
            res = True
            # cleanup
            writeToFile("logging/shared", "Cluster cleanup...", True)
            kubectl(Action.delete, type=Type.pod, name="dodas-pod")

    queue.put(({"test": "dodasTest", "deployed": res}, testCost))


def dlTest():
    """Run Deep Learning test -GAN training- on GPU nodes.

    Returns:
        None: In case of errors the function stops (returns None)
    """

    start = time.time()
    testCost = 0
    dl = testsCatalog["dlTest"]
    kubeconfig = "tests/dlTest/config"
    if onlyTest is False:
        prov, msg = terraformProvisionment(
            "dlTest", dl["nodes"], dl["flavor"], extraInstanceConfig, "logging/dlTest", configs, testsRoot, retry, instanceDefinition, credentials, dependencies, baseCWD, provDict)
        if prov is False:
            writeFail(resDir, "bb_train_history.json", msg, "logging/dlTest")
            return
    else:
        if not checkCluster("dlTest"):
            return  # Cluster not reachable, do not add cost for this test
    res = False

    #### This should be done at the end of this function #####################
    if obtainCost is True:
        testCost = ((time.time() - start) / 3600) * \
            configs["costCalculation"]["GPUInstancePrice"] * dl["nodes"]
    ##########################################################################

    ##########################################################################
    writeFail(resDir,
              "bb_train_history.json",
              "Unable to download training data: bucket endpoint not reachable.",
              "logging/dlTest")
    queue.put(({"test": "dlTest", "deployed": res}, testCost))
    return
    ##########################################################################

    # 1) Install the stuff needed for this test: device plugin yaml file
    # (contains driver too) and dl_stack.sh for kubeflow and mpi
    if checkDLsupport() is False and viaBackend is False:  # backend run assumes dl support
        writeToFile("logging/dlTest", "Preparing cluster for DL test...", True)
        masterIP = runCMD(
            "kubectl --kubeconfig %s get nodes -owide | grep master | awk '{print $6}'" %
            kubeconfig, read=True)
        script = "tests/dlTest/installKubeflow.sh"
        retries = 10
        if runCMD(
            "terraform/ssh_connect.sh --usr root --ip %s --file %s --retries %s" %
                (masterIP, script, retries)) != 0:
            writeFail(resDir,
                      "bb_train_history.json",
                      "Failed to prepare GPU/DL cluster (Kubeflow/Tensorflow/MPI)",
                      "logging/dlTest")
            return
    kubectl(Action.create, file=testsRoot +
            "dlTest/device_plugin.yaml", ignoreErr=True)
    kubectl(Action.create, file=testsRoot +
            "dlTest/pv-volume.yaml", ignoreErr=True)
    kubectl(Action.create, file=testsRoot +
            "dlTest/3dgan-datafile-lists-configmap.yaml", ignoreErr=True)

    # 2) Deploy the required files.
    if dl["nodes"] and isinstance(dl["nodes"],
                                  int) and dl["nodes"] > 1 and dl["nodes"]:
        nodesToUse = dl["nodes"]
    else:
        writeToFile(
            "logging/dlTest",
            "Provided value for 'nodes' not valid or unset, trying to use 5.",
            True)
        nodesToUse = 5
    with open(testsRoot + 'dlTest/train-mpi_3dGAN_raw.yaml', 'r') as inputfile:
        with open(testsRoot + "dlTest/train-mpi_3dGAN.yaml", 'w') as outfile:
            outfile.write(str(inputfile.read()).replace(
                "REP_PH", str(nodesToUse)))

    if kubectl(
        Action.create,
        file=testsRoot +
        "dlTest/train-mpi_3dGAN.yaml",
            toLog="logging/dlTest") != 0:
        writeFail(resDir, "bb_train_history.json",
                  "Error deploying train-mpi_3dGAN.", "logging/dlTest")
    elif runCMD(
            'kubectl describe pods | grep \"Insufficient nvidia.com/gpu\"', read=True):
        writeFail(resDir,
                  "bb_train_history.json",
                  "Cluster doesn't have enough GPU support. GPU flavor required.",
                  "logging/dlTest")
    else:
        fetchResults(resDir, "train-mpijob-worker-0:/mpi_learn/bb_train_history.json",
                     "bb_train_history.json", "logging/dlTest")
        res = True
    # cleanup
    writeToFile("logging/dlTest", "Cluster cleanup...", True)
    kubectl(Action.delete, type=Type.mpijob, name="train-mpijob")
    kubectl(Action.delete, type=Type.configmap, name="3dgan-datafile-lists")
    kubectl(Action.delete, type=Type.pv, name="pv-volume1")
    kubectl(Action.delete, type=Type.pv, name="pv-volume2")
    kubectl(Action.delete, type=Type.pv, name="pv-volume3")

    queue.put(({"test": "dlTest", "deployed": res}, testCost))


def hpcTest():
    """HPC test."""

    start = time.time()
    testCost = 0
    hpc = testsCatalog["hpcTest"]
    if onlyTest is False:
        prov, msg = terraformProvisionment(
            "hpcTest", hpc["nodes"], hpc["flavor"], None, "logging/hpcTest", configs, testsRoot, retry, instanceDefinition, credentials, dependencies, baseCWD, provDict)
        if prov is False:
            writeFail(resDir, "hpcTest_result.json", msg, "logging/hpcTest")
            return
    else:
        if not checkCluster("hpcTest"):
            return  # Cluster not reachable, do not add cost for this test
    writeToFile("logging/hpcTest", "(to be done)", True)
    res = False

    if obtainCost is True:
        testCost = ((time.time() - start) / 3600) * \
            configs["costCalculation"]["HPCInstancePrice"] * hpc["nodes"]

    queue.put(({"test": "hpcTest", "deployed": res}, testCost))
    return  # if errors: finish run


def sharedClusterTests(msgArr):
    """Runs the test that shared the general purpose cluster.

    Parameters:
        msgArray (Array<str>): Stuff to show on the banner. Contains the
                               tests to be deployed on the shared cluster.

    Returns:
        None: In case of errors the function stops (returns None)
    """

    start = time.time()
    sharedClusterProcs = []
    testCost = 0
    logger(msgArr, "=", "logging/shared")
    if onlyTest is False:
        # minus 1 because the array contains the string message
        prov, msg = terraformProvisionment(
            "shared", len(msgArr) - 1, None, None, "logging/shared", configs, testsRoot, retry, instanceDefinition, credentials, dependencies, baseCWD, provDict)
        if prov is False:
            writeFail(resDir, "sharedCluster_result.json",
                      msg, "logging/shared")
            return
    else:
        if not checkCluster("shared"):
            return  # Cluster not reachable, do not add cost for this test
    for test in msgArr[1:]:
        p = Process(target=eval(test))
        sharedClusterProcs.append(p)
        p.start()
    for p in sharedClusterProcs:
        p.join()
    if obtainCost is True:  # duration * instancePrice * numberOfInstances
        testCost = ((time.time() - start) / 3600) * \
            configs["costCalculation"]["generalInstancePrice"] * \
            len(msgArr[1:])
    queue.put((None, testCost))


# -----------------CMD OPTIONS--------------------------------------------
try:
    opts, args = getopt.getopt(
        sys.argv, "ul", ["--only-test", "--via-backend", "--retry"])
except getopt.GetoptError as err:
    writeToFile("logging/header", err, True)
    stop(1)
for arg in args[1:len(args)]:
    if arg == '--only-test':
        writeToFile("logging/header", "(ONLY TEST EXECUTION)", True)
        #runCMD("kubectl delete pods --all", hideLogs=True)
        onlyTest = True
    elif arg == '--retry':
        retry = True
    else:
        writeToFile("logging/header", "Bad option '%s'. Docs at %s " %
                    (arg, publicRepo), True)
        stop(1)

# -----------------CHECKS AND PREPARATION---------------------------------
if not initAndChecks():
    writeToFile("logging/header", "No tests selected, nothing to do!", True)
    stop(0)


# ----------------CREATE RESULTS FOLDER AND GENERAL FILE------------------
s3ResDirBase = configs["providerName"] + "/" + \
    str(datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S"))
resDir = "../results/%s/detailed" % s3ResDirBase
os.makedirs(resDir)
generalResults = {
    "testing": []
}

# ----------------RUN TESTS-----------------------------------------------
queue = Queue()
cluster = 1

msgArr = ["CLUSTER %s: (parallel running tests):" % (cluster)]
for test in testsSharingCluster:
    if testsCatalog[test]["run"] is True:
        msgArr.append(test)

if len(msgArr) > 1:
    p = Process(target=sharedClusterTests, args=(msgArr,))
    procs.append(p)
    p.start()
    cluster += 1

for test in customClustersTests:
    if testsCatalog[test]["run"] is True:
        logger("CLUSTER %s: %s" % (cluster, test), "=", "logging/%s" % test)
        p = Process(target=eval(test))
        procs.append(p)
        p.start()
        cluster += 1

for p in procs:  # All tests launched (functions run): wait for completion
    p.join()

while not queue.empty():
    entry, cost = queue.get()
    if entry:
        generalResults["testing"].append(entry)
    totalCost += cost

if checkResultsExist(resDir) is True:
    # ----------------CALCULATE COSTS-----------------------------------------
    if totalCost > 0:
        generalResults["estimatedCost"] = totalCost
    else:
        writeToFile(
            "logging/footer",
            "(Costs aren't correctly set: calculation will not be made)",
            True)

    # ----------------MANAGE RESULTS------------------------------------------
    with open("../results/" + s3ResDirBase + "/general.json", 'w') as outfile:
        json.dump(generalResults, outfile, indent=4, sort_keys=True)

    msg1 = "TESTING COMPLETED. Results at:"
    # No results push if local run (only ts-backend has AWS creds for this)
    if viaBackend is True:
        s3Endpoint = "https://s3.cern.ch"
        bucket = "s3://ts-results"
        pushResults = runCMD(
            "aws s3 cp --endpoint-url=%s %s %s/%s --recursive > /dev/null" %
            (s3Endpoint, "../results/" + s3ResDirBase, bucket, s3ResDirBase))
        runCMD("cp ../results/%s/general.json .. " % s3ResDirBase)
        if pushResults != 0:
            logger("S3 upload failed! Is 'awscli' installed and configured?",
                   "!", "logging/footer")
        else:
            logger([msg1, "S3 bucket"], "#", "logging/footer")
    else:
        logger([msg1, "results/" + s3ResDirBase], "#", "logging/footer")
else:
    shutil.rmtree("../results/" + s3ResDirBase, True)

stop(0)

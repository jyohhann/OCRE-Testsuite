#!/usr/bin/env python3

from tests.lib.checker import *
from tests.lib.terraform import *
from tests.lib.kubern8s import *

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

def validateYaml(provider):
    """ Validates configs.yaml and testsCatalog.yaml file against schemas.

    Parameters:
        provider (str): Provider on which the suite is being run. According to
                        it a specific YAML schema is used.
    """

    configsSchema = "schemas/configs_sch_%s.yaml" % provider if provider \
        in extraSupportedClouds else "schemas/configs_sch.yaml"

    try:
        jsonschema.validate(configs, loadFile(configsSchema))
    except jsonschema.exceptions.ValidationError as ex:
        print("Error validating configs.yaml: \n %s" % ex)
        stop(1)

    try:
        jsonschema.validate(
            testsCatalog,
            loadFile("schemas/testsCatalog_sch.yaml"))
    except jsonschema.exceptions.ValidationError as ex:
        print("Error validating testsCatalog.yaml: \n %s" % ex)
        stop(1)


def initAndChecks(configs, testsCatalog, instanceDefinition, 
                    extraInstanceConfig, dependencies, credentials, obtainCost):
    """Initial checks and initialization of variables.

    Returns:
        Array(str): Array containing the selected tests (strings)
    """

    # --------File check
    if runCMD("terraform version", hideLogs=True) != 0:
        print("Terraform is not installed")
        stop(1)
    if runCMD("kubectl", hideLogs=True) != 0:
        print("kubectl is not installed")
        stop(1)

    # SSH key checks: exists and permissions set to 600
    if os.path.isfile(configs["pathToKey"]) is False:
        print("Key file not found at '%s'" % configs["pathToKey"])
        stop(1)
    if "600" not in oct(os.stat(configs["pathToKey"]).st_mode & 0o777):
        print("Key permissions must be set to 600")
        stop(1)

    if configs['providerName'] not in provDict:
        writeToFile("logging/header", "Provider '%s' not supported" %
                    configs['providerName'], True)
        stop(1)

    # --------General config checks
    if configs['providerName'] not in extraSupportedClouds \
            and "NAME_PH" not in instanceDefinition:
        writeToFile(
            "logging/header",
            "ERROR: NAME_PH was not found in instanceDefinition file.",
            True)
        stop(1)

    # --------Tests config checks
    selected = []
    if testsCatalog["s3Test"]["run"] is True:
        selected.append("s3Test")
        obtainCost = checkCost(
            obtainCost,
            configs["costCalculation"]["generalInstancePrice"])
        obtainCost = checkCost(
            obtainCost, configs["costCalculation"]["s3bucketPrice"])

    if testsCatalog["perfsonarTest"]["run"] is True:
        selected.append("perfsonarTest")
        obtainCost = checkCost(
            obtainCost,
            configs["costCalculation"]["generalInstancePrice"])

    if testsCatalog["dataRepatriationTest"]["run"] is True:
        selected.append("dataRepatriationTest")
        obtainCost = checkCost(
            obtainCost,
            configs["costCalculation"]["generalInstancePrice"])

    if testsCatalog["cpuBenchmarking"]["run"] is True:
        selected.append("cpuBenchmarking")
        obtainCost = checkCost(
            obtainCost,
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
        obtainCost = checkCost(
            obtainCost,
            configs["costCalculation"]["generalInstancePrice"])

# -----------------CMD OPTIONS--------------------------------------------
try:
    opts, args = getopt.getopt(
        sys.argv, "ul", ["--only-test", "--via-backend", "--retry", "--s3Test", "--sharedClusterTest", "--perfSonarTest", 
                            "--hpcTest", "--dodasTest", "--dlTest", "--dataRepatriationTest", "--cpuBenchmarkingTest"])
except getopt.GetoptError as err:
    writeToFile("logging/header", err, True)
    stop(1)
for arg in args[1:len(args)]:
    if arg == '--only-test':
        writeToFile("logging/header", "(ONLY TEST EXECUTION)", True)
        #runCMD("kubectl delete pods --all", hideLogs=True)
        onlyTest = True
    elif arg == '--dataRepatriationTest':
        dataRepatriationTest = True
    elif arg == '--cpuBenchmarkingTest':
        cpuBenchmarkingTest = True
    elif arg == '--sharedClusterTest':
        sharedClusterTest = True
    elif arg == '--perfSonarTest':
        perfSonarTest = True
    elif arg == '--dodasTest':
        dodasTest = True
    elif arg == '--hpcTest':
        hpcTest = True
    elif arg == '--dlTest':
        dlTest = True
    elif arg == '--s3Test':
        s3Test = True
    elif arg == '--retry':
        retry = True
    else:
        writeToFile("logging/header", "Bad option '%s'. Docs at %s " %
                    (arg, publicRepo), True)
        stop(1)

# -----------------CONFIGURE PATHS ---------------------------------------
print("About to set paths to the config files.")
configs = loadFile("/var/jenkins_home/configurations/configs.yaml", required=True)
testsCatalog = loadFile(
        "/var/jenkins_home/configurations/testsCatalog.yaml", required=True)

provDict = loadFile("schemas/provDict.yaml",
                    required=True)["allProviders"]
extraSupportedClouds = loadFile("schemas/provDict.yaml",
                                required=True)["extraSupportedClouds"] 

publicRepo = "https://ocre-testsuite.rtfd.io"                                       

# TODO: instanceDefinition is now only required when not running on main clouds
instanceDefinition = loadFile("/var/jenkins_home/configurations/instanceDefinition")
extraInstanceConfig = loadFile("/var/jenkins_home/configurations/extraInstanceConfig")
dependencies = loadFile("/var/jenkins_home/configurations/dependencies")
credentials = loadFile("/var/jenkins_home/configurations/credentials")

# ----------------CREATE RESULTS FOLDER AND GENERAL FILE------------------
print("About to create results folder and general file.")
s3ResDirBase = configs["providerName"] + "/" + str(
    datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S"))
resDir = "../results/%s/detailed" % s3ResDirBase
os.makedirs(resDir)
generalResults = {
    "testing": []
}

# ----------------VALIDATION AND INIT RUN---------------------------------
# disabled schema validation for testing
# validateYaml(configs["providerName"], extraSupportedClouds)
print("About to run the required checks.")
initAndChecks(configs, testsCatalog, instanceDefinition, 
                extraInstanceConfig, dependencies, credentials, True)
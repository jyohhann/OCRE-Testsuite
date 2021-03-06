**THE SUITE HAS BEEN MOVED OVER TO** |eosc-repo| **. THIS REPOSITORY IS NO LONGER UPDATED**

.. |eosc-repo| raw:: html

  <a href="https://github.com/cern-it-efp/EOSC-Testsuite" target="_blank">cern-it-efp/EOSC-Testsuite</a>

*****

.. header-start

================================================
OCRE Test-Suite for cloud validation - CERN
================================================

This tool is intended to be used to test and validate commercial cloud services across the stack for research and education environments.
This Test-Suite is being used as a validation tool for commercial cloud services procurement in OCRE (Open Clouds for Research Environments) project sponsored by the European Commission.

More information at: http://ocre-project.eu.

.. header-end

Documentation
---------------------------------------------
Full documentation can be found at: `http://ocre-testsuite.rtfd.io <https://ocre-testsuite.readthedocs.io/en/latest/>`_

.. body

The test-suite executes four main steps:

1) Infrastructure provisioning: VMs are created using Terraform and then Kubernetes and Docker are installed on them to create several k8s cluster according to the selected tests.

2) Deploy the tests: Kubernetes resource definition files (YAML) are used to deploy the tests, either as single pods or deployments.

3) Harvest results: at the end of each test run a result file -written in JSON- is created. This file is harvested from the cluster and stored locally.

4) Through a verification system, the Test-Suite can also be triggered from a service running at CERN. In this case, results are then pushed to a S3 Bucket at CERN. (Under development)

The test set described below is based on the tests used in `Helix Nebula The Science Cloud <https://www.hnscicloud.eu/>`_ PCP project funded by the European Commission.

The developers would like to thank all test owners and contributors to this project.

**This test-suite has been tested on:**

+------------------------------+---------------------------------------------------------------------------------+
|OS on launcher machine        | Ubuntu, CentOS, CoreOS, Debian, RedHat, Fedora                                  |
+------------------------------+---------------------------------------------------------------------------------+
|OS running on provider's VMs  | CentOS7                                                                         |
+------------------------------+---------------------------------------------------------------------------------+
|Providers / clouds            | | AWS                                                                           |
|                              | | Google Cloud                                                                  |
|                              | | Microsoft Azure                                                               |
|                              | | Exoscale (CloudStack)                                                         |
|                              | | CERN Private Cloud (OpenStack)                                                |
|                              | | CloudFerro (OpenStack)                                                        |
|                              | | Cloudscale (OpenStack)                                                        |
|                              | | CloudStack                                                                    |
|                              | | OpenStack                                                                     |
+------------------------------+---------------------------------------------------------------------------------+

The test suite is being tested in several additional cloud providers. As tests are concluded the cloud providers names will be added in the table above.

Release notes
---------------------------------------------
(Note the versions are numbered with the date of the release: YEAR.MONTH)

``19.12``

-Project restructured.

-Improved support for running on Google, AWS, Azure, Exoscale, OpenStack and CloudStack.

``19.8``

-Parallel creation of clusters, with different flavors according to tests needs.

-New logging system to keep parallel running tests logs sorted.

-Restructured configuration: moved configuration files to */configurations* and created new files taking HCL code (terraform configuration code) to keep *configs.yaml* clean.

-Automated allowance of root ssh by copying open user's authorized_keys to root's ~/.ssh as well as *sshd_config* modification.

-Usage of Kubernetes API instead of Kubernetes CLI.

-For network test (perfSONAR), usage of API instead of pscheduler CLI.

-New test: Dynamic On Demand Analysis Service, provided by INFN.

-Added configurations validation with jsonschema.

-Created Docker image to run a Test-Suite launcher container: rapidly creates a ready to use Test-Suite launcher.

``19.4``

-New tests: perfsonar and cpu-benchmarking

``19.2``

-First release.

Contact
---------------------------------------------
For more information contact ignacio.peluaga.lozada AT cern.ch

License
---------------------------------------------
Copyright (C) CERN.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see `gnu.org/licenses <https://www.gnu.org/licenses/>`_.

.. body-end

.. image:: img/logo.jpg
   :height: 20px
   :width: 20px
   :scale: 20
   :target: https://home.cern/
   :alt: CERN logo

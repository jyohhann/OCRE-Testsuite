pipeline {
  agent any
  stages {
    stage('SCM') {
      steps{
        cleanWs()
        git(
           url: 'git@github.com:cern-it-efp/OCRE-Testsuite.git',
           credentialsId: 'Jakub',
           branch: "jenkins"
        )
      }
    }

    stage('Clean') {
      steps{
        dir ("$WORKSPACE/src/logging") {
        pwd() 
        sh "rm -f header killMe footer hpcTest dlTest shared logs"
        sh "touch logs run.txt"
        }
      }
    }

    stage('Validation') {
      steps{
        dir ("$WORKSPACE/src") {
        pwd() 
        sh "python3 -B validation.py --s3Test &> ../logs"
        }
      }
    }

    stage("Execution") {
      parallel {
        stage("logging") {
          steps{
              script{
                  dir ("$WORKSPACE/src/logging") {
                  sh '''
                      set +x
                        if [ -s header ]; then
                          cat header > logs; echo "" >> logs
                        fi
                        if [ -s shared ]; then
                          cat shared >> logs; echo "" >> logs
                        fi
                        if [ -s dlTest ]; then
                          cat dlTest >> logs; echo "" >> logs
                        fi
                        if [ -s hpcTest ]; then
                          cat hpcTest >> logs; echo "" >> logs
                        fi
                  '''
                    def output = sh(returnStdout: true, script: 'cat run.txt')
                    return !output.empty
                  }
            }
          }
        }
        
        stage('tests run') {
          steps{
            script{ 
            dir ("$WORKSPACE/src/logging") {
            sh """
                #!/bin/bash
                touch logs header shared dlTest hpcTest footer
                echo "Logs to the file logs"
            """     
              try { 
                  dir ("$WORKSPACE/src") {
                  //sh "python3 -B main.py &> ../logs"
                  }
              } catch(Exception err) {
                  print err
                  failure = true
                  currentBuild.result = 'FAILURE'
                }
              }
            }
          }
          post {
            always {
              sh """                        
              echo 'finished' >  $WORKSPACE/src/logging/run.txt
              cat $ld/footer >> $ld/logs
              cat $ld/logs
              """
            }
          }
          }
        }
      }
  }
}

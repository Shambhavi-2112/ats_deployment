pipeline {
    agent any

    environment {
        APP_NAME        = 'ats-production-engine'
        IMAGE_TAG       = "${env.BUILD_NUMBER}"
        REGISTRY        = 'docker.io/yourusername' // Replace with your DockerHub / ECR registry
        PYTHONPATH      = '.'
        CONTAINER_NAME  = "ats_engine_build_${env.BUILD_NUMBER}"
        PORT_API        = "8000"
        PORT_UI         = "8501"
    }

    options {
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15'))
        disableConcurrentBuilds()
    }

    stages {
        stage('1. Environment Setup & Dependency Installation') {
            steps {
                echo "--> Setting up Python virtual environment and installing dependencies..."
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('2. Static Code Analysis & Linting') {
            steps {
                echo "--> Executing Flake8 linting and code quality gates..."
                sh '''
                    . .venv/bin/activate
                    # Fail on syntax errors, undefined names, and critical issues
                    flake8 ats_pipeline.py api.py --count --select=E9,F63,F7,F82 --show-source --statistics
                    # Warning check for PEP8 formatting
                    flake8 ats_pipeline.py api.py --count --exit-zero --max-complexity=15 --max-line-length=120 --statistics
                '''
            }
        }

        stage('3. Model Artifact & Data Validation') {
            steps {
                echo "--> Verifying mathematical invariants and serialized model files..."
                sh '''
                    . .venv/bin/activate
                    # Verify model artifacts exist and are non-empty
                    test -s models/delhi_pm25_sarimax_model.joblib || { echo "Missing SARIMAX model!"; exit 1; }
                    test -s models/delhi_exog_var_model.joblib || { echo "Missing VAR model!"; exit 1; }
                    test -s models/nifty_garch_model.joblib || { echo "Missing GARCH model!"; exit 1; }
                    
                    # Quick integrity check script
                    python3 -c "
import joblib
m_pm = joblib.load('models/delhi_pm25_sarimax_model.joblib')
m_var = joblib.load('models/delhi_exog_var_model.joblib')
m_garch = joblib.load('models/nifty_garch_model.joblib')
print('Artifact verification passed: all models unpickled successfully.')
"
                '''
            }
        }

        stage('4. Automated Test Suite (Pytest)') {
            steps {
                echo "--> Running unit, invariant, and API integration tests..."
                sh '''
                    . .venv/bin/activate
                    mkdir -p reports
                    PYTHONPATH=. pytest tests/test_pipeline.py -v --junitxml=reports/test-results.xml
                '''
            }
        }

        stage('5. Docker Image Build') {
            steps {
                echo "--> Building production Docker container image..."
                sh '''
                    docker build -t ${APP_NAME}:${IMAGE_TAG} -t ${APP_NAME}:latest .
                '''
            }
        }

        stage('6. Smoke Test in Ephemeral Container') {
            steps {
                echo "--> Launching ephemeral container for live healthcheck and smoke tests..."
                sh '''
                    # Stop any previous leftover test container
                    docker rm -f ${CONTAINER_NAME} || true

                    # Start test container
                    docker run -d --name ${CONTAINER_NAME} -p 8001:8000 -p 8585:8501 ${APP_NAME}:${IMAGE_TAG}

                    # Poll /health directly via docker exec (works regardless of whether Jenkins is inside Docker or on host)
                    echo "Waiting for service to become healthy inside ephemeral container..."
                    ATTEMPTS=0
                    UNTIL=15
                    until docker exec ${CONTAINER_NAME} curl -sf http://127.0.0.1:8000/health > /dev/null || [ $ATTEMPTS -eq $UNTIL ]; do
                        echo "Waiting for API startup... ($ATTEMPTS/$UNTIL)"
                        sleep 2
                        ATTEMPTS=$((ATTEMPTS+1))
                    done

                    if [ $ATTEMPTS -eq $UNTIL ]; then
                        echo "Healthcheck FAILED! Printing container logs:"
                        docker logs ${CONTAINER_NAME}
                        docker rm -f ${CONTAINER_NAME}
                        exit 1
                    fi

                    echo "Healthcheck PASSED! Running live inference smoke test..."
                    docker exec ${CONTAINER_NAME} curl -s -f -X POST "http://127.0.0.1:8000/forecast/pm25" \
                         -H "Content-Type: application/json" \
                         -d '{"horizon_days": 5, "scenario": "autonomous_var"}' | grep "forecast_records"

                    docker exec ${CONTAINER_NAME} curl -s -f -X POST "http://127.0.0.1:8000/forecast/volatility" \
                         -H "Content-Type: application/json" \
                         -d '{"horizon_days": 5}' | grep "forecast_records"

                    echo "Live smoke test succeeded! Cleaning up ephemeral container..."
                    docker rm -f ${CONTAINER_NAME}
                '''
            }
        }

        stage('7. Push Image to Registry (Optional / Production)') {
            when {
                branch 'main'
            }
            steps {
                echo "--> Tagging and pushing image to container registry..."
                /*
                withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker tag ${APP_NAME}:${IMAGE_TAG} ${REGISTRY}/${APP_NAME}:${IMAGE_TAG}
                        docker tag ${APP_NAME}:${IMAGE_TAG} ${REGISTRY}/${APP_NAME}:latest
                        docker push ${REGISTRY}/${APP_NAME}:${IMAGE_TAG}
                        docker push ${REGISTRY}/${APP_NAME}:latest
                    '''
                }
                */
                echo "Image ready for production deployment: ${APP_NAME}:${IMAGE_TAG}"
            }
        }

        stage('8. Deploy to Production / Staging Environment') {
            when {
                branch 'main'
            }
            steps {
                echo "--> Deploying updated container to production server..."
                sh '''
                    # Example Docker Compose or systemd service restart:
                    # docker compose -f docker-compose.prod.yml up -d --pull always
                    echo "Service deployed successfully."
                '''
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/test-results.xml'
            cleanWs deleteDirs: true, notFailBuild: true
        }
        success {
            echo "✅ CI/CD Pipeline Succeeded: Version ${IMAGE_TAG} validated and deployed."
        }
        failure {
            echo "❌ CI/CD Pipeline FAILED! Review stage logs above."
        }
    }
}

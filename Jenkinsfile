pipeline {
    agent any
    environment {
        PYTHON_PATH = 'C:\\Users\\oi\\AppData\\Local\\Programs\\Python\\Python313'
        PYTHON_SCRIPTS_PATH = 'C:\\Users\\oi\\AppData\\Local\\Programs\\Python\\Python313\\Scripts'
        
        PATH = "${env.PYTHON_PATH};${env.PYTHON_SCRIPTS_PATH};${env.PATH}"
    }

    stages {
        // Stage 1: Install Python dependencies
        stage('Install Dependencies') {
            steps {
                bat 'python -m pip install z3-solver pyyaml'
            }
        }

        // Stage 2: Run the Parsers
        stage('Parse Files') {
            steps {
                bat 'python tools/parser/routes_parser.py --files routes.js --output routes.json'
                bat 'python tools/parser/main_parser.py --compose docker-compose.yaml --openapi openapi.yml --output system_spec.json'
            }
        }

        // Stage 3: Run the Verification
        stage('Run HelioVerify') {
            steps {
                bat 'python tools/solver/main_solver.py --specs system_spec.json --routes routes.json'
            }
        }
    }

    post {
        always {
            echo 'Verification run finished.'
            deleteDir()
        }
    }
}
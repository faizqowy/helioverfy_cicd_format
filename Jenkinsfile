pipeline {
    agent any

    stages {
        // Stage 1: Install Python dependencies
        stage('Install Dependencies') {
            steps {
                sh 'pip install z3-solver pyyaml'
            }
        }

        // Stage 2: Run the Parsers
        stage('Parse Files') {
            steps {
                sh 'python tools/parser/routes_parser.py --files $(find ./test_files -name "*.js") --output routes.json'
                sh 'python tools/parser/main_parser.py --compose ./test_files/docker-compose.yml --openapi ./test_files/openapi.yml --output system_spec.json'
            }
        }

        // Stage 3: Run the Verification
        stage('Run HelioVerify') {
            steps {
                sh 'python tools/solver/main_solver.py --specs system_spec.json --routes routes.json'
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
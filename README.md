# Vidoora – DevOps CI/CD on AWS EKS

Vidoora is a Flask-based web application packaged with Docker and deployed to Amazon EKS using a Jenkins CI/CD pipeline. This repository documents the application delivery workflow and the infrastructure/deployment configuration used in the project.

> **Portfolio note:** The application source code and Dockerfile are maintained in this repository's application root. Keep your existing working `app.py`, templates, static files, requirements files and Dockerfile. The infrastructure examples in `terraform/` are a clean reference implementation based on the architecture used during the project; compare them with your actual working Terraform configuration before applying them.

## Project architecture

```text
Developer
   |
   v
GitHub (main branch)
   |
   v
Jenkins pipeline
   |-- Checkout source
   |-- Install Python dependencies
   |-- SonarQube code analysis
   |-- Docker build
   |-- Trivy image scan
   |-- Push image to Amazon ECR
   |-- Terraform init / validate / plan / approval / apply
   |
   v
Amazon EKS
   |-- Kubernetes Deployment (Vidoora pods)
   |-- Kubernetes Service (LoadBalancer)
   |
   v
Application access through AWS Load Balancer
```

## Technology stack

| Area | Technology |
|---|---|
| Source control | Git, GitHub |
| CI/CD | Jenkins |
| Code quality | SonarQube |
| Containerization | Docker |
| Image security | Trivy |
| Container registry | Amazon ECR |
| Infrastructure as Code | Terraform |
| Cloud | AWS |
| Orchestration | Amazon EKS, Kubernetes |
| Application | Python / Flask |

## Repository layout

```text
vidoora/
├── app.py                       # Existing Flask application
├── Dockerfile                   # Existing application image build
├── requirements.txt             # Existing Python dependencies
├── requirements-prod.txt        # Existing production dependencies (if used)
├── templates/                   # Existing Flask templates
├── static/                      # Existing static assets
├── Jenkinsfile                  # CI/CD pipeline
├── sonar-project.properties     # SonarQube project configuration
├── .dockerignore
├── .gitignore
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
├── terraform/
│   ├── README.md
│   ├── versions.tf
│   ├── providers.tf
│   ├── variables.tf
│   ├── main.tf
│   └── outputs.tf
└── docs/
    └── deployment-runbook.md
```

## Prerequisites

- An AWS account and an IAM role/user with appropriately scoped permissions.
- AWS CLI configured on the Jenkins agent.
- Jenkins with Git, Pipeline, Docker Pipeline and SonarQube Scanner integrations configured as required.
- Docker, Terraform, Trivy, Python 3 and Git installed on the Jenkins agent.
- SonarQube server configured in Jenkins as `mysonar`; scanner tool configured as `mysonar` (change the names in the Jenkinsfile if your Jenkins configuration differs).
- An existing ECR repository named `vidoora` in `ap-south-1`.
- An EKS cluster and node group, or use the Terraform reference configuration after reviewing it.
- `kubectl` installed and a Jenkins identity authorized to access the EKS cluster.

## Configuration before running Jenkins

1. Update the `AWS_ACCOUNT_ID` value in the Jenkinsfile or provide it as a Jenkins environment/credential.
2. Confirm the ECR repository exists in `ap-south-1`.
3. Configure AWS credentials for the Jenkins agent using an EC2 instance profile or Jenkins AWS credentials. Prefer an instance profile/role over static access keys.
4. Confirm the Jenkins agent can reach the SonarQube server and AWS APIs.
5. Set the correct Terraform directory and backend configuration.
6. Confirm the Kubernetes cluster name, region and namespace.
7. Review the Terraform plan and approve only the expected changes.

## Pipeline stages

1. **Clean workspace** – removes files from the previous build.
2. **Checkout** – clones the configured GitHub branch.
3. **Install dependencies** – creates a Python virtual environment and installs requirements.
4. **Code quality** – runs SonarQube analysis.
5. **Docker build** – builds `vidoora:latest`.
6. **Trivy scan** – scans the built image for known vulnerabilities.
7. **Push to ECR** – authenticates to ECR, tags and pushes the image.
8. **Terraform init / validate / plan** – initializes the backend and generates an execution plan.
9. **Manual approval** – pauses before infrastructure changes.
10. **Terraform apply** – applies the approved plan.
11. **Kubernetes deploy** – apply the Deployment and Service manifests (enable/add this stage after confirming Jenkins has kubeconfig access).

## Deploy the Kubernetes manifests manually

Run from a machine/agent with a working kubeconfig and EKS access:

```bash
aws eks update-kubeconfig --region ap-south-1 --name vidoora-eks
kubectl get nodes
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/vidoora
kubectl get pods
kubectl get svc vidoora-service
```

The Service uses `type: LoadBalancer`. AWS provisions a load balancer; wait until the `EXTERNAL-IP`/hostname is populated:

```bash
kubectl get svc vidoora-service --watch
```

## Useful troubleshooting commands

```bash
kubectl get nodes
kubectl get pods -A
kubectl get deployments
kubectl get svc
kubectl describe pod <pod-name>
kubectl logs deployment/vidoora --tail=100
kubectl rollout status deployment/vidoora
kubectl get events --sort-by=.metadata.creationTimestamp
aws eks describe-cluster --name vidoora-eks --region ap-south-1
aws eks list-nodegroups --cluster-name vidoora-eks --region ap-south-1
aws eks describe-nodegroup --cluster-name vidoora-eks --nodegroup-name vidoora-node-group --region ap-south-1
```

## Important application/database note

During the project, the Flask app returned HTTP 500 because SQLite reported `no such table: provider_profile`. The container had an empty SQLite database file. The app's `init-db` Flask CLI command was used to create tables. For a production deployment, do **not** rely on a pod-local SQLite file: pod filesystems are ephemeral and each replica can have a different database. Use a managed persistent database such as Amazon RDS, configure `DATABASE_URL` through Kubernetes Secrets, and run schema migrations as a controlled deployment step.

## Security and files that must NOT be committed

Never commit:
- `.env` files containing credentials or database passwords.
- AWS access keys, secret keys, session tokens or private keys.
- `terraform.tfstate`, `terraform.tfstate.backup`, `.terraform/` or saved plan files.
- Jenkins credentials, kubeconfig files, certificates or tokens.
- Real production database files or customer data.

The `.gitignore` in this repository excludes common sensitive/generated files. Review `git status` before every push.

## Terraform state

The project used an S3 remote backend with bucket versioning, server-side encryption and public-access blocking. The backend bucket name observed during the project was `vidoora-terraform-state-834283091445`, with key `vidoora/terraform.tfstate` in `ap-south-1`. Backend settings are account-specific; verify that this bucket is still yours and exists before using the example backend configuration. The Terraform reference files require `cluster_role_arn` and `node_role_arn`; populate them in an untracked `terraform/terraform.tfvars` file using `terraform/terraform.tfvars.example` as a guide.

Terraform state contains infrastructure metadata and can expose sensitive values. Keep it private in S3; never upload it to GitHub.

## Cleanup warning

`terraform destroy` deletes infrastructure and can cause downtime/data loss and incur cleanup complications when Kubernetes-created load balancers still exist. Delete Kubernetes Services of type `LoadBalancer` first, wait for AWS load balancers and ENIs to be removed, then review a Terraform destroy plan. Do not run destroy against a shared/production account without explicit approval.

## Recruiter overview

This project demonstrates an end-to-end DevOps workflow: source control, automated quality analysis, container build and security scanning, image publishing, Infrastructure as Code, Kubernetes deployment and troubleshooting. The repository includes the pipeline, deployment manifests, Terraform reference files and operational runbook.

## Author

**Afroz Babu**  
GitHub: https://github.com/afrozbabu1111  
Project repository: https://github.com/afrozbabu1111/vidoora

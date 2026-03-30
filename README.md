# culture-escrow-pg17

Client-server productization repo for pg17 (Escrow Holder Acknowledgment) workflow.

## Scope
- pg17 fill engine
- API service
- client UI
- docs-first delivery

## Demo Quick Start
```bash
cd /Users/wu/workspace/culture-escrow-pg17
./scripts/run_demo.sh
```
Then open: `http://127.0.0.1:8788`

## Stable Local Run
See: `docs/09-运维/LOCAL_DEMO_RUNBOOK.md`

## Deployment Baseline
- Environment split guide: `docs/06-部署/ENV_SPLIT_STAGING_PROD.md`
- Runner script: `deploy/scripts/run_api.sh`

## Engine Dependencies
Install deployable engine dependencies with:

```bash
./deploy/scripts/install_engine_deps.sh
```

## EC2 Auto Deploy
- Workflow: `.github/workflows/deploy-ec2.yml`
- Remote script: `deploy/scripts/deploy_prod.sh`

## Auto Deploy Options
- Preferred: `.github/workflows/deploy-self-hosted.yml` (self-hosted runner on EC2)
- Fallback: `.github/workflows/deploy-ec2.yml` (SSH-based)
